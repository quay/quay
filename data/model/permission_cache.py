"""
Permission cache invalidation and revocation for the provides cache.

When permissions change, this module invalidates cached provides entries
and adds revocation entries so that concurrent requests are blocked
immediately, even before the database is updated.
"""

import logging

from data.cache import cache_key
from data.cache.revocation_list import PermissionRevocationList

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _get_revocation_list(model_cache):
    """Get a PermissionRevocationList from the cache's Redis client."""
    if model_cache is None:
        return None

    redis_client = getattr(model_cache, "client", None)
    if redis_client is None:
        return None

    return PermissionRevocationList(redis_client)


def is_repo_permission_revoked(user_id, namespace_name, repo_name, model_cache):
    """
    Check if a user's repository permission has been recently revoked.

    Called during provides loading to prevent stale cached permissions
    from granting access after revocation.

    Returns False (not revoked) if caching is disabled or Redis is unavailable.
    """
    revocation_list = _get_revocation_list(model_cache)
    if revocation_list is None:
        return False

    return revocation_list.is_repo_revoked(user_id, namespace_name, repo_name)


def add_repo_revocation(user_id, namespace_name, repo_name, model_cache):
    """
    Add a repository permission to the revocation list.

    Called BEFORE database changes to ensure concurrent requests are blocked.

    Returns:
        bool: True if successful, False if failed
    """
    revocation_list = _get_revocation_list(model_cache)
    if revocation_list is None:
        return True  # Caching disabled, nothing to do

    try:
        revocation_list.add_repo_revocation(user_id, namespace_name, repo_name)
        return True
    except Exception as e:
        logger.error(f"Failed to add permission revocation: {e}", exc_info=True)
        return False


def invalidate_org_permission(user_id, namespace_name, model_cache):
    """
    Invalidate cached org-wide permission provides for a user.

    Called when a user's team membership or team org role changes.

    Returns:
        bool: True if successful (or caching disabled), False if failed
    """
    if model_cache is None:
        return True

    try:
        org_provides_key = cache_key.for_user_org_provides(
            user_id, namespace_name, model_cache.cache_config
        )
        model_cache.invalidate(org_provides_key)
        logger.debug(f"Invalidated org permission cache: user={user_id}, org={namespace_name}")
        return True
    except Exception as e:
        logger.warning(f"Failed to invalidate org permission cache: {e}")
        return False


def invalidate_repository_permission(
    user_id, repo_id, model_cache=None, namespace_name=None, repo_name=None
):
    """
    Invalidate cached permission provides for a user/repo combination.

    Called after adding to the revocation list. Invalidates the provides
    cache so subsequent requests go back to the database.

    Returns:
        bool: True if successful (or caching disabled), False if failed
    """
    if model_cache is None:
        return True

    try:
        if namespace_name and repo_name:
            repo_provides_key = cache_key.for_user_repo_provides(
                user_id, namespace_name, repo_name, model_cache.cache_config
            )
            model_cache.invalidate(repo_provides_key)

            org_provides_key = cache_key.for_user_org_provides(
                user_id, namespace_name, model_cache.cache_config
            )
            model_cache.invalidate(org_provides_key)

        logger.debug(f"Invalidated permission cache: user={user_id}, repo={repo_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to invalidate permission cache: {e}")
        return False


# ---------------------------------------------------------------------------
# Composite operations — used by data/model/permission.py and team.py
# ---------------------------------------------------------------------------


def revoke_and_invalidate_repo(user_id, repo_id, namespace_name, repo_name, model_cache):
    """
    Revoke + invalidate cached permission for a single user/repo.

    Adds a revocation entry first, then invalidates the cache.

    Raises:
        DataModelException: If the revocation entry could not be added (fail-safe).
    """
    from data.model import DataModelException

    success = add_repo_revocation(user_id, namespace_name, repo_name, model_cache)
    if not success:
        raise DataModelException(
            "Permission revocation failed - cache service unavailable. "
            "Please try again later or contact support if this persists."
        )

    invalidate_repository_permission(
        user_id, repo_id, model_cache,
        namespace_name=namespace_name, repo_name=repo_name,
    )


def revoke_and_invalidate_team_members(
    team_id, repo_id, namespace_name, repo_name, model_cache
):
    """
    Revoke + invalidate for all members of a team on a specific repo.

    Used before deleting or downgrading a team's repo permission to ensure
    no team member retains stale cached access.

    Raises DataModelException if any revocation fails (fail-safe).
    """
    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team_id):
        revoke_and_invalidate_repo(
            member.id, repo_id, namespace_name, repo_name, model_cache
        )


def invalidate_team_members(
    team_id, repo_id, namespace_name, repo_name, model_cache
):
    """
    Invalidate cache (no revocation) for all members of a team on a repo.

    Used after granting or upgrading a team's repo permission.
    """
    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team_id):
        invalidate_repository_permission(
            member.id, repo_id, model_cache,
            namespace_name=namespace_name, repo_name=repo_name,
        )


def invalidate_user_team_grant(user_obj, team_obj, model_cache):
    """
    Invalidate cached provides when a user is ADDED to a team (grant scenario).

    Only invalidates cache — no revocation entries needed since we're granting
    more access, not revoking it. Best-effort: failures are logged but don't
    block the operation.
    """
    from data.model import permission as perm_model

    org_name = team_obj.organization.username

    invalidate_org_permission(user_obj.id, org_name, model_cache)

    for team_perm in perm_model.list_team_permissions(team_obj):
        repo = team_perm.repository
        invalidate_repository_permission(
            user_obj.id, repo.id, model_cache,
            namespace_name=org_name, repo_name=repo.name,
        )


def invalidate_user_team_removal(user_obj, team_obj, org_name, model_cache):
    """
    Invalidate cached provides when a user is REMOVED from a team.

    For each repo the team has access to:
    - If the user has NO direct permission on the repo, adds a revocation entry
      to block the race window between cache invalidation and DB change.
    - If the user HAS a direct permission, only invalidates cache (revocation
      would incorrectly block their direct access for 5 minutes).

    Always invalidates:
    - org_provides__ for the user in this org
    - repo_provides__ for each repo the team has permissions on
    """
    from data.database import RepositoryPermission
    from data.model import permission as perm_model

    invalidate_org_permission(user_obj.id, org_name, model_cache)

    for team_perm in perm_model.list_team_permissions(team_obj):
        repo = team_perm.repository

        has_direct = (
            RepositoryPermission.select()
            .where(
                RepositoryPermission.user == user_obj,
                RepositoryPermission.repository == repo,
            )
            .exists()
        )

        if not has_direct:
            add_repo_revocation(user_obj.id, org_name, repo.name, model_cache)

        invalidate_repository_permission(
            user_obj.id, repo.id, model_cache,
            namespace_name=org_name, repo_name=repo.name,
        )


def invalidate_team_org_role(team_id, org_name, model_cache):
    """
    Invalidate org provides for all team members when a team's org role changes.
    """
    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team_id):
        invalidate_org_permission(member.id, org_name, model_cache)


def invalidate_team_removal(team, org_name, model_cache):
    """
    Invalidate cached permissions for all members when a team is being deleted.

    Calls invalidate_user_team_removal for each member.
    """
    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team.id):
        invalidate_user_team_removal(member, team, org_name, model_cache)
