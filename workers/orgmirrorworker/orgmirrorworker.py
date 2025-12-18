"""
Organization mirror worker.

Runs periodically to discover and sync repositories at the organization level.
"""

import argparse
import logging
import logging.config
import os
import time

import features
from app import app
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.orgmirrorworker import process_org_mirrors
from workers.orgmirrorworker.org_mirror_model import org_mirror_model
from workers.worker import Worker

logger = logging.getLogger(__name__)

DEFAULT_ORG_MIRROR_INTERVAL = 30  # Process org mirrors every 30 seconds


class OrgMirrorWorker(Worker):
    """
    Worker to perform organization-level repository mirroring.

    Two-phase approach:
    1. Discovery: Enumerate repositories from source registry (stub for now)
    2. Creation: Create discovered repositories and mark status

    The worker claims organization mirrors using optimistic locking to coordinate
    with other workers in a distributed environment.
    """

    def __init__(self):
        super(OrgMirrorWorker, self).__init__()

        if not features.ORG_MIRROR:
            logger.warning("Organization mirror feature is disabled")
            return

        self._model = org_mirror_model
        self._next_token = None

        interval = app.config.get("ORG_MIRROR_INTERVAL", DEFAULT_ORG_MIRROR_INTERVAL)
        logger.info("OrgMirrorWorker initialized with interval: %s seconds", interval)

        self.add_operation(self._process_org_mirrors, interval)

    def _process_org_mirrors(self):
        """
        Process organization mirrors in a loop with pagination.

        Continues processing until no more work is available.
        """
        while True:
            if not features.ORG_MIRROR:
                logger.debug("Organization mirror disabled")
                return

            self._next_token = process_org_mirrors(self._model, self._next_token)

            if self._next_token is None:
                # No more work to do
                break


def create_gunicorn_worker():
    """
    Create gunicorn worker for organization mirroring.

    Follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    This is useful when utilizing gunicorn's hot reload in local dev.
    """
    worker = GunicornWorker(__name__, app, OrgMirrorWorker(), features.ORG_MIRROR)
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

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.ORG_MIRROR:
        logger.debug("Organization mirror disabled; skipping OrgMirrorWorker")
        while True:
            time.sleep(100000)

    worker = OrgMirrorWorker()
    worker.start()
