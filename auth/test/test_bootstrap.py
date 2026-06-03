from base64 import b64encode
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from jwt import InvalidTokenError

from auth.bootstrap import (
    BootstrapAuthError,
    BootstrapAuthResult,
    validate_bootstrap_auth,
)


def _basic_auth_header(username, password):
    """Build a Basic Auth header value."""
    token_bytes = b"%s:%s" % (username.encode("utf-8"), password.encode("utf-8"))
    return "Basic " + b64encode(token_bytes).decode("ascii")


@pytest.fixture
def flask_app():
    """Create a minimal Flask app for request context."""
    test_app = Flask(__name__)
    test_app.config["AUTHENTICATION_TYPE"] = "Database"
    return test_app


@pytest.fixture
def oidc_flask_app():
    """Create a Flask app configured for OIDC authentication."""
    test_app = Flask(__name__)
    test_app.config["AUTHENTICATION_TYPE"] = "OIDC"
    return test_app


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.username = "testadmin"
    user.enabled = True
    return user


@pytest.fixture
def disabled_user():
    user = MagicMock()
    user.username = "disableduser"
    user.enabled = False
    return user


@pytest.fixture
def mock_oidc_service():
    """Create a mock OIDCLoginService."""
    service = MagicMock()
    service.service_id.return_value = "someoidc"
    service.service_name.return_value = "Some OIDC"
    service.config = {}
    return service


def _mock_login_result(user_obj=None, error_message=None):
    """Create a mock OAuthLoginResult."""
    result = MagicMock()
    result.user_obj = user_obj
    result.error_message = error_message
    return result


class TestValidateBootstrapAuth:
    def test_feature_flag_disabled(self, flask_app):
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("admin", "password")}
        ):
            with patch("auth.bootstrap.features") as mock_features:
                mock_features.PROGRAMMATIC_BOOTSTRAP = False
                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 403
                assert "FEATURE_PROGRAMMATIC_BOOTSTRAP" in exc_info.value.message

    def test_oidc_basic_auth_rejected(self, oidc_flask_app):
        """Basic Auth on OIDC deployment returns 401 (requires Bearer)."""
        with oidc_flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("admin", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Bearer" in exc_info.value.message

    def test_apptoken_returns_501(self, flask_app):
        flask_app.config["AUTHENTICATION_TYPE"] = "AppToken"
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("admin", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 501

    def test_missing_auth_header(self, flask_app):
        with flask_app.test_request_context():
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Missing" in exc_info.value.message

    def test_bearer_on_database_rejected(self, flask_app):
        """Bearer token on Database deployment returns 401."""
        with flask_app.test_request_context(headers={"Authorization": "Bearer sometoken"}):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Basic" in exc_info.value.message

    def test_valid_database_superuser(self, flask_app, mock_user):
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("testadmin", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.model") as mock_model,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_model.user.verify_user.return_value = mock_user
                mock_usermanager.is_superuser.return_value = True

                result = validate_bootstrap_auth()
                assert isinstance(result, BootstrapAuthResult)
                assert result.user == mock_user
                assert result.auth_method == "Database"

    def test_invalid_database_credentials(self, flask_app):
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("testadmin", "wrongpw")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.model") as mock_model,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_model.user.verify_user.return_value = None

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Invalid credentials" in exc_info.value.message

    def test_database_non_superuser_rejected(self, flask_app, mock_user):
        """Non-superuser gets 401."""
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("testadmin", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.model") as mock_model,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_model.user.verify_user.return_value = mock_user
                mock_usermanager.is_superuser.return_value = False

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Superuser" in exc_info.value.message

    def test_disabled_user(self, flask_app, disabled_user):
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("disableduser", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.model") as mock_model,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_model.user.verify_user.return_value = disabled_user

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "disabled" in exc_info.value.message

    def test_ldap_superuser(self, flask_app, mock_user):
        flask_app.config["AUTHENTICATION_TYPE"] = "LDAP"
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("ldapuser", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.authentication") as mock_auth,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_auth.verify_and_link_user.return_value = (mock_user, None)
                mock_usermanager.is_superuser.return_value = True

                result = validate_bootstrap_auth()
                assert result.auth_method == "LDAP"
                assert result.user == mock_user

    def test_ldap_invalid_credentials(self, flask_app):
        flask_app.config["AUTHENTICATION_TYPE"] = "LDAP"
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("ldapuser", "wrongpw")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.authentication") as mock_auth,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_auth.verify_and_link_user.return_value = (None, "Invalid LDAP credentials")

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401

    def test_ldap_non_superuser_rejected(self, flask_app, mock_user):
        """LDAP non-superuser gets 401."""
        flask_app.config["AUTHENTICATION_TYPE"] = "LDAP"
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("ldapuser", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.authentication") as mock_auth,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_auth.verify_and_link_user.return_value = (mock_user, None)
                mock_usermanager.is_superuser.return_value = False

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401

    def test_ldap_jit_provision(self, flask_app, mock_user):
        """LDAP user without local account -- verify_and_link_user creates and returns user."""
        flask_app.config["AUTHENTICATION_TYPE"] = "LDAP"
        with flask_app.test_request_context(
            headers={"Authorization": _basic_auth_header("newldapuser", "password")}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
                patch("auth.bootstrap.authentication") as mock_auth,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                # verify_and_link_user JIT-provisions and returns the user
                mock_auth.verify_and_link_user.return_value = (mock_user, None)
                mock_usermanager.is_superuser.return_value = True

                result = validate_bootstrap_auth()
                assert result.user == mock_user
                mock_auth.verify_and_link_user.assert_called_once_with("newldapuser", "password")

    def test_invalid_base64_encoding(self, flask_app):
        with flask_app.test_request_context(headers={"Authorization": "Basic not-valid-base64!!!"}):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", flask_app),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401


class TestOIDCBootstrapAuth:
    """Tests for OIDC JWT bearer token authentication."""

    def test_oidc_bearer_valid_superuser(self, oidc_flask_app, mock_user, mock_oidc_service):
        """Valid JWT with user in SUPER_USERS succeeds."""
        decoded_jwt = {
            "sub": "oidc-user-123",
            "preferred_username": "oidcadmin",
            "email": "oidcadmin@test.com",
            "email_verified": True,
        }
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
                patch("auth.bootstrap.get_sub_username_email_from_token") as mock_extract,
                patch("auth.bootstrap._conduct_oauth_login") as mock_login,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.return_value = decoded_jwt
                mock_extract.return_value = ("oidc-user-123", "oidcadmin", "oidcadmin@test.com", {})
                mock_login.return_value = _mock_login_result(user_obj=mock_user)
                mock_usermanager.is_superuser.return_value = True

                result = validate_bootstrap_auth()
                assert isinstance(result, BootstrapAuthResult)
                assert result.user == mock_user
                assert result.auth_method == "OIDC"
                mock_oidc_service.decode_user_jwt.assert_called_once_with("valid.jwt.token")

    def test_oidc_bearer_non_superuser_rejected(self, oidc_flask_app, mock_user, mock_oidc_service):
        """OIDC user not in SUPER_USERS returns 401."""
        decoded_jwt = {
            "sub": "oidc-user-123",
            "preferred_username": "regularuser",
            "email": "regular@test.com",
            "email_verified": True,
        }
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
                patch("auth.bootstrap.get_sub_username_email_from_token") as mock_extract,
                patch("auth.bootstrap._conduct_oauth_login") as mock_login,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.return_value = decoded_jwt
                mock_extract.return_value = ("oidc-user-123", "regularuser", "regular@test.com", {})
                mock_login.return_value = _mock_login_result(user_obj=mock_user)
                mock_usermanager.is_superuser.return_value = False

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Superuser" in exc_info.value.message

    def test_oidc_bearer_expired_jwt(self, oidc_flask_app, mock_oidc_service):
        """Expired JWT returns 401 with generic message (no detail leak)."""
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer expired.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.side_effect = InvalidTokenError("Token expired")

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert exc_info.value.message == "Invalid OIDC token"

    def test_oidc_bearer_invalid_jwt(self, oidc_flask_app, mock_oidc_service):
        """Garbage bearer token returns 401."""
        with oidc_flask_app.test_request_context(headers={"Authorization": "Bearer not-a-jwt"}):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.side_effect = InvalidTokenError("Invalid token")

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401

    def test_oidc_jit_provisions_new_user(self, oidc_flask_app, mock_user, mock_oidc_service):
        """JIT provisioning: _conduct_oauth_login is called with correct args."""
        decoded_jwt = {
            "sub": "new-oidc-user",
            "preferred_username": "newuser",
            "email": "newuser@test.com",
            "email_verified": True,
        }
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap.analytics") as mock_analytics,
                patch("auth.bootstrap.authentication") as mock_auth,
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
                patch("auth.bootstrap.get_sub_username_email_from_token") as mock_extract,
                patch("auth.bootstrap._conduct_oauth_login") as mock_login,
                patch("auth.bootstrap.usermanager") as mock_usermanager,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.return_value = decoded_jwt
                mock_extract.return_value = ("new-oidc-user", "newuser", "newuser@test.com", {})
                mock_login.return_value = _mock_login_result(user_obj=mock_user)
                mock_usermanager.is_superuser.return_value = True

                result = validate_bootstrap_auth()
                assert result.user == mock_user

                mock_login.assert_called_once_with(
                    config=oidc_flask_app.config,
                    analytics=mock_analytics,
                    auth_system=mock_auth,
                    login_service=mock_oidc_service,
                    lid="new-oidc-user",
                    lusername="newuser",
                    lemail="newuser@test.com",
                    captcha_verified=True,
                )

    def test_oidc_disabled_user_401(self, oidc_flask_app, disabled_user, mock_oidc_service):
        """Disabled OIDC user returns 401."""
        decoded_jwt = {
            "sub": "disabled-user",
            "preferred_username": "disableduser",
            "email": "disabled@test.com",
            "email_verified": True,
        }
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
                patch("auth.bootstrap.get_sub_username_email_from_token") as mock_extract,
                patch("auth.bootstrap._conduct_oauth_login") as mock_login,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.return_value = decoded_jwt
                mock_extract.return_value = (
                    "disabled-user",
                    "disableduser",
                    "disabled@test.com",
                    {},
                )
                mock_login.return_value = _mock_login_result(user_obj=disabled_user)

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "disabled" in exc_info.value.message

    def test_oidc_login_failure_401(self, oidc_flask_app, mock_oidc_service):
        """_conduct_oauth_login returning an error raises 401."""
        decoded_jwt = {
            "sub": "oidc-user-123",
            "preferred_username": "failuser",
            "email": "fail@test.com",
            "email_verified": True,
        }
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
                patch("auth.bootstrap.get_sub_username_email_from_token") as mock_extract,
                patch("auth.bootstrap._conduct_oauth_login") as mock_login,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.return_value = decoded_jwt
                mock_extract.return_value = ("oidc-user-123", "failuser", "fail@test.com", {})
                mock_login.return_value = _mock_login_result(error_message="User creation blocked")

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert exc_info.value.message == "OIDC login failed"

    def test_oidc_no_service_configured_501(self, oidc_flask_app):
        """No OIDCLoginService registered returns 501."""
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap.oauth_login") as mock_oauth_login,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oauth_login.services = []

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 501
                assert "No OIDC login service" in exc_info.value.message

    def test_oidc_public_key_load_failure(self, oidc_flask_app, mock_oidc_service):
        """PublicKeyLoadException during JWT validation returns 401."""
        from oauth.oidc import PublicKeyLoadException

        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.side_effect = PublicKeyLoadException(
                    "Key not found"
                )

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Could not validate" in exc_info.value.message

    def test_oidc_connection_error(self, oidc_flask_app, mock_oidc_service):
        """ConnectionError when OIDC provider is unreachable returns 401."""
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.side_effect = ConnectionError(
                    "Connection refused"
                )

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert "Could not connect" in exc_info.value.message

    def test_oidc_conduct_login_raises_exception(self, oidc_flask_app, mock_oidc_service):
        """OAuthLoginException from _conduct_oauth_login returns 401."""
        from oauth.login import OAuthLoginException

        decoded_jwt = {
            "sub": "oidc-user-123",
            "preferred_username": "baduser",
            "email": "bad@test.com",
            "email_verified": True,
        }
        with oidc_flask_app.test_request_context(
            headers={"Authorization": "Bearer valid.jwt.token"}
        ):
            with (
                patch("auth.bootstrap.features") as mock_features,
                patch("auth.bootstrap.app", oidc_flask_app),
                patch("auth.bootstrap._get_oidc_service", return_value=mock_oidc_service),
                patch("auth.bootstrap.get_sub_username_email_from_token") as mock_extract,
                patch("auth.bootstrap._conduct_oauth_login") as mock_login,
            ):
                mock_features.PROGRAMMATIC_BOOTSTRAP = True
                mock_oidc_service.decode_user_jwt.return_value = decoded_jwt
                mock_extract.return_value = ("oidc-user-123", "baduser", "bad@test.com", {})
                mock_login.side_effect = OAuthLoginException("Impersonated principal")

                with pytest.raises(BootstrapAuthError) as exc_info:
                    validate_bootstrap_auth()
                assert exc_info.value.status_code == 401
                assert exc_info.value.message == "OIDC login failed"
