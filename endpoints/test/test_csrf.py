from unittest.mock import MagicMock, patch

from app import app
from endpoints.csrf import _has_bootstrap_auth, generate_csrf_token


def test_generate_csrf_token():
    with app.test_request_context():
        token = generate_csrf_token()
        assert isinstance(token, str)


def test_has_bootstrap_auth_enforces_csrf_when_session_active():
    with app.test_request_context(
        headers={"Authorization": "Basic dGVzdDp0ZXN0"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("auth.auth_context.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = MagicMock()
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_bypasses_csrf_when_no_session():
    with app.test_request_context(
        headers={"Authorization": "Basic dGVzdDp0ZXN0"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("auth.auth_context.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is True


def test_has_bootstrap_auth_returns_false_when_feature_disabled():
    with app.test_request_context(
        headers={"Authorization": "Basic dGVzdDp0ZXN0"},
    ):
        with patch("endpoints.csrf.features") as mock_features:
            mock_features.PROGRAMMATIC_BOOTSTRAP = False
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_accepts_bearer():
    with app.test_request_context(
        headers={"Authorization": "Bearer some.jwt.token"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("auth.auth_context.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is True


def test_has_bootstrap_auth_rejects_unknown_scheme():
    with app.test_request_context(
        headers={"Authorization": "Digest abc123"},
    ):
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("auth.auth_context.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is False


def test_has_bootstrap_auth_no_header():
    with app.test_request_context():
        with (
            patch("endpoints.csrf.features") as mock_features,
            patch("auth.auth_context.get_authenticated_user") as mock_get_user,
        ):
            mock_features.PROGRAMMATIC_BOOTSTRAP = True
            mock_get_user.return_value = None
            assert _has_bootstrap_auth() is False
