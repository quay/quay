import logging
import time

from prometheus_client import Gauge

from app import app
from data import model
from data.database import UseThenDisconnect
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from workers.worker import Worker
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)

repository_rows = Gauge("quay_repository_rows", "number of repositories in the database")
user_rows = Gauge("quay_user_rows", "number of users in the database")
org_rows = Gauge("quay_org_rows", "number of organizations in the database")
robot_rows = Gauge("quay_robot_rows", "number of robot accounts in the database")


WORKER_FREQUENCY = app.config.get("GLOBAL_PROMETHEUS_STATS_FREQUENCY", 60 * 60)


def get_repository_count():
    return model.repository.get_estimated_repository_count()


def get_active_user_count():
    return model.user.get_active_user_count()


def get_active_org_count():
    return model.organization.get_active_org_count()


def get_robot_count():
    return model.user.get_estimated_robot_count()


class GlobalPrometheusStatsWorker(Worker):
    """
    Worker which reports global stats (# of users, orgs, repos, etc) to Prometheus periodically.
    """

    def __init__(self):
        super(GlobalPrometheusStatsWorker, self).__init__()
        self.add_operation(self._try_report_stats, WORKER_FREQUENCY)

    def _try_report_stats(self):
        logger.debug("Attempting to report stats")

        try:
            with GlobalLock("GLOBAL_PROM_STATS"):
                self._report_stats()
        except LockNotAcquiredException:
            logger.debug("Could not acquire global lock for global prometheus stats")

    def _report_stats(self):
        logger.debug("Reporting global stats")
        with UseThenDisconnect(app.config):
            repository_rows.set(get_repository_count())
            user_rows.set(get_active_user_count())
            org_rows.set(get_active_org_count())
            robot_rows.set(get_robot_count())


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    feature_flag = app.config.get("PROMETHEUS_PUSHGATEWAY_URL") is not None
    worker = GunicornWorker(__name__, app, GlobalPrometheusStatsWorker(), feature_flag)
    return worker


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not app.config.get("PROMETHEUS_PUSHGATEWAY_URL"):
        logger.debug("Prometheus not enabled; skipping global stats reporting")
        while True:
            time.sleep(100000)

    GlobalLock.configure(app.config)
    worker = GlobalPrometheusStatsWorker()
    worker.start()


if __name__ == "__main__":
    main()
