from unittest.mock import MagicMock, patch

from flask import session

from app import app
from endpoints.csrf import _has_bootstrap_auth, generate_csrf_token

BOOTSTRAP_PATH = "/api/v1/bootstrap/renew"


def test_generate_csrf_token():
    with app.test_request_context():
        token = generate_csrf_token()
        assert isinstance(token, str)


def test_generate_csrf_token_reuses_existing_token_unless_forced():
    with app.test_request_context():
        first = generate_csrf_token()
        assert generate_csrf_token() == first

        forced = generate_csrf_token(force=True)
        assert forced != first
        assert generate_csrf_token() == forced


def test_has_bootstrap_auth_bypasses_csrf_when_no_session():
    with app.test_request_context(
        BOOTSTRAP_PATH,
        headers={"Authorization": "Bearer some-token"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("endpoints.csrf.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is True


def test_has_bootstrap_auth_enforces_csrf_when_session_active():
    with app.test_request_context(
        BOOTSTRAP_PATH,
        headers={"Authorization": "Bearer some-token"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("endpoints.csrf.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = MagicMock()
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_enforces_csrf_when_session_user_id_present():
    with app.test_request_context(
        BOOTSTRAP_PATH,
        headers={"Authorization": "Bearer some-token"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("endpoints.csrf.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            session["_user_id"] = "devtable"
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_returns_false_when_feature_disabled():
    with app.test_request_context(
        BOOTSTRAP_PATH,
        headers={"Authorization": "Bearer some-token"},
    ):
        with patch("endpoints.csrf.features") as mock_features:
            mock_features.PROGRAMMATIC_BOOTSTRAP = False
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_rejects_basic_scheme():
    with app.test_request_context(
        BOOTSTRAP_PATH,
        headers={"Authorization": "Basic dGVzdDp0ZXN0"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("endpoints.csrf.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_rejects_unknown_scheme():
    with app.test_request_context(
        BOOTSTRAP_PATH,
        headers={"Authorization": "Digest abc123"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("endpoints.csrf.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_no_header():
    with app.test_request_context(BOOTSTRAP_PATH):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("endpoints.csrf.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_rejects_non_bootstrap_path():
    with app.test_request_context(
        "/api/v1/superuser/",
        headers={"Authorization": "Bearer some-token"},
    ):
        with patch("endpoints.csrf.features") as mock_features:
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            assert _has_bootstrap_auth() is False
