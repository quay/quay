import logging
import time

import features
from app import app, helm_chart_metadata_queue, storage
from workers.gunicorn_worker import GunicornWorker
from workers.helmchartworker.extractor import extract_helm_chart_metadata
from workers.queueworker import QueueWorker

logger = logging.getLogger(__name__)


class HelmChartMetadataWorker(QueueWorker):
    """
    Worker that processes the helm_chart_metadata_queue and extracts
    metadata from Helm chart OCI artifacts.
    """

    def process_queue_item(self, job_details):
        manifest_id = job_details["manifest_id"]
        repository_id = job_details["repository_id"]
        extract_helm_chart_metadata(manifest_id, repository_id, storage)

    def watchdog(self):
        """Extend the reservation while an extraction is still running."""
        logger.debug("Watchdog extending processing reservation")
        self.extend_processing(self._reservation_seconds)


def create_gunicorn_worker():
    worker = HelmChartMetadataWorker(
        helm_chart_metadata_queue,
        poll_period_seconds=5,
        reservation_seconds=300,
        retry_after_seconds=60,
    )
    return GunicornWorker(__name__, app, worker, features.HELM_CHART_METADATA_EXTRACTION)


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.HELM_CHART_METADATA_EXTRACTION:
        logger.debug("Helm chart metadata extraction not enabled; skipping")
        while True:
            time.sleep(100000)

    worker = HelmChartMetadataWorker(
        helm_chart_metadata_queue,
        poll_period_seconds=5,
        reservation_seconds=300,
        retry_after_seconds=60,
    )
    worker.start()
