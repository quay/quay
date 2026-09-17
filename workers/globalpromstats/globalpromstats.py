import logging
import time

from prometheus_client import Gauge

from app import app
from data import model
from data.database import UseThenDisconnect
from data.model.org_mirror import (
    get_enabled_org_mirror_config_count,
    get_org_mirror_config_count,
)
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

repository_rows = Gauge("quay_repository_rows", "number of repositories in the database")
user_rows = Gauge("quay_user_rows", "number of users in the database")
org_rows = Gauge("quay_org_rows", "number of organizations in the database")
robot_rows = Gauge("quay_robot_rows", "number of robot accounts in the database")
org_mirror_configs_total = Gauge(
    "quay_org_mirrors_total", "number of org-level mirror configurations in the database"
)
org_mirror_configs_enabled = Gauge(
    "quay_org_mirrors_enabled", "number of enabled org-level mirror configurations in the database"
)
registry_total_used_bytes = Gauge(
    "quay_registry_total_used_bytes",
    "Storage consumption in bytes for the entire registry",
)
namespace_stats_used_bytes = Gauge(
    "quay_namespace_stats_used_bytes",
    "Storage consumption in bytes per namespace",
    labelnames=["namespace", "entity_type"],
)
repository_stats_used_bytes = Gauge(
    "quay_repository_stats_used_bytes",
    "Storage consumption in bytes per repository",
    labelnames=["repository", "namespace"],
)
namespace_quota_stats_capacity_bytes = Gauge(
    "quay_namespace_quota_stats_capacity_bytes",
    "Storage quota in bytes per namespace",
    labelnames=["namespace", "entity_type"],
)
namespace_quota_stats_available_bytes = Gauge(
    "quay_namespace_quota_stats_available_bytes",
    "Remaining storage capacity per quota in bytes per namespace",
    labelnames=["namespace", "entity_type"],
)


WORKER_FREQUENCY = app.config.get("GLOBAL_PROMETHEUS_STATS_FREQUENCY", 60 * 60)
QUOTA_METRICS = app.config.get("QUOTA_METRICS", False)
QUOTA_METRICS_REPOS_LIMIT = app.config.get("QUOTA_METRICS_REPOS_LIMIT", 10000)
QUOTA_METRICS_NAMESPACES_LIMIT = app.config.get("QUOTA_METRICS_NAMESPACES_LIMIT", 10000)


def get_repository_count():
    return model.repository.get_estimated_repository_count()


def get_active_user_count():
    return model.user.get_active_user_count()


def get_active_org_count():
    return model.organization.get_active_org_count()


def get_robot_count():
    return model.user.get_estimated_robot_count()


def populate_namespace_quota_stats():
    """Populate namespace usage, quota capacity and available-bytes metrics.

    Iterates both namespace sizes and quota records so that namespaces with a
    quota but no QuotaNamespaceSize row yet (e.g. before backfill completes)
    still emit capacity and available-bytes metrics with usage treated as zero.

    At most QUOTA_METRICS_NAMESPACES_LIMIT namespaces are processed per cycle.
    The limit is pushed into the database generators to bound memory, database
    work and metric cardinality on large registries.
    """
    namespace_stats_used_bytes._metrics.clear()
    namespace_quota_stats_capacity_bytes._metrics.clear()
    namespace_quota_stats_available_bytes._metrics.clear()

    limit = QUOTA_METRICS_NAMESPACES_LIMIT

    namespace_quotas = {}
    for row in model.namespacequota.get_namespaces_with_quotas(max_rows=limit):
        namespace_quotas[row["id"]] = row

    seen_namespace_ids = set()
    count = 0

    for namespace in model.quota.get_all_namespace_sizes(max_rows=limit):
        namespace_id = namespace["id"]
        namespace_name = namespace["username"]
        namespace_entity_type = "organization" if namespace["organization"] else "user"
        namespace_used_bytes = namespace["size_bytes"]
        seen_namespace_ids.add(namespace_id)
        count += 1

        namespace_stats_used_bytes.labels(
            namespace=namespace_name, entity_type=namespace_entity_type
        ).set(namespace_used_bytes)

        namespace_quota = namespace_quotas.get(namespace_id)

        if namespace_quota is not None:
            namespace_capacity = namespace_quota["limit_bytes"]
            namespace_available = max(0, namespace_capacity - namespace_used_bytes)

            namespace_quota_stats_capacity_bytes.labels(
                namespace=namespace_name, entity_type=namespace_entity_type
            ).set(namespace_capacity)
            namespace_quota_stats_available_bytes.labels(
                namespace=namespace_name, entity_type=namespace_entity_type
            ).set(namespace_available)

    for ns_id, quota in namespace_quotas.items():
        if ns_id in seen_namespace_ids:
            continue
        if count >= limit:
            break
        entity_type = "organization" if quota.get("organization") else "user"
        namespace_quota_stats_capacity_bytes.labels(
            namespace=quota["username"], entity_type=entity_type
        ).set(quota["limit_bytes"])
        namespace_quota_stats_available_bytes.labels(
            namespace=quota["username"], entity_type=entity_type
        ).set(quota["limit_bytes"])
        count += 1

    if count >= limit:
        logger.warning(
            "Namespace quota metrics limit reached (%d); "
            "remaining namespaces skipped this cycle",
            limit,
        )


def populate_repo_quota_stats():
    """Populate per-repository usage metrics with a bounded traversal.

    At most QUOTA_METRICS_REPOS_LIMIT repositories are processed per cycle.
    The limit is pushed into the database generator to bound memory, database
    work and metric cardinality on large registries.
    """
    repository_stats_used_bytes._metrics.clear()

    limit = QUOTA_METRICS_REPOS_LIMIT
    count = 0
    for repository in model.quota.get_all_repository_sizes(max_rows=limit):
        repository_stats_used_bytes.labels(
            repository=repository["name"], namespace=repository["namespace"]
        ).set(repository["size_bytes"])
        count += 1

    if count >= limit:
        logger.warning(
            "Repository quota metrics limit reached (%d); "
            "remaining repositories skipped this cycle",
            limit,
        )


def populate_registry_size_stats():
    """Populate the total registry storage consumption metric."""
    registry_size = model.quota.get_registry_size()

    if registry_size is not None:
        registry_total_used_bytes.set(registry_size.size_bytes)
    else:
        registry_total_used_bytes.set(0)


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
            org_mirror_configs_total.set(get_org_mirror_config_count())
            org_mirror_configs_enabled.set(get_enabled_org_mirror_config_count())

            if QUOTA_METRICS:
                logger.debug("Reporting quota stats")
                try:
                    populate_namespace_quota_stats()
                except Exception:
                    logger.exception("Failed to populate namespace quota stats")
                try:
                    populate_repo_quota_stats()
                except Exception:
                    logger.exception("Failed to populate repository quota stats")
                try:
                    populate_registry_size_stats()
                except Exception:
                    logger.exception("Failed to populate registry size stats")


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
