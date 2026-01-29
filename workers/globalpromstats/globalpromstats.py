import logging
import time

from prometheus_client import Gauge

from app import app
from data import model
from data.database import UseThenDisconnect
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

repository_rows = Gauge("quay_repository_rows", "number of repositories in the database")
user_rows = Gauge("quay_user_rows", "number of users in the database")
org_rows = Gauge("quay_org_rows", "number of organizations in the database")
robot_rows = Gauge("quay_robot_rows", "number of robot accounts in the database")
registry_total_used_bytes = Gauge(
    "registry_total_used_bytes",
    "Storage consumption in bytes for the entire registry",
)
namespace_stats_used_bytes = Gauge(
    "namespace_stats_used_bytes",
    "Storage consumption in bytes per namespace",
    labelnames=["namespace", "entity_type"],
)
repository_stats_used_bytes = Gauge(
    "repository_stats_used_bytes",
    "Storage consumption in bytes per repository",
    labelnames=["repository", "namespace"],
)
namespace_quota_stats_capacity_bytes = Gauge(
    "namespace_quota_stats_capacity_bytes",
    "Storage quota in bytes per namespace",
    labelnames=["namespace", "entity_type"],
)
namespace_quota_stats_available_bytes = Gauge(
    "namespace_quota_stats_available_bytes",
    "Remaining storage capacity per quota in bytes per namespace",
    labelnames=["namespace", "entity_type"],
)


WORKER_FREQUENCY = app.config.get("GLOBAL_PROMETHEUS_STATS_FREQUENCY", 60 * 60)
QUOTA_METRICS = app.config.get("QUOTA_METRICS", False)


def get_repository_count():
    return model.repository.get_estimated_repository_count()


def get_active_user_count():
    return model.user.get_active_user_count()


def get_active_org_count():
    return model.organization.get_active_org_count()


def get_robot_count():
    return model.user.get_estimated_robot_count()


def populate_namespace_quota_stats():
    namespaces = model.quota.get_all_namespace_sizes()
    namespace_quotas = model.namespacequota.get_namespaces_with_quotas()

    for namespace in namespaces:
        namespace_id = namespace["id"]
        namespace_name = namespace["username"]
        namespace_entity_type = "organization" if namespace["organization"] else "user"
        namespace_used_bytes = namespace["size_bytes"]

        namespace_stats_used_bytes.labels(
            namespace=namespace_name, entity_type=namespace_entity_type
        ).set(namespace_used_bytes)

        namespace_quota = next(
            (quota for quota in namespace_quotas if quota["id"] == namespace_id), None
        )

        if namespace_quota is not None:
            namespace_capacity = namespace_quota["limit_bytes"]
            namespace_available = (
                0
                if namespace_capacity < namespace_used_bytes
                else namespace_capacity - namespace_used_bytes
            )

            namespace_quota_stats_capacity_bytes.labels(
                namespace=namespace_name, entity_type=namespace_entity_type
            ).set(namespace_capacity)
            namespace_quota_stats_available_bytes.labels(
                namespace=namespace_name, entity_type=namespace_entity_type
            ).set(namespace_available)


def populate_repo_quota_stats():
    repositories = model.quota.get_all_repository_sizes()

    for repository in repositories:
        repository_name = repository["name"]
        repository_namespace = repository["namespace"]
        repository_used_bytes = repository["size_bytes"]

        repository_stats_used_bytes.labels(
            repository=repository_name, namespace=repository_namespace
        ).set(repository_used_bytes)


def populate_registry_size_stats():
    registry_size = model.quota.get_registry_size()

    if registry_size is not None:
        registry_total_used_bytes.set(registry_size.size_bytes)


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

            if QUOTA_METRICS:
                logger.debug("Reporting quota stats")
                populate_namespace_quota_stats()
                populate_repo_quota_stats()
                populate_registry_size_stats()


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

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not app.config.get("PROMETHEUS_PUSHGATEWAY_URL"):
        logger.debug("Prometheus not enabled; skipping global stats reporting")
        while True:
            time.sleep(100000)

    GlobalLock.configure(app.config)
    worker = GlobalPrometheusStatsWorker()
    worker.start()


if __name__ == "__main__":
    main()
