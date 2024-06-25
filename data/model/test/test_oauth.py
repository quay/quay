from unittest.mock import patch

from auth.scopes import READ_REPO
from data import model
from data.model.oauth import DatabaseAuthorizationProvider
from test.fixtures import *

REDIRECT_URI = "http://foo/bar/baz"


class MockDatabaseAuthorizationProvider(DatabaseAuthorizationProvider):
    def get_authorized_user(self):
        return model.user.get_user("devtable")


def setup(num_assignments=0):
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, "test", "http://foo/bar", REDIRECT_URI)
    token_assignment = model.oauth.assign_token_to_user(
        application, user, REDIRECT_URI, READ_REPO.scope, "token"
    )
    return (application, token_assignment, user, org)


def test_get_token_response_with_assignment_id(initialized_db):
    application, token_assignment, user, org = setup()

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        db_auth_provider = MockDatabaseAuthorizationProvider()
        response = db_auth_provider.get_token_response(
            "token",
            application.client_id,
            REDIRECT_URI,
            token_assignment.uuid,
            scope=READ_REPO.scope,
        )

    assert response.status_code == 302
    assert "error" not in response.headers["Location"]
    assert model.oauth.get_token_assignment(token_assignment.uuid, user, org) is None


def test_delete_application(initialized_db):
    application, token_assignment, user, org = setup()

    model.oauth.delete_application(org, application.client_id)

    assert model.oauth.get_token_assignment(token_assignment.uuid, user, org) is None
    assert model.oauth.lookup_application(org, application.client_id) is None


def test_get_assigned_authorization_for_user(initialized_db):
    application, token_assignment, user, org = setup()
    assigned_oauth = model.oauth.get_assigned_authorization_for_user(user, token_assignment.uuid)
    assert assigned_oauth is not None
    assert assigned_oauth.uuid == token_assignment.uuid


def test_list_assigned_authorizations_for_user(initialized_db):
    application, token_assignment, user, org = setup()
    second_token_assignment = model.oauth.assign_token_to_user(
        application, user, REDIRECT_URI, READ_REPO.scope, "token"
    )

    assigned_oauths = model.oauth.list_assigned_authorizations_for_user(user)
    assert len(assigned_oauths) == 3
    assert assigned_oauths[1].uuid == token_assignment.uuid
    assert assigned_oauths[2].uuid == second_token_assignment.uuid


def test_get_oauth_application_for_client_id(initialized_db):
    application, token_assignment, user, org = setup()
    assert model.oauth.get_oauth_application_for_client_id(application.client_id) == application


def test_assign_token_to_user(initialized_db):
    application, token_assignment, user, org = setup()
    created_assignment = model.oauth.get_token_assignment(token_assignment.uuid, user, org)
    assert created_assignment is not None
    assert created_assignment.uuid == token_assignment.uuid
    assert created_assignment.application == application
    assert created_assignment.assigned_user == user
    assert created_assignment.redirect_uri == REDIRECT_URI
    assert created_assignment.scope == READ_REPO.scope
    assert created_assignment.response_type == "token"


def test_get_token_assignment_for_client_id(initialized_db):
    application, token_assignment, user, org = setup()
    assert (
        model.oauth.get_token_assignment_for_client_id(
            token_assignment.uuid, user, application.client_id
        )
        == token_assignment
    )
