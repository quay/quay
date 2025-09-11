# pylint: disable=missing-docstring

import json
import urllib.parse
from unittest.mock import Mock

import pytest
import requests
from httmock import HTTMock, urlmatch

from oauth.base import OAuthEndpoint, OAuthService
from util.config import URLSchemeAndHostname


class MockOAuthService(OAuthService):
    """Test implementation of OAuthService for testing base functionality"""

    def __init__(self):
        # Call parent constructor with test config
        test_config = {
            "TESTING": True,
            "TEST_SERVICE": {
                "CLIENT_ID": "test_client_id",
                "CLIENT_SECRET": "test_client_secret",
                "AUTHORIZATION_ENDPOINT": "http://testauth/authorize",
                "TOKEN_ENDPOINT": "http://testauth/token",
                "USER_ENDPOINT": "http://testauth/user",
                "SERVICE_NAME": "Test Service",
            },
        }
        super().__init__(test_config, "TEST_SERVICE")

    def service_id(self):
        return "testservice"

    def service_name(self):
        return self.config["SERVICE_NAME"]

    def client_id(self):
        return self.config["CLIENT_ID"]

    def client_secret(self):
        return self.config["CLIENT_SECRET"]

    def authorize_endpoint(self):
        return OAuthEndpoint(self.config["AUTHORIZATION_ENDPOINT"]).with_param(
            "response_type", "code"
        )

    def token_endpoint(self):
        return OAuthEndpoint(self.config["TOKEN_ENDPOINT"])

    def user_endpoint(self):
        return OAuthEndpoint(self.config["USER_ENDPOINT"])

    def validate_client_id_and_secret(self, http_client, url_scheme_and_hostname):
        # Simple validation for testing
        return self.client_id() == "test_client_id" and self.client_secret() == "test_client_secret"

    def get_login_scopes(self):
        return ["read", "write"]


@pytest.fixture()
def oauth_service():
    return MockOAuthService()


@pytest.fixture()
def http_client():
    sess = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    return sess


class TestGetAuthUrl:
    def test_get_auth_url_basic(self, oauth_service):
        url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")
        redirect_suffix = ""
        csrf_token = "test_csrf_token"
        scopes = ["read", "write"]

        auth_url = oauth_service.get_auth_url(
            url_scheme_hostname, redirect_suffix, csrf_token, scopes
        )

        # Parse the URL to check components
        parsed = urllib.parse.urlparse(auth_url)
        query_params = urllib.parse.parse_qs(parsed.query)

        assert parsed.scheme == "http"
        assert parsed.netloc == "testauth"
        assert parsed.path == "/authorize"
        assert query_params["client_id"][0] == "test_client_id"
        assert query_params["response_type"][0] == "code"
        assert query_params["scope"][0] == "read write"
        assert query_params["state"][0] == urllib.parse.quote(csrf_token)
        assert "redirect_uri" in query_params

    def test_get_auth_url_with_extra_params(self, oauth_service):
        url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")
        redirect_suffix = ""
        csrf_token = "test_csrf_token"
        scopes = ["read", "write"]
        extra_auth_params = {"code_challenge": "test_challenge", "code_challenge_method": "S256"}

        auth_url = oauth_service.get_auth_url(
            url_scheme_hostname, redirect_suffix, csrf_token, scopes, extra_auth_params
        )

        parsed = urllib.parse.urlparse(auth_url)
        query_params = urllib.parse.parse_qs(parsed.query)

        # Standard parameters should still be present
        assert query_params["client_id"][0] == "test_client_id"
        assert query_params["response_type"][0] == "code"
        assert query_params["scope"][0] == "read write"
        assert query_params["state"][0] == urllib.parse.quote(csrf_token)

        # Extra parameters should be included
        assert query_params["code_challenge"][0] == "test_challenge"
        assert query_params["code_challenge_method"][0] == "S256"

    def test_get_auth_url_without_extra_params(self, oauth_service):
        """Test backward compatibility - extra_auth_params=None should work"""
        url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")
        redirect_suffix = ""
        csrf_token = "test_csrf_token"
        scopes = ["read", "write"]

        auth_url = oauth_service.get_auth_url(
            url_scheme_hostname, redirect_suffix, csrf_token, scopes, None
        )

        parsed = urllib.parse.urlparse(auth_url)
        query_params = urllib.parse.parse_qs(parsed.query)

        # Should have standard parameters only
        assert query_params["client_id"][0] == "test_client_id"
        assert query_params["response_type"][0] == "code"
        assert query_params["scope"][0] == "read write"
        assert "code_challenge" not in query_params
        assert "code_challenge_method" not in query_params

    def test_get_auth_url_with_redirect_suffix(self, oauth_service):
        url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")
        redirect_suffix = "/attach"
        csrf_token = "test_csrf_token"
        scopes = ["read"]

        auth_url = oauth_service.get_auth_url(
            url_scheme_hostname, redirect_suffix, csrf_token, scopes
        )

        parsed = urllib.parse.urlparse(auth_url)
        query_params = urllib.parse.parse_qs(parsed.query)

        # Check that redirect_uri includes the suffix
        redirect_uri = query_params["redirect_uri"][0]
        assert redirect_uri.endswith("/attach")


class TestExchangeCode:
    @pytest.fixture()
    def token_handler_basic(self):
        @urlmatch(netloc=r"testauth", path=r"/token")
        def handler(_, request):
            # Parse parameters from body or URL
            if request.body:
                params = urllib.parse.parse_qs(request.body)
            else:
                # If no body, try URL parameters
                from urllib.parse import parse_qs, urlparse

                parsed_url = urlparse(request.url)
                params = parse_qs(parsed_url.query)

            # Validate required parameters
            if not params.get("code") or params.get("code")[0] != "valid_code":
                return {"status_code": 400, "content": "Invalid code"}

            if not params.get("grant_type") or params.get("grant_type")[0] != "authorization_code":
                return {"status_code": 400, "content": "Invalid grant type"}

            if not params.get("client_id") or params.get("client_id")[0] != "test_client_id":
                return {"status_code": 400, "content": "Invalid client_id"}

            if (
                not params.get("client_secret")
                or params.get("client_secret")[0] != "test_client_secret"
            ):
                return {"status_code": 400, "content": "Invalid client_secret"}

            content = {"access_token": "test_access_token", "token_type": "Bearer"}
            return {"status_code": 200, "content": json.dumps(content)}

        return handler

    @pytest.fixture()
    def token_handler_with_extra_params(self):
        @urlmatch(netloc=r"testauth", path=r"/token")
        def handler(_, request):
            # Parse parameters from body or URL
            if request.body:
                params = urllib.parse.parse_qs(request.body)
            else:
                from urllib.parse import parse_qs, urlparse

                parsed_url = urlparse(request.url)
                params = parse_qs(parsed_url.query)

            # Must include code_verifier for PKCE
            if not params.get("code_verifier"):
                return {"status_code": 400, "content": "Missing code_verifier"}

            if params.get("code_verifier")[0] != "test_verifier":
                return {"status_code": 400, "content": "Invalid code_verifier"}

            content = {"access_token": "test_access_token", "token_type": "Bearer"}
            return {"status_code": 200, "content": json.dumps(content)}

        return handler

    @pytest.fixture()
    def token_handler_omit_client_secret(self):
        @urlmatch(netloc=r"testauth", path=r"/token")
        def handler(_, request):
            # Parse parameters from body or URL
            if request.body:
                params = urllib.parse.parse_qs(request.body)
            else:
                from urllib.parse import parse_qs, urlparse

                parsed_url = urlparse(request.url)
                params = parse_qs(parsed_url.query)

            # client_secret should not be present for public clients
            if "client_secret" in params:
                return {"status_code": 400, "content": "client_secret should not be sent"}

            if not params.get("client_id") or params.get("client_id")[0] != "test_client_id":
                return {"status_code": 400, "content": "Invalid client_id"}

            content = {"access_token": "test_access_token", "token_type": "Bearer"}
            return {"status_code": 200, "content": json.dumps(content)}

        return handler

    def test_exchange_code_basic(self, oauth_service, http_client, token_handler_basic):
        """Test standard token exchange"""
        with HTTMock(token_handler_basic):
            url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")

            result = oauth_service.exchange_code(
                {"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "localhost:8080"},
                http_client,
                "valid_code",
            )

            assert result["access_token"] == "test_access_token"
            assert result["token_type"] == "Bearer"

    def test_exchange_code_with_extra_token_params(
        self, oauth_service, http_client, token_handler_with_extra_params
    ):
        """Test token exchange with extra parameters (PKCE)"""
        with HTTMock(token_handler_with_extra_params):
            url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")
            extra_token_params = {"code_verifier": "test_verifier"}

            result = oauth_service.exchange_code(
                {"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "localhost:8080"},
                http_client,
                "valid_code",
                extra_token_params=extra_token_params,
            )

            assert result["access_token"] == "test_access_token"

    def test_exchange_code_without_extra_params(
        self, oauth_service, http_client, token_handler_basic
    ):
        """Test backward compatibility with no extra params"""
        with HTTMock(token_handler_basic):
            url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")

            result = oauth_service.exchange_code(
                {"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "localhost:8080"},
                http_client,
                "valid_code",
                extra_token_params=None,
            )

            assert result["access_token"] == "test_access_token"

    def test_exchange_code_omit_client_secret(
        self, oauth_service, http_client, token_handler_omit_client_secret
    ):
        """Test public client token exchange (omit client_secret)"""
        with HTTMock(token_handler_omit_client_secret):
            url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")

            result = oauth_service.exchange_code(
                {"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "localhost:8080"},
                http_client,
                "valid_code",
                omit_client_secret=True,
            )

            assert result["access_token"] == "test_access_token"

    def test_exchange_code_include_client_secret(
        self, oauth_service, http_client, token_handler_basic
    ):
        """Test standard client behavior (include client_secret)"""
        with HTTMock(token_handler_basic):
            url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")

            result = oauth_service.exchange_code(
                {"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "localhost:8080"},
                http_client,
                "valid_code",
                omit_client_secret=False,
            )

            assert result["access_token"] == "test_access_token"

    def test_exchange_code_with_redirect_suffix(
        self, oauth_service, http_client, token_handler_basic
    ):
        """Test token exchange with redirect suffix"""
        with HTTMock(token_handler_basic):
            url_scheme_hostname = URLSchemeAndHostname("http", "localhost:8080")

            result = oauth_service.exchange_code(
                {"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "localhost:8080"},
                http_client,
                "valid_code",
                redirect_suffix="/attach",
            )

            assert result["access_token"] == "test_access_token"

    def test_exchange_code_form_encode(self, oauth_service, http_client):
        """Test form encoding parameter"""

        @urlmatch(netloc=r"testauth", path=r"/token")
        def handler(url, request):
            # Check that content-type is form-encoded when form_encode=True
            content_type = request.headers.get("Content-Type", "")
            if "application/x-www-form-urlencoded" not in content_type:
                return {"status_code": 400, "content": "Expected form encoding"}

            content = {"access_token": "test_access_token"}
            return {"status_code": 200, "content": json.dumps(content)}

        with HTTMock(handler):
            result = oauth_service.exchange_code(
                {"PREFERRED_URL_SCHEME": "http", "SERVER_HOSTNAME": "localhost:8080"},
                http_client,
                "valid_code",
                form_encode=True,
            )
