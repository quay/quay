import logging
import time

import features

from app import app, authentication
from data.users.teamsync import sync_teams_to_groups
from workers.worker import Worker
from util.timedeltastring import convert_to_timedelta
from util.log import logfile_path


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


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not features.TEAM_SYNCING or not authentication.federated_service:
        logger.debug("Team syncing is disabled; sleeping")
        while True:
            time.sleep(100000)

    worker = TeamSynchronizationWorker()
    worker.start()


if __name__ == "__main__":
    main()
