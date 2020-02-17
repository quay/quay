import pytest

from mock import patch

from data import model, database
from data.users import get_users_handler, DatabaseUsers
from endpoints.oauth.login import _conduct_oauth_login
from oauth.services.github import GithubOAuthService
from test.test_ldap import mock_ldap

from test.fixtures import *


@pytest.fixture(params=[None, "username", "email"])
def login_service(request, app):
    config = {"GITHUB": {}}
    if request is not None:
        config["GITHUB"]["LOGIN_BINDING_FIELD"] = request.param

    return GithubOAuthService(config, "GITHUB")


@pytest.fixture(params=["Database", "LDAP"])
def auth_system(request):
    return _get_users_handler(request.param)


def _get_users_handler(auth_type):
    config = {}
    config["AUTHENTICATION_TYPE"] = auth_type
    config["LDAP_BASE_DN"] = ["dc=quay", "dc=io"]
    config["LDAP_ADMIN_DN"] = "uid=testy,ou=employees,dc=quay,dc=io"
    config["LDAP_ADMIN_PASSWD"] = "password"
    config["LDAP_USER_RDN"] = ["ou=employees"]

    return get_users_handler(config, None, None)


def test_existing_account(auth_system, login_service):
    login_service_lid = "someexternaluser"

    # Create an existing bound federated user.
    created_user = model.user.create_federated_user(
        "someuser", "example@example.com", login_service.service_id(), login_service_lid, False
    )
    existing_user_count = database.User.select().count()

    with mock_ldap():
        result = _conduct_oauth_login(
            auth_system, login_service, login_service_lid, login_service_lid, "example@example.com"
        )

        assert result.user_obj == created_user

        # Ensure that no addtional users were created.
        current_user_count = database.User.select().count()
        assert current_user_count == existing_user_count


def test_new_account_via_database(login_service):
    existing_user_count = database.User.select().count()
    login_service_lid = "someexternaluser"
    internal_auth = DatabaseUsers()

    # Conduct login. Since the external user doesn't (yet) bind to a user in the database,
    # a new user should be created and bound to the external service.
    result = _conduct_oauth_login(
        internal_auth, login_service, login_service_lid, login_service_lid, "example@example.com"
    )
    assert result.user_obj is not None

    current_user_count = database.User.select().count()
    assert current_user_count == existing_user_count + 1

    # Find the user and ensure it is bound.
    new_user = model.user.get_user(login_service_lid)
    federated_login = model.user.lookup_federated_login(new_user, login_service.service_id())
    assert federated_login is not None

    # Ensure that a notification was created.
    assert list(
        model.notification.list_notifications(result.user_obj, kind_name="password_required")
    )


@pytest.mark.parametrize(
    "open_creation, invite_only, has_invite, expect_success",
    [
        # Open creation -> Success!
        (True, False, False, True),
        # Open creation + invite only + no invite -> Failure!
        (True, True, False, False),
        # Open creation + invite only + invite -> Success!
        (True, True, True, True),
        # Close creation -> Failure!
        (False, False, False, False),
    ],
)
def test_flagged_user_creation(
    open_creation, invite_only, has_invite, expect_success, login_service
):
    login_service_lid = "someexternaluser"
    email = "some@example.com"

    if has_invite:
        inviter = model.user.get_user("devtable")
        team = model.team.get_organization_team("buynlarge", "owners")
        model.team.add_or_invite_to_team(inviter, team, email=email)

    internal_auth = DatabaseUsers()

    with patch("features.USER_CREATION", open_creation):
        with patch("features.INVITE_ONLY_USER_CREATION", invite_only):
            # Conduct login.
            result = _conduct_oauth_login(
                internal_auth, login_service, login_service_lid, login_service_lid, email
            )
            assert (result.user_obj is not None) == expect_success
            assert (result.error_message is None) == expect_success


@pytest.mark.parametrize(
    "binding_field, lid, lusername, lemail, expected_error",
    [
        # No binding field + newly seen user -> New unlinked user
        (None, "someid", "someunknownuser", "someemail@example.com", None),
        # sub binding field + unknown sub -> Error.
        ("sub", "someid", "someuser", "foo@bar.com", "sub someid not found in backing auth system"),
        # username binding field + unknown username -> Error.
        (
            "username",
            "someid",
            "someunknownuser",
            "foo@bar.com",
            "username someunknownuser not found in backing auth system",
        ),
        # email binding field + unknown email address -> Error.
        (
            "email",
            "someid",
            "someuser",
            "someemail@example.com",
            "email someemail@example.com not found in backing auth system",
        ),
        # No binding field + newly seen user -> New unlinked user.
        (None, "someid", "someuser", "foo@bar.com", None),
        # username binding field + valid username -> fully bound user.
        ("username", "someid", "someuser", "foo@bar.com", None),
        # sub binding field + valid sub -> fully bound user.
        ("sub", "someuser", "someusername", "foo@bar.com", None),
        # email binding field + valid email -> fully bound user.
        ("email", "someid", "someuser", "foo@bar.com", None),
        # username binding field + valid username + invalid email -> fully bound user.
        ("username", "someid", "someuser", "another@email.com", None),
        # email binding field + valid email + invalid username -> fully bound user.
        ("email", "someid", "someotherusername", "foo@bar.com", None),
    ],
)
def test_new_account_via_ldap(binding_field, lid, lusername, lemail, expected_error, app):
    existing_user_count = database.User.select().count()

    config = {"GITHUB": {}}
    if binding_field is not None:
        config["GITHUB"]["LOGIN_BINDING_FIELD"] = binding_field

    external_auth = GithubOAuthService(config, "GITHUB")
    internal_auth = _get_users_handler("LDAP")

    with mock_ldap():
        # Conduct OAuth login.
        result = _conduct_oauth_login(internal_auth, external_auth, lid, lusername, lemail)
        assert result.error_message == expected_error

        current_user_count = database.User.select().count()
        if expected_error is None:
            # Ensure that the new user was created and that it is bound to both the
            # external login service and to LDAP (if a binding_field was given).
            assert current_user_count == existing_user_count + 1
            assert result.user_obj is not None

            # Check the service bindings.
            external_login = model.user.lookup_federated_login(
                result.user_obj, external_auth.service_id()
            )
            assert external_login is not None

            internal_login = model.user.lookup_federated_login(
                result.user_obj, internal_auth.federated_service
            )
            if binding_field is not None:
                assert internal_login is not None
            else:
                assert internal_login is None

            # Ensure that no notification was created.
            assert not list(
                model.notification.list_notifications(
                    result.user_obj, kind_name="password_required"
                )
            )
        else:
            # Ensure that no addtional users were created.
            assert current_user_count == existing_user_count


def test_existing_account_in_ldap(app):
    config = {"GITHUB": {"LOGIN_BINDING_FIELD": "username"}}

    external_auth = GithubOAuthService(config, "GITHUB")
    internal_auth = _get_users_handler("LDAP")

    # Add an existing federated user bound to the LDAP account associated with `someuser`.
    bound_user = model.user.create_federated_user(
        "someuser", "foo@bar.com", internal_auth.federated_service, "someuser", False
    )

    existing_user_count = database.User.select().count()

    with mock_ldap():
        # Conduct OAuth login with the same lid and bound field. This should find the existing LDAP
        # user (via the `username` binding), and then bind Github to it as well.
        result = _conduct_oauth_login(
            internal_auth, external_auth, bound_user.username, bound_user.username, bound_user.email
        )
        assert result.error_message is None

        # Ensure that the same user was returned, and that it is now bound to the Github account
        # as well.
        assert result.user_obj.id == bound_user.id

        # Ensure that no additional users were created.
        current_user_count = database.User.select().count()
        assert current_user_count == existing_user_count

        # Check the service bindings.
        external_login = model.user.lookup_federated_login(
            result.user_obj, external_auth.service_id()
        )
        assert external_login is not None

        internal_login = model.user.lookup_federated_login(
            result.user_obj, internal_auth.federated_service
        )
        assert internal_login is not None
