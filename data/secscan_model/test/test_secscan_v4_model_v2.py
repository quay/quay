import logging
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest

from app import app as application
from app import instance_keys, storage
from data.database import IndexerVersion, IndexStatus, Manifest, ManifestSecurityStatus
from data.registry_model import registry_model
from data.secscan_model.datatypes import ScanLookupStatus
from data.secscan_model.secscan_v4_model import IndexReportState
from data.secscan_model.secscan_v4_model_v2 import V4SecurityScanner2
from test.fixtures import *
from util.secscan.v4.api import (
    APIRequestFailure,
    InvalidContentSent,
    LayerTooLargeException,
)

logger = logging.getLogger(__name__)


@pytest.fixture()
def set_secscan_config():
    application.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"
    application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 86400
    application.config["SECURITY_SCANNER_V4_IN_PROGRESS_TIMEOUT"] = 1800


@pytest.fixture()
def v2_scanner(set_secscan_config):
    """Create a V4SecurityScanner2 instance with mocked API."""
    scanner = V4SecurityScanner2(application, instance_keys, storage)
    scanner._secscan_api = mock.Mock()
    scanner._secscan_api.state.return_value = {"state": "test_state"}
    scanner._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}
    scanner._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "test_state",
    )
    return scanner


def test_perform_indexing_not_indexed(initialized_db, v2_scanner):
    """Test indexing manifests that have never been scanned."""
    manifest_count = Manifest.select().count()

    # Perform indexing
    result = v2_scanner.perform_indexing()

    # V2 returns None (no ScanToken)
    assert result is None

    # All manifests should be indexed
    assert ManifestSecurityStatus.select().count() == manifest_count
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.COMPLETED
        assert mss.indexer_hash == "test_state"
        assert mss.last_indexed is not None


def test_perform_indexing_stale_in_progress(initialized_db, v2_scanner):
    """Test crash recovery: reclaim manifests stuck IN_PROGRESS."""
    manifest = Manifest.select().first()
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=1800 + 300)  # Past 1800s timeout

    ManifestSecurityStatus.create(
        manifest=manifest,
        repository=manifest.repository,
        index_status=IndexStatus.IN_PROGRESS,
        indexer_hash="old",
        indexer_version=IndexerVersion.V4,
        last_indexed=stale_time,
        metadata_json={},
        error_json={},
    )

    # Perform indexing
    v2_scanner.perform_indexing()

    # Stale manifest should be reclaimed and completed
    mss = ManifestSecurityStatus.get(ManifestSecurityStatus.manifest == manifest)
    assert mss.index_status == IndexStatus.COMPLETED
    assert mss.indexer_hash == "test_state"
    assert str(mss.last_indexed) > str(stale_time)


def test_perform_indexing_failed_retry(initialized_db, v2_scanner):
    """Test retrying failed manifests after threshold."""
    manifest = Manifest.select().first()
    old_time = datetime.now(timezone.utc) - timedelta(days=2)  # Past reindex threshold

    ManifestSecurityStatus.create(
        manifest=manifest,
        repository=manifest.repository,
        index_status=IndexStatus.FAILED,
        indexer_hash="old",
        indexer_version=IndexerVersion.V4,
        last_indexed=old_time,
        metadata_json={},
        error_json={},
    )

    # Perform indexing
    v2_scanner.perform_indexing()

    # Failed manifest should be retried and completed
    mss = ManifestSecurityStatus.get(ManifestSecurityStatus.manifest == manifest)
    assert mss.index_status == IndexStatus.COMPLETED
    assert str(mss.last_indexed) > str(old_time)


def test_perform_indexing_api_failure(initialized_db, v2_scanner):
    """Test handling of Clair API failures."""
    v2_scanner._secscan_api.index.side_effect = APIRequestFailure("API error")

    # Perform indexing
    v2_scanner.perform_indexing()

    # Manifests should be marked as FAILED
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.FAILED


def test_perform_indexing_invalid_content(initialized_db, v2_scanner):
    """Test handling of invalid content errors."""
    v2_scanner._secscan_api.index.side_effect = InvalidContentSent("Invalid")

    # Perform indexing
    v2_scanner.perform_indexing()

    # Manifests should be marked as MANIFEST_UNSUPPORTED
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.MANIFEST_UNSUPPORTED


def test_perform_indexing_layer_too_large(initialized_db, v2_scanner):
    """Test handling of layer too large errors."""
    v2_scanner._secscan_api.index.side_effect = LayerTooLargeException("Too large")

    # Perform indexing
    v2_scanner.perform_indexing()

    # Manifests should be marked as MANIFEST_LAYER_TOO_LARGE
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.MANIFEST_LAYER_TOO_LARGE


def test_perform_indexing_index_error(initialized_db, v2_scanner):
    """Test handling of Clair returning Index_Error state."""
    v2_scanner._secscan_api.index.return_value = (
        {"err": "some error", "state": IndexReportState.Index_Error},
        "test_state",
    )

    # Perform indexing
    v2_scanner.perform_indexing()

    # Manifests should be marked as FAILED
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.FAILED


def test_mark_batch_in_progress_inserts_last_indexed(initialized_db, v2_scanner):
    """Test that _mark_batch_in_progress sets last_indexed for new rows."""
    manifest = Manifest.select().first()

    # Claim the manifest
    v2_scanner._mark_batch_in_progress([manifest])

    # Check that last_indexed was set
    mss = ManifestSecurityStatus.get(ManifestSecurityStatus.manifest == manifest)
    assert mss.last_indexed is not None
    assert mss.index_status == IndexStatus.IN_PROGRESS


def test_concurrent_indexing_batch_size(initialized_db, v2_scanner):
    """Test that batch_size parameter is respected."""
    batch_size = 5
    manifest_count = Manifest.select().count()

    # Perform indexing with small batch
    v2_scanner.perform_indexing(batch_size=batch_size)

    indexed_count = ManifestSecurityStatus.select().count()
    assert indexed_count == batch_size


def test_load_security_information_not_indexed(initialized_db, v2_scanner):
    """Test loading security info for manifest not yet indexed."""
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    result = v2_scanner.load_security_information(manifest)
    assert result.status == ScanLookupStatus.NOT_YET_INDEXED


def test_load_security_information_in_progress(initialized_db, v2_scanner):
    """Test loading security info for manifest currently being indexed."""
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        index_status=IndexStatus.IN_PROGRESS,
        indexer_hash="test",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
        error_json={},
    )

    result = v2_scanner.load_security_information(manifest)
    assert result.status == ScanLookupStatus.NOT_YET_INDEXED


def test_load_security_information_failed(initialized_db, v2_scanner):
    """Test loading security info for failed manifest."""
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        index_status=IndexStatus.FAILED,
        indexer_hash="test",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
        error_json={},
    )

    result = v2_scanner.load_security_information(manifest)
    assert result.status == ScanLookupStatus.FAILED_TO_INDEX


def test_load_security_information_unsupported(initialized_db, v2_scanner):
    """Test loading security info for unsupported manifest."""
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        index_status=IndexStatus.MANIFEST_UNSUPPORTED,
        indexer_hash="test",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
        error_json={},
    )

    result = v2_scanner.load_security_information(manifest)
    assert result.status == ScanLookupStatus.UNSUPPORTED_FOR_INDEXING


def test_load_security_information_layer_too_large(initialized_db, v2_scanner):
    """Test loading security info for manifest with layer too large."""
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        index_status=IndexStatus.MANIFEST_LAYER_TOO_LARGE,
        indexer_hash="test",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
        error_json={},
    )

    result = v2_scanner.load_security_information(manifest)
    assert result.status == ScanLookupStatus.MANIFEST_LAYER_TOO_LARGE


def test_garbage_collect_manifest_report_deletes(initialized_db, v2_scanner):
    """Test GC deletes report when manifest doesn't exist."""
    v2_scanner._secscan_api.delete.return_value = True

    result = v2_scanner.garbage_collect_manifest_report("sha256:nonexistent")

    # Should call delete and return True
    assert result is True
    v2_scanner._secscan_api.delete.assert_called_once_with("sha256:nonexistent")


def test_garbage_collect_manifest_report_manifest_exists(initialized_db, v2_scanner):
    """Test GC doesn't delete report when manifest still exists."""
    manifest = Manifest.select().first()

    result = v2_scanner.garbage_collect_manifest_report(manifest.digest)

    # Should not call delete and return None
    assert result is None
    v2_scanner._secscan_api.delete.assert_not_called()


def test_garbage_collect_manifest_report_api_failure(initialized_db, v2_scanner):
    """Test GC handles API failure gracefully."""
    v2_scanner._secscan_api.delete.side_effect = APIRequestFailure("API error")

    result = v2_scanner.garbage_collect_manifest_report("sha256:nonexistent")

    # Should handle exception and return None
    assert result is None


def test_perform_indexing_recent_manifests_noop(initialized_db, v2_scanner):
    """Test that perform_indexing_recent_manifests is a no-op in V2."""
    # Should not raise an exception
    v2_scanner.perform_indexing_recent_manifests()

    # Should not have indexed anything
    assert ManifestSecurityStatus.select().count() == 0


def test_reindex_query_respects_threshold(initialized_db, v2_scanner):
    """Test that reindex query respects reindex threshold."""
    manifest = Manifest.select().first()
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)  # Within 86400s threshold

    ManifestSecurityStatus.create(
        manifest=manifest,
        repository=manifest.repository,
        index_status=IndexStatus.COMPLETED,
        indexer_hash="old_hash",  # Different from current state
        indexer_version=IndexerVersion.V4,
        last_indexed=recent_time,
        metadata_json={},
        error_json={},
    )

    # Perform indexing
    v2_scanner.perform_indexing()

    # Should not reindex because it's within threshold
    mss = ManifestSecurityStatus.get(ManifestSecurityStatus.manifest == manifest)
    assert mss.indexer_hash == "old_hash"  # Not updated
    # last_indexed should remain unchanged (stored as string in SQLite with timezone-aware datetime)
    assert str(mss.last_indexed) == str(recent_time)


def test_none_report_handling(initialized_db, v2_scanner):
    """Test defensive handling of None report from Clair API."""
    # Mock to return (None, state) instead of raising exception
    v2_scanner._secscan_api.index.return_value = (None, "test_state")

    # Perform indexing
    v2_scanner.perform_indexing()

    # Should mark as FAILED
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.FAILED
