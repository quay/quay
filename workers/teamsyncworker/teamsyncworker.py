import logging
import time

import features

from app import app, authentication
from data.users.teamsync import sync_teams_to_groups
from workers.worker import Worker
from util.timedeltastring import convert_to_timedelta
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)


WORKER_FREQUENCY = app.config.get("TEAM_SYNC_WORKER_FREQUENCY", 60)
STALE_CUTOFF = convert_to_timedelta(app.config.get("TEAM_RESYNC_STALE_TIME", "30m"))


class TeamSynchronizationWorker(Worker):
    """
    Worker which synchronizes teams with their backing groups in LDAP/Keystone/etc.
    """

    def __init__(self):
        super(TeamSynchronizationWorker, self).__init__()
        self.add_operation(self._sync_teams_to_groups, WORKER_FREQUENCY)

    def _sync_teams_to_groups(self):
        sync_teams_to_groups(authentication, STALE_CUTOFF)


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    feature_flag = (features.TEAM_SYNCING) and (authentication.federated_service)
    worker = GunicornWorker(__name__, app, TeamSynchronizationWorker(), feature_flag)
    return worker


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.TEAM_SYNCING or not authentication.federated_service:
        logger.debug("Team syncing is disabled; sleeping")
        while True:
            time.sleep(100000)

    worker = TeamSynchronizationWorker()
    worker.start()


if __name__ == "__main__":
    main()
