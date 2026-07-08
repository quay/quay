import logging
from datetime import datetime, timedelta
from unittest import mock

import pytest
from peewee import fn

import features
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


class TestFindAndClaimBatch:
    def _create_mss_for_all(
        self, status, indexer_hash="abc", last_indexed=None, metadata_json=None, error_count=0
    ):
        if last_indexed is None:
            last_indexed = datetime.utcnow() - timedelta(days=2)
        if metadata_json is None:
            metadata_json = {}
        ManifestSecurityStatus.delete().execute()
        for m in Manifest.select():
            ManifestSecurityStatus.create(
                manifest=m,
                repository=m.repository,
                error_json={},
                index_status=status,
                indexer_hash=indexer_hash,
                indexer_version=IndexerVersion.V4,
                last_indexed=last_indexed,
                metadata_json=metadata_json,
                error_count=error_count,
            )

    def test_claims_pending(self, initialized_db, scanner):
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(IndexStatus.PENDING)

        manifest_count = Manifest.select().count()
        claimed = scanner._find_and_claim_batch(
            manifest_count, reindex_threshold, stale_threshold, "abc"
        )
        assert len(claimed) == manifest_count

        for mss in ManifestSecurityStatus.select():
            assert mss.index_status == IndexStatus.IN_PROGRESS
            assert mss.indexer_hash == "in_progress_v2"

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

    def test_skips_failed_exceeding_max_retries(self, initialized_db, scanner):
        application.config["SECURITY_SCANNER_V2_MAX_SCAN_RETRIES"] = 3
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.FAILED,
            last_indexed=datetime.utcnow() - timedelta(seconds=600),
            error_count=3,
        )

        claimed = scanner._find_and_claim_batch(50, reindex_threshold, stale_threshold, "abc")
        assert len(claimed) == 0

    def test_claims_failed_under_max_retries(self, initialized_db, scanner):
        application.config["SECURITY_SCANNER_V2_MAX_SCAN_RETRIES"] = 3
        reindex_threshold = datetime.utcnow() - timedelta(seconds=300)
        stale_threshold = datetime.utcnow() - timedelta(hours=6)

        self._create_mss_for_all(
            IndexStatus.FAILED,
            last_indexed=datetime.utcnow() - timedelta(seconds=600),
            error_count=2,
        )

        manifest_count = Manifest.select().count()
        claimed = scanner._find_and_claim_batch(
            manifest_count, reindex_threshold, stale_threshold, "abc"
        )
        assert len(claimed) == manifest_count

    def test_claims_failed_with_no_error_count(self, initialized_db, scanner):
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

        ManifestSecurityStatus.delete().execute()
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

        ManifestSecurityStatus.delete().execute()
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

        mss_count_before = ManifestSecurityStatus.select().count()
        scanner.perform_indexing(batch_size=10)

        assert ManifestSecurityStatus.select().count() == mss_count_before

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

    def test_mark_failed_increments_error_count(self, initialized_db, scanner):
        scanner._secscan_api.index.return_value = (
            {"err": "something went wrong", "state": IndexReportState.Index_Error},
            "abc",
        )

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select().where(
            ManifestSecurityStatus.index_status == IndexStatus.FAILED
        ):
            assert mss.error_count == 1

        application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 0
        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select().where(
            ManifestSecurityStatus.index_status == IndexStatus.FAILED
        ):
            assert mss.error_count == 2

    def test_error_count_resets_on_success(self, initialized_db, scanner):
        application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 0

        scanner._secscan_api.index.return_value = (
            {"err": "something went wrong", "state": IndexReportState.Index_Error},
            "abc",
        )
        scanner.perform_indexing(batch_size=100)

        failed_count = (
            ManifestSecurityStatus.select()
            .where(ManifestSecurityStatus.index_status == IndexStatus.FAILED)
            .count()
        )
        assert failed_count > 0

        scanner._secscan_api.index.return_value = (
            {"err": None, "state": IndexReportState.Index_Finished},
            "abc",
        )
        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select().where(
            ManifestSecurityStatus.index_status == IndexStatus.COMPLETED
        ):
            assert mss.error_count == 0

    def test_stops_retrying_after_max_failures(self, initialized_db, scanner):
        application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 0
        application.config["SECURITY_SCANNER_V2_MAX_SCAN_RETRIES"] = 2

        scanner._secscan_api.index.return_value = (
            {"err": "something went wrong", "state": IndexReportState.Index_Error},
            "abc",
        )

        scanner.perform_indexing(batch_size=100)
        scanner.perform_indexing(batch_size=100)

        scanner._secscan_api.index.reset_mock()
        scanner.perform_indexing(batch_size=100)

        scanner._secscan_api.index.assert_not_called()

    def test_noop_when_nothing_to_do(self, initialized_db, scanner):
        ManifestSecurityStatus.delete().execute()
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

    def test_handles_api_request_failure_during_index(self, initialized_db, scanner):
        from util.secscan.v4.api import APIRequestFailure

        scanner._secscan_api.index.side_effect = APIRequestFailure("connection refused")

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select().where(
            ManifestSecurityStatus.index_status == IndexStatus.FAILED
        ):
            assert mss.error_count == 1
            assert mss.indexer_hash == "api_failure"

    def test_handles_unknown_index_state(self, initialized_db, scanner):
        scanner._secscan_api.index.return_value = (
            {"err": None, "state": "some_unknown_state"},
            "abc",
        )

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select().where(
            ManifestSecurityStatus.index_status == IndexStatus.FAILED
        ):
            assert mss.error_count == 1
            assert mss.indexer_hash == "unknown_state"

    def test_handles_invalid_content_sent(self, initialized_db, scanner):
        from util.secscan.v4.api import InvalidContentSent

        scanner._secscan_api.index.side_effect = InvalidContentSent()

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select().where(
            ManifestSecurityStatus.index_status == IndexStatus.MANIFEST_UNSUPPORTED
        ):
            assert mss.indexer_hash == "none"

    def test_handles_layer_too_large(self, initialized_db, scanner):
        from util.secscan.v4.api import LayerTooLargeException

        scanner._secscan_api.index.side_effect = LayerTooLargeException()

        scanner.perform_indexing(batch_size=100)

        for mss in ManifestSecurityStatus.select().where(
            ManifestSecurityStatus.index_status == IndexStatus.MANIFEST_LAYER_TOO_LARGE
        ):
            assert mss.indexer_hash == "none"

    def test_handles_deleted_manifest(self, initialized_db, scanner):
        mss = ManifestSecurityStatus.select().first()
        manifest_id = mss.manifest_id
        repository_id = mss.repository_id

        ManifestSecurityStatus.update(
            index_status=IndexStatus.IN_PROGRESS,
        ).where(ManifestSecurityStatus.id == mss.id).execute()

        with mock.patch(
            "data.secscan_model.secscan_v4_model_v2.Manifest.get",
            side_effect=Manifest.DoesNotExist(),
        ):
            scanner._index_manifest_by_id(manifest_id, repository_id)

        updated = ManifestSecurityStatus.get(ManifestSecurityStatus.id == mss.id)
        assert updated.index_status == IndexStatus.FAILED
        assert updated.indexer_hash == "manifest_deleted"

    def test_handles_manifest_list(self, initialized_db, scanner):
        mss = ManifestSecurityStatus.select().first()
        manifest_id = mss.manifest_id
        repository_id = mss.repository_id

        ManifestSecurityStatus.update(
            index_status=IndexStatus.IN_PROGRESS,
        ).where(ManifestSecurityStatus.id == mss.id).execute()

        with mock.patch(
            "data.secscan_model.secscan_v4_model_v2.ManifestDataType.for_manifest"
        ) as mock_for_manifest:
            mock_manifest = mock.Mock()
            mock_manifest.is_manifest_list = True
            mock_manifest._db_id = manifest_id
            mock_manifest.repository._db_id = repository_id
            mock_for_manifest.return_value = mock_manifest

            scanner._index_manifest_by_id(manifest_id, repository_id)

        updated = ManifestSecurityStatus.get(
            ManifestSecurityStatus.manifest == manifest_id,
            ManifestSecurityStatus.index_status == IndexStatus.MANIFEST_UNSUPPORTED,
        )
        assert updated.indexer_hash == "none"

    def test_handles_manifest_with_no_layers(self, initialized_db, scanner):
        mss = ManifestSecurityStatus.select().first()
        manifest_id = mss.manifest_id
        repository_id = mss.repository_id

        ManifestSecurityStatus.update(
            index_status=IndexStatus.IN_PROGRESS,
        ).where(ManifestSecurityStatus.id == mss.id).execute()

        with mock.patch.object(registry_model, "list_manifest_layers", return_value=None):
            scanner._index_manifest_by_id(manifest_id, repository_id)

        updated = ManifestSecurityStatus.get(
            ManifestSecurityStatus.manifest == manifest_id,
            ManifestSecurityStatus.index_status == IndexStatus.MANIFEST_UNSUPPORTED,
        )
        assert updated.indexer_hash == "none"

    def test_handles_non_container_image(self, initialized_db, scanner):
        mss = ManifestSecurityStatus.select().first()
        manifest_id = mss.manifest_id
        repository_id = mss.repository_id

        ManifestSecurityStatus.update(
            index_status=IndexStatus.IN_PROGRESS,
        ).where(ManifestSecurityStatus.id == mss.id).execute()

        fake_layer = mock.Mock()
        fake_layer.layer_info = mock.Mock()
        fake_layer.layer_info.is_remote = False
        fake_layer.estimated_size = mock.Mock(return_value=100)
        fake_layer.layer_info.content_type = "application/vnd.oci.empty.v1+json"

        with mock.patch(
            "data.secscan_model.secscan_v4_model_v2.ManifestDataType.for_manifest"
        ) as mock_for_manifest:
            mock_manifest = mock.Mock()
            mock_manifest.is_manifest_list = False
            mock_manifest.media_type = "application/vnd.oci.image.manifest.v1+json"
            mock_manifest._db_id = manifest_id
            mock_manifest.repository._db_id = repository_id
            mock_for_manifest.return_value = mock_manifest

            with mock.patch.object(
                registry_model, "list_manifest_layers", return_value=[fake_layer]
            ):
                with mock.patch(
                    "data.secscan_model.secscan_v4_model_v2._has_container_layers",
                    return_value=False,
                ):
                    scanner._index_manifest_by_id(manifest_id, repository_id)

        updated = ManifestSecurityStatus.get(
            ManifestSecurityStatus.manifest == manifest_id,
            ManifestSecurityStatus.index_status == IndexStatus.MANIFEST_UNSUPPORTED,
        )
        assert updated.indexer_hash == "none"

    def test_scan_success_emits_notifications(self, initialized_db, scanner):
        from data.registry_model.datatypes import Manifest as ManifestDataType

        candidate = Manifest.select().first()
        manifest = ManifestDataType.for_manifest(candidate, None)

        scanner._secscan_api.vulnerability_report.return_value = {
            "vulnerabilities": {
                "CVE-2021-12345": {
                    "id": "CVE-2021-12345",
                    "description": "test vuln",
                    "links": "https://example.com",
                    "severity": "High",
                    "normalized_severity": "High",
                    "fixed_in_version": "1.2.3",
                },
            },
        }

        with mock.patch.object(
            type(manifest), "has_been_scanned", new_callable=mock.PropertyMock, return_value=False
        ):
            with mock.patch.object(features, "SECURITY_SCANNER_NOTIFY_ON_NEW_INDEX", True):
                with mock.patch("notifications.spawn_notification") as mock_spawn:
                    scanner._handle_scan_success(manifest, candidate)
                    assert mock_spawn.called

    def test_send_notifications_skips_low_severity(self, initialized_db, scanner):
        from data.registry_model.datatypes import Manifest as ManifestDataType

        candidate = Manifest.select().first()
        manifest = ManifestDataType.for_manifest(candidate, None)

        scanner._secscan_api.vulnerability_report.return_value = {
            "vulnerabilities": {
                "CVE-2021-99999": {
                    "id": "CVE-2021-99999",
                    "description": "low vuln",
                    "links": "https://example.com",
                    "severity": "Low",
                    "normalized_severity": "Low",
                    "fixed_in_version": "",
                },
            },
        }

        with mock.patch("notifications.spawn_notification") as mock_spawn:
            scanner._send_vulnerability_notifications(manifest, candidate)
            assert not mock_spawn.called

    def test_send_notifications_handles_api_failure(self, initialized_db, scanner):
        from data.registry_model.datatypes import Manifest as ManifestDataType
        from util.secscan.v4.api import APIRequestFailure

        candidate = Manifest.select().first()
        manifest = ManifestDataType.for_manifest(candidate, None)

        scanner._secscan_api.vulnerability_report.side_effect = APIRequestFailure("fail")
        scanner._send_vulnerability_notifications(manifest, candidate)

    def test_send_notifications_handles_none_report(self, initialized_db, scanner):
        from data.registry_model.datatypes import Manifest as ManifestDataType

        candidate = Manifest.select().first()
        manifest = ManifestDataType.for_manifest(candidate, None)

        scanner._secscan_api.vulnerability_report.return_value = None
        scanner._send_vulnerability_notifications(manifest, candidate)
