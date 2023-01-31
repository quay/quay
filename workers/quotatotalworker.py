import logging.config
import os
import time
from data.registry_model.quota import run_total

import features

from app import app, quota_total_queue
from workers.gunicorn_worker import GunicornWorker
from workers.queueworker import QueueWorker
from workers.worker import Worker
from util.locking import GlobalLock
from util.log import logfile_path


logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 10
RESERVATION_SECONDS = 3600


class QuotaTotalWorker(QueueWorker):
    def process_queue_item(self, job_details):
        run_total(job_details.get("namespace", None), job_details.get("repository", None))


def create_gunicorn_worker():
    quota_total_worker = QuotaTotalWorker(
        quota_total_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    worker = GunicornWorker(__name__, app, quota_total_worker, features.QUOTA_MANAGEMENT)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.QUOTA_MANAGEMENT:
        logger.debug("Security scanner disabled; skipping SecurityWorker")
        while True:
            time.sleep(100000)

    GlobalLock.configure(app.config)
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = QuotaTotalWorker(
        quota_total_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    worker.start()
