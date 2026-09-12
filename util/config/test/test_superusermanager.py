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


def test_register_superuser():
    app.config = {"SUPER_USERS": []}

    manager = ConfigUserManager(app)
    assert manager.is_superuser("newuser") is False

    manager.register_superuser("newuser")
    assert manager.is_superuser("newuser") is True
    assert manager.has_superusers() is True


def test_register_superuser_idempotent():
    app.config = {"SUPER_USERS": ["existing"]}

    manager = ConfigUserManager(app)
    manager.register_superuser("existing")
    assert manager.is_superuser("existing") is True

    usernames = manager._superusers_array.value.decode("utf8").split(",")
    assert usernames.count("existing") == 1


def test_deregister_superuser():
    app.config = {"SUPER_USERS": []}

    manager = ConfigUserManager(app)
    manager.register_superuser("dynamic_user")
    assert manager.is_superuser("dynamic_user") is True

    manager.deregister_superuser("dynamic_user")
    assert manager.is_superuser("dynamic_user") is False


def test_deregister_superuser_preserves_static():
    app.config = {"SUPER_USERS": ["static_admin"]}

    manager = ConfigUserManager(app)
    assert manager.is_superuser("static_admin") is True

    manager.deregister_superuser("static_admin")
    assert manager.is_superuser("static_admin") is True


def test_deregister_superuser_noop_for_absent():
    app.config = {"SUPER_USERS": ["admin"]}

    manager = ConfigUserManager(app)
    manager.deregister_superuser("nonexistent")
    assert manager.is_superuser("admin") is True


def test_register_deregister_cycle():
    app.config = {"SUPER_USERS": ["static"]}

    manager = ConfigUserManager(app)
    manager.register_superuser("dynamic")
    assert manager.is_superuser("dynamic") is True
    assert manager.is_superuser("static") is True

    manager.deregister_superuser("dynamic")
    assert manager.is_superuser("dynamic") is False
    assert manager.is_superuser("static") is True


def test_register_global_readonly_superuser():
    app.config = {"GLOBAL_READONLY_SUPER_USERS": []}

    manager = ConfigUserManager(app)
    assert manager.is_global_readonly_superuser("reader") is False

    manager.register_global_readonly_superuser("reader")
    assert manager.is_global_readonly_superuser("reader") is True
    assert manager.has_global_readonly_superusers() is True


def test_register_global_readonly_superuser_idempotent():
    app.config = {"GLOBAL_READONLY_SUPER_USERS": ["existing"]}

    manager = ConfigUserManager(app)
    manager.register_global_readonly_superuser("existing")

    usernames = manager._global_readonly_array.value.decode("utf8").split(",")
    assert usernames.count("existing") == 1


def test_deregister_global_readonly_superuser():
    app.config = {"GLOBAL_READONLY_SUPER_USERS": []}

    manager = ConfigUserManager(app)
    manager.register_global_readonly_superuser("dynamic_reader")
    assert manager.is_global_readonly_superuser("dynamic_reader") is True

    manager.deregister_global_readonly_superuser("dynamic_reader")
    assert manager.is_global_readonly_superuser("dynamic_reader") is False


def test_deregister_global_readonly_superuser_noop_for_absent():
    app.config = {"GLOBAL_READONLY_SUPER_USERS": ["reader"]}

    manager = ConfigUserManager(app)
    manager.deregister_global_readonly_superuser("nonexistent")
    assert manager.is_global_readonly_superuser("reader") is True


def test_deregister_global_readonly_superuser_preserves_static():
    app.config = {"GLOBAL_READONLY_SUPER_USERS": ["static_reader"]}

    manager = ConfigUserManager(app)
    assert manager.is_global_readonly_superuser("static_reader") is True

    manager.deregister_global_readonly_superuser("static_reader")
    assert manager.is_global_readonly_superuser("static_reader") is True


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
