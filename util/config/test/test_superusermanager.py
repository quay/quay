import pytest
from dataclasses import dataclass

from util.config.superusermanager import ConfigUserManager
from test.fixtures import *


@pytest.mark.parametrize(
    "config, username, expected",
    [
        ({"RESTRICTED_USERS_WHITELIST": []}, "devtable", False),
        ({"RESTRICTED_USERS_WHITELIST": ["devtable"]}, "devtable", False),
        ({"RESTRICTED_USERS_WHITELIST": ["someotheruser"]}, "devtable", True),
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
