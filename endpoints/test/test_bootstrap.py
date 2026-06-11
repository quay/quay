from base64 import b64encode
from unittest.mock import MagicMock, patch

import pytest

from auth.bootstrap import BootstrapAuthError, BootstrapAuthResult
from data import model
from data.model.oauth import validate_access_token
from test.fixtures import *


def _basic_auth_header(username, password):
    """Build a Basic Auth Authorization header value."""
    token_bytes = b"%s:%s" % (username.encode("utf-8"), password.encode("utf-8"))
    return "Basic " + b64encode(token_bytes).decode("ascii")


def _enable_bootstrap(app):
    """Enable FEATURE_PROGRAMMATIC_BOOTSTRAP on the app."""
    import features as features_module

    app.config["FEATURE_PROGRAMMATIC_BOOTSTRAP"] = True
    features_module.PROGRAMMATIC_BOOTSTRAP.value = True


def _make_superuser_result(username="devtable", auth_method="Database"):
    """Create a BootstrapAuthResult for a superuser."""
    user = model.user.get_user(username)
    return BootstrapAuthResult(user=user, auth_method=auth_method)


class TestBootstrapToken:
    def test_bootstrap_feature_disabled_404(self, app):
        """Feature flag off returns 404 (route_show_if hides the endpoint)."""
        import features as features_module

        old_value = features_module.PROGRAMMATIC_BOOTSTRAP.value
        features_module.PROGRAMMATIC_BOOTSTRAP.value = False
        try:
            with app.test_client() as client:
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 404
        finally:
            features_module.PROGRAMMATIC_BOOTSTRAP.value = old_value

    def test_bootstrap_creates_token_success(self, app, initialized_db):
        """Valid superuser Basic Auth creates token."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert "token" in data
                assert "uuid" in data
                assert "application_name" in data
                assert "client_id" in data
                assert "scope" in data
                assert "expires_at" in data
                assert data["scope"] == "repo:read"
                assert data["application_name"] == "bootstrap"

    def test_bootstrap_token_is_valid(self, app, initialized_db):
        """Returned token works with validate_access_token()."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                data = resp.get_json()

                validated = validate_access_token(data["token"])
                assert validated is not None
                assert validated.uuid == data["uuid"]

    def test_bootstrap_reuses_application(self, app, initialized_db):
        """Two calls with same application_name return same client_id."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp1 = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read", "application_name": "myapp"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                resp2 = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read", "application_name": "myapp"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp1.status_code == 200
                assert resp2.status_code == 200
                assert resp1.get_json()["client_id"] == resp2.get_json()["client_id"]

    def test_bootstrap_missing_scope_400(self, app, initialized_db):
        """No scope field returns 400."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 400
                assert "scope" in resp.get_json()["message"].lower()

    def test_bootstrap_invalid_scope_400(self, app, initialized_db):
        """Unrecognized scope returns 400."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "invalid:scope:nonexistent"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 400
                assert "scope" in resp.get_json()["message"].lower()

    def test_bootstrap_super_user_scope_allowed(self, app, initialized_db):
        """scope: 'super:user' succeeds."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "super:user"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                assert resp.get_json()["scope"] == "super:user"

    def test_bootstrap_comma_separated_scope(self, app, initialized_db):
        """scope: 'repo:read,repo:write' accepted and normalized."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read,repo:write"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                assert resp.get_json()["scope"] == "repo:read repo:write"

    def test_bootstrap_non_superuser_401(self, app, initialized_db):
        """Valid creds for non-superuser returns 401."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            with patch(
                "auth.bootstrap.validate_bootstrap_auth",
                side_effect=BootstrapAuthError("Superuser access required", 401),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("public", "password")},
                )
                assert resp.status_code == 401

    def test_bootstrap_invalid_credentials_401(self, app, initialized_db):
        """Bad password returns 401."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            with patch(
                "auth.bootstrap.validate_bootstrap_auth",
                side_effect=BootstrapAuthError("Invalid credentials", 401),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "wrongpw")},
                )
                assert resp.status_code == 401

    def test_bootstrap_custom_expiration(self, app, initialized_db):
        """Custom positive expiration accepted."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read", "expiration": 3600},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200

    def test_bootstrap_negative_expiration_400(self, app, initialized_db):
        """Non-positive expiration returns 400."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read", "expiration": -1},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 400
                assert "expiration" in resp.get_json()["message"]

    def test_bootstrap_zero_expiration_400(self, app, initialized_db):
        """Zero expiration returns 400."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read", "expiration": 0},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 400

    def test_bootstrap_application_name_in_response(self, app, initialized_db):
        """application_name reflected in response."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read", "application_name": "my-ci-app"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                assert resp.get_json()["application_name"] == "my-ci-app"

    def test_bootstrap_non_idempotent(self, app, initialized_db):
        """Two identical calls create two different tokens."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp1 = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                resp2 = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp1.status_code == 200
                assert resp2.status_code == 200
                data1 = resp1.get_json()
                data2 = resp2.get_json()
                assert data1["token"] != data2["token"]
                assert data1["uuid"] != data2["uuid"]

    def test_bootstrap_no_csrf_required(self, app, initialized_db):
        """Request without CSRF token or session succeeds (regression test for CSRF bypass)."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                # No session, no CSRF header, no cookies -- just Basic Auth
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200


class TestBootstrapTokenOIDC:
    """Integration tests for OIDC bootstrap token creation."""

    def test_bootstrap_oidc_creates_token(self, app, initialized_db):
        """OIDC-authenticated superuser creates a valid token."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result(auth_method="OIDC")
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read", "application_name": "oidc-bootstrap"},
                    headers={"Authorization": "Bearer valid.jwt.token"},
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert "token" in data
                assert "uuid" in data
                assert data["application_name"] == "oidc-bootstrap"
                assert data["scope"] == "repo:read"

                validated = validate_access_token(data["token"])
                assert validated is not None

    def test_bootstrap_oidc_audit_method(self, app, initialized_db):
        """Audit log receives 'OIDC' as auth method metadata."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result(auth_method="OIDC")
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action") as mock_log,
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": "Bearer valid.jwt.token"},
                )
                assert resp.status_code == 200
                mock_log.assert_called_once()
                call_kwargs = mock_log.call_args.kwargs
                assert call_kwargs["metadata"]["auth_method"] == "OIDC"

    def test_bootstrap_oidc_super_user_scope(self, app, initialized_db):
        """OIDC-authenticated superuser can create token with super:user scope."""
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result(auth_method="OIDC")
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "super:user"},
                    headers={"Authorization": "Bearer valid.jwt.token"},
                )
                assert resp.status_code == 200
                assert resp.get_json()["scope"] == "super:user"


class TestBootstrapTokenList:
    """Integration tests for listing bootstrap tokens."""

    def _create_token(self, client, auth_result, scope="repo:read", app_name="test-app"):
        with (
            patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
            patch("endpoints.web.log_action"),
        ):
            resp = client.post(
                "/api/v1/bootstrap/token",
                json={"scope": scope, "application_name": app_name},
                headers={"Authorization": _basic_auth_header("devtable", "password")},
            )
            assert resp.status_code == 200
            return resp.get_json()

    def test_list_returns_created_tokens(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            created = self._create_token(client, auth_result)

            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.get(
                    "/api/v1/bootstrap/tokens",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert "tokens" in data
                uuids = [t["uuid"] for t in data["tokens"]]
                assert created["uuid"] in uuids

    def test_list_token_fields(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            created = self._create_token(client, auth_result, app_name="field-check")

            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.get(
                    "/api/v1/bootstrap/tokens",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                token = next(t for t in resp.get_json()["tokens"] if t["uuid"] == created["uuid"])
                assert token["application_name"] == "field-check"
                assert token["scope"] == "repo:read"
                assert token["authorized_user"] == "devtable"
                assert token["created_by"] == "devtable"
                assert token["expires_at"] is not None
                assert token["expired"] is False

    def test_list_expired_false(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            self._create_token(client, auth_result)

            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.get(
                    "/api/v1/bootstrap/tokens?expired=false",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                for token in resp.get_json()["tokens"]:
                    assert token["expired"] is False

    def test_list_invalid_expired_param(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.get(
                    "/api/v1/bootstrap/tokens?expired=maybe",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 400

    def test_list_non_superuser_401(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            with patch(
                "endpoints.web.validate_bootstrap_auth",
                side_effect=BootstrapAuthError("Superuser access required", 401),
            ):
                resp = client.get(
                    "/api/v1/bootstrap/tokens",
                    headers={"Authorization": _basic_auth_header("public", "password")},
                )
                assert resp.status_code == 401


class TestBootstrapTokenDelete:
    """Integration tests for deleting bootstrap tokens."""

    def test_delete_token(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
            ):
                create_resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert create_resp.status_code == 200
                token_uuid = create_resp.get_json()["uuid"]

            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action") as mock_log,
            ):
                resp = client.delete(
                    f"/api/v1/bootstrap/tokens/{token_uuid}",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 204
                mock_log.assert_called_once()

    def test_delete_nonexistent_404(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.delete(
                    "/api/v1/bootstrap/tokens/nonexistent-uuid",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 404

    def test_delete_non_superuser_401(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            with patch(
                "endpoints.web.validate_bootstrap_auth",
                side_effect=BootstrapAuthError("Superuser access required", 401),
            ):
                resp = client.delete(
                    "/api/v1/bootstrap/tokens/some-uuid",
                    headers={"Authorization": _basic_auth_header("public", "password")},
                )
                assert resp.status_code == 401


class TestBootstrapTokenLimit:
    """Tests for token-per-application limit enforcement."""

    def test_token_limit_enforced(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch("endpoints.web.log_action"),
                patch("endpoints.web.MAX_TOKENS_PER_APPLICATION", 2),
                patch("endpoints.web.oauth_model.count_active_tokens", return_value=2),
            ):
                resp = client.post(
                    "/api/v1/bootstrap/token",
                    json={"scope": "repo:read"},
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 400
                assert "limit" in resp.get_json()["message"].lower()


class TestBootstrapTokenListFilters:
    """Tests for list endpoint query parameter edge cases."""

    def _create_token(self, client, auth_result, scope="repo:read", app_name="filter-test"):
        with (
            patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
            patch("endpoints.web.log_action"),
        ):
            resp = client.post(
                "/api/v1/bootstrap/token",
                json={"scope": scope, "application_name": app_name},
                headers={"Authorization": _basic_auth_header("devtable", "password")},
            )
            assert resp.status_code == 200
            return resp.get_json()

    def test_list_expired_true(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.get(
                    "/api/v1/bootstrap/tokens?expired=true",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                assert "tokens" in resp.get_json()

    def test_list_invalid_datetime_format(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.get(
                    "/api/v1/bootstrap/tokens?expires_before=not-a-date",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 400
                assert "ISO 8601" in resp.get_json()["message"]

    def test_list_valid_datetime_filters(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            self._create_token(client, auth_result)

            with patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result):
                resp = client.get(
                    "/api/v1/bootstrap/tokens?expires_before=2099-01-01T00:00:00Z&expires_after=2020-01-01T00:00:00Z",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200

    def test_list_pagination_next_page(self, app, initialized_db):
        _enable_bootstrap(app)

        with app.test_client() as client:
            auth_result = _make_superuser_result()
            for _ in range(3):
                self._create_token(client, auth_result)

            with (
                patch("endpoints.web.validate_bootstrap_auth", return_value=auth_result),
                patch(
                    "endpoints.web.oauth_model.list_bootstrap_tokens",
                    return_value=([], "next-page-cursor"),
                ),
            ):
                resp = client.get(
                    "/api/v1/bootstrap/tokens",
                    headers={"Authorization": _basic_auth_header("devtable", "password")},
                )
                assert resp.status_code == 200
                assert resp.get_json()["next_page"] == "next-page-cursor"
