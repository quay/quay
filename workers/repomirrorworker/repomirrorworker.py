import argparse
import logging.config
import os
import time

import features
from app import app, repo_mirror_api
from util.log import logfile_path
from util.repomirror.skopeomirror import SkopeoMirror
from util.repomirror.validator import RepoMirrorConfigValidator
from workers.gunicorn_worker import GunicornWorker
from workers.repomirrorworker import (
    process_mirrors,
    process_org_mirror_discovery,
    process_org_mirrors,
)
from workers.worker import Worker

logger = logging.getLogger(__name__)

DEFAULT_MIRROR_INTERVAL = 30


class RepoMirrorWorker(Worker):
    def __init__(self):
        super(RepoMirrorWorker, self).__init__()
        RepoMirrorConfigValidator(app.config.get("FEATURE_REPO_MIRROR", False)).valid()

        self._mirrorer = SkopeoMirror()
        self._next_token = None
        self._org_discovery_token = None
        self._org_next_token = None

        # Repository-level mirror operation
        interval = app.config.get("REPO_MIRROR_INTERVAL", DEFAULT_MIRROR_INTERVAL)
        self.add_operation(self._process_mirrors, interval)

        # Organization-level mirror operations (if enabled)
        # Discovery phase runs first to populate OrgMirrorRepository table
        org_interval = app.config.get("ORG_MIRROR_INTERVAL", DEFAULT_MIRROR_INTERVAL)
        self.add_operation(self._process_org_mirror_discovery, org_interval)
        self.add_operation(self._process_org_mirrors, org_interval)

    def _process_mirrors(self):
        while True:
            assert app.config.get("FEATURE_REPO_MIRROR", False)

            self._next_token = process_mirrors(self._mirrorer, self._next_token)
            if self._next_token is None:
                break

    def _process_org_mirror_discovery(self):
        """
        Discover repositories from source registries for org-level mirrors.

        Phase 1: Fetches repository list from source, applies filters,
        and populates OrgMirrorRepository table for subsequent sync.
        """
        while True:
            self._org_discovery_token = process_org_mirror_discovery(self._org_discovery_token)
            if self._org_discovery_token is None:
                break

    def _process_org_mirrors(self):
        """
        Process organization-level mirror repositories.

        Phase 2: Syncs tags for discovered repositories in OrgMirrorRepository table.
        """
        while True:
            self._org_next_token = process_org_mirrors(self._mirrorer, self._org_next_token)
            if self._org_next_token is None:
                break


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, app, RepoMirrorWorker(), features.REPO_MIRROR)
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

    if not features.REPO_MIRROR:
        logger.debug("Repository mirror disabled; skipping RepoMirrorWorker")
        while True:
            time.sleep(100000)

    worker = RepoMirrorWorker()
    worker.start()
