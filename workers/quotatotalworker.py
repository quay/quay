import logging.config
import os
import time

from peewee import fn
from data.registry_model.quota import run_backfill
from data.database import QuotaNamespaceSize, User

import features

from app import app
from workers.gunicorn_worker import GunicornWorker
from workers.queueworker import QueueWorker
from workers.worker import Worker
from util.locking import GlobalLock
from util.log import logfile_path


logger = logging.getLogger(__name__)
POLL_PERIOD = 5
BATCH_SIZE = 1000


class QuotaTotalWorker(Worker):
    def __init__(self):
        super(QuotaTotalWorker, self).__init__()
        self.add_operation(self.backfill, POLL_PERIOD)

    def backfill(self):
        subq = QuotaNamespaceSize.select().where(
            QuotaNamespaceSize.namespace_user == User.id,
            QuotaNamespaceSize.backfill_start_ms.is_null(False),
        )
        for namespace in User.select().where(~fn.EXISTS(subq)).limit(BATCH_SIZE):
            run_backfill(namespace.id)


def create_gunicorn_worker():
    worker = GunicornWorker(__name__, app, QuotaTotalWorker(), features.QUOTA_MANAGEMENT)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.QUOTA_MANAGEMENT:
        logger.debug("Quota management disabled; skipping quotatotalworker")
        while True:
            time.sleep(100000)

    if app.config.get("QUOTA_TOTAL_DELAY_SECONDS", None) is not None:
        logger.debug(
            "Delaying quota backfill for %s seconds.",
            str(app.config.get("QUOTA_TOTAL_DELAY_SECONDS", 0)),
        )
        time.sleep(app.config.get("QUOTA_TOTAL_DELAY_SECONDS", 0))
        logger.debug("Delay complete, starting quotatotalworker...")

    GlobalLock.configure(app.config)
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = QuotaTotalWorker()
    worker.start()
