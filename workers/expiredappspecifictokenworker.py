import logging
import time

import features

from app import app  # This is required to initialize the database.
from data import model
from workers.worker import Worker
from util.log import logfile_path
from util.timedeltastring import convert_to_timedelta
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 60 * 60  # 1 hour


class ExpiredAppSpecificTokenWorker(Worker):
    def __init__(self):
        super(ExpiredAppSpecificTokenWorker, self).__init__()

        expiration_window = app.config.get("EXPIRED_APP_SPECIFIC_TOKEN_GC", "1d")
        self.expiration_window = convert_to_timedelta(expiration_window)

        logger.debug("Found expiration window: %s", expiration_window)
        self.add_operation(self._gc_expired_tokens, POLL_PERIOD_SECONDS)

    def _gc_expired_tokens(self):
        """
        Garbage collects any expired app specific tokens outside of the configured window.
        """
        logger.debug(
            "Garbage collecting expired app specific tokens with window: %s", self.expiration_window
        )
        model.appspecifictoken.gc_expired_tokens(self.expiration_window)
        return True


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    feature_flag = (features.APP_SPECIFIC_TOKENS) or (
        app.config.get("EXPIRED_APP_SPECIFIC_TOKEN_GC") is not None
    )
    worker = GunicornWorker(__name__, app, ExpiredAppSpecificTokenWorker(), feature_flag)
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.APP_SPECIFIC_TOKENS:
        logger.debug("App specific tokens disabled; skipping")
        while True:
            time.sleep(100000)

    if app.config.get("EXPIRED_APP_SPECIFIC_TOKEN_GC") is None:
        logger.debug("GC of App specific tokens is disabled; skipping")
        while True:
            time.sleep(100000)

    logger.debug("Starting expired app specific token GC worker")
    worker = ExpiredAppSpecificTokenWorker()
    worker.start()
