from unittest.mock import MagicMock, patch

import pytest
import requests

from auth.test.mock_oidc_server import (
    MOCK_CUSTOM_AUDIENCE,
    MOCK_V1_ISSUER,
    MOCK_V2_ISSUER,
    generate_mock_oidc_token,
    mock_get,
    mock_request,
)
from oauth.oidc import OIDCLoginService
from util.security.jwtutil import InvalidTokenError


def _make_service(config_overrides=None):
    """Helper to create an OIDCLoginService without triggering discovery."""
    base_config = {
        "CLIENT_ID": "test-client-id",
        "CLIENT_SECRET": "test-secret",
        "OIDC_SERVER": "https://login.microsoftonline.com/tenant/v2.0",
        "DEBUGGING": True,
    }
    if config_overrides:
        base_config.update(config_overrides)
    service = OIDCLoginService.__new__(OIDCLoginService)
    service.config = base_config
    service._id = "testoidc"
    service._http_client = MagicMock()
    service._mailing = False
    return service


class TestOIDCIssuers:
    """Tests for multi-issuer resolution in OIDCLoginService."""

    def test_issuers_from_oidc_issuers_config(self):
        """OIDC_ISSUERS list takes priority."""
        service = _make_service(
            {
                "OIDC_ISSUERS": [
                    "https://sts.windows.net/tenant/",
                    "https://login.microsoftonline.com/tenant/v2.0",
                ]
            }
        )
        assert service._issuers == [
            "https://sts.windows.net/tenant/",
            "https://login.microsoftonline.com/tenant/v2.0",
        ]

    def test_issuers_fallback_to_oidc_issuer(self):
        """Falls back to single OIDC_ISSUER when OIDC_ISSUERS not set."""
        service = _make_service(
            {
                "OIDC_ISSUER": "https://sts.windows.net/tenant/",
            }
        )
        assert service._issuers == ["https://sts.windows.net/tenant/"]

    def test_issuers_precedence_over_singular(self):
        """OIDC_ISSUERS takes precedence over OIDC_ISSUER."""
        service = _make_service(
            {
                "OIDC_ISSUER": "https://sts.windows.net/tenant/",
                "OIDC_ISSUERS": [
                    "https://login.microsoftonline.com/tenant/v2.0",
                ],
            }
        )
        assert service._issuers == [
            "https://login.microsoftonline.com/tenant/v2.0",
        ]


class TestOIDCAudiences:
    """Tests for multi-audience resolution in OIDCLoginService."""

    def test_audiences_from_config(self):
        """OIDC_AUDIENCES list is used when configured."""
        service = _make_service(
            {
                "OIDC_AUDIENCES": ["test-client-id", "api://quay-api"],
            }
        )
        assert "test-client-id" in service._audiences
        assert "api://quay-api" in service._audiences

    def test_audiences_default_to_client_id(self):
        """Defaults to [CLIENT_ID] when OIDC_AUDIENCES not set."""
        service = _make_service()
        assert service._audiences == ["test-client-id"]

    def test_audiences_always_includes_client_id(self):
        """CLIENT_ID is always included even if not in OIDC_AUDIENCES."""
        service = _make_service(
            {
                "OIDC_AUDIENCES": ["api://quay-api"],
            }
        )
        assert "test-client-id" in service._audiences
        assert "api://quay-api" in service._audiences


class TestOIDCAllowedClients:
    """Tests for OIDC_ALLOWED_CLIENTS configuration."""

    def test_allowed_clients_returns_config(self):
        """Returns OIDC_ALLOWED_CLIENTS when configured."""
        service = _make_service(
            {
                "OIDC_ALLOWED_CLIENTS": ["rhdh-client", "devspaces-client"],
            }
        )
        assert service.allowed_clients == ["rhdh-client", "devspaces-client"]

    def test_allowed_clients_none_when_not_configured(self):
        """Returns None when OIDC_ALLOWED_CLIENTS not set."""
        service = _make_service()
        assert service.allowed_clients is None


def _mock_http_get(url, *args, **kwargs):
    """Wrapper that adapts mock_get (expects obj, url) for direct call (url only)."""
    return mock_get(None, url, *args, **kwargs)


def _make_service_with_mock(config_overrides=None):
    """Create an OIDCLoginService backed by the mock OIDC server for decode tests."""
    base_config = {
        "CLIENT_ID": "mock-client-id",
        "CLIENT_SECRET": "test-secret",
        "OIDC_SERVER": "https://mock-oidc-server.com",
        "DEBUGGING": True,
    }
    if config_overrides:
        base_config.update(config_overrides)

    http_client = MagicMock()
    http_client.get = _mock_http_get

    config = {"testoidc": base_config, "HTTPCLIENT": http_client}
    service = OIDCLoginService(config, "testoidc", client=http_client)
    return service


class TestDecodeMultiIssuer:
    """Tests for decode_user_jwt with multiple issuers.

    These test the core question: when a token arrives with a particular
    issuer, does Quay accept or reject it based on the configured issuer list?
    """

    @patch.object(requests.Session, "request", mock_request)
    def test_decode_v1_token_with_multi_issuer(self):
        """A v1.0 token is accepted when the v1 issuer is in OIDC_ISSUERS."""
        service = _make_service_with_mock(
            {
                "OIDC_ISSUERS": [MOCK_V1_ISSUER, MOCK_V2_ISSUER],
            }
        )
        token = generate_mock_oidc_token(
            issuer=MOCK_V1_ISSUER,
            audience="mock-client-id",
        )
        decoded = service.decode_user_jwt(token)
        assert decoded["iss"] == MOCK_V1_ISSUER

    @patch.object(requests.Session, "request", mock_request)
    def test_decode_v2_token_with_multi_issuer(self):
        """A v2.0 token is accepted when the v2 issuer is in OIDC_ISSUERS."""
        service = _make_service_with_mock(
            {
                "OIDC_ISSUERS": [MOCK_V1_ISSUER, MOCK_V2_ISSUER],
            }
        )
        token = generate_mock_oidc_token(
            issuer=MOCK_V2_ISSUER,
            audience="mock-client-id",
        )
        decoded = service.decode_user_jwt(token)
        assert decoded["iss"] == MOCK_V2_ISSUER

    @patch.object(requests.Session, "request", mock_request)
    def test_decode_unknown_issuer_rejected(self):
        """A token from an unknown issuer is rejected."""
        service = _make_service_with_mock(
            {
                "OIDC_ISSUERS": [MOCK_V1_ISSUER],
            }
        )
        token = generate_mock_oidc_token(
            issuer="https://evil-server.com",
            audience="mock-client-id",
        )
        with pytest.raises(InvalidTokenError, match="not in configured issuers"):
            service.decode_user_jwt(token)

    @patch.object(requests.Session, "request", mock_request)
    def test_decode_custom_audience_accepted(self):
        """A token with aud=api://quay-api is accepted when it's in OIDC_AUDIENCES."""
        service = _make_service_with_mock(
            {
                "OIDC_AUDIENCES": [MOCK_CUSTOM_AUDIENCE],
            }
        )
        token = generate_mock_oidc_token(
            audience=MOCK_CUSTOM_AUDIENCE,
        )
        decoded = service.decode_user_jwt(token)
        assert decoded["aud"] == MOCK_CUSTOM_AUDIENCE

    @patch.object(requests.Session, "request", mock_request)
    def test_decode_wrong_audience_rejected(self):
        """A token with an unlisted audience is rejected."""
        service = _make_service_with_mock(
            {
                "OIDC_AUDIENCES": ["api://quay-api"],
            }
        )
        token = generate_mock_oidc_token(
            audience="api://wrong-api",
        )
        with pytest.raises(InvalidTokenError):
            service.decode_user_jwt(token)


class TestConfigValidation:
    """Tests for validation of OIDC_ISSUERS, OIDC_AUDIENCES, OIDC_ALLOWED_CLIENTS."""

    def test_oidc_issuers_must_be_list(self):
        """OIDC_ISSUERS as a string raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            _make_service_with_mock({"OIDC_ISSUERS": "https://issuer.com"})

    def test_oidc_issuers_must_not_be_empty(self):
        """Empty OIDC_ISSUERS raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            _make_service_with_mock({"OIDC_ISSUERS": []})

    def test_oidc_audiences_must_be_list(self):
        """OIDC_AUDIENCES as a string raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            _make_service_with_mock({"OIDC_AUDIENCES": "api://quay"})

    def test_oidc_allowed_clients_must_contain_strings(self):
        """OIDC_ALLOWED_CLIENTS with non-strings raises ValueError."""
        with pytest.raises(ValueError, match="must contain only strings"):
            _make_service_with_mock({"OIDC_ALLOWED_CLIENTS": [123, 456]})


class TestBackwardCompatibility:
    """Ensure existing single-issuer/audience configs work unchanged after upgrade.

    An admin who upgrades Quay without touching their config should see
    zero behavior change. These tests verify that.
    """

    def test_single_issuer_config_still_works(self):
        """Existing OIDC_ISSUER (singular string) config works for _issuers."""
        service = _make_service({"OIDC_ISSUER": "https://sts.windows.net/tenant/"})
        assert service._issuers == ["https://sts.windows.net/tenant/"]
        assert service.get_issuers() == ["https://sts.windows.net/tenant/"]

    def test_no_oidc_audiences_defaults_to_client_id(self):
        """When OIDC_AUDIENCES is not set, audience defaults to [CLIENT_ID]."""
        service = _make_service()
        assert service._audiences == ["test-client-id"]

    def test_no_allowed_clients_returns_none(self):
        """When OIDC_ALLOWED_CLIENTS is not set, allowed_clients is None."""
        service = _make_service()
        assert service.allowed_clients is None

    @patch.object(requests.Session, "request", mock_request)
    def test_decode_with_default_audience(self):
        """Token with aud=CLIENT_ID works without OIDC_AUDIENCES configured."""
        service = _make_service_with_mock()
        token = generate_mock_oidc_token(audience="mock-client-id")
        decoded = service.decode_user_jwt(token)
        assert decoded["aud"] == "mock-client-id"

    @patch.object(requests.Session, "request", mock_request)
    def test_decode_with_default_issuer(self):
        """Token with issuer from discovery works without OIDC_ISSUERS configured."""
        service = _make_service_with_mock()
        token = generate_mock_oidc_token()
        decoded = service.decode_user_jwt(token)
        assert decoded["iss"] == "https://mock-oidc-server.com"


class TestLoginManagerMultiIssuer:
    """Tests for get_service_by_issuer with multi-issuer services.

    When a bearer token arrives, Quay uses this method to figure out which
    OIDC provider the token belongs to. With multi-issuer, a single provider
    can match on either the v1.0 or v2.0 issuer URL.
    """

    def _make_manager(self, login_config_overrides=None):
        base_login_config = {
            "CLIENT_ID": "test-client",
            "CLIENT_SECRET": "test-secret",
            "OIDC_SERVER": "https://mock-oidc-server.com",
            "DEBUGGING": True,
        }
        if login_config_overrides:
            base_login_config.update(login_config_overrides)

        http_client = MagicMock()
        http_client.get = _mock_http_get

        config = {
            "HTTPCLIENT": http_client,
            "TESTOIDC_LOGIN_CONFIG": base_login_config,
        }

        from oauth.loginmanager import OAuthLoginManager

        return OAuthLoginManager(config, client=http_client)

    def test_lookup_by_v1_issuer(self):
        """Finds the provider when a token has a v1.0 issuer."""
        manager = self._make_manager(
            {
                "OIDC_ISSUERS": [
                    "https://sts.windows.net/tenant/",
                    "https://login.microsoftonline.com/tenant/v2.0",
                ],
            }
        )
        service = manager.get_service_by_issuer("https://sts.windows.net/tenant/")
        assert service is not None
        assert service.service_id() == "testoidc"

    def test_lookup_by_v2_issuer(self):
        """Finds the provider when a token has a v2.0 issuer."""
        manager = self._make_manager(
            {
                "OIDC_ISSUERS": [
                    "https://sts.windows.net/tenant/",
                    "https://login.microsoftonline.com/tenant/v2.0",
                ],
            }
        )
        service = manager.get_service_by_issuer("https://login.microsoftonline.com/tenant/v2.0")
        assert service is not None
        assert service.service_id() == "testoidc"

    def test_lookup_unknown_issuer_returns_none(self):
        """Returns None for an issuer that isn't configured anywhere."""
        manager = self._make_manager(
            {
                "OIDC_ISSUERS": ["https://sts.windows.net/tenant/"],
            }
        )
        service = manager.get_service_by_issuer("https://evil.com")
        assert service is None

    def test_lookup_backward_compat_single_issuer(self):
        """Existing single OIDC_ISSUER config still works for lookup."""
        manager = self._make_manager(
            {
                "OIDC_ISSUER": "https://sts.windows.net/tenant/",
            }
        )
        service = manager.get_service_by_issuer("https://sts.windows.net/tenant/")
        assert service is not None
