import logging
import logging.config

from data.users.teamsync import sync_teams_to_groups
from singletons.authentication import authentication
from singletons.config import app_config
from util.log import logfile_path
from util.timedeltastring import convert_to_timedelta
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

WORKER_FREQUENCY = app_config.get("TEAM_SYNC_WORKER_FREQUENCY", 60)
STALE_CUTOFF = convert_to_timedelta(app_config.get("TEAM_RESYNC_STALE_TIME", "30m"))


class TeamSynchronizationWorker(Worker):
    """
    Worker which synchronizes teams with their backing groups in LDAP/Keystone/etc.
    """

    def __init__(self):
        super(TeamSynchronizationWorker, self).__init__()
        self.add_operation(self._sync_teams_to_groups, WORKER_FREQUENCY)

    def _sync_teams_to_groups(self):
        sync_teams_to_groups(authentication, STALE_CUTOFF)


def create_gunicorn_worker() -> GunicornWorker:
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, TeamSynchronizationWorker())
    return worker


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    worker = TeamSynchronizationWorker()
    worker.start()


if __name__ == "__main__":
    main()
