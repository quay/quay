"""
Permission cache invalidation and revocation for the provides cache.

When permissions change, this module invalidates cached provides entries
and adds revocation entries so that concurrent requests are blocked
immediately, even before the database is updated.
"""

import logging

from data.cache import cache_key

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _get_revocation_list():
    from app import model_cache

    return getattr(model_cache, "revocation_list", None)


def is_repo_permission_revoked(user_id, namespace_name, repo_name):
    rl = _get_revocation_list()
    if rl is None:
        return False

    return rl.is_repo_revoked(user_id, namespace_name, repo_name)


def add_repo_revocation(user_id, namespace_name, repo_name):
    rl = _get_revocation_list()
    if rl is None:
        return True

    try:
        rl.add_repo_revocation(user_id, namespace_name, repo_name)
        return True
    except Exception as e:
        logger.error(f"Failed to add permission revocation: {e}", exc_info=True)
        return False


def invalidate_org_permission(user_id, namespace_name, model_cache):
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
#
# All composite operations are gated by FEATURE_PERMISSION_CACHE.
# When disabled, they no-op immediately.
# ---------------------------------------------------------------------------


def _is_enabled():
    import features

    return bool(getattr(features, "PERMISSION_CACHE", False))


def revoke_and_invalidate_repo(user_id, repo_id, namespace_name, repo_name, model_cache):
    if not _is_enabled():
        return

    from data.model import DataModelException

    success = add_repo_revocation(user_id, namespace_name, repo_name)
    if not success:
        raise DataModelException(
            "Permission revocation failed - cache service unavailable. "
            "Please try again later or contact support if this persists."
        )

    invalidate_repository_permission(
        user_id,
        repo_id,
        model_cache,
        namespace_name=namespace_name,
        repo_name=repo_name,
    )


def revoke_and_invalidate_team_members(team_id, repo_id, namespace_name, repo_name, model_cache):
    if not _is_enabled():
        return

    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team_id):
        revoke_and_invalidate_repo(member.id, repo_id, namespace_name, repo_name, model_cache)


def invalidate_team_members(team_id, repo_id, namespace_name, repo_name, model_cache):
    if not _is_enabled():
        return

    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team_id):
        invalidate_repository_permission(
            member.id,
            repo_id,
            model_cache,
            namespace_name=namespace_name,
            repo_name=repo_name,
        )


def invalidate_user_team_grant(user_obj, team_obj, model_cache):
    if not _is_enabled():
        return

    from data.model import permission as perm_model

    org_name = team_obj.organization.username

    invalidate_org_permission(user_obj.id, org_name, model_cache)

    for team_perm in perm_model.list_team_permissions(team_obj):
        repo = team_perm.repository
        invalidate_repository_permission(
            user_obj.id,
            repo.id,
            model_cache,
            namespace_name=org_name,
            repo_name=repo.name,
        )


def invalidate_user_team_removal(user_obj, team_obj, org_name, model_cache):
    if not _is_enabled():
        return

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
            add_repo_revocation(user_obj.id, org_name, repo.name)

        invalidate_repository_permission(
            user_obj.id,
            repo.id,
            model_cache,
            namespace_name=org_name,
            repo_name=repo.name,
        )


def invalidate_team_org_role(team_id, org_name, model_cache):
    if not _is_enabled():
        return

    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team_id):
        invalidate_org_permission(member.id, org_name, model_cache)


def invalidate_team_removal(team, org_name, model_cache):
    if not _is_enabled():
        return

    from data.model import organization as org_model

    for member in org_model.get_organization_team_members(team.id):
        invalidate_user_team_removal(member, team, org_name, model_cache)


def invalidate_org_member_removal(user_obj, org, model_cache):
    if not _is_enabled():
        return

    from data.database import Repository, RepositoryPermission

    org_name = org.username

    # Revoke + invalidate for each repo the user has direct permissions on
    direct_perms = list(
        RepositoryPermission.select(RepositoryPermission, Repository)
        .join(Repository)
        .where(Repository.namespace_user == org, RepositoryPermission.user == user_obj)
    )

    for perm in direct_perms:
        add_repo_revocation(user_obj.id, org_name, perm.repository.name)
        invalidate_repository_permission(
            user_obj.id,
            perm.repository.id,
            model_cache,
            namespace_name=org_name,
            repo_name=perm.repository.name,
        )

    # Invalidate org-wide provides (team roles)
    invalidate_org_permission(user_obj.id, org_name, model_cache)

    # Invalidate repo provides for repos accessible through teams
    from data.database import Team, TeamMember
    from data.model import permission as perm_model

    user_teams = (
        Team.select().join(TeamMember).where(Team.organization == org, TeamMember.user == user_obj)
    )

    for user_team in user_teams:
        for team_perm in perm_model.list_team_permissions(user_team):
            repo = team_perm.repository
            direct_repo_ids = {p.repository.id for p in direct_perms}
            if repo.id not in direct_repo_ids:
                add_repo_revocation(user_obj.id, org_name, repo.name)
            invalidate_repository_permission(
                user_obj.id,
                repo.id,
                model_cache,
                namespace_name=org_name,
                repo_name=repo.name,
            )


def invalidate_bulk_team_member_removal(team, removed_user_ids, model_cache):
    if not _is_enabled():
        return

    from data.database import RepositoryPermission, User
    from data.model import permission as perm_model

    org_name = team.organization.username

    for user_id in removed_user_ids:
        user_obj = User.get_by_id(user_id)

        invalidate_org_permission(user_id, org_name, model_cache)

        for team_perm in perm_model.list_team_permissions(team):
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
                add_repo_revocation(user_id, org_name, repo.name)

            invalidate_repository_permission(
                user_id,
                repo.id,
                model_cache,
                namespace_name=org_name,
                repo_name=repo.name,
            )
