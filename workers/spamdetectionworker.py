import logging.config
import time

import features
from app import app
from data.model.spam_detection_engine import ScanConfig, SpamScanner
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

POLL_PERIOD = app.config.get("SPAM_DETECTION_POLL_PERIOD", 86400)
BATCH_SIZE = app.config.get("SPAM_DETECTION_BATCH_SIZE", 200)
SLEEP_BETWEEN_BATCHES = app.config.get("SPAM_DETECTION_SLEEP_BETWEEN_BATCHES", 0.5)
MIN_CONFIDENCE = app.config.get("SPAM_DETECTION_MIN_CONFIDENCE", 50)
DRY_RUN = app.config.get("SPAM_DETECTION_DRY_RUN", True)


class SpamDetectionWorker(Worker):
    def __init__(self):
        super(SpamDetectionWorker, self).__init__()
        self.add_operation(self._scan, POLL_PERIOD)

    def _scan(self):
        logger.info("Starting spam detection scan (dry_run=%s)", DRY_RUN)
        config = ScanConfig(
            batch_size=BATCH_SIZE,
            sleep_between_batches=SLEEP_BETWEEN_BATCHES,
            min_confidence_threshold=MIN_CONFIDENCE,
            dry_run=DRY_RUN,
        )
        scanner = SpamScanner(config)
        report = scanner.scan()
        logger.info("Spam detection scan complete: %s", report.to_dict())


def create_gunicorn_worker():
    worker = GunicornWorker(__name__, app, SpamDetectionWorker(), features.SPAM_DETECTION)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.SPAM_DETECTION:
        logger.debug("Spam detection disabled; skipping spamdetectionworker")
        while True:
            time.sleep(100000)

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = SpamDetectionWorker()
    worker.start()
