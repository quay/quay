# -*- coding: utf-8 -*-
"""
Unit tests for organization mirroring registry adapters.
"""

from unittest.mock import MagicMock, patch

import pytest
import responses
from requests.exceptions import ConnectionError, SSLError, Timeout

from data.database import SourceRegistryType
from util.orgmirror import get_registry_adapter
from util.orgmirror.exceptions import (
    HarborDiscoveryException,
    QuayDiscoveryException,
    RegistryDiscoveryException,
)
from util.orgmirror.harbor_adapter import HarborAdapter
from util.orgmirror.quay_adapter import QuayAdapter


@pytest.fixture(autouse=True)
def _mock_ssrf_validation():
    """Mock SSRF validation to avoid DNS resolution in unit tests.

    SSRF validation calls socket.getaddrinfo() which fails in CI for fake
    hostnames like harbor.example.com. SSRF validation is tested separately
    in util/security/test/test_ssrf.py.
    """
    with patch("util.orgmirror.registry_adapter.validate_external_registry_url"):
        yield


class TestQuayAdapter:
    """Tests for QuayAdapter."""

    @responses.activate
    def test_list_repositories_single_page(self):
        """Test fetching repositories with a single page response."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={
                "repositories": [
                    {"name": "repo1"},
                    {"name": "repo2"},
                    {"name": "repo3"},
                ]
            },
            status=200,
        )

        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            username="user",
            password="pass",
        )

        repos = adapter.list_repositories()

        assert repos == ["repo1", "repo2", "repo3"]
        assert len(responses.calls) == 1
        assert "namespace=testorg" in responses.calls[0].request.url

    @responses.activate
    def test_list_repositories_paginated(self):
        """Test fetching repositories with multiple pages."""
        # First page
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={
                "repositories": [
                    {"name": "repo1"},
                    {"name": "repo2"},
                ],
                "next_page": "token123",
            },
            status=200,
        )

        # Second page
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={
                "repositories": [
                    {"name": "repo3"},
                ]
            },
            status=200,
        )

        adapter = QuayAdapter(
            url="https://quay.io/",  # Test trailing slash handling
            namespace="testorg",
        )

        repos = adapter.list_repositories()

        assert repos == ["repo1", "repo2", "repo3"]
        assert len(responses.calls) == 2
        assert "next_page=token123" in responses.calls[1].request.url

    @responses.activate
    def test_list_repositories_empty(self):
        """Test fetching when no repositories exist."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"repositories": []},
            status=200,
        )

        adapter = QuayAdapter(url="https://quay.io", namespace="emptyorg")

        repos = adapter.list_repositories()

        assert repos == []

    @responses.activate
    def test_test_connection_success(self):
        """Test successful connection verification."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/organization/testorg",
            json={"name": "testorg"},
            status=200,
        )

        adapter = QuayAdapter(url="https://quay.io", namespace="testorg")

        success, message = adapter.test_connection()

        assert success is True
        assert message == "Connection successful"

    @responses.activate
    def test_test_connection_auth_failed(self):
        """Test connection with authentication failure."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/organization/testorg",
            json={"error": "Unauthorized"},
            status=401,
        )

        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            username="baduser",
            password="badpass",
        )

        success, message = adapter.test_connection()

        assert success is False
        assert message == "Authentication failed"

    @responses.activate
    def test_test_connection_not_found(self):
        """Test connection when namespace doesn't exist."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/organization/nonexistent",
            json={"error": "Not found"},
            status=404,
        )

        adapter = QuayAdapter(url="https://quay.io", namespace="nonexistent")

        success, message = adapter.test_connection()

        assert success is False
        assert "not found" in message.lower()

    def test_proxy_configuration(self):
        """Test that proxy settings are correctly applied."""
        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            config={
                "proxy": {
                    "http_proxy": "http://proxy:8080",
                    "https_proxy": "https://proxy:8443",
                }
            },
        )

        proxies = adapter._build_proxies()

        assert proxies["http"] == "http://proxy:8080"
        assert proxies["https"] == "https://proxy:8443"

    def test_tls_verification_disabled(self):
        """Test that TLS verification can be disabled."""
        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            config={"verify_tls": False},
        )

        assert adapter.verify_tls is False

    @responses.activate
    def test_list_repositories_large_pagination(self):
        """Test fetching 150+ repositories across multiple pages."""
        # First page - 50 repos with next_page token
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={
                "repositories": [{"name": f"repo{i}"} for i in range(50)],
                "next_page": "token_page2",
            },
            status=200,
        )

        # Second page - 50 repos with next_page token
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={
                "repositories": [{"name": f"repo{i}"} for i in range(50, 100)],
                "next_page": "token_page3",
            },
            status=200,
        )

        # Third page - 55 repos, no next_page (final page)
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={
                "repositories": [{"name": f"repo{i}"} for i in range(100, 155)],
            },
            status=200,
        )

        adapter = QuayAdapter(url="https://quay.io", namespace="largeorg")

        repos = adapter.list_repositories()

        assert len(repos) == 155
        assert repos[0] == "repo0"
        assert repos[49] == "repo49"
        assert repos[100] == "repo100"
        assert repos[-1] == "repo154"
        assert len(responses.calls) == 3
        # Verify pagination tokens were used
        assert "next_page=token_page2" in responses.calls[1].request.url
        assert "next_page=token_page3" in responses.calls[2].request.url

    @responses.activate
    def test_list_repositories_401_raises_exception(self):
        """Test that 401 response raises QuayDiscoveryException."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"error": "Unauthorized"},
            status=401,
        )

        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            username="baduser",
            password="badpass",
        )

        with pytest.raises(QuayDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "Authentication failed" in str(exc_info.value)

    @responses.activate
    def test_list_repositories_403_raises_exception(self):
        """Test that 403 response raises QuayDiscoveryException."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"error": "Forbidden"},
            status=403,
        )

        adapter = QuayAdapter(url="https://quay.io", namespace="privateorg")

        with pytest.raises(QuayDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "Access forbidden" in str(exc_info.value)
        assert "privateorg" in str(exc_info.value)

    @responses.activate
    def test_list_repositories_404_raises_exception(self):
        """Test that 404 response raises QuayDiscoveryException."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"error": "Not found"},
            status=404,
        )

        adapter = QuayAdapter(url="https://quay.io", namespace="nonexistent")

        with pytest.raises(QuayDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "not found" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    @responses.activate
    def test_list_repositories_500_raises_exception(self):
        """Test that 500 response raises QuayDiscoveryException after retries."""
        # Add multiple 500 responses to exhaust retries
        for _ in range(4):  # max_retries (3) + 1
            responses.add(
                responses.GET,
                "https://quay.io/api/v1/repository",
                json={"error": "Internal Server Error"},
                status=500,
            )

        adapter = QuayAdapter(url="https://quay.io", namespace="testorg", max_retries=3)

        with pytest.raises(QuayDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "500" in str(exc_info.value)

    def test_list_repositories_connection_error_raises_exception(self):
        """Test that connection error raises QuayDiscoveryException."""
        adapter = QuayAdapter(url="https://quay.io", namespace="testorg")

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            with pytest.raises(QuayDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert "Failed to connect" in str(exc_info.value)

    def test_list_repositories_timeout_raises_exception(self):
        """Test that timeout raises QuayDiscoveryException."""
        adapter = QuayAdapter(url="https://quay.io", namespace="testorg")

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = Timeout("Connection timed out")

            with pytest.raises(QuayDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert "timed out" in str(exc_info.value)

    def test_list_repositories_ssl_error_raises_exception(self):
        """Test that SSL error raises QuayDiscoveryException."""
        adapter = QuayAdapter(url="https://quay.io", namespace="testorg")

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = SSLError("SSL certificate verify failed")

            with pytest.raises(QuayDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert "SSL" in str(exc_info.value)

    def test_exception_includes_cause(self):
        """Test that QuayDiscoveryException includes the original cause."""
        adapter = QuayAdapter(url="https://quay.io", namespace="testorg")
        original_error = ConnectionError("Original error message")

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = original_error

            with pytest.raises(QuayDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert exc_info.value.cause is original_error

    def test_exception_hierarchy(self):
        """Test that QuayDiscoveryException inherits from RegistryDiscoveryException."""
        assert issubclass(QuayDiscoveryException, RegistryDiscoveryException)

    def test_bearer_token_authentication_via_token_param(self):
        """Test that token parameter sets Bearer authentication header."""
        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            token="my-api-token",
        )

        assert "Authorization" in adapter.session.headers
        assert adapter.session.headers["Authorization"] == "Bearer my-api-token"
        # Basic auth should NOT be set
        assert adapter.session.auth is None

    def test_bearer_token_authentication_via_password(self):
        """Test that password field is used as Bearer token when token param is not set."""
        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            username="ignored-user",
            password="my-api-token-from-password",
        )

        assert "Authorization" in adapter.session.headers
        assert adapter.session.headers["Authorization"] == "Bearer my-api-token-from-password"
        # Basic auth should NOT be set (password is used as Bearer token, not basic auth)
        assert adapter.session.auth is None

    def test_token_param_takes_precedence_over_password(self):
        """Test that explicit token parameter takes precedence over password."""
        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            username="user",
            password="password-token",
            token="explicit-token",
        )

        assert adapter.session.headers["Authorization"] == "Bearer explicit-token"

    def test_no_auth_when_no_credentials(self):
        """Test that no auth is set when no credentials are provided."""
        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
        )

        assert "Authorization" not in adapter.session.headers
        assert adapter.session.auth is None

    @responses.activate
    def test_bearer_token_sent_in_request(self):
        """Test that Bearer token is actually sent in HTTP requests."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"repositories": [{"name": "repo1"}]},
            status=200,
        )

        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            token="test-bearer-token",
        )

        adapter.list_repositories()

        # Verify the Authorization header was sent
        assert len(responses.calls) == 1
        auth_header = responses.calls[0].request.headers.get("Authorization")
        assert auth_header == "Bearer test-bearer-token"


class TestHarborAdapter:
    """Tests for HarborAdapter."""

    @responses.activate
    def test_list_repositories_single_page(self):
        """Test fetching repositories with a single page response."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json=[
                {"name": "myproject/repo1"},
                {"name": "myproject/repo2"},
            ],
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
            username="admin",
            password="secret",
        )

        repos = adapter.list_repositories()

        assert repos == ["repo1", "repo2"]

    @responses.activate
    def test_list_repositories_paginated(self):
        """Test fetching repositories with multiple pages."""
        # First page - full page
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json=[{"name": f"myproject/repo{i}"} for i in range(100)],
            status=200,
        )

        # Second page - partial page (indicates end)
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json=[{"name": "myproject/repo100"}],
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com/",
            namespace="myproject",
        )

        repos = adapter.list_repositories()

        assert len(repos) == 101
        assert repos[0] == "repo0"
        assert repos[-1] == "repo100"

    @responses.activate
    def test_list_repositories_strips_project_prefix(self):
        """Test that project prefix is correctly stripped from repo names."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/my-project/repositories",
            json=[
                {"name": "my-project/alpine"},
                {"name": "my-project/nginx"},
                {"name": "standalone"},  # No prefix (edge case)
            ],
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="my-project",
        )

        repos = adapter.list_repositories()

        assert repos == ["alpine", "nginx", "standalone"]

    @responses.activate
    def test_list_repositories_empty(self):
        """Test fetching when no repositories exist."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/emptyproject/repositories",
            json=[],
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="emptyproject",
        )

        repos = adapter.list_repositories()

        assert repos == []

    @responses.activate
    def test_test_connection_success(self):
        """Test successful connection verification."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject",
            json={"name": "myproject"},
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
        )

        success, message = adapter.test_connection()

        assert success is True
        assert message == "Connection successful"

    @responses.activate
    def test_test_connection_forbidden(self):
        """Test connection with insufficient permissions."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject",
            json={"errors": [{"code": "FORBIDDEN"}]},
            status=403,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
            username="user",
            password="pass",
        )

        success, message = adapter.test_connection()

        assert success is False
        assert "forbidden" in message.lower()

    @responses.activate
    def test_list_repositories_large_pagination(self):
        """Test fetching 250+ repositories across multiple pages."""
        # First page - 100 repos
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/largeproject/repositories",
            json=[{"name": f"largeproject/repo{i}"} for i in range(100)],
            status=200,
        )

        # Second page - 100 repos
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/largeproject/repositories",
            json=[{"name": f"largeproject/repo{i}"} for i in range(100, 200)],
            status=200,
        )

        # Third page - 55 repos (final page, less than page_size)
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/largeproject/repositories",
            json=[{"name": f"largeproject/repo{i}"} for i in range(200, 255)],
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="largeproject",
        )

        repos = adapter.list_repositories()

        assert len(repos) == 255
        assert repos[0] == "repo0"
        assert repos[99] == "repo99"
        assert repos[200] == "repo200"
        assert repos[-1] == "repo254"
        assert len(responses.calls) == 3
        # Verify page numbers were used
        assert "page=1" in responses.calls[0].request.url
        assert "page=2" in responses.calls[1].request.url
        assert "page=3" in responses.calls[2].request.url

    @responses.activate
    def test_list_repositories_401_raises_exception(self):
        """Test that 401 response raises HarborDiscoveryException."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json={"errors": [{"code": "UNAUTHORIZED"}]},
            status=401,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
            username="baduser",
            password="badpass",
        )

        with pytest.raises(HarborDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "Authentication failed" in str(exc_info.value)

    @responses.activate
    def test_list_repositories_403_raises_exception(self):
        """Test that 403 response raises HarborDiscoveryException."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/privateproject/repositories",
            json={"errors": [{"code": "FORBIDDEN"}]},
            status=403,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="privateproject",
        )

        with pytest.raises(HarborDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "Access forbidden" in str(exc_info.value)
        assert "privateproject" in str(exc_info.value)

    @responses.activate
    def test_list_repositories_404_raises_exception(self):
        """Test that 404 response raises HarborDiscoveryException."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/nonexistent/repositories",
            json={"errors": [{"code": "NOT_FOUND"}]},
            status=404,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="nonexistent",
        )

        with pytest.raises(HarborDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "not found" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    @responses.activate
    def test_list_repositories_500_raises_exception(self):
        """Test that 500 response raises HarborDiscoveryException after retries."""
        for _ in range(4):  # max_retries (3) + 1
            responses.add(
                responses.GET,
                "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
                json={"error": "Internal Server Error"},
                status=500,
            )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
            max_retries=3,
        )

        with pytest.raises(HarborDiscoveryException) as exc_info:
            adapter.list_repositories()

        assert "500" in str(exc_info.value)

    def test_list_repositories_connection_error_raises_exception(self):
        """Test that connection error raises HarborDiscoveryException."""
        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
        )

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            with pytest.raises(HarborDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert "Failed to connect" in str(exc_info.value)

    def test_list_repositories_timeout_raises_exception(self):
        """Test that timeout raises HarborDiscoveryException."""
        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
        )

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = Timeout("Connection timed out")

            with pytest.raises(HarborDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert "timed out" in str(exc_info.value)

    def test_list_repositories_ssl_error_raises_exception(self):
        """Test that SSL error raises HarborDiscoveryException."""
        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
        )

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = SSLError("SSL certificate verify failed")

            with pytest.raises(HarborDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert "SSL" in str(exc_info.value)

    def test_exception_includes_cause(self):
        """Test that HarborDiscoveryException includes the original cause."""
        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
        )
        original_error = ConnectionError("Original error message")

        with patch.object(adapter.session, "get") as mock_get:
            mock_get.side_effect = original_error

            with pytest.raises(HarborDiscoveryException) as exc_info:
                adapter.list_repositories()

            assert exc_info.value.cause is original_error

    def test_exception_hierarchy(self):
        """Test that HarborDiscoveryException inherits from RegistryDiscoveryException."""
        assert issubclass(HarborDiscoveryException, RegistryDiscoveryException)


class TestGetRegistryAdapter:
    """Tests for the get_registry_adapter factory function."""

    def test_get_quay_adapter(self):
        """Test creating a Quay adapter."""
        adapter = get_registry_adapter(
            registry_type=SourceRegistryType.QUAY,
            url="https://quay.io",
            namespace="testorg",
            username="user",
            password="pass",
        )

        assert isinstance(adapter, QuayAdapter)
        assert adapter.base_url == "https://quay.io"
        assert adapter.namespace == "testorg"
        # Quay uses Bearer token auth (password is used as token)
        assert adapter.session.headers["Authorization"] == "Bearer pass"

    def test_get_quay_adapter_with_token(self):
        """Test creating a Quay adapter with explicit token parameter."""
        adapter = get_registry_adapter(
            registry_type=SourceRegistryType.QUAY,
            url="https://quay.io",
            namespace="testorg",
            token="my-api-token",
        )

        assert isinstance(adapter, QuayAdapter)
        assert adapter.session.headers["Authorization"] == "Bearer my-api-token"

    def test_get_harbor_adapter(self):
        """Test creating a Harbor adapter."""
        adapter = get_registry_adapter(
            registry_type=SourceRegistryType.HARBOR,
            url="https://harbor.example.com",
            namespace="myproject",
            config={"verify_tls": False},
        )

        assert isinstance(adapter, HarborAdapter)
        assert adapter.base_url == "https://harbor.example.com"
        assert adapter.namespace == "myproject"
        assert adapter.verify_tls is False

    def test_unsupported_registry_type(self):
        """Test that unsupported registry types raise ValueError."""
        # Create a mock unsupported type by using an invalid value
        with pytest.raises(ValueError) as exc_info:
            get_registry_adapter(
                registry_type=999,  # Invalid type
                url="https://example.com",
                namespace="test",
            )

        assert "Unsupported registry type" in str(exc_info.value)


class TestRetryBehavior:
    """Tests for retry behavior with transient failures."""

    @responses.activate
    def test_quay_retry_on_429_succeeds(self):
        """Test that QuayAdapter retries on 429 and eventually succeeds."""
        # First request: 429 rate limited
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"error": "Rate limited"},
            status=429,
        )

        # Second request: 429 rate limited
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"error": "Rate limited"},
            status=429,
        )

        # Third request: success
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"repositories": [{"name": "repo1"}]},
            status=200,
        )

        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            max_retries=3,
        )

        repos = adapter.list_repositories()

        assert repos == ["repo1"]
        # Should have made 3 requests (2 retries + 1 success)
        assert len(responses.calls) == 3

    @responses.activate
    def test_quay_retry_on_503_succeeds(self):
        """Test that QuayAdapter retries on 503 Service Unavailable."""
        # First request: 503
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"error": "Service Unavailable"},
            status=503,
        )

        # Second request: success
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"repositories": [{"name": "repo1"}, {"name": "repo2"}]},
            status=200,
        )

        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            max_retries=3,
        )

        repos = adapter.list_repositories()

        assert repos == ["repo1", "repo2"]
        assert len(responses.calls) == 2

    @responses.activate
    def test_harbor_retry_on_502_succeeds(self):
        """Test that HarborAdapter retries on 502 Bad Gateway."""
        # First request: 502
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json={"error": "Bad Gateway"},
            status=502,
        )

        # Second request: success
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json=[{"name": "myproject/repo1"}],
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
            max_retries=3,
        )

        repos = adapter.list_repositories()

        assert repos == ["repo1"]
        assert len(responses.calls) == 2

    @responses.activate
    def test_harbor_retry_on_500_succeeds(self):
        """Test that HarborAdapter retries on 500 Internal Server Error."""
        # First request: 500
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json={"error": "Internal Server Error"},
            status=500,
        )

        # Second request: 500
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json={"error": "Internal Server Error"},
            status=500,
        )

        # Third request: success
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json=[{"name": "myproject/repo1"}, {"name": "myproject/repo2"}],
            status=200,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
            max_retries=3,
        )

        repos = adapter.list_repositories()

        assert repos == ["repo1", "repo2"]
        assert len(responses.calls) == 3

    @responses.activate
    def test_quay_no_retry_on_400(self):
        """Test that QuayAdapter does not retry on 400 Bad Request."""
        responses.add(
            responses.GET,
            "https://quay.io/api/v1/repository",
            json={"error": "Bad Request"},
            status=400,
        )

        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            max_retries=3,
        )

        with pytest.raises(QuayDiscoveryException):
            adapter.list_repositories()

        # Should only make 1 request (no retry for 400)
        assert len(responses.calls) == 1

    @responses.activate
    def test_harbor_no_retry_on_401(self):
        """Test that HarborAdapter does not retry on 401 Unauthorized."""
        responses.add(
            responses.GET,
            "https://harbor.example.com/api/v2.0/projects/myproject/repositories",
            json={"error": "Unauthorized"},
            status=401,
        )

        adapter = HarborAdapter(
            url="https://harbor.example.com",
            namespace="myproject",
            max_retries=3,
        )

        with pytest.raises(HarborDiscoveryException):
            adapter.list_repositories()

        # Should only make 1 request (no retry for 401)
        assert len(responses.calls) == 1

    def test_max_retries_parameter(self):
        """Test that max_retries parameter is properly set."""
        adapter_default = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
        )
        assert adapter_default.max_retries == 3  # Default

        adapter_custom = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
            max_retries=5,
        )
        assert adapter_custom.max_retries == 5

    def test_session_has_retry_adapter(self):
        """Test that session is configured with retry adapter."""
        adapter = QuayAdapter(
            url="https://quay.io",
            namespace="testorg",
        )

        # Check that adapters are mounted for both http and https
        assert "https://" in adapter.session.adapters
        assert "http://" in adapter.session.adapters

        # The adapter should be an HTTPAdapter
        from requests.adapters import HTTPAdapter

        assert isinstance(adapter.session.adapters["https://"], HTTPAdapter)
        assert isinstance(adapter.session.adapters["http://"], HTTPAdapter)
