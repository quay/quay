import json
from unittest.mock import MagicMock, patch

import pytest
from peewee import fn

from data.database import HelmChartMetadata, Manifest, Repository
from data.model.repository import create_repository
from test.fixtures import *
from util.locking import LockNotAcquiredException
from workers.helmchartworker.backfillworker import (
    HELM_CHART_CONFIG_TYPE,
    HelmChartBackfillWorker,
)


def _create_helm_manifest(repo, digest, config_media_type=HELM_CHART_CONFIG_TYPE):
    """Create a Manifest row that looks like a Helm chart."""
    return Manifest.create(
        repository=repo,
        digest=digest,
        media_type=Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        ),
        manifest_bytes=json.dumps(
            {
                "schemaVersion": 2,
                "config": {"mediaType": config_media_type, "digest": "sha256:abc", "size": 100},
                "layers": [],
            }
        ),
        config_media_type=config_media_type,
        layers_compressed_size=0,
    )


class TestHelmChartBackfillWorker:
    @pytest.fixture(autouse=True)
    def _enable_helm_extraction(self):
        """Enable the feature flag so _do_backfill proceeds past the guard."""
        import features

        original = features.HELM_CHART_METADATA_EXTRACTION
        features.HELM_CHART_METADATA_EXTRACTION = True
        yield
        features.HELM_CHART_METADATA_EXTRACTION = original

    def test_no_unprocessed_manifests(self, initialized_db):
        """When all manifests are already processed, backfill returns False."""
        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            assert worker._do_backfill() is False

    def test_backfill_enqueues_unprocessed_helm_manifests(self, initialized_db):
        """Pre-existing Helm manifests without HelmChartMetadata rows are enqueued."""
        repo = create_repository("devtable", "backfilltest", None)
        m1 = _create_helm_manifest(repo, "sha256:backfill001")
        m2 = _create_helm_manifest(repo, "sha256:backfill002")

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            mock_queue.alive.return_value = False
            result = worker._do_backfill()

        assert result is True
        assert mock_queue.put.call_count == 2

    def test_backfill_skips_processed_manifests(self, initialized_db):
        """Manifests with existing HelmChartMetadata rows (completed) are not re-enqueued."""
        repo = create_repository("devtable", "backfilltest2", None)
        m1 = _create_helm_manifest(repo, "sha256:backfill003")

        HelmChartMetadata.create(
            manifest=m1,
            repository=repo,
            chart_name="test",
            chart_version="1.0.0",
            api_version="v2",
            chart_yaml="apiVersion: v2\nname: test\nversion: 1.0.0\n",
            extraction_status="completed",
        )

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            assert worker._do_backfill() is False

    def test_backfill_skips_failed_manifests(self, initialized_db):
        """Manifests with failed HelmChartMetadata rows are NOT re-enqueued (tombstone)."""
        repo = create_repository("devtable", "backfilltest3", None)
        m1 = _create_helm_manifest(repo, "sha256:backfill004")

        HelmChartMetadata.create(
            manifest=m1,
            repository=repo,
            chart_name="",
            chart_version="",
            api_version="",
            chart_yaml="",
            extraction_status="failed",
            extraction_error="corrupt archive",
        )

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            assert worker._do_backfill() is False

    def test_backfill_skips_non_helm_manifests(self, initialized_db):
        """Non-Helm manifests (e.g., container images) are not enqueued."""
        repo = create_repository("devtable", "backfilltest4", None)
        _create_helm_manifest(
            repo,
            "sha256:backfill005",
            config_media_type="application/vnd.docker.container.image.v1+json",
        )

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            assert worker._do_backfill() is False

    def test_manual_retry_after_deleting_failed_row(self, initialized_db):
        """Deleting a failed HelmChartMetadata row allows the backfill to re-enqueue."""
        repo = create_repository("devtable", "backfilltest5", None)
        m1 = _create_helm_manifest(repo, "sha256:backfill006")

        failed_row = HelmChartMetadata.create(
            manifest=m1,
            repository=repo,
            chart_name="",
            chart_version="",
            api_version="",
            chart_yaml="",
            extraction_status="failed",
            extraction_error="corrupt archive",
        )

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            assert worker._do_backfill() is False

        failed_row.delete_instance()
        worker._cursor_id = 0

        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            mock_queue.alive.return_value = False
            result = worker._do_backfill()

        assert result is True
        assert mock_queue.put.call_count == 1

    def test_backfill_respects_queue_limit(self, initialized_db):
        """Backfill skips cycle when queue already has too many items."""
        repo = create_repository("devtable", "backfilltest6", None)
        _create_helm_manifest(repo, "sha256:backfill007")

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 99999, 0)
            result = worker._do_backfill()

        assert result is False
        assert mock_queue.put.call_count == 0

    def test_create_gunicorn_worker_passes_feature_flag(self, initialized_db):
        """create_gunicorn_worker passes the backfill feature flag to GunicornWorker."""
        with patch("workers.helmchartworker.backfillworker.GunicornWorker") as MockGunicorn:
            from workers.helmchartworker.backfillworker import create_gunicorn_worker

            create_gunicorn_worker()

        _, args, _ = MockGunicorn.mock_calls[0]
        feature_flag_arg = args[3]
        import features

        assert feature_flag_arg is features.HELM_CHART_METADATA_BACKFILL

    def test_backfill_acquires_global_lock(self, initialized_db):
        """_backfill_helm_charts acquires a GlobalLock before calling _do_backfill."""
        worker = HelmChartBackfillWorker()
        with patch("workers.helmchartworker.backfillworker.GlobalLock") as MockLock:
            mock_ctx = MagicMock()
            MockLock.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            MockLock.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(worker, "_do_backfill", return_value=False) as mock_do:
                result = worker._backfill_helm_charts()

            MockLock.assert_called_once_with(
                "HELM_CHART_BACKFILL", lock_ttl=pytest.approx(3660, abs=60)
            )
            mock_do.assert_called_once()
        assert result is False

    def test_backfill_handles_lock_contention(self, initialized_db):
        """_backfill_helm_charts returns False when the lock cannot be acquired."""
        worker = HelmChartBackfillWorker()
        with patch("workers.helmchartworker.backfillworker.GlobalLock") as MockLock:
            MockLock.return_value.__enter__ = MagicMock(side_effect=LockNotAcquiredException)
            MockLock.return_value.__exit__ = MagicMock(return_value=False)
            result = worker._backfill_helm_charts()

        assert result is False

    def test_cursor_advances_and_wraps(self, initialized_db):
        """The PK cursor advances each cycle and wraps when it passes max(Manifest.id)."""
        from workers.helmchartworker.backfillworker import BACKFILL_BATCH_SIZE

        repo = create_repository("devtable", "backfilltest_cursor", None)
        m1 = _create_helm_manifest(repo, "sha256:backfill_cursor001")

        worker = HelmChartBackfillWorker()
        assert worker._cursor_id == 0

        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            mock_queue.alive.return_value = False
            worker._do_backfill()

        scan_end = BACKFILL_BATCH_SIZE * 20
        assert worker._cursor_id > 0
        assert worker._cursor_id <= scan_end

        # Set cursor past the max manifest ID to trigger wrap-around
        max_id = Manifest.select(fn.Max(Manifest.id)).scalar()
        worker._cursor_id = max_id + 1

        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            mock_queue.alive.return_value = False
            worker._do_backfill()

        assert worker._cursor_id > 0
        assert worker._cursor_id <= scan_end

    def test_backfill_skips_when_extraction_disabled(self, initialized_db):
        """Backfill does nothing when FEATURE_HELM_CHART_METADATA_EXTRACTION is off."""
        import features

        repo = create_repository("devtable", "backfilltest_extr", None)
        _create_helm_manifest(repo, "sha256:backfill_extr001")

        features.HELM_CHART_METADATA_EXTRACTION = False

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            result = worker._do_backfill()

        assert result is False
        assert mock_queue.put.call_count == 0

    def test_backfill_skips_manifest_with_missing_namespace(self, initialized_db):
        """A manifest whose namespace user cannot be resolved is skipped."""
        repo = create_repository("devtable", "backfilltest_ns", None)
        m1 = _create_helm_manifest(repo, "sha256:backfill_ns001")

        worker = HelmChartBackfillWorker()
        with patch(
            "workers.helmchartworker.backfillworker.helm_chart_metadata_queue"
        ) as mock_queue:
            mock_queue.get_metrics.return_value = (0, 0, 0)
            mock_queue.alive.return_value = False

            def mock_unprocessed_iter():
                class BrokenRepo:
                    @property
                    def namespace_user(self):
                        raise Exception("namespace user deleted")

                    @property
                    def name(self):
                        return "backfilltest_ns"

                mock_row = MagicMock()
                mock_row.id = m1.id
                mock_row.repository_id = repo.id
                mock_row.repository = BrokenRepo()
                return [mock_row]

            with patch("workers.helmchartworker.backfillworker.Manifest") as MockManifest:
                mock_max_query = MagicMock()
                mock_max_query.scalar.return_value = m1.id + 1000

                mock_query = MagicMock()
                mock_query.__iter__ = MagicMock(return_value=iter(mock_unprocessed_iter()))

                call_count = [0]

                def select_side_effect(*args):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return mock_max_query
                    mock_chain = MagicMock()
                    mock_chain.join.return_value.join.return_value.switch.return_value.join.return_value.where.return_value.order_by.return_value.limit.return_value = (
                        mock_query
                    )
                    return mock_chain

                MockManifest.select.side_effect = select_side_effect
                MockManifest.config_media_type = Manifest.config_media_type
                MockManifest.id = Manifest.id

                result = worker._do_backfill()

        assert result is False
        assert mock_queue.put.call_count == 0
