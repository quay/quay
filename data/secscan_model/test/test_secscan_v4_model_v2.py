import logging
from datetime import datetime, timedelta
from unittest import mock

import pytest
from peewee import fn

from app import app as application
from app import instance_keys, storage
from data.database import IndexerVersion, IndexStatus, Manifest, ManifestSecurityStatus
from data.registry_model import registry_model
from data.secscan_model.secscan_v4_model import IndexReportState
from data.secscan_model.secscan_v4_model_v2 import V4SecurityScannerV2
from test.fixtures import *

logger = logging.getLogger(__name__)


@pytest.fixture()
def set_secscan_config():
    application.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"


@pytest.fixture()
def scanner(set_secscan_config):
    s = V4SecurityScannerV2(application, instance_keys, storage)
    s._secscan_api = mock.Mock()
    s._secscan_api.state.return_value = {"state": "abc"}
    s._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "abc",
    )
    s._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}
    return s


class TestClaimUnindexedManifests:
    def test_claims_manifests_without_mss(self, initialized_db, scanner):
        manifest_count = Manifest.select().count()
        assert manifest_count > 0

        claimed = scanner._claim_unindexed_manifests(manifest_count)
        assert len(claimed) == manifest_count

        for mss in ManifestSecurityStatus.select():
            assert mss.index_status == IndexStatus.IN_PROGRESS
            assert mss.indexer_hash == "in_progress_v2"

    def test_skips_manifests_with_existing_mss(self, initialized_db, scanner):
        manifests = list(Manifest.select().limit(3))
        for m in manifests:
            ManifestSecurityStatus.create(
                manifest=m,
                repository=m.repository,
                error_json={},
                index_status=IndexStatus.COMPLETED,
                indexer_hash="abc",
                indexer_version=IndexerVersion.V4,
                metadata_json={},
            )

        total = Manifest.select().count()
        claimed = scanner._claim_unindexed_manifests(total)

        assert len(claimed) == total - 3

    def test_respects_batch_size(self, initialized_db, scanner):
        claimed = scanner._claim_unindexed_manifests(2)
        assert len(claimed) == 2

    def test_returns_empty_when_all_indexed(self, initialized_db, scanner):
        for m in Manifest.select():
            ManifestSecurityStatus.create(
                manifest=m,
                repository=m.repository,
                error_json={},
                index_status=IndexStatus.COMPLETED,
                indexer_hash="abc",
                indexer_version=IndexerVersion.V4,
                metadata_json={},
            )

        claimed = scanner._claim_unindexed_manifests(10)
        assert len(claimed) == 0


class TestFindAndClaimBatch:
    def _create_mss_for_all(self, status, indexer_hash="abc", last_indexed=None):
        if last_indexed is None:
            last_indexed = datetime.utcnow() - timedelta(days=2)
        for m in Manifest.select():
            ManifestSecurityStatus.create(
                manifest=m,
                repository=m.repository,
                error_json={},
                index_status=status,
                indexer_hash=indexer_hash,
                indexer_version=IndexerVersion.V4,
                last_indexed=last_indexed,
                metadata_json={},
            )

    def test_claims_failed_past_threshold(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.FAILED,
            last_indexed=datetime.utcnow() - timedelta(seconds=600),
        )

        manifest_count = Manifest.select().count()
        claimed = scanner._find_and_claim_batch(
            manifest_count, reindex_threshold, stale_threshold, "abc"
        )
        assert len(claimed) == manifest_count

        for mss in ManifestSecurityStatus.select():
            assert mss.index_status == IndexStatus.IN_PROGRESS
            assert mss.indexer_hash == "in_progress_v2"

    def test_skips_failed_within_threshold(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.FAILED,
            last_indexed=datetime.utcnow(),
        )

        claimed = scanner._find_and_claim_batch(50, reindex_threshold, stale_threshold, "abc")
        assert len(claimed) == 0

    def test_claims_stale_in_progress(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.IN_PROGRESS,
            last_indexed=datetime.utcnow() - timedelta(hours=7),
        )

        manifest_count = Manifest.select().count()
        claimed = scanner._find_and_claim_batch(
            manifest_count, reindex_threshold, stale_threshold, "abc"
        )
        assert len(claimed) == manifest_count

    def test_skips_fresh_in_progress(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.IN_PROGRESS,
            last_indexed=datetime.utcnow(),
        )

        claimed = scanner._find_and_claim_batch(50, reindex_threshold, stale_threshold, "abc")
        assert len(claimed) == 0

    def test_claims_needs_reindexing(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.COMPLETED,
            indexer_hash="old_hash",
            last_indexed=datetime.utcnow() - timedelta(seconds=600),
        )

        manifest_count = Manifest.select().count()
        claimed = scanner._find_and_claim_batch(
            manifest_count, reindex_threshold, stale_threshold, "new_hash"
        )
        assert len(claimed) == manifest_count

    def test_skips_completed_with_matching_hash(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.COMPLETED,
            indexer_hash="abc",
            last_indexed=datetime.utcnow() - timedelta(seconds=600),
        )

        claimed = scanner._find_and_claim_batch(50, reindex_threshold, stale_threshold, "abc")
        assert len(claimed) == 0

    @pytest.mark.parametrize(
        "status",
        [IndexStatus.MANIFEST_UNSUPPORTED, IndexStatus.MANIFEST_LAYER_TOO_LARGE],
    )
    def test_skips_unsupported_and_too_large(self, initialized_db, scanner, status):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            status,
            indexer_hash="old_hash",
            last_indexed=datetime.utcnow() - timedelta(days=30),
        )

        claimed = scanner._find_and_claim_batch(50, reindex_threshold, stale_threshold, "new_hash")
        assert len(claimed) == 0

    def test_respects_batch_size(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.FAILED,
            last_indexed=datetime.utcnow() - timedelta(seconds=600),
        )

        claimed = scanner._find_and_claim_batch(2, reindex_threshold, stale_threshold, "abc")
        assert len(claimed) == 2


class TestPerformIndexingCycle:
    def test_indexes_unindexed_manifests(self, initialized_db, scanner):
        scanner.perform_indexing(batch_size=100)

        manifest_count = Manifest.select().count()
        assert ManifestSecurityStatus.select().count() == manifest_count
        for mss in ManifestSecurityStatus.select():
            assert mss.index_status in (
                IndexStatus.COMPLETED,
                IndexStatus.MANIFEST_UNSUPPORTED,
            )

    def test_reindexes_failed_manifests(self, initialized_db, scanner):
        application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 300

        for m in Manifest.select():
            ManifestSecurityStatus.create(
                manifest=m,
                repository=m.repository,
                error_json={},
                index_status=IndexStatus.FAILED,
                indexer_hash="abc",
                indexer_version=IndexerVersion.V4,
                last_indexed=datetime.utcnow() - timedelta(seconds=600),
                metadata_json={},
            )

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select():
            assert mss.index_status in (
                IndexStatus.COMPLETED,
                IndexStatus.MANIFEST_UNSUPPORTED,
            )

    def test_skips_failed_within_threshold(self, initialized_db, scanner):
        application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 300

        for m in Manifest.select():
            ManifestSecurityStatus.create(
                manifest=m,
                repository=m.repository,
                error_json={},
                index_status=IndexStatus.FAILED,
                indexer_hash="abc",
                indexer_version=IndexerVersion.V4,
                metadata_json={},
            )

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select():
            assert mss.index_status == IndexStatus.FAILED

    def test_handles_api_failure(self, initialized_db, scanner):
        scanner._secscan_api.state.side_effect = Exception("connection refused")

        with pytest.raises(Exception):
            scanner.perform_indexing(batch_size=10)

    def test_handles_clair_state_failure(self, initialized_db, scanner):
        from util.secscan.v4.api import APIRequestFailure

        scanner._secscan_api.state.side_effect = APIRequestFailure("connection refused")

        scanner.perform_indexing(batch_size=10)

        assert ManifestSecurityStatus.select().count() == 0

    def test_handles_index_error_response(self, initialized_db, scanner):
        scanner._secscan_api.index.return_value = (
            {"err": "something went wrong", "state": IndexReportState.Index_Error},
            "abc",
        )

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select():
            assert mss.index_status in (
                IndexStatus.FAILED,
                IndexStatus.MANIFEST_UNSUPPORTED,
            )

    def test_noop_when_nothing_to_do(self, initialized_db, scanner):
        for m in Manifest.select():
            ManifestSecurityStatus.create(
                manifest=m,
                repository=m.repository,
                error_json={},
                index_status=IndexStatus.COMPLETED,
                indexer_hash="abc",
                indexer_version=IndexerVersion.V4,
                metadata_json={},
            )

        scanner.perform_indexing(batch_size=100)

        scanner._secscan_api.index.assert_not_called()
