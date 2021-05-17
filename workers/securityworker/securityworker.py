import logging.config
import os
import time

import features
import threading

from app import app
from data.secscan_model import secscan_model
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker
from util.log import logfile_path
from endpoints.v2 import v2_bp


logger = logging.getLogger(__name__)


DEFAULT_INDEXING_INTERVAL = 30


class SecurityWorker(Worker):
    def __init__(self):
        super(SecurityWorker, self).__init__()
        self._next_token = None
        self._model = secscan_model

        interval = app.config.get("SECURITY_SCANNER_INDEXING_INTERVAL", DEFAULT_INDEXING_INTERVAL)
        self.add_operation(self._index_in_scanner, interval)

    def _index_in_scanner(self):
        self._next_token = self._model.perform_indexing(self._next_token)


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    app.register_blueprint(v2_bp, url_prefix="/v2")
    worker = GunicornWorker(__name__, app, SecurityWorker(), features.SECURITY_SCANNER)
    return worker


if __name__ == "__main__":
    if os.getenv("PYDEV_DEBUG", None):
        import pydevd_pycharm

        host, port = os.getenv("PYDEV_DEBUG").split(":")
        pydevd_pycharm.settrace(
            host, port=int(port), stdoutToServer=True, stderrToServer=True, suspend=False
        )

    app.register_blueprint(v2_bp, url_prefix="/v2")

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.SECURITY_SCANNER:
        logger.debug("Security scanner disabled; skipping SecurityWorker")
        while True:
            time.sleep(100000)

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = SecurityWorker()
    worker.start()
