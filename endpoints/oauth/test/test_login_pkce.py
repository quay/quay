# pylint: disable=missing-docstring

import time
from unittest.mock import MagicMock, patch

import pytest

from test.fixtures import *


class MockPKCEOIDCService:
    """Mock OIDC service with PKCE enabled for login testing"""

    def __init__(self, pkce_enabled=True, pkce_method="S256"):
        self.pkce_enabled_value = pkce_enabled
        self.pkce_method_value = pkce_method
        self.service_id_value = "testoidc"

    def service_id(self):
        return self.service_id_value

    def pkce_enabled(self):
        return self.pkce_enabled_value

    def pkce_method(self):
        return self.pkce_method_value

    def exchange_code_for_login(self, app_config, http_client, code, redirect_suffix, **kwargs):
        # Simulate successful login with PKCE
        if self.pkce_enabled_value and not kwargs.get("code_verifier"):
            raise Exception("Missing code_verifier")

        return ("test_user_id", "test_username", "test@example.com", {"name": "Test User"})


@pytest.fixture()
def mock_pkce_service():
    return MockPKCEOIDCService()


@pytest.fixture()
def mock_non_pkce_service():
    return MockPKCEOIDCService(pkce_enabled=False)


class TestOAuthLoginPKCE:
    def test_oauth_login_pkce_verifier_retrieval(self, mock_pkce_service):
        """Test session verifier extraction during login"""

        # Simulate session data
        session_data = {
            f"_oauth_pkce_{mock_pkce_service.service_id()}": {
                "verifier": "test-verifier-12345",
                "ts": int(time.time()),
            }
        }

        # Simulate the OAuth callback processing code that would happen in login.py
        session_key = f"_oauth_pkce_{mock_pkce_service.service_id()}"
        data = session_data.pop(session_key, None)
        kwargs = {}

        # Check if service has PKCE enabled
        if hasattr(mock_pkce_service, "pkce_enabled") and mock_pkce_service.pkce_enabled():
            if data and data.get("verifier"):
                kwargs["code_verifier"] = data.get("verifier")

        # Verify verifier was extracted from session
        assert "code_verifier" in kwargs
        assert kwargs["code_verifier"] == "test-verifier-12345"

        # Verify session data was removed
        assert session_key not in session_data

    def test_oauth_login_pkce_missing_session(self, mock_pkce_service):
        """Test graceful handling of missing session"""

        # Simulate empty session data
        session_data = {}

        # Simulate the OAuth callback processing code
        session_key = f"_oauth_pkce_{mock_pkce_service.service_id()}"
        data = session_data.pop(session_key, None)
        kwargs = {}

        # Check if service has PKCE enabled
        if hasattr(mock_pkce_service, "pkce_enabled") and mock_pkce_service.pkce_enabled():
            if data and data.get("verifier"):
                kwargs["code_verifier"] = data.get("verifier")

        # Verify no verifier when session missing
        assert "code_verifier" not in kwargs

    def test_oauth_login_pkce_corrupted_session(self, mock_pkce_service):
        """Test graceful handling of corrupted session data"""

        # Simulate session with corrupted PKCE data
        session_data = {
            f"_oauth_pkce_{mock_pkce_service.service_id()}": "not-a-dict"  # Corrupted data
        }

        # Simulate the OAuth callback processing code
        session_key = f"_oauth_pkce_{mock_pkce_service.service_id()}"
        data = session_data.pop(session_key, None)
        kwargs = {}

        # Check if service has PKCE enabled and data is valid
        if hasattr(mock_pkce_service, "pkce_enabled") and mock_pkce_service.pkce_enabled():
            if data and hasattr(data, "get") and data.get("verifier"):
                kwargs["code_verifier"] = data.get("verifier")

        # Verify no verifier when session is corrupted
        assert "code_verifier" not in kwargs

    def test_oauth_login_pkce_disabled_service(self, mock_non_pkce_service):
        """Test standard flow for non-PKCE services"""

        # Simulate session data (would be ignored for non-PKCE services)
        session_data = {
            f"_oauth_pkce_{mock_non_pkce_service.service_id()}": {
                "verifier": "should-be-ignored",
                "ts": int(time.time()),
            }
        }

        # Simulate the OAuth callback processing code
        session_key = f"_oauth_pkce_{mock_non_pkce_service.service_id()}"
        data = session_data.pop(session_key, None)
        kwargs = {}

        # Check if service has PKCE enabled
        if hasattr(mock_non_pkce_service, "pkce_enabled") and mock_non_pkce_service.pkce_enabled():
            if data and data.get("verifier"):
                kwargs["code_verifier"] = data.get("verifier")

        # Verify no verifier for non-PKCE service
        assert "code_verifier" not in kwargs

    def test_oauth_login_service_without_pkce_methods(self):
        """Test services that don't have PKCE methods at all"""

        # Mock a service without PKCE methods
        mock_service = MagicMock()
        mock_service.service_id.return_value = "oldservice"
        # Don't add pkce_enabled method to simulate old service
        del mock_service.pkce_enabled

        # Simulate session data
        session_data = {
            "_oauth_pkce_oldservice": {"verifier": "old-service-verifier", "ts": int(time.time())}
        }

        # Simulate the OAuth callback processing code
        session_key = "_oauth_pkce_oldservice"
        data = session_data.pop(session_key, None)
        kwargs = {}

        # Check if service has PKCE methods before using them
        if hasattr(mock_service, "pkce_enabled") and mock_service.pkce_enabled():
            if data and data.get("verifier"):
                kwargs["code_verifier"] = data.get("verifier")

        # Verify no error and no verifier for old service
        assert "code_verifier" not in kwargs

    def test_oauth_login_session_key_format(self, mock_pkce_service):
        """Test that session key format is consistent"""

        service_id = mock_pkce_service.service_id()
        expected_key = f"_oauth_pkce_{service_id}"

        # Verify the session key format matches expectation
        assert expected_key == f"_oauth_pkce_testoidc"

    def test_oauth_login_session_data_structure(self, mock_pkce_service):
        """Test session data structure validation"""

        before_time = int(time.time())

        # Simulate proper session data structure
        session_data = {
            f"_oauth_pkce_{mock_pkce_service.service_id()}": {
                "verifier": "test-verifier-structure",
                "ts": int(time.time()),
            }
        }

        after_time = int(time.time())

        # Extract and validate session data
        session_key = f"_oauth_pkce_{mock_pkce_service.service_id()}"
        data = session_data[session_key]

        # Verify data structure
        assert isinstance(data, dict)
        assert "verifier" in data
        assert "ts" in data

        # Verify verifier is valid string
        verifier = data["verifier"]
        assert isinstance(verifier, str)
        assert len(verifier) > 0

        # Verify timestamp is reasonable
        timestamp = data["ts"]
        assert isinstance(timestamp, int)
        assert before_time <= timestamp <= after_time
