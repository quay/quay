import pytest

from auth import scopes
from auth.permissions import SuperUserPermission, QuayDeferredPermissionUser
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
        (normie, {scopes.SUPERUSER}, False),
        (normie, {scopes.DIRECT_LOGIN}, False),
        (normie, {scopes.READ_USER, scopes.SUPERUSER}, False),
        (normie, {scopes.READ_USER}, False),
    ]

    for user_obj, scope_set, expected in test_cases:
        perm_user = QuayDeferredPermissionUser.for_user(user_obj, scope_set)
        has_su = perm_user.can(SuperUserPermission())
        assert has_su == expected
