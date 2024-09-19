import pytest

from data.model.organization import (
    get_organization,
    get_organizations,
    has_immutable_tags,
    is_org_admin,
)
from data.model.repository import create_repository
from data.model.test.test_repository import _create_tag
from data.model.user import get_user, mark_namespace_for_deletion
from data.queue import WorkQueue
from data.registry_model import registry_model
from test.fixtures import *


@pytest.mark.parametrize(
    "deleted",
    [
        (True),
        (False),
    ],
)
def test_get_organizations(deleted, initialized_db):
    # Delete an org.
    deleted_org = get_organization("sellnsmall")
    queue = WorkQueue("testgcnamespace", lambda db: db.transaction())
    mark_namespace_for_deletion(deleted_org, [], queue)

    orgs = get_organizations(deleted=deleted)
    assert orgs

    deleted_found = [org for org in orgs if org.id == deleted_org.id]
    assert bool(deleted_found) == deleted


def test_is_org_admin(initialized_db):
    user = get_user("devtable")
    org = get_organization("sellnsmall")
    assert is_org_admin(user, org) is True


def test_check_for_repositories_with_immutable_tags(initialized_db):
    # Create a repository and some tags
    repo = create_repository(
        "sellnsmall", "somenewrepo", None, repo_kind="image", visibility="public"
    )
    _ = _create_tag(repo, "tag1")
    _ = _create_tag(repo, "tag2")
    _ = _create_tag(repo, "tag3")

    # Expect the organization to not have repositories with immutable tags
    assert not has_immutable_tags("sellnsmall")

    # Set one of the tags to immutable
    tag = _create_tag(repo, "tag4")
    registry_model.set_tag_immutable(tag)

    # Expect the organization to have repositories with immutable tags
    assert has_immutable_tags("sellnsmall")
