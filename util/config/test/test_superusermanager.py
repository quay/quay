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
