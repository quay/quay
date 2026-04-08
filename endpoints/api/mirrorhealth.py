# -*- coding: utf-8 -*-
"""
Repository Mirror Health Endpoint

Provides health status and monitoring information for repository mirroring operations.
"""

import logging
from datetime import datetime, timedelta, timezone

import features
from auth.auth_context import get_authenticated_user
from auth.permissions import (
    AdministerOrganizationPermission,
    OrganizationMemberPermission,
    UserAdminPermission,
)
from data import model
from data.database import RepoMirrorConfig, RepoMirrorStatus, Repository, RepositoryState
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
from endpoints.exception import Unauthorized
from prometheus_client import REGISTRY

logger = logging.getLogger(__name__)


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


def get_mirror_health_data(namespace=None):
    """
    Gather health data for repository mirroring operations.
    
    Args:
        namespace: Optional namespace to filter results
        
    Returns:
        Dictionary with health status information
    """
    # Build base query
    query = (
        RepoMirrorConfig.select(RepoMirrorConfig, Repository)
        .join(Repository)
        .where(Repository.state == RepositoryState.MIRROR)
    )
    
    # Filter by namespace if provided
    if namespace:
        from data.database import User
        query = query.switch(Repository).join(User).where(User.username == namespace)
    
    mirrors = list(query)
    
    # Count repositories by sync status
    total_repos = len(mirrors)
    syncing = sum(1 for m in mirrors if m.sync_status == RepoMirrorStatus.SYNCING)
    completed = sum(1 for m in mirrors if m.sync_status == RepoMirrorStatus.SUCCESS)
    failed = sum(
        1
        for m in mirrors
        if m.sync_status in (RepoMirrorStatus.FAIL, RepoMirrorStatus.NEVER_RUN)
    )
    
    # Calculate total pending tags (this is an approximation since we don't store this in DB)
    # In a real implementation, this would come from metrics or a cached value
    tags_pending = 0  # Would need to query from metrics or calculate
    
    # Determine overall health status
    now = datetime.utcnow()
    issues = []
    
    # Check for repositories that haven't synced recently (stale syncs)
    stale_threshold = now - timedelta(hours=24)
    last_sync_timestamps = _get_last_sync_timestamps()
    stale_repos = []
    never_synced_repos = []
    for mirror in mirrors:
        if not mirror.is_enabled or mirror.sync_status == RepoMirrorStatus.SYNCING:
            continue
        namespace_name = mirror.repository.namespace_user.username
        repo_name = mirror.repository.name
        last_sync_ts = last_sync_timestamps.get((namespace_name, repo_name))
        if last_sync_ts is None:
            if mirror.sync_status == RepoMirrorStatus.NEVER_RUN:
                never_synced_repos.append(mirror)
            continue
        last_sync_dt = datetime.fromtimestamp(last_sync_ts, tz=timezone.utc).replace(
            tzinfo=None
        )
        if last_sync_dt < stale_threshold:
            stale_repos.append(mirror)
    
    if stale_repos:
        for repo in stale_repos[:5]:  # Limit to first 5 for brevity
            issues.append(
                {
                    "severity": "warning",
                    "message": f"Repository {repo.repository.namespace_user.username}/{repo.repository.name} hasn't synced in over 24 hours",
                    "timestamp": now.isoformat() + "Z",
                }
            )
    if never_synced_repos:
        for repo in never_synced_repos[:5]:  # Limit to first 5 for brevity
            issues.append(
                {
                    "severity": "warning",
                    "message": f"Repository {repo.repository.namespace_user.username}/{repo.repository.name} has never been synced",
                    "timestamp": now.isoformat() + "Z",
                }
            )
    
    # Check for repeatedly failing repositories
    failing_repos = [
        m
        for m in mirrors
        if m.sync_status == RepoMirrorStatus.FAIL and m.sync_retries_remaining == 0
    ]
    
    if failing_repos:
        for repo in failing_repos[:5]:  # Limit to first 5
            issues.append(
                {
                    "severity": "error",
                    "message": f"Repository {repo.repository.namespace_user.username}/{repo.repository.name} has exhausted all retry attempts",
                    "timestamp": now.isoformat() + "Z",
                }
            )
    
    # Determine if system is healthy
    # System is unhealthy if:
    # - More than 20% of repos are failing
    # - Any critical errors exist
    critical_threshold = 0.2
    healthy = True
    
    if total_repos > 0:
        failure_rate = failed / total_repos
        if failure_rate > critical_threshold:
            healthy = False
            issues.insert(
                0,
                {
                    "severity": "critical",
                    "message": f"{failure_rate*100:.1f}% of repositories are failing (threshold: {critical_threshold*100}%)",
                    "timestamp": now.isoformat() + "Z",
                },
            )
    
    # Note: Worker count would ideally come from a coordination service or config
    # For now, we assume workers are healthy if repos are being processed
    workers_status = "healthy" if healthy else "degraded"
    
    return {
        "healthy": healthy,
        "workers": {
            "active": 0,  # Would need coordination service to track this accurately
            "configured": 0,  # Would come from config
            "status": workers_status,
        },
        "repositories": {
            "total": total_repos,
            "syncing": syncing,
            "completed": completed,
            "failed": failed,
        },
        "tags_pending": tags_pending,
        "last_check": now.isoformat() + "Z",
        "issues": issues,
    }


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
        type=bool,
        default=False,
    )
    def get(self, parsed_args):
        """
        Get the health status of repository mirroring operations.
        
        Returns overall health status, worker information, and any issues.
        HTTP status code reflects health: 200 for healthy, 503 for unhealthy.
        """
        namespace = parsed_args.get("namespace")
        detailed = parsed_args.get("detailed", False)
        
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
                raise Unauthorized()
            if not (allow_if_superuser() or allow_if_global_readonly_superuser()):
                if namespace_user.organization:
                    if not OrganizationMemberPermission(namespace).can():
                        raise Unauthorized()
                else:
                    if authed_user.username != namespace and not UserAdminPermission(
                        namespace
                    ).can():
                        raise Unauthorized()
        
        health_data = get_mirror_health_data(namespace=namespace)
        
        # Add detailed per-repository information if requested
        if detailed:
            query = (
                RepoMirrorConfig.select(RepoMirrorConfig, Repository)
                .join(Repository)
                .where(Repository.state == RepositoryState.MIRROR)
            )
            
            if namespace:
                from data.database import User
                query = query.switch(Repository).join(User).where(User.username == namespace)
            
            repos_detail = []
            last_sync_timestamps = _get_last_sync_timestamps()
            for mirror in query:
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
            
            health_data["repositories"]["details"] = repos_detail
        
        # Return 503 if unhealthy, 200 if healthy
        status_code = 200 if health_data["healthy"] else 503
        
        return health_data, status_code

