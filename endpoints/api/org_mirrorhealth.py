# -*- coding: utf-8 -*-
"""
Organization Mirror Health Endpoint

Provides health status and monitoring information for organization-level mirroring.
"""

import logging
from datetime import datetime, timedelta, timezone

from peewee import JOIN

import features
from app import app
from auth.auth_context import get_authenticated_user
from auth.permissions import OrganizationMemberPermission
from data import model
from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepository,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
    Repository,
    RepositoryState,
)
from endpoints.api import (
    ApiResource,
    allow_if_global_readonly_superuser,
    allow_if_superuser,
    nickname,
    parse_args,
    path_param,
    query_param,
    require_fresh_login,
    resource,
    show_if,
)
from endpoints.exception import NotFound, Unauthorized
from util.metrics.mirror_registry import (
    get_metric_timestamps,
    get_mirror_workers_active_value,
    get_namespace_gauge_value,
    get_pending_tags_total,
)
from util.parsing import truthy_bool

logger = logging.getLogger(__name__)

_MAX_DETAIL_PAGE = 1000
_ISSUE_SAMPLE_CAP = 5
_CACHE_CONTROL_NO_STORE = "no-cache, no-store, must-revalidate"


def _utc_z_timestamp(when: datetime) -> str:
    utc = when.astimezone(timezone.utc)
    return utc.isoformat().replace("+00:00", "Z")


def _org_mirror_repo_rows_query(config: OrgMirrorConfig):
    return (
        OrgMirrorRepository.select()
        .join(Repository, JOIN.LEFT_OUTER, on=(OrgMirrorRepository.repository == Repository.id))
        .where(OrgMirrorRepository.org_mirror_config == config)
        .where(
            (OrgMirrorRepository.repository >> None)
            | (Repository.state != RepositoryState.MARKED_FOR_DELETION)
        )
        .order_by(OrgMirrorRepository.repository_name)
    )


def _config_status_indicators(sync_status: OrgMirrorStatus) -> dict:
    return {
        "syncing": 1 if sync_status == OrgMirrorStatus.SYNCING else 0,
        "completed": 1 if sync_status == OrgMirrorStatus.SUCCESS else 0,
        "failed": 1 if sync_status == OrgMirrorStatus.FAIL else 0,
        "never_run": 1 if sync_status == OrgMirrorStatus.NEVER_RUN else 0,
    }


def _aggregate_repo_counts(status_counts: dict) -> dict:
    syncing = status_counts.get("SYNCING", 0) + status_counts.get("SYNC_NOW", 0)
    return {
        "total": sum(status_counts.values()),
        "syncing": syncing,
        "completed": status_counts.get("SUCCESS", 0),
        "failed": status_counts.get("FAIL", 0),
        "never_run": status_counts.get("NEVER_RUN", 0),
        "skipped": status_counts.get("SKIP", 0),
    }


def _discovery_status_from_registry(orgname: str, config: OrgMirrorConfig):
    """
    Return (status_int, timestamp_iso_or_none) from in-process metrics when available.
    """
    metric_status = get_namespace_gauge_value(
        "quay_org_mirror_last_discovery_status",
        orgname,
    )
    metric_ts = get_namespace_gauge_value(
        "quay_org_mirror_last_discovery_timestamp",
        orgname,
    )

    if metric_status is not None:
        status_int = int(metric_status)
    else:
        if config.sync_status == OrgMirrorStatus.SYNCING:
            status_int = 2
        elif config.sync_status == OrgMirrorStatus.SUCCESS:
            status_int = 1
        elif config.sync_status == OrgMirrorStatus.FAIL:
            status_int = 0
        else:
            status_int = 0

    timestamp_value = None
    if metric_ts is not None:
        timestamp_value = (
            datetime.fromtimestamp(metric_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        )
    elif config.sync_start_date is not None:
        timestamp_value = _utc_z_timestamp(config.sync_start_date)

    return status_int, timestamp_value


def get_org_mirror_health_data(
    orgname: str,
    detailed: bool = False,
    detail_limit: int = 100,
    detail_offset: int = 0,
):
    """
    Gather health data for organization-level mirroring for a single organization.
    """
    org = model.user.get_namespace_user(orgname)
    if not org or not org.organization:
        raise NotFound()

    config = model.org_mirror.get_org_mirror_config(org)
    if not config:
        raise NotFound()

    now = datetime.now(timezone.utc)
    issues = []
    healthy = True

    status_counts = model.org_mirror.get_org_mirror_repo_status_counts(config)
    repo_counts = _aggregate_repo_counts(status_counts)
    tags_pending = get_pending_tags_total("quay_org_mirror_pending_tags", orgname)
    repo_counts["tags_pending"] = tags_pending

    discovery_status, discovery_timestamp = _discovery_status_from_registry(orgname, config)
    org_block = {
        **_config_status_indicators(config.sync_status),
        "last_discovery_status": discovery_status,
        "last_discovery_timestamp": discovery_timestamp,
        "repositories": repo_counts,
    }

    last_sync_timestamps = get_metric_timestamps(
        "quay_org_mirror_last_sync_timestamp",
        namespace=orgname,
    )
    stale_threshold = now - timedelta(hours=24)
    stale_repos = []
    lim = max(1, min(int(detail_limit), _MAX_DETAIL_PAGE)) if detailed else 0
    off = max(0, int(detail_offset)) if detailed else 0
    repos_detail = []
    has_more = False

    failing_repos = list(
        _org_mirror_repo_rows_query(config)
        .where(
            OrgMirrorRepository.sync_status == OrgMirrorRepoStatus.FAIL,
            OrgMirrorRepository.sync_retries_remaining == 0,
        )
        .limit(_ISSUE_SAMPLE_CAP)
    )

    never_synced_repos = []
    if config.sync_status == OrgMirrorStatus.SUCCESS:
        never_synced_repos = list(
            _org_mirror_repo_rows_query(config)
            .where(OrgMirrorRepository.sync_status == OrgMirrorRepoStatus.NEVER_RUN)
            .limit(_ISSUE_SAMPLE_CAP)
        )

    for (ns, repo), ts in last_sync_timestamps.items():
        if len(stale_repos) >= _ISSUE_SAMPLE_CAP:
            break
        if ns != orgname:
            continue
        last_sync_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if last_sync_dt < stale_threshold:
            stale_repos.append({"namespace": ns, "repository": repo})

    if config.sync_status == OrgMirrorStatus.FAIL:
        healthy = False
        issues.append(
            {
                "severity": "error",
                "message": (
                    f"Organization mirror configuration for '{orgname}' is in a failed state"
                ),
                "timestamp": _utc_z_timestamp(now),
            }
        )

    if stale_repos:
        for repo in stale_repos[:_ISSUE_SAMPLE_CAP]:
            issues.append(
                {
                    "severity": "warning",
                    "message": (
                        f"Repository {repo['namespace']}/{repo['repository']} "
                        "hasn't synced in over 24 hours"
                    ),
                    "timestamp": _utc_z_timestamp(now),
                }
            )

    if never_synced_repos:
        for repo in never_synced_repos[:_ISSUE_SAMPLE_CAP]:
            issues.append(
                {
                    "severity": "warning",
                    "message": (
                        f"Repository {orgname}/{repo.repository_name} has never been synced"
                    ),
                    "timestamp": _utc_z_timestamp(now),
                }
            )

    if failing_repos:
        for repo in failing_repos[:_ISSUE_SAMPLE_CAP]:
            issues.append(
                {
                    "severity": "error",
                    "message": (
                        f"Repository {orgname}/{repo.repository_name} "
                        "has exhausted all retry attempts"
                    ),
                    "timestamp": _utc_z_timestamp(now),
                }
            )

    mirrors_for_failure_rate = (
        repo_counts["total"] - repo_counts["never_run"] - repo_counts["skipped"]
    )
    critical_threshold = 0.2
    if mirrors_for_failure_rate > 0:
        failure_rate = repo_counts["failed"] / mirrors_for_failure_rate
        if failure_rate > critical_threshold:
            healthy = False
            issues.insert(
                0,
                {
                    "severity": "critical",
                    "message": (
                        f"{failure_rate * 100:.1f}% of discovered repositories are failing "
                        f"(threshold: {critical_threshold * 100:.1f}%)"
                    ),
                    "timestamp": _utc_z_timestamp(now),
                },
            )

    replicas = app.config.get("REPO_MIRROR_WORKER_REPLICAS")
    active_workers = get_mirror_workers_active_value()
    configured_workers = replicas if replicas is not None else active_workers

    # Replica mismatch uses PushGateway worker counts (fresh groupings only). Skip when
    # no workers report in, avoiding false 503s when metrics are unavailable.
    if (
        replicas is not None
        and config.is_enabled
        and features.ORG_MIRROR
        and active_workers > 0
        and active_workers < replicas
    ):
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

    workers_status = "healthy" if healthy else "degraded"

    if detailed:
        page_query = _org_mirror_repo_rows_query(config).limit(lim + 1).offset(off)
        page_rows = list(page_query)
        has_more = len(page_rows) > lim
        page_rows = page_rows[:lim]
        for repo_row in page_rows:
            last_sync_ts = last_sync_timestamps.get((orgname, repo_row.repository_name))
            last_sync_value = None
            if last_sync_ts is not None:
                last_sync_value = (
                    datetime.fromtimestamp(last_sync_ts, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )
            elif repo_row.last_sync_date is not None:
                last_sync_value = _utc_z_timestamp(repo_row.last_sync_date)

            repos_detail.append(
                {
                    "namespace": orgname,
                    "repository": repo_row.repository_name,
                    "sync_status": repo_row.sync_status.name,
                    "last_sync": last_sync_value,
                    "retries_remaining": repo_row.sync_retries_remaining,
                    "status_message": repo_row.status_message,
                }
            )

        org_block["repositories"]["details"] = repos_detail
        org_block["repositories"]["pagination"] = {
            "limit": lim,
            "offset": off,
            "has_more": has_more,
        }

    return {
        "healthy": healthy,
        "workers": {
            "active": active_workers,
            "configured": configured_workers,
            "status": workers_status,
        },
        "organization": org_block,
        "last_check": _utc_z_timestamp(now),
        "issues": issues,
    }


@resource("/v1/organization/<orgname>/mirror/health")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrganizationMirrorHealth(ApiResource):
    """
    Resource for checking the health of organization-level mirroring operations.
    """

    @require_fresh_login
    @nickname("getOrganizationMirrorHealth")
    @parse_args()
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
        "Offset into the sorted discovered-repository list for detailed view",
        type=int,
        default=0,
    )
    def get(self, orgname, parsed_args):
        """
        Get the health status of organization mirroring for a single organization.

        Returns overall health status, worker summary, organization mirror state,
        and any issues. HTTP status reflects health: 200 for healthy, 503 for unhealthy.
        """
        authed_user = get_authenticated_user()
        if not authed_user:
            raise Unauthorized()

        if not (allow_if_superuser() or allow_if_global_readonly_superuser()):
            namespace_user = model.user.get_namespace_user(orgname)
            if not namespace_user:
                raise NotFound()
            if not OrganizationMemberPermission(orgname).can():
                raise Unauthorized()

        health_data = get_org_mirror_health_data(
            orgname=orgname,
            detailed=parsed_args.get("detailed", False),
            detail_limit=parsed_args.get("limit", 100),
            detail_offset=parsed_args.get("offset", 0),
        )

        status_code = 200 if health_data["healthy"] else 503
        return (
            health_data,
            status_code,
            {"Cache-Control": _CACHE_CONTROL_NO_STORE},
        )
