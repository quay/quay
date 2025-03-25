from datetime import datetime
from unittest.mock import Mock

import pytest
from mock import patch

from auth.scopes import READ_REPO
from auth.test.mock_oidc_server import MOCK_PUBLIC_KEY, generate_mock_oidc_token
from data import model
from data.database import DeletedNamespace, EmailConfirmation, FederatedLogin, User
from data.fields import Credential
from data.model.notification import create_notification
from data.model.oauth import (
    assign_token_to_user,
    get_oauth_application_for_client_id,
    get_token_assignment,
)
from data.model.organization import (
    create_organization,
    get_organization,
    get_organizations,
)
from data.model.repository import create_repository
from data.model.team import add_user_to_team, create_team
from data.model.user import (
    InvalidRobotException,
    RobotAccountToken,
    attach_federated_login,
    create_robot,
    create_user_noverify,
    delete_namespace_via_marker,
    delete_robot,
    get_active_namespaces,
    get_active_users,
    get_estimated_robot_count,
    get_matching_users,
    get_public_repo_count,
    get_pull_credentials,
    get_quay_user_from_federated_login_name,
    get_user,
    list_namespace_robots,
    lookup_robot,
    mark_namespace_for_deletion,
    retrieve_robot_token,
    validate_reset_code,
    verify_robot,
)
from data.queue import WorkQueue
from test.fixtures import *
from test.helpers import check_transitive_modifications
from util.security.instancekeys import InstanceKeys
from util.security.token import encode_public_private_token
from util.timedeltastring import convert_to_timedelta


def test_create_user_with_expiration(initialized_db):
    with patch("data.model.config.app_config", {"DEFAULT_TAG_EXPIRATION": "1h"}):
        user = create_user_noverify("foobar", "foo@example.com", email_required=False)
        assert user.removed_tag_expiration_s == 60 * 60


@pytest.mark.parametrize(
    "token_lifetime, time_since",
    [
        ("1m", "2m"),
        ("2m", "1m"),
        ("1h", "1m"),
    ],
)
def test_validation_code(token_lifetime, time_since, initialized_db):
    user = create_user_noverify("foobar", "foo@example.com", email_required=False)
    created = datetime.now() - convert_to_timedelta(time_since)
    verification_code, unhashed = Credential.generate()
    confirmation = EmailConfirmation.create(
        user=user, pw_reset=True, created=created, verification_code=verification_code
    )
    encoded = encode_public_private_token(confirmation.code, unhashed)

    with patch("data.model.config.app_config", {"USER_RECOVERY_TOKEN_LIFETIME": token_lifetime}):
        result = validate_reset_code(encoded)
        expect_success = convert_to_timedelta(token_lifetime) >= convert_to_timedelta(time_since)
        assert expect_success == (result is not None)


@pytest.mark.parametrize(
    "disabled",
    [
        (True),
        (False),
    ],
)
@pytest.mark.parametrize(
    "deleted",
    [
        (True),
        (False),
    ],
)
def test_get_active_users(disabled, deleted, initialized_db):
    # Delete a user.
    deleted_user = model.user.get_user("public")
    queue = WorkQueue("testgcnamespace", lambda db: db.transaction())
    mark_namespace_for_deletion(deleted_user, [], queue)

    users = get_active_users(disabled=disabled, deleted=deleted)
    deleted_found = [user for user in users if user.id == deleted_user.id]
    assert bool(deleted_found) == (deleted and disabled)

    for user in users:
        if not disabled:
            assert user.enabled


def test_mark_user_for_deletion(initialized_db):
    def create_transaction(db):
        return db.transaction()

    # Create a user and then mark it for deletion.
    user = create_user_noverify("foobar", "foo@example.com", email_required=False)

    # Add some robots.
    create_robot("foo", user)
    create_robot("bar", user)

    assert lookup_robot("foobar+foo") is not None
    assert lookup_robot("foobar+bar") is not None
    assert len(list(list_namespace_robots("foobar"))) == 2

    # Add some federated user links.
    attach_federated_login(user, "google", "someusername")
    attach_federated_login(user, "github", "someusername")
    assert FederatedLogin.select().where(FederatedLogin.user == user).count() == 2
    assert FederatedLogin.select().where(FederatedLogin.service_ident == "someusername").exists()

    # Add an oauth assigned token
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(
        org, "test", "http://foo/bar", "http://foo/bar/baz"
    )
    assigned_token = assign_token_to_user(
        application, user, "http://foo/bar/baz", READ_REPO.scope, "token"
    )
    assert get_token_assignment(assigned_token.uuid, user, org) is not None

    # Mark the user for deletion.
    queue = WorkQueue("testgcnamespace", create_transaction)
    mark_namespace_for_deletion(user, [], queue)

    # Ensure the older user is still in the DB.
    older_user = User.get(id=user.id)
    assert older_user.username != "foobar"

    # Ensure the robots are deleted.
    with pytest.raises(InvalidRobotException):
        assert lookup_robot("foobar+foo")

    with pytest.raises(InvalidRobotException):
        assert lookup_robot("foobar+bar")

    assert len(list(list_namespace_robots(older_user.username))) == 0

    # Ensure the federated logins are gone.
    assert FederatedLogin.select().where(FederatedLogin.user == user).count() == 0
    assert (
        not FederatedLogin.select().where(FederatedLogin.service_ident == "someusername").exists()
    )

    # Ensure the oauth assigned token is gone
    assert get_token_assignment(assigned_token.uuid, user, org) is None

    # Ensure we can create a user with the same namespace again.
    new_user = create_user_noverify("foobar", "foo@example.com", email_required=False)
    assert new_user.id != user.id

    # Ensure the older user is still in the DB.
    assert User.get(id=user.id).username != "foobar"


def test_mark_organization_for_deletion(initialized_db):
    def create_transaction(db):
        return db.transaction()

    # Create a user and then mark it for deletion.
    user = get_user("devtable")
    org = create_organization("foobar", "foobar@devtable.com", user)

    # Add some robots.
    create_robot("foo", org)
    create_robot("bar", org)

    assert lookup_robot("foobar+foo") is not None
    assert lookup_robot("foobar+bar") is not None
    assert len(list(list_namespace_robots("foobar"))) == 2

    # Add some federated user links.
    attach_federated_login(org, "google", "someusername")
    attach_federated_login(org, "github", "someusername")
    assert FederatedLogin.select().where(FederatedLogin.user == org).count() == 2
    assert FederatedLogin.select().where(FederatedLogin.service_ident == "someusername").exists()

    # Add an oauth assigned token and application
    application1 = model.oauth.create_application(
        org, "test", "http://foo/bar", "http://foo/bar/baz"
    )
    application = model.oauth.create_application(
        org, "test2", "http://foo/bar", "http://foo/bar/baz"
    )
    assigned_token = assign_token_to_user(
        application, user, "http://foo/bar/baz", READ_REPO.scope, "token"
    )
    assert get_token_assignment(assigned_token.uuid, user, org) is not None

    # Mark the user for deletion.
    queue = WorkQueue("testgcnamespace", create_transaction)
    mark_namespace_for_deletion(org, [], queue)

    # Ensure the older user is still in the DB.
    older_user = User.get(id=org.id)
    assert older_user.username != "foobar"

    # Ensure the robots are deleted.
    with pytest.raises(InvalidRobotException):
        assert lookup_robot("foobar+foo")

    with pytest.raises(InvalidRobotException):
        assert lookup_robot("foobar+bar")

    assert len(list(list_namespace_robots(older_user.username))) == 0

    # Ensure the federated logins are gone.
    assert FederatedLogin.select().where(FederatedLogin.user == org).count() == 0
    assert (
        not FederatedLogin.select().where(FederatedLogin.service_ident == "someusername").exists()
    )

    # Ensure the oauth assigned token is gone
    assert get_oauth_application_for_client_id(application1.client_id) is None
    assert get_oauth_application_for_client_id(application.client_id) is None
    assert get_token_assignment(assigned_token.uuid, org, org) is None

    # Ensure we can create a user with the same namespace again.
    new_org = create_organization("foobar", "foobar@devtable.com", user)
    assert new_org.id != org.id

    # Ensure the older org is still in the DB.
    assert User.get(id=org.id).username != "foobar"


def test_delete_namespace_via_marker(initialized_db):
    def create_transaction(db):
        return db.transaction()

    # Create a user and then mark it for deletion.
    user = create_user_noverify("foobar", "foo@example.com", email_required=False)

    # Add some repositories.
    create_repository("foobar", "somerepo", user)
    create_repository("foobar", "anotherrepo", user)

    # Mark the user for deletion.
    queue = WorkQueue("testgcnamespace", create_transaction)
    marker_id = mark_namespace_for_deletion(user, [], queue)

    # Delete the user.
    with check_transitive_modifications():
        delete_namespace_via_marker(marker_id, [])

    # Ensure the user was actually deleted.
    with pytest.raises(User.DoesNotExist):
        User.get(id=user.id)

    with pytest.raises(DeletedNamespace.DoesNotExist):
        DeletedNamespace.get(id=marker_id)


def test_delete_robot(initialized_db):
    # Create a robot account.
    user = create_user_noverify("foobar", "foo@example.com", email_required=False)
    robot, _ = create_robot("foo", user)

    # Add some notifications and other rows pointing to the robot.
    create_notification("repo_push", robot)

    team = create_team("someteam", get_organization("buynlarge"), "member")
    add_user_to_team(robot, team)

    # Ensure the robot exists.
    assert lookup_robot(robot.username).id == robot.id

    # Delete the robot.
    delete_robot(robot.username)

    # Ensure it is gone.
    with pytest.raises(InvalidRobotException):
        lookup_robot(robot.username)


def test_get_matching_users(initialized_db):
    # Exact match.
    for user in User.select().where(User.organization == False, User.robot == False):
        assert list(get_matching_users(user.username))[0].username == user.username

    # Prefix matching.
    for user in User.select().where(User.organization == False, User.robot == False):
        assert user.username in [r.username for r in get_matching_users(user.username[:2])]


def test_get_matching_users_with_same_prefix(initialized_db):
    # Create a bunch of users with the same prefix.
    for index in range(0, 20):
        create_user_noverify("foo%s" % index, "foo%s@example.com" % index, email_required=False)

    # For each user, ensure that lookup of the exact name is found first.
    for index in range(0, 20):
        username = "foo%s" % index
        assert list(get_matching_users(username))[0].username == username

    # Prefix matching.
    found = list(get_matching_users("foo", limit=50))
    assert len(found) == 20


def test_robot(initialized_db):
    # Create a robot account.
    user = create_user_noverify("foobar", "foo@example.com", email_required=False)
    robot, token = create_robot("foo", user)
    assert retrieve_robot_token(robot) == token

    # Ensure we can retrieve its information.
    found = lookup_robot("foobar+foo")
    assert found == robot

    creds = get_pull_credentials("foobar+foo")
    assert creds is not None
    assert creds["username"] == "foobar+foo"
    assert creds["password"] == token

    assert verify_robot("foobar+foo", token, None) == robot

    with pytest.raises(InvalidRobotException):
        assert verify_robot("foobar+foo", "someothertoken", None)

    with pytest.raises(InvalidRobotException):
        assert verify_robot("foobar+unknownbot", token, None)


def test_jwt_robot_token(initialized_db):
    user = get_user("devtable")
    org = create_organization("foobar", "foobar@devtable.com", user)
    create_robot("foo", org)

    mock_oidc_token = generate_mock_oidc_token(
        issuer="quay", audience="quay-aud", subject="foobar+foo"
    )
    robot, token = create_robot("foo", user)

    mock_instance_keys = Mock(InstanceKeys)
    mock_instance_keys.service_name = "quay"
    mock_instance_keys.get_service_key_public_key = Mock(return_value=MOCK_PUBLIC_KEY)

    with patch("data.model.config.app_config", {"SERVER_HOSTNAME": "quay-aud"}):
        verify_robot("foobar+foo", mock_oidc_token, mock_instance_keys)


def test_get_estimated_robot_count(initialized_db):
    assert get_estimated_robot_count() >= RobotAccountToken.select().count()


def test_get_quay_user_from_federated_login_name(initialized_db):
    username = "non-existant-user"
    assert get_quay_user_from_federated_login_name(username) is None

    devtable_username = "devtable"
    # When quay.io username is same as SSO username
    result = get_quay_user_from_federated_login_name(devtable_username)
    assert result.username == devtable_username

    freshuser_username = "freshuser"  # SSO username
    public_username = "public"  # quayio username
    # When quay.io username is different from SSO username
    result = get_quay_user_from_federated_login_name(freshuser_username)
    assert result.username == public_username


def test_get_public_repo_count(initialized_db):
    username = "non-existant-user"
    assert get_public_repo_count(username) == 0

    public_username = "public"
    assert get_public_repo_count(public_username) == 1


def test_get_active_namespaces(initialized_db):
    num_active_users = len(get_active_users(disabled=False))
    num_organizations = len(get_organizations())
    active_namespaces = len(get_active_namespaces())
    assert num_active_users > 0
    assert num_organizations > 0
    assert active_namespaces == num_active_users + num_organizations
