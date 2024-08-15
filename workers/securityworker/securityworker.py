import logging.config
import os
import threading
import time

import features
from app import app
from data.secscan_model import secscan_model
from endpoints.v2 import v2_bp
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)


DEFAULT_INDEXING_INTERVAL = 30


class SecurityWorker(Worker):
    def __init__(self):
        super(SecurityWorker, self).__init__()
        self._next_token = None
        self._model = secscan_model

        interval = app.config.get("SECURITY_SCANNER_INDEXING_INTERVAL", DEFAULT_INDEXING_INTERVAL)
        self.add_operation(self._index_in_scanner, interval)
        self.add_operation(self._index_recent_manifests_in_scanner, interval)

    def _index_in_scanner(self):
        batch_size = app.config.get("SECURITY_SCANNER_V4_BATCH_SIZE", 0)

        if app.config.get("SECURITY_SCANNER_V4_LOCK", False):
            try:
                with GlobalLock("SECURITY_SCANNER_V4_INDEXING"):
                    self._next_token = self._model.perform_indexing(self._next_token, batch_size)
            except LockNotAcquiredException:
                return

        else:
            self._next_token = self._model.perform_indexing(self._next_token, batch_size)

    def _index_recent_manifests_in_scanner(self):
        batch_size = app.config.get("SECURITY_SCANNER_V4_RECENT_MANIFEST_BATCH_SIZE", 1000)

        if app.config.get("SECURITY_SCANNER_V4_RECENT_MANIFEST_BATCH_LOCK", False):
            try:
                with GlobalLock(
                    "SECURITYWORKER_INDEX_RECENT_MANIFEST", lock_ttl=300, auto_renewal=True
                ):
                    self._model.perform_indexing_recent_manifests(batch_size)
            except LockNotAcquiredException:
                logger.warning(
                    "Could not acquire global lock for recent manifest indexing. Skipping"
                )

        else:
            self._model.perform_indexing_recent_manifests(batch_size)


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
    pydev_debug = os.getenv("PYDEV_DEBUG", None)
    if pydev_debug:
        import pydevd_pycharm

        host, port = pydev_debug.split(":")
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

    GlobalLock.configure(app.config)
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = SecurityWorker()
    worker.start()
