import os
import logging
import logging.config
import argparse

from app import app
from workers.worker import Worker
from workers.repomirrorworker import process_mirrors
from util.repomirror.validator import RepoMirrorConfigValidator
from util.repomirror.skopeomirror import SkopeoMirror
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)

DEFAULT_MIRROR_INTERVAL = 30


class RepoMirrorWorker(Worker):
    def __init__(self):
        super(RepoMirrorWorker, self).__init__()
        RepoMirrorConfigValidator(app.config.get("FEATURE_REPO_MIRROR", False)).valid()

        self._mirrorer = SkopeoMirror()
        self._next_token = None

        interval = app.config.get("REPO_MIRROR_INTERVAL", DEFAULT_MIRROR_INTERVAL)
        self.add_operation(self._process_mirrors, interval)

    def _process_mirrors(self):
        while True:
            assert app.config.get("FEATURE_REPO_MIRROR", False)

            self._next_token = process_mirrors(self._mirrorer, self._next_token)
            if self._next_token is None:
                break


def create_gunicorn_worker() -> GunicornWorker:
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, RepoMirrorWorker())
    return worker


if __name__ == "__main__":
    pydev_debug = os.getenv("PYDEV_DEBUG", None)
    if pydev_debug:
        import pydevd_pycharm

        host, port = pydev_debug.split(":")
        pydevd_pycharm.settrace(
            host, port=int(port), stdoutToServer=True, stderrToServer=True, suspend=False
        )

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", metavar="MODE", type=str, nargs="?", default="", choices=["mirror", ""]
    )
    args = parser.parse_args()

    worker = RepoMirrorWorker()
    worker.start()
