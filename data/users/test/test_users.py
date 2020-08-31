import pytest

from contextlib import contextmanager
from mock import patch

from data import model
from data.users.federated import DISABLED_MESSAGE
from test.test_ldap import mock_ldap
from test.test_keystone_auth import fake_keystone
from test.test_external_jwt_authn import fake_jwt

from test.fixtures import *


@pytest.mark.parametrize(
    "auth_system_builder, user1, user2",
    [
        (mock_ldap, ("someuser", "somepass"), ("testy", "password")),
        (fake_keystone, ("cool.user", "password"), ("some.neat.user", "foobar")),
    ],
)
def test_auth_createuser(auth_system_builder, user1, user2, config, app):
    with auth_system_builder() as auth:
        # Login as a user and ensure a row in the database is created for them.
        user, err = auth.verify_and_link_user(*user1)
        assert err is None
        assert user

        federated_info = model.user.lookup_federated_login(user, auth.federated_service)
        assert federated_info is not None

        # Disable user creation.
        with patch("features.USER_CREATION", False):
            # Ensure that the existing user can login.
            user_again, err = auth.verify_and_link_user(*user1)
            assert err is None
            assert user_again.id == user.id

            # Ensure that a new user cannot.
            new_user, err = auth.verify_and_link_user(*user2)
            assert new_user is None
            assert err == DISABLED_MESSAGE


@pytest.mark.parametrize(
    "email, blacklisting_enabled, can_create",
    [
        # Blacklisting Enabled, Blacklisted Domain => Blocked
        ("foo@blacklisted.net", True, False),
        ("foo@blacklisted.com", True, False),
        # Blacklisting Enabled, similar to blacklisted domain => Allowed
        ("foo@notblacklisted.com", True, True),
        ("foo@blacklisted.org", True, True),
        # Blacklisting *Disabled*, Blacklisted Domain => Allowed
        ("foo@blacklisted.com", False, True),
        ("foo@blacklisted.net", False, True),
    ],
)
@pytest.mark.parametrize("auth_system_builder", [mock_ldap, fake_keystone, fake_jwt])
def test_createuser_with_blacklist(
    auth_system_builder, email, blacklisting_enabled, can_create, config, app
):
    """
    Verify email blacklisting with User Creation.
    """

    MOCK_CONFIG = {"BLACKLISTED_EMAIL_DOMAINS": ["blacklisted.com", "blacklisted.net"]}
    MOCK_PASSWORD = "somepass"

    with auth_system_builder() as auth:
        with patch("features.BLACKLISTED_EMAILS", blacklisting_enabled):
            with patch.dict("data.model.config.app_config", MOCK_CONFIG):
                with patch("features.USER_CREATION", True):
                    new_user, err = auth.verify_and_link_user(email, MOCK_PASSWORD)
                    if can_create:
                        assert err is None
                        assert new_user
                    else:
                        assert err
                        assert new_user is None


@pytest.mark.parametrize(
    "auth_system_builder,auth_kwargs",
    [
        (mock_ldap, {}),
        (fake_keystone, {"version": 3}),
        (fake_keystone, {"version": 2}),
        (fake_jwt, {}),
    ],
)
def test_ping(auth_system_builder, auth_kwargs, app):
    with auth_system_builder(**auth_kwargs) as auth:
        status, err = auth.ping()
        assert status
        assert err is None


@pytest.mark.parametrize(
    "auth_system_builder,auth_kwargs",
    [
        (mock_ldap, {}),
        (fake_keystone, {"version": 3}),
        (fake_keystone, {"version": 2}),
    ],
)
def test_at_least_one_user_exists(auth_system_builder, auth_kwargs, app):
    with auth_system_builder(**auth_kwargs) as auth:
        status, err = auth.at_least_one_user_exists()
        assert status
        assert err is None
