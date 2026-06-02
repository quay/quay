from unittest.mock import ANY, MagicMock, patch

import pytest

from test.fixtures import *
from workers.helmchartworker.helmchartworker import HelmChartMetadataWorker


class TestHelmChartMetadataWorker:
    def test_process_queue_item_calls_extractor(self, initialized_db):
        """process_queue_item delegates to extract_helm_chart_metadata."""
        with patch(
            "workers.helmchartworker.helmchartworker.extract_helm_chart_metadata"
        ) as mock_extract:
            worker = HelmChartMetadataWorker.__new__(HelmChartMetadataWorker)
            worker.process_queue_item(
                {
                    "manifest_id": 42,
                    "repository_id": 7,
                    "manifest_digest": "sha256:abc",
                }
            )
            mock_extract.assert_called_once_with(42, 7, ANY)

    def test_create_gunicorn_worker_passes_feature_flag(self, initialized_db):
        """create_gunicorn_worker passes the extraction feature flag to GunicornWorker."""
        with patch("workers.helmchartworker.helmchartworker.GunicornWorker") as MockGunicorn:
            from workers.helmchartworker.helmchartworker import create_gunicorn_worker

            create_gunicorn_worker()

        _, args, _ = MockGunicorn.mock_calls[0]
        feature_flag_arg = args[3]
        import features

        assert feature_flag_arg is features.HELM_CHART_METADATA_EXTRACTION
