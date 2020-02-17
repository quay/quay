import pytest

from peewee import JOIN
from playhouse.test_utils import assert_query_count

from data.database import Repository, RepositoryPermission, TeamMember, Namespace
from data.model._basequery import filter_to_repos_for_user
from data.model.organization import get_admin_users
from data.model.user import get_namespace_user
from util.names import parse_robot_username

from test.fixtures import *


def _is_team_member(team, user):
    return user.id in [
        member.user_id for member in TeamMember.select().where(TeamMember.team == team)
    ]


def _get_visible_repositories_for_user(
    user, repo_kind="image", include_public=False, namespace=None
):
    """
    Returns all repositories directly visible to the given user, by either repo permission, or the
    user being the admin of a namespace.
    """
    for repo in Repository.select():
        if repo_kind is not None and repo.kind.name != repo_kind:
            continue

        if namespace is not None and repo.namespace_user.username != namespace:
            continue

        if include_public and repo.visibility.name == "public":
            yield repo
            continue

        # Direct repo permission.
        try:
            RepositoryPermission.get(repository=repo, user=user).get()
            yield repo
            continue
        except RepositoryPermission.DoesNotExist:
            pass

        # Team permission.
        found_in_team = False
        for perm in RepositoryPermission.select().where(RepositoryPermission.repository == repo):
            if perm.team and _is_team_member(perm.team, user):
                found_in_team = True
                break

        if found_in_team:
            yield repo
            continue

        # Org namespace admin permission.
        if user in get_admin_users(repo.namespace_user):
            yield repo
            continue


@pytest.mark.parametrize("username", ["devtable", "devtable+dtrobot", "public", "reader",])
@pytest.mark.parametrize("include_public", [True, False])
@pytest.mark.parametrize("filter_to_namespace", [True, False])
@pytest.mark.parametrize("repo_kind", [None, "image", "application",])
def test_filter_repositories(
    username, include_public, filter_to_namespace, repo_kind, initialized_db
):
    namespace = username if filter_to_namespace else None
    if "+" in username and filter_to_namespace:
        namespace, _ = parse_robot_username(username)

    user = get_namespace_user(username)
    query = (
        Repository.select()
        .distinct()
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .switch(Repository)
        .join(RepositoryPermission, JOIN.LEFT_OUTER)
    )

    # Prime the cache.
    Repository.kind.get_id("image")

    with assert_query_count(1):
        found = list(
            filter_to_repos_for_user(
                query,
                user.id,
                namespace=namespace,
                include_public=include_public,
                repo_kind=repo_kind,
            )
        )

    expected = list(
        _get_visible_repositories_for_user(
            user, repo_kind=repo_kind, namespace=namespace, include_public=include_public
        )
    )

    assert len(found) == len(expected)
    assert {r.id for r in found} == {r.id for r in expected}
