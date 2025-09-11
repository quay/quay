# pylint: disable=missing-docstring

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from flask import session

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import ExternalLoginInformation
from endpoints.test.shared import client_with_identity
from test.fixtures import *


class MockPKCEOIDCService:
    """Mock OIDC service with PKCE enabled for testing"""

    def __init__(self, pkce_enabled=True, pkce_method="S256"):
        self.service_id_value = "testoidc"
        self.pkce_enabled_value = pkce_enabled
        self.pkce_method_value = pkce_method

    def service_id(self):
        return self.service_id_value

    def pkce_enabled(self):
        return self.pkce_enabled_value

    def pkce_method(self):
        return self.pkce_method_value

    def get_login_scopes(self):
        return ["openid", "profile", "email"]

    def get_auth_url(
        self, url_scheme_hostname, redirect_suffix, csrf_token, scopes, extra_auth_params=None
    ):
        # Simulate auth URL generation with PKCE parameters
        base_url = "https://auth.example.com/authorize"
        params = {
            "client_id": "test_client",
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": csrf_token,
            "redirect_uri": f"{url_scheme_hostname.get_url()}/oauth2/{self.service_id_value}/callback{redirect_suffix}",
        }
        if extra_auth_params:
            params.update(extra_auth_params)

        param_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{param_string}"


class MockNonPKCEOIDCService(MockPKCEOIDCService):
    """Mock OIDC service without PKCE for testing"""

    def __init__(self):
        super().__init__(pkce_enabled=False)

    def service_id(self):
        return "nonpkceoidc"


class TestExternalLoginInformationPKCE:
    @pytest.fixture()
    def mock_pkce_service(self):
        return MockPKCEOIDCService()

    @pytest.fixture()
    def mock_non_pkce_service(self):
        return MockNonPKCEOIDCService()

    def test_external_login_info_pkce_enabled(self, app, mock_pkce_service):
        """Test PKCE session storage and auth URL generation"""
        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_pkce_service

            with client_with_identity("devtable", app) as cl:
                # Make request to get external login info
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "login"},
                )

                # Verify response contains auth URL
                assert response.status_code == 200
                data = response.json
                assert "auth_url" in data
                auth_url = data["auth_url"]

                # Verify PKCE parameters are in the auth URL
                assert "code_challenge=" in auth_url
                assert "code_challenge_method=" in auth_url

                # Verify session contains PKCE data
                with cl.session_transaction() as sess:
                    session_key = "_oauth_pkce_testoidc"
                    assert session_key in sess
                    pkce_data = sess[session_key]
                    assert "verifier" in pkce_data
                    assert "ts" in pkce_data
                    assert len(pkce_data["verifier"]) == 64  # Default verifier length
                    assert isinstance(pkce_data["ts"], int)

    def test_external_login_info_pkce_disabled(self, app, mock_non_pkce_service):
        """Test standard behavior without PKCE"""
        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_non_pkce_service

            with client_with_identity("devtable", app) as cl:
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "nonpkceoidc"},
                    {"kind": "login"},
                )

                # Verify response contains auth URL
                assert response.status_code == 200
                data = response.json
                assert "auth_url" in data
                auth_url = data["auth_url"]

                # Verify PKCE parameters are NOT in the auth URL
                assert "code_challenge=" not in auth_url
                assert "code_challenge_method=" not in auth_url

                # Verify session does NOT contain PKCE data
                with cl.session_transaction() as sess:
                    session_key = "_oauth_pkce_nonpkceoidc"
                    assert session_key not in sess

    def test_external_login_info_pkce_s256_method(self, app):
        """Test S256 challenge generation"""
        mock_service = MockPKCEOIDCService(pkce_method="S256")

        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            with client_with_identity("devtable", app) as cl:
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "login"},
                )

                assert response.status_code == 200
                auth_url = response.json["auth_url"]

                # Verify S256 method is used
                assert "code_challenge_method=S256" in auth_url

    def test_external_login_info_pkce_plain_method(self, app):
        """Test plain challenge generation"""
        mock_service = MockPKCEOIDCService(pkce_method="plain")

        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            with client_with_identity("devtable", app) as cl:
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "login"},
                )

                assert response.status_code == 200
                auth_url = response.json["auth_url"]

                # Verify plain method is used
                assert "code_challenge_method=plain" in auth_url

    def test_external_login_info_session_key_format(self, app, mock_pkce_service):
        """Test correct session key naming"""
        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_pkce_service

            with client_with_identity("devtable", app) as cl:
                conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "login"},
                )

                # Verify session key follows expected format
                with cl.session_transaction() as sess:
                    session_key = "_oauth_pkce_testoidc"
                    assert session_key in sess

    def test_external_login_info_session_data_structure(self, app, mock_pkce_service):
        """Test verifier and timestamp storage"""
        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_pkce_service

            with client_with_identity("devtable", app) as cl:
                before_time = int(time.time())

                conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "login"},
                )

                after_time = int(time.time())

                with cl.session_transaction() as sess:
                    session_key = "_oauth_pkce_testoidc"
                    pkce_data = sess[session_key]

                    # Verify data structure
                    assert isinstance(pkce_data, dict)
                    assert "verifier" in pkce_data
                    assert "ts" in pkce_data

                    # Verify verifier is valid
                    verifier = pkce_data["verifier"]
                    assert isinstance(verifier, str)
                    assert 43 <= len(verifier) <= 128  # PKCE spec length

                    # Verify timestamp is reasonable
                    timestamp = pkce_data["ts"]
                    assert isinstance(timestamp, int)
                    assert before_time <= timestamp <= after_time

    def test_external_login_info_attach_flow(self, app, mock_pkce_service):
        """Test PKCE works with attach flow"""
        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_pkce_service

            with client_with_identity("devtable", app) as cl:
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "attach"},
                )

                assert response.status_code == 200
                auth_url = response.json["auth_url"]

                # Verify PKCE parameters are present for attach flow
                assert "code_challenge=" in auth_url
                assert "code_challenge_method=" in auth_url

                # Verify session contains PKCE data for attach flow
                with cl.session_transaction() as sess:
                    session_key = "_oauth_pkce_testoidc"
                    assert session_key in sess

    def test_external_login_info_cli_flow(self, app, mock_pkce_service):
        """Test PKCE works with CLI flow"""
        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_pkce_service

            with client_with_identity("devtable", app) as cl:
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "cli"},
                )

                assert response.status_code == 200
                auth_url = response.json["auth_url"]

                # Verify PKCE parameters are present for CLI flow
                assert "code_challenge=" in auth_url
                assert "code_challenge_method=" in auth_url

    def test_external_login_info_service_without_pkce_methods(self, app):
        """Test graceful handling when service doesn't have PKCE methods"""
        # Create a service without pkce_enabled or pkce_method methods
        mock_service = MagicMock()
        mock_service.service_id.return_value = "oldservice"
        mock_service.get_login_scopes.return_value = ["openid"]
        mock_service.get_auth_url.return_value = "https://auth.example.com/authorize?basic=params"

        # Don't add pkce_enabled or pkce_method methods to simulate old service
        del mock_service.pkce_enabled
        del mock_service.pkce_method

        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            with client_with_identity("devtable", app) as cl:
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "oldservice"},
                    {"kind": "login"},
                )

                # Should succeed without PKCE
                assert response.status_code == 200
                auth_url = response.json["auth_url"]

                # Should not contain PKCE parameters
                assert "code_challenge=" not in auth_url
                assert "code_challenge_method=" not in auth_url

    def test_external_login_info_challenge_verifier_relationship(self, app, mock_pkce_service):
        """Test that challenge is properly derived from verifier"""
        with patch("app.oauth_login.get_service") as mock_get_service:
            mock_get_service.return_value = mock_pkce_service

            with client_with_identity("devtable", app) as cl:
                response = conduct_api_call(
                    cl,
                    ExternalLoginInformation,
                    "POST",
                    {"service_id": "testoidc"},
                    {"kind": "login"},
                )

                assert response.status_code == 200
                auth_url = response.json["auth_url"]

                # Extract challenge from URL
                import urllib.parse

                parsed_url = urllib.parse.urlparse(auth_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                challenge = query_params["code_challenge"][0]
                method = query_params["code_challenge_method"][0]

                # Get verifier from session
                with cl.session_transaction() as sess:
                    session_key = "_oauth_pkce_testoidc"
                    verifier = sess[session_key]["verifier"]

                # Verify challenge was derived from verifier correctly
                from oauth.pkce import code_challenge

                expected_challenge = code_challenge(verifier, method)
                assert challenge == expected_challenge
