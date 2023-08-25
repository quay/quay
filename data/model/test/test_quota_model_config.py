from test.fixtures import *

from data.model import namespacequota
from data.model.organization import create_organization
from data.model.user import create_user_noverify


def create_org(user_name, user_email, org_name, org_email):
    user_obj = create_user_noverify(user_name, user_email)
    return create_organization(org_name, org_email, user_obj)


def test_create_quota(initialized_db):
    user_name = "foo_user"
    user_email = "foo_user@foo.com"
    org_name = "foo_org"
    org_email = "foo_org@foo.com"
    limit_bytes = 2048

    new_org = create_org(user_name, user_email, org_name, org_email)
    new_quota = namespacequota.create_namespace_quota(new_org, limit_bytes)

    assert new_quota.limit_bytes == limit_bytes
    assert new_quota.namespace == new_org
    assert new_quota.namespace.id == new_org.id
