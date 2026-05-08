from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from data.users import FederatedUserManager, UserManager
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


@pytest.mark.parametrize(
    "is_superuser, state_is_restricted, expected",
    [
        (True, True, False),
        (True, False, False),
        (False, True, True),
        (False, False, False),
    ],
)
def test_usermanager_superuser_not_restricted(is_superuser, state_is_restricted, expected):
    """
    UserManager.is_restricted_user() must return False for superusers,
    even when the underlying state considers them restricted.
    Regression test for PROJQUAY-5196.
    """
    manager = object.__new__(UserManager)
    mock_state = MagicMock()
    mock_state.is_superuser.return_value = is_superuser
    mock_state.is_restricted_user.return_value = state_is_restricted
    manager.state = mock_state
    manager.authentication = MagicMock()

    with patch("data.users.features") as mock_features:
        mock_features.RESTRICTED_USERS = True
        mock_features.SUPER_USERS = True
        assert manager.is_restricted_user("devtable") == expected


@pytest.mark.parametrize(
    "restricted_feature, super_feature, is_superuser, state_restricted, expected",
    [
        (False, True, True, True, False),
        (False, False, False, True, False),
        (True, False, True, True, True),
    ],
)
def test_usermanager_feature_flags(
    restricted_feature, super_feature, is_superuser, state_restricted, expected
):
    """
    UserManager.is_restricted_user() respects feature flags:
    - RESTRICTED_USERS off -> always False
    - SUPER_USERS off -> superuser check skipped, restriction applies
    """
    manager = object.__new__(UserManager)
    mock_state = MagicMock()
    mock_state.is_superuser.return_value = is_superuser
    mock_state.is_restricted_user.return_value = state_restricted
    manager.state = mock_state
    manager.authentication = MagicMock()

    with patch("data.users.features") as mock_features:
        mock_features.RESTRICTED_USERS = restricted_feature
        mock_features.SUPER_USERS = super_feature
        assert manager.is_restricted_user("devtable") == expected


def test_usermanager_superuser_config_integration():
    """
    End-to-end test: ConfigUserManager-backed UserManager should not
    restrict a user who appears in the SUPER_USERS config list.
    Regression test for PROJQUAY-5196.
    """
    app.config = {"SUPER_USERS": ["devtable"]}

    manager = object.__new__(UserManager)
    manager.state = ConfigUserManager(app)
    manager.authentication = MagicMock()

    with patch("data.users.features") as mock_features:
        mock_features.RESTRICTED_USERS = True
        mock_features.SUPER_USERS = True
        assert manager.is_restricted_user("devtable") is False
        assert manager.is_restricted_user("otheruser") is True


def test_federated_superuser_not_restricted():
    """
    A user identified as superuser via LDAP (federated service) should
    not be restricted, even when the LDAP restricted user filter would
    match them. Regression test for PROJQUAY-5196.
    """
    app.config = {}

    mock_auth = MagicMock()
    mock_auth.is_superuser.return_value = True
    mock_auth.is_restricted_user.return_value = True
    mock_auth.has_superusers.return_value = True

    with (
        patch.object(
            FederatedUserManager,
            "_FederatedUserManager__get_federated_login_identifier",
            return_value="devtable",
        ),
        patch("data.users.features") as mock_features,
    ):
        mock_features.RESTRICTED_USERS = True
        mock_features.SUPER_USERS = True

        manager = object.__new__(UserManager)
        manager.state = FederatedUserManager(app, mock_auth)
        manager.authentication = mock_auth

        assert manager.is_restricted_user("devtable") is False
