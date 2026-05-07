# -*- coding: utf-8 -*-
"""
Repository Mirror Health Endpoint

Provides health status and monitoring information for repository mirroring operations.
"""

import logging
from datetime import datetime, timedelta, timezone

from peewee import Case, fn
from prometheus_client import REGISTRY

import features
from app import app
from auth.auth_context import get_authenticated_user
from auth.permissions import OrganizationMemberPermission, UserAdminPermission
from data import model
from data.database import (
    RepoMirrorConfig,
    RepoMirrorStatus,
    Repository,
    RepositoryState,
    User,
)
from endpoints.api import (
    ApiResource,
    allow_if_global_readonly_superuser,
    allow_if_superuser,
    nickname,
    parse_args,
    query_param,
    require_fresh_login,
    resource,
    show_if,
)
from endpoints.exception import NotFound, Unauthorized
from util.parsing import truthy_bool

logger = logging.getLogger(__name__)

_MAX_DETAIL_PAGE = 1000
_ISSUE_SAMPLE_CAP = 5

_CACHE_CONTROL_NO_STORE = "no-cache, no-store, must-revalidate"


def _utc_z_timestamp(when: datetime) -> str:
    """Format an aware UTC datetime as ISO-8601 with Z suffix."""
    utc = when.astimezone(timezone.utc)
    return utc.isoformat().replace("+00:00", "Z")


def _get_last_sync_timestamps():
    """
    Retrieve last sync timestamps from the Prometheus registry in this process.

    Mirror timestamps are emitted by the repository mirror worker. API/gunicorn processes
    typically do not run that worker, so REGISTRY often has no samples and this returns {}.
    In that case stale-mirror warnings are skipped (not treated as errors).

    Returns a dict keyed by (namespace, repository) with unix timestamps as values.
    If the metric is not present in this process, returns an empty dict.
    """
    timestamps = {}
    try:
        for metric in REGISTRY.collect():
            if metric.name != "quay_repository_mirror_last_sync_timestamp":
                continue
            for sample in metric.samples:
                if sample.name != "quay_repository_mirror_last_sync_timestamp":
                    continue
                namespace = sample.labels.get("namespace")
                repository = sample.labels.get("repository")
                if namespace and repository:
                    timestamps[(namespace, repository)] = sample.value
            break
    except Exception as ex:
        logger.debug("Unable to read last sync timestamps from registry: %s", ex)
    return timestamps


def _get_pending_tags_total(namespace=None):
    """
    Sum quay_repository_mirror_pending_tags gauge values from this process's registry.

    Same limitation as _get_last_sync_timestamps: values exist only if the mirror worker
    registers metrics in this process; otherwise this returns 0.
    """
    total = 0.0
    try:
        for metric in REGISTRY.collect():
            if metric.name != "quay_repository_mirror_pending_tags":
                continue
            for sample in metric.samples:
                if sample.name != "quay_repository_mirror_pending_tags":
                    continue
                if namespace is not None and sample.labels.get("namespace") != namespace:
                    continue
                total += float(sample.value)
            break
    except Exception as ex:
        logger.debug("Unable to read pending tags from registry: %s", ex)
    return int(total) if total == int(total) else total


def _get_mirror_workers_active_value():
    """
    Read quay_repository_mirror_workers_active from this process's Prometheus registry.

    The repository mirror worker sets this to 1 while RepoMirrorWorker is running; API
    processes typically report 0 unless they embed the worker.
    """
    try:
        for metric in REGISTRY.collect():
            if metric.name != "quay_repository_mirror_workers_active":
                continue
            for sample in metric.samples:
                if sample.name != "quay_repository_mirror_workers_active":
                    continue
                return int(sample.value)
            break
    except Exception as ex:
        logger.debug("Unable to read mirror workers active gauge from registry: %s", ex)
    return 0


def _mirror_rows_query(namespace=None):
    """
    Enabled RepoMirrorConfig rows with Repository and namespace User joined and selected
    so repository.namespace_user is populated (avoids N+1 on .username).

    Health aggregates and issue sampling use enabled configs only; disabled mirrors
    are omitted from totals and from this listing.
    """
    q = (
        RepoMirrorConfig.select(RepoMirrorConfig, Repository, User)
        .join(Repository)
        .switch(Repository)
        .join(User, on=(Repository.namespace_user == User.id))
        .where(
            Repository.state == RepositoryState.MIRROR,
            RepoMirrorConfig.is_enabled == True,
        )
    )
    if namespace:
        q = q.where(User.username == namespace)
    return q.order_by(Repository.namespace_user_id, Repository.name)


def _mirror_status_counts(namespace=None):
    """Aggregated status counts for enabled mirror configs only (no row load)."""
    syncing_sum = fn.SUM(
        Case(None, [(RepoMirrorConfig.sync_status == RepoMirrorStatus.SYNCING, 1)], 0)
    )
    completed_sum = fn.SUM(
        Case(None, [(RepoMirrorConfig.sync_status == RepoMirrorStatus.SUCCESS, 1)], 0)
    )
    failed_sum = fn.SUM(Case(None, [(RepoMirrorConfig.sync_status == RepoMirrorStatus.FAIL, 1)], 0))
    never_run_sum = fn.SUM(
        Case(None, [(RepoMirrorConfig.sync_status == RepoMirrorStatus.NEVER_RUN, 1)], 0)
    )
    q = (
        RepoMirrorConfig.select(
            fn.COUNT(RepoMirrorConfig.id).alias("total"),
            syncing_sum.alias("syncing"),
            completed_sum.alias("completed"),
            failed_sum.alias("failed"),
            never_run_sum.alias("never_run"),
        )
        .join(Repository)
        .switch(Repository)
        .join(User, on=(Repository.namespace_user == User.id))
        .where(
            Repository.state == RepositoryState.MIRROR,
            RepoMirrorConfig.is_enabled == True,
        )
    )
    if namespace:
        q = q.where(User.username == namespace)
    dict_rows = list(q.dicts())
    row = dict_rows[0] if dict_rows else {}
    return {
        "total": int(row["total"] or 0),
        "syncing": int(row["syncing"] or 0),
        "completed": int(row["completed"] or 0),
        "failed": int(row["failed"] or 0),
        "never_run": int(row["never_run"] or 0),
    }


def get_mirror_health_data(
    namespace=None,
    detailed=False,
    detail_limit=100,
    detail_offset=0,
):
    """
    Gather health data for repository mirroring operations.

    Args:
        namespace: Optional namespace to filter results
        detailed: If true, include paginated per-repository rows under repositories.details
        detail_limit: Max repositories in detailed view (clamped 1..1000)
        detail_offset: Pagination offset into the sorted mirror list (SQL LIMIT/OFFSET)

    Returns:
        Dictionary with health status information. Totals and `details` use enabled
        mirror configs only.
    """
    counts = _mirror_status_counts(namespace)
    total_repos = counts["total"]
    syncing = counts["syncing"]
    completed = counts["completed"]
    failed = counts["failed"]
    never_run = counts["never_run"]

    # From in-process Prometheus registry when mirror worker shares this process; else 0.
    tags_pending = _get_pending_tags_total(namespace)

    # Determine overall health status
    now = datetime.now(timezone.utc)
    issues = []

    # Stale detection: last sync from quay_repository_mirror_last_sync_timestamp in REGISTRY—not
    # mirror.sync_start_date (that field is the next scheduled run). Missing samples: skip stale
    # (never-synced NEVER_RUN handled separately); enabled repos with no metric are not flagged stale.
    stale_threshold = now - timedelta(hours=24)
    last_sync_timestamps = _get_last_sync_timestamps()
    stale_repos = []
    never_synced_repos = []
    failing_repos = []
    repos_detail = []
    has_more = False
    lim = max(1, min(int(detail_limit), _MAX_DETAIL_PAGE)) if detailed else 0
    off = max(0, int(detail_offset)) if detailed else 0

    # Bounded queries: sample up to _ISSUE_SAMPLE_CAP of each issue type via SQL LIMIT.
    failing_repos = list(
        _mirror_rows_query(namespace)
        .where(
            RepoMirrorConfig.sync_status == RepoMirrorStatus.FAIL,
            RepoMirrorConfig.sync_retries_remaining == 0,
        )
        .limit(_ISSUE_SAMPLE_CAP)
    )

    never_synced_repos = list(
        _mirror_rows_query(namespace)
        .where(RepoMirrorConfig.sync_status == RepoMirrorStatus.NEVER_RUN)
        .limit(_ISSUE_SAMPLE_CAP)
    )

    # Stale detection uses in-process Prometheus timestamps (bounded by registry size).
    for (ns, repo), ts in last_sync_timestamps.items():
        if len(stale_repos) >= _ISSUE_SAMPLE_CAP:
            break
        if namespace and ns != namespace:
            continue
        last_sync_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if last_sync_dt < stale_threshold:
            stale_repos.append({"namespace": ns, "repository": repo})

    if detailed:
        page_query = _mirror_rows_query(namespace).limit(lim + 1).offset(off)
        page_rows = list(page_query)
        has_more = len(page_rows) > lim
        page_rows = page_rows[:lim]
        for mirror in page_rows:
            namespace_name = mirror.repository.namespace_user.username
            repo_name = mirror.repository.name
            last_sync_ts = last_sync_timestamps.get((namespace_name, repo_name))
            last_sync_value = None
            if last_sync_ts is not None:
                last_sync_value = (
                    datetime.fromtimestamp(last_sync_ts, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )
            repos_detail.append(
                {
                    "namespace": namespace_name,
                    "repository": repo_name,
                    "sync_status": mirror.sync_status.name,
                    "is_enabled": mirror.is_enabled,
                    "last_sync": last_sync_value,
                    "retries_remaining": mirror.sync_retries_remaining,
                }
            )

    if stale_repos:
        for repo in stale_repos[:_ISSUE_SAMPLE_CAP]:
            ns = repo["namespace"] if isinstance(repo, dict) else repo.repository.namespace_user.username
            name = repo["repository"] if isinstance(repo, dict) else repo.repository.name
            issues.append(
                {
                    "severity": "warning",
                    "message": f"Repository {ns}/{name} hasn't synced in over 24 hours",
                    "timestamp": _utc_z_timestamp(now),
                }
            )
    if never_synced_repos:
        for repo in never_synced_repos[:5]:  # Limit to first 5 for brevity
            issues.append(
                {
                    "severity": "warning",
                    "message": f"Repository {repo.repository.namespace_user.username}/{repo.repository.name} has never been synced",
                    "timestamp": _utc_z_timestamp(now),
                }
            )

    if failing_repos:
        for repo in failing_repos[:5]:  # Limit to first 5
            issues.append(
                {
                    "severity": "error",
                    "message": f"Repository {repo.repository.namespace_user.username}/{repo.repository.name} has exhausted all retry attempts",
                    "timestamp": _utc_z_timestamp(now),
                }
            )

    # Determine if system is healthy
    # System is unhealthy if:
    # - More than 20% of repos that have run (non-NEVER_RUN) are failing
    # - Any critical errors exist
    critical_threshold = 0.2
    healthy = True

    mirrors_for_failure_rate = total_repos - never_run
    if mirrors_for_failure_rate > 0:
        failure_rate = failed / mirrors_for_failure_rate
        if failure_rate > critical_threshold:
            healthy = False
            issues.insert(
                0,
                {
                    "severity": "critical",
                    "message": (
                        f"{failure_rate * 100:.1f}% of repositories are failing "
                        f"(threshold: {critical_threshold * 100:.1f}%)"
                    ),
                    "timestamp": _utc_z_timestamp(now),
                },
            )

    replicas = app.config.get("REPO_MIRROR_WORKER_REPLICAS")
    active_workers = _get_mirror_workers_active_value()
    configured_workers = replicas if replicas is not None else active_workers

    if replicas is not None and total_repos > 0 and active_workers < replicas:
        healthy = False
        issues.insert(
            0,
            {
                "severity": "warning",
                "message": (
                    f"{replicas - active_workers} mirror worker(s) are not reporting in this "
                    f"process (REPO_MIRROR_WORKER_REPLICAS={replicas}, "
                    f"quay_repository_mirror_workers_active={active_workers})"
                ),
                "timestamp": _utc_z_timestamp(now),
            },
        )

    # workers.status: aggregate health (repository states and optional replica mismatch).
    workers_status = "healthy" if healthy else "degraded"

    result = {
        "healthy": healthy,
        "workers": {
            "active": active_workers,
            "configured": configured_workers,
            "status": workers_status,
        },
        "repositories": {
            "total": total_repos,
            "syncing": syncing,
            "completed": completed,
            "failed": failed,
            "never_run": never_run,
        },
        "tags_pending": tags_pending,
        "last_check": _utc_z_timestamp(now),
        "issues": issues,
    }

    if detailed:
        result["repositories"]["details"] = repos_detail
        result["repositories"]["pagination"] = {
            "limit": lim,
            "offset": off,
            "has_more": has_more,
        }

    return result


@resource("/v1/repository/mirror/health")
@show_if(features.REPO_MIRROR)
class RepositoryMirrorHealth(ApiResource):
    """
    Resource for checking the health of repository mirroring operations.
    """

    @require_fresh_login
    @nickname("getRepositoryMirrorHealth")
    @parse_args()
    @query_param(
        "namespace",
        "Filter health check to specific namespace",
        type=str,
        default=None,
    )
    @query_param(
        "detailed",
        "Include per-repository breakdown",
        type=truthy_bool,
        default=False,
    )
    @query_param(
        "limit",
        "Maximum repositories in detailed view (when detailed=true)",
        type=int,
        default=100,
    )
    @query_param(
        "offset",
        "Offset into the sorted mirror list for detailed view",
        type=int,
        default=0,
    )
    def get(self, parsed_args):
        """
        Get the health status of repository mirroring operations.

        Returns overall health status, `workers.status` (repository-derived summary),
        and any issues. HTTP status reflects health: 200 for healthy, 503 for unhealthy.
        """
        namespace = parsed_args.get("namespace")
        detailed = parsed_args.get("detailed", False)
        detail_limit = parsed_args.get("limit", 100)
        detail_offset = parsed_args.get("offset", 0)

        authed_user = get_authenticated_user()
        if not authed_user:
            raise Unauthorized()

        # Global access requires superuser or global readonly superuser
        if namespace is None:
            if not (allow_if_superuser() or allow_if_global_readonly_superuser()):
                raise Unauthorized()
        else:
            namespace_user = model.user.get_namespace_user(namespace)
            if not namespace_user:
                raise NotFound()
            if not (allow_if_superuser() or allow_if_global_readonly_superuser()):
                if namespace_user.organization:
                    if not OrganizationMemberPermission(namespace).can():
                        raise Unauthorized()
                else:
                    if (
                        authed_user.username != namespace
                        and not UserAdminPermission(namespace).can()
                    ):
                        raise Unauthorized()

        health_data = get_mirror_health_data(
            namespace=namespace,
            detailed=detailed,
            detail_limit=detail_limit,
            detail_offset=detail_offset,
        )

        # Return 503 if unhealthy, 200 if healthy
        status_code = 200 if health_data["healthy"] else 503

        return (
            health_data,
            status_code,
            {"Cache-Control": _CACHE_CONTROL_NO_STORE},
        )
