import logging.config
import time

import features

from app import app
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker
from util.log import logfile_path


logger = logging.getLogger(__name__)
POLL_PERIOD = app.config.get("AUTO_PRUNING_POLL_PERIOD", 30)
BATCH_SIZE = app.config.get("AUTO_PRUNING_BATCH_SIZE", 10)


class AutoPruneWorker(Worker):
    def __init__(self):
        super(AutoPruneWorker, self).__init__()
        self.add_operation(self.prune, POLL_PERIOD)

    def prune(self):
        logger.info("Prune method not yet implemented...")


def create_gunicorn_worker():
    worker = GunicornWorker(__name__, app, AutoPruneWorker(), features.AUTO_PRUNE)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.AUTO_PRUNE:
        logger.debug("Auto-prune disabled; skipping autopruneworker")
        while True:
            time.sleep(100000)

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = AutoPruneWorker()
    worker.start()
