import logging.config
import os
import time

from peewee import fn

import features
from app import app
from data.database import DeletedNamespace, QuotaNamespaceSize, User
from data.model.quota import run_backfill
from util.locking import GlobalLock
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.queueworker import QueueWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)
POLL_PERIOD = app.config.get("QUOTA_BACKFILL_POLL_PERIOD", 15)
BATCH_SIZE = app.config.get("QUOTA_BACKFILL_BATCH_SIZE", 100)


class QuotaTotalWorker(Worker):
    def __init__(self):
        super(QuotaTotalWorker, self).__init__()
        self.add_operation(self.backfill, POLL_PERIOD)

    def backfill(self):
        logger.info("Quota backfill worker started, searching for namespaces to calculate size")
        subq = QuotaNamespaceSize.select().where(
            QuotaNamespaceSize.namespace_user == User.id,
            QuotaNamespaceSize.backfill_start_ms.is_null(False),
        )
        for namespace in (
            User.select()
            .where(
                ~fn.EXISTS(subq),
                User.enabled == True,
                User.robot == False,
            )
            .limit(BATCH_SIZE)
        ):
            logger.info("Running backfill for namespace %s", namespace.id)
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

    if not app.config.get("QUOTA_BACKFILL", True):
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
