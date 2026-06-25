from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from data.users import FederatedUserManager
from test.fixtures import *
from util.config.superusermanager import ConfigUserManager


@pytest.mark.parametrize(
    "config, username, expected",
    [
        ({"RESTRICTED_USERS_WHITELIST": []}, "devtable", True),
        ({"RESTRICTED_USERS_WHITELIST": ["devtable"]}, "devtable", False),
        ({"RESTRICTED_USERS_WHITELIST": ["someotheruser"]}, "devtable", True),
        ({"RESTRICTED_USERS_WHITELIST": None}, "devtable", True),
    ],
)
def test_restricted_user_whitelist(config, username, expected):
    app.config = config

    configusermanager = ConfigUserManager(app)

    assert configusermanager.is_restricted_user(username) == expected
    if expected:
        assert configusermanager.has_restricted_users()


@pytest.mark.parametrize(
    "config, username, expected",
    [
        ({"SUPER_USERS": []}, "devtable", False),
        ({"SUPER_USERS": ["devtable"]}, "devtable", True),
        ({"SUPER_USERS": ["someotheruser"]}, "devtable", False),
    ],
)
def test_superuser_list(config, username, expected):
    app.config = config

    configusermanager = ConfigUserManager(app)

    assert configusermanager.is_superuser(username) == expected
    if expected:
        assert configusermanager.has_superusers()


@pytest.mark.parametrize(
    "config, username, expected",
    [
        ({"GLOBAL_READONLY_SUPER_USERS": []}, "devtable", False),
        ({"GLOBAL_READONLY_SUPER_USERS": ["devtable"]}, "devtable", True),
        ({"GLOBAL_READONLY_SUPER_USERS": ["someotheruser"]}, "devtable", False),
        ({"SUPER_USERS": ["devtable"]}, "devtable", False),
    ],
)
def test_global_readonly_superuser_list(config, username, expected):
    app.config = config

    configusermanager = ConfigUserManager(app)

    assert configusermanager.is_global_readonly_superuser(username) == expected
    if expected:
        assert configusermanager.has_global_readonly_superusers()


@pytest.mark.parametrize(
    "config, ldap_restricted, expected",
    [
        # No whitelist, LDAP says not restricted -> not restricted (bug fix)
        ({}, False, False),
        # No whitelist, LDAP says restricted -> restricted
        ({}, True, True),
        # Whitelist set, user in whitelist -> not restricted (early return)
        ({"RESTRICTED_USERS_WHITELIST": ["devtable"]}, True, False),
        # Whitelist set, user NOT in whitelist, LDAP says restricted -> restricted
        ({"RESTRICTED_USERS_WHITELIST": ["otheruser"]}, True, True),
        # Whitelist set, user NOT in whitelist, LDAP says not restricted -> restricted (config says restricted)
        ({"RESTRICTED_USERS_WHITELIST": ["otheruser"]}, False, True),
    ],
)
def test_federated_is_restricted_user(config, ldap_restricted, expected):
    """
    When no RESTRICTED_USERS_WHITELIST is configured, the LDAP (federated)
    result should be authoritative. ConfigUserManager defaults all users to
    restricted when no whitelist is set, which should not override LDAP.
    """
    app.config = config

    mock_auth = MagicMock()
    mock_auth.is_restricted_user.return_value = ldap_restricted

    with patch.object(
        FederatedUserManager,
        "_FederatedUserManager__get_federated_login_identifier",
        return_value="devtable",
    ):
        manager = FederatedUserManager(app, mock_auth)
        assert manager.is_restricted_user("devtable") == expected
