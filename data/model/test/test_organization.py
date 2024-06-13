import pytest

from data.model.organization import get_organization, get_organizations, is_org_admin
from data.model.user import get_user, mark_namespace_for_deletion
from data.queue import WorkQueue
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
