from types import SimpleNamespace
from unittest.mock import patch

import pytest
from jwt import InvalidTokenError

from auth.oauth import (
    validate_bearer_auth,
    validate_oauth_token,
    validate_sso_oauth_token,
)
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
    oauth_token, _ = model.oauth.create_user_access_token(
        user, app.client_id, "repo:read", access_token=token_string
    )
    assert oauth_token.last_accessed is None

    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken == oauth_token
    assert result.authed_user == user
    assert result.auth_valid
    assert result.context.oauthtoken.last_accessed is not None


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


class FakeSSOService:
    def __init__(self, decoded=None, allowed_clients=None, exception=None):
        self.decoded = decoded or {}
        self.allowed_clients = allowed_clients
        self.exception = exception

    def decode_user_jwt(self, token, options=None):
        self.options = options
        if self.exception is not None:
            raise self.exception
        return self.decoded


def test_validate_oauth_token_routes_jwt_to_sso():
    expected = object()
    with (
        patch("auth.oauth.is_jwt", return_value=True),
        patch("auth.oauth.validate_sso_oauth_token", return_value=expected) as validate_sso,
    ):
        assert validate_oauth_token("jwt-token") is expected
        validate_sso.assert_called_once_with("jwt-token")


def test_validate_sso_oauth_token_missing_issuer():
    with patch("auth.oauth.get_jwt_issuer", return_value=None):
        result = validate_sso_oauth_token("jwt-token")

    assert result.kind == AuthKind.ssojwt
    assert result.error_message == "Token does not contain issuer"


def test_validate_sso_oauth_token_unconfigured_issuer():
    with (
        patch("auth.oauth.get_jwt_issuer", return_value="https://issuer.example"),
        patch("auth.oauth.oauth_login.get_service_by_issuer", return_value=None),
    ):
        result = validate_sso_oauth_token("jwt-token")

    assert result.kind == AuthKind.ssojwt
    assert result.error_message == "Issuer https://issuer.example not configured"


def test_validate_sso_oauth_token_connection_error():
    with (
        patch("auth.oauth.get_jwt_issuer", return_value="https://issuer.example"),
        patch("auth.oauth.oauth_login.get_service_by_issuer", side_effect=ConnectionError),
    ):
        result = validate_sso_oauth_token("jwt-token")

    assert result.kind == AuthKind.ssojwt
    assert result.error_message == "Unable to connect to auth server"


def test_validate_sso_oauth_token_rejects_disallowed_azp(app):
    service = FakeSSOService(decoded={"azp": "bad-client"}, allowed_clients=["good-client"])
    with (
        patch("auth.oauth.get_jwt_issuer", return_value="https://issuer.example"),
        patch("auth.oauth.oauth_login.get_service_by_issuer", return_value=service),
    ):
        result = validate_sso_oauth_token("jwt-token")

    assert result.kind == AuthKind.ssojwt
    assert result.error_message == "Client 'bad-client' is not in the allowed clients list"
    assert service.options["verify_nbf"] is False
    assert service.options["verify_signature"] is False


def test_validate_sso_oauth_token_returns_login_error(app):
    service = FakeSSOService(decoded={"sub": "sub"}, allowed_clients=[])
    login_result = SimpleNamespace(error_message="login failed", user_obj=None)

    with (
        patch("auth.oauth.get_jwt_issuer", return_value="https://issuer.example"),
        patch("auth.oauth.oauth_login.get_service_by_issuer", return_value=service),
        patch(
            "auth.oauth.get_sub_username_email_from_token",
            return_value=("sub", "username", "user@example.com", {}),
        ),
        patch("auth.oauth._conduct_oauth_login", return_value=login_result),
    ):
        result = validate_sso_oauth_token("jwt-token")

    assert result.kind == AuthKind.ssojwt
    assert result.error_message == "login failed"


def test_validate_sso_oauth_token_success_with_azp(app):
    user = model.user.get_user("devtable")
    service = FakeSSOService(decoded={"azp": "good-client"}, allowed_clients=["good-client"])
    login_result = SimpleNamespace(error_message=None, user_obj=user)

    with (
        patch("auth.oauth.get_jwt_issuer", return_value="https://issuer.example"),
        patch("auth.oauth.oauth_login.get_service_by_issuer", return_value=service),
        patch(
            "auth.oauth.get_sub_username_email_from_token",
            return_value=("sub", "devtable", "devtable@example.com", {}),
        ),
        patch("auth.oauth._conduct_oauth_login", return_value=login_result),
    ):
        result = validate_sso_oauth_token("jwt-token")

    assert result.kind == AuthKind.ssojwt
    assert result.authed_user == user
    assert result.context.sso_token == "jwt-token"


def test_validate_sso_oauth_token_decode_exception(app):
    service = FakeSSOService(exception=InvalidTokenError("bad token"))
    with (
        patch("auth.oauth.get_jwt_issuer", return_value="https://issuer.example"),
        patch("auth.oauth.oauth_login.get_service_by_issuer", return_value=service),
    ):
        result = validate_sso_oauth_token("jwt-token")

    assert result.kind == AuthKind.ssojwt
    assert result.error_message == "bad token"


def test_invalid_oauth_logs_when_audit_enabled(app):
    with app.test_request_context("/", headers={"User-Agent": "test-agent"}):
        with (
            patch.dict(app.config, {"ACTION_LOG_AUDIT_LOGIN_FAILURES": True}),
            patch("auth.oauth.log_action") as log_action,
        ):
            result = validate_bearer_auth("bearer invalidtoken")

    assert not result.auth_valid
    log_action.assert_called_once()
    assert log_action.call_args.args[0] == "login_failure"
    assert log_action.call_args.args[2]["useragent"] == "test-agent"


def test_expired_oauth_logs_when_audit_enabled(app):
    user = model.user.get_user("devtable")
    token_string = "%s%s" % ("d" * 20, "e" * 20)
    oauth_token, _ = model.oauth.create_user_access_token(
        user, "deadbeef", "repo:admin", access_token=token_string, expires_in=-1000
    )

    with app.test_request_context("/", headers={"User-Agent": "test-agent"}):
        with (
            patch.dict(app.config, {"ACTION_LOG_AUDIT_LOGIN_FAILURES": True}),
            patch("auth.oauth.log_action") as log_action,
        ):
            result = validate_bearer_auth("bearer " + token_string)

    assert not result.auth_valid
    log_action.assert_called_once()
    metadata = log_action.call_args.args[2]
    assert metadata["token"] == oauth_token.token_name
    assert metadata["message"] == "OAuth access token has expired"


def test_disabled_oauth_logs_when_audit_enabled(app):
    user = model.user.get_user("disabled")
    token_string = "%s%s" % ("f" * 20, "g" * 20)
    model.oauth.create_user_access_token(user, "deadbeef", "repo:admin", access_token=token_string)

    with app.test_request_context("/", headers={"User-Agent": "test-agent"}):
        with (
            patch.dict(app.config, {"ACTION_LOG_AUDIT_LOGIN_FAILURES": True}),
            patch("auth.oauth.log_action") as log_action,
        ):
            result = validate_bearer_auth("bearer " + token_string)

    assert not result.auth_valid
    log_action.assert_called_once()
    metadata = log_action.call_args.args[2]
    assert metadata["username"] == "disabled"
    assert metadata["message"] == "Granter of the oauth access token is disabled"
