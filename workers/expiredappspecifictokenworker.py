import logging

from data import model
from singletons.config import app_config
from util.log import logfile_path
from util.timedeltastring import convert_to_timedelta
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

POLL_PERIOD_SECONDS = 60 * 60  # 1 hour


class ExpiredAppSpecificTokenWorker(Worker):
    def __init__(self):
        super(ExpiredAppSpecificTokenWorker, self).__init__()

        expiration_window = app_config.get("EXPIRED_APP_SPECIFIC_TOKEN_GC", "1d")
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


def create_gunicorn_worker() -> GunicornWorker:
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, ExpiredAppSpecificTokenWorker())
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    logger.debug("Starting expired app specific token GC worker")
    worker = ExpiredAppSpecificTokenWorker()
    worker.start()
