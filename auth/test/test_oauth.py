import pytest

from auth.oauth import validate_bearer_auth
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.model import api_token
from test.fixtures import *


@pytest.mark.parametrize(
    "header, expected_result",
    [
        ("", ValidateResult(AuthKind.oauth, missing=True)),
        ("somerandomtoken", ValidateResult(AuthKind.oauth, missing=True)),
        ("bearer some random token", ValidateResult(AuthKind.oauth, missing=True)),
        (
            "bearer invalidtoken",
            ValidateResult(
                AuthKind.oauth, error_message="OAuth access token could not be validated"
            ),
        ),
    ],
)
def test_bearer(header, expected_result, app):
    assert validate_bearer_auth(header) == expected_result


def test_valid_oauth(app):
    user = model.user.get_user("devtable")
    app = model.oauth.list_applications_for_org(model.user.get_user_or_org("buynlarge"))[0]
    token_string = "%s%s" % ("a" * 20, "b" * 20)
    oauth_token, _ = model.oauth.create_user_access_token(
        user, app.client_id, "repo:read", access_token=token_string
    )
    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken == oauth_token
    assert result.authed_user == user
    assert result.auth_valid


def test_robot_api_token_authenticates_as_its_robot(app):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("api-token", creator)
    token, secret = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "CI token"
    )

    assert secret.startswith(api_token.API_TOKEN_PREFIX)
    assert token.token_code.matches(secret[len(token.token_name) :])

    result = validate_bearer_auth("Bearer " + secret)

    assert result.context.robot == robot
    assert result.context.api_scopes == "repo:read"
    assert result.authed_user == robot
    assert result.auth_valid

    assert api_token.revoke_token(robot, token.uuid)
    revoked_result = validate_bearer_auth("Bearer " + secret)
    assert not revoked_result.auth_valid
    assert revoked_result.error_message == "API token is invalid, revoked or expired"


@pytest.mark.parametrize("scope", ["", "   ", "direct_user_login"])
def test_robot_api_token_requires_a_non_direct_api_scope(app, scope):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("scoped-api-token", creator)

    with pytest.raises(ValueError, match="must include at least one API scope"):
        api_token.create_token_under_limit(robot, creator, scope, 3600, "Invalid token")


def test_robot_api_token_with_persisted_empty_scope_is_rejected(app):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("empty-scope-token", creator)
    token, secret = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "CI token"
    )
    token.scope = " "
    token.save()

    result = validate_bearer_auth("Bearer " + secret)

    assert not result.auth_valid
    assert result.error_message == "API token has invalid scopes"


def test_disabled_user_oauth(app):
    user = model.user.get_user("disabled")
    token_string = "%s%s" % ("a" * 20, "b" * 20)
    oauth_token, _ = model.oauth.create_user_access_token(
        user, "deadbeef", "repo:admin", access_token=token_string
    )

    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken is None
    assert result.authed_user is None
    assert not result.auth_valid
    assert result.error_message == "Granter of the oauth access token is disabled"


def test_expired_token(app):
    user = model.user.get_user("devtable")
    token_string = "%s%s" % ("a" * 20, "b" * 20)
    oauth_token, _ = model.oauth.create_user_access_token(
        user, "deadbeef", "repo:admin", access_token=token_string, expires_in=-1000
    )

    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken is None
    assert result.authed_user is None
    assert not result.auth_valid
    assert result.error_message == "OAuth access token has expired"
