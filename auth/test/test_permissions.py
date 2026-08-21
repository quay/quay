from unittest.mock import patch

import pytest

import features
from auth import scopes
from auth.permissions import (
    QuayDeferredPermissionUser,
    ReadRepositoryPermission,
    SuperUserPermission,
)
from data import model
from test.fixtures import *

SUPER_USERNAME = "devtable"
UNSUPER_USERNAME = "freshuser"


@pytest.fixture()
def superuser(initialized_db):
    return model.user.get_user(SUPER_USERNAME)


@pytest.fixture()
def normie(initialized_db):
    return model.user.get_user(UNSUPER_USERNAME)


def test_superuser_matrix(superuser, normie):
    test_cases = [
        (superuser, {scopes.SUPERUSER}, True),
        (superuser, {scopes.DIRECT_LOGIN}, True),
        (superuser, {scopes.READ_USER, scopes.SUPERUSER}, True),
        (superuser, {scopes.READ_USER}, False),
        (superuser, {scopes.SUPERUSER, scopes.DIRECT_LOGIN}, True),
        (normie, {scopes.SUPERUSER}, False),
        (normie, {scopes.DIRECT_LOGIN}, False),
        (normie, {scopes.READ_USER, scopes.SUPERUSER}, False),
        (normie, {scopes.READ_USER}, False),
    ]

    for user_obj, scope_set, expected in test_cases:
        perm_user = QuayDeferredPermissionUser.for_user(user_obj, scope_set)
        has_su = perm_user.can(SuperUserPermission())
        assert has_su == expected


def test_docker_lazyload_permissions(superuser, normie, initialized_db):
    """
    Verifies that we load one repository permission at a time when calls are scoped, like during Docker v2 API access.
    """
    orgs = [f"org{i}" for i in range(1, 5)]
    for org in orgs:
        org_obj = model.organization.create_organization(
            name=org, email=f"test-{org}@test.com", creating_user=superuser
        )
        model.repository.create_repository(org, "testrepo", creating_user=superuser)
        owners_team = model.team.get_organization_team(org, "owners")
        model.team.add_user_to_team(normie, owners_team)

    perm_normaluser = QuayDeferredPermissionUser.for_user(normie, auth_scopes={scopes.READ_REPO})

    with patch(
        "auth.permissions.model.permission.get_org_wide_permissions",
        wraps=model.permission.get_org_wide_permissions,
    ) as mock_perms:
        for org in orgs:
            perm_normaluser.can(ReadRepositoryPermission(org, "testrepo"))
        assert mock_perms.call_count == len(orgs)


def test_direct_login_load_all_permissions(superuser, normie, initialized_db):
    """
    Verifies that we call loading of permissions only once when we login via UI.
    """
    orgs = [f"org{i}" for i in range(1, 5)]
    for org in orgs:
        org_obj = model.organization.create_organization(
            name=org, email=f"test-{org}@test.com", creating_user=superuser
        )
        model.repository.create_repository(org, "testrepo", creating_user=superuser)
        owners_team = model.team.get_organization_team(org, "owners")
        model.team.add_user_to_team(normie, owners_team)

    perm_normaluser = QuayDeferredPermissionUser.for_user(
        normie, auth_scopes={scopes.READ_REPO, scopes.DIRECT_LOGIN}
    )

    with patch(
        "auth.permissions.model.permission.get_org_wide_permissions",
        wraps=model.permission.get_org_wide_permissions,
    ) as mock_perms:
        for org in orgs:
            perm_normaluser.can(ReadRepositoryPermission(org, "testrepo"))
        mock_perms.assert_called_once()


def test_superuser_never_calls_get_org_wide_permissions(superuser, initialized_db):
    """
    Verifies that for super users we never call get_org_wide_permissions.
    """
    features.import_features({"FEATURE_SUPERUSERS_FULL_ACCESS": True, "FEATURE_SUPER_USERS": True})
    orgs = [f"org{i}" for i in range(1, 5)]
    for org in orgs:
        org_obj = model.organization.create_organization(
            name=org, email=f"test-{org}@test.com", creating_user=superuser
        )
        model.repository.create_repository(org, "testrepo", creating_user=superuser)

    perm_superuser = QuayDeferredPermissionUser.for_user(
        superuser, auth_scopes={scopes.SUPERUSER, scopes.DIRECT_LOGIN}
    )

    with patch(
        "auth.permissions.model.permission.get_org_wide_permissions",
        wraps=model.permission.get_org_wide_permissions,
    ) as mock_perms:
        for org in orgs:
            perm_superuser.can(ReadRepositoryPermission(org, "testrepo"))
        mock_perms.assert_not_called()
