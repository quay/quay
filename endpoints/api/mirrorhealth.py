# -*- coding: utf-8 -*-
"""
Repository Mirror Health Endpoint

Provides health status and monitoring information for repository mirroring operations.
"""

import logging
from datetime import datetime, timedelta

import features
from data import model
from data.database import RepoMirrorConfig, RepoMirrorStatus, Repository, RepositoryState
from endpoints.api import (
    ApiResource,
    nickname,
    parse_args,
    query_param,
    require_fresh_login,
    resource,
    show_if,
)
from endpoints.exception import Unauthorized

logger = logging.getLogger(__name__)


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
    stale_repos = [
        m
        for m in mirrors
        if m.is_enabled
        and m.sync_start_date
        and m.sync_start_date < stale_threshold
        and m.sync_status != RepoMirrorStatus.SYNCING
    ]
    
    if stale_repos:
        for repo in stale_repos[:5]:  # Limit to first 5 for brevity
            issues.append(
                {
                    "severity": "warning",
                    "message": f"Repository {repo.repository.namespace_user.username}/{repo.repository.name} hasn't synced in over 24 hours",
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
        
        # Verify user has access to the namespace if specified
        if namespace:
            user = model.user.get_namespace_user(namespace)
            if not user:
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
            for mirror in query:
                repos_detail.append(
                    {
                        "namespace": mirror.repository.namespace_user.username,
                        "repository": mirror.repository.name,
                        "sync_status": mirror.sync_status.name,
                        "is_enabled": mirror.is_enabled,
                        "last_sync": (
                            mirror.sync_start_date.isoformat() + "Z"
                            if mirror.sync_start_date
                            else None
                        ),
                        "retries_remaining": mirror.sync_retries_remaining,
                    }
                )
            
            health_data["repositories"]["details"] = repos_detail
        
        # Return 503 if unhealthy, 200 if healthy
        status_code = 200 if health_data["healthy"] else 503
        
        return health_data, status_code

