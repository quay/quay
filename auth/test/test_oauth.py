import pytest

from auth.oauth import validate_bearer_auth, validate_oauth_token
from auth.validateresult import AuthKind, ValidateResult
from data import model
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
    oauth_token, _ = model.oauth.create_access_token_for_testing(
        user, app.client_id, "repo:read", access_token=token_string
    )
    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken == oauth_token
    assert result.authed_user == user
    assert result.auth_valid


def test_disabled_user_oauth(app):
    user = model.user.get_user("disabled")
    token_string = "%s%s" % ("a" * 20, "b" * 20)
    oauth_token, _ = model.oauth.create_access_token_for_testing(
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
    oauth_token, _ = model.oauth.create_access_token_for_testing(
        user, "deadbeef", "repo:admin", access_token=token_string, expires_in=-1000
    )

    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken is None
    assert result.authed_user is None
    assert not result.auth_valid
    assert result.error_message == "OAuth access token has expired"
