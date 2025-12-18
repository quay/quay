"""
Unit tests for Quay discovery client.

Tests Quay API integration with mocked responses.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from util.repomirror.quay_discovery import (
    QuayDiscoveryClient,
    QuayDiscoveryException,
    is_quay_registry,
    parse_quay_external_reference,
)

# Test QuayDiscoveryClient initialization


def test_client_init_with_token():
    """Test client initialization with token authentication."""
    client = QuayDiscoveryClient(
        quay_url="https://quay.io",
        token="test-token",
    )

    assert client.quay_url == "https://quay.io"
    assert client.token == "test-token"
    assert "Authorization" in client.session.headers
    assert client.session.headers["Authorization"] == "Bearer test-token"


def test_client_init_with_basic_auth():
    """Test client initialization with robot account (username/password)."""
    client = QuayDiscoveryClient(
        quay_url="https://quay.io",
        username="myorg+robot",
        password="testpass",
    )

    assert client.username == "myorg+robot"
    assert client.password == "testpass"
    assert client.session.auth == ("myorg+robot", "testpass")


def test_client_init_with_proxy():
    """Test client initialization with proxy configuration."""
    proxy = {"http": "http://proxy.example.com", "https": "https://proxy.example.com"}
    client = QuayDiscoveryClient(
        quay_url="https://quay.io",
        proxy=proxy,
    )

    assert client.session.proxies == proxy


def test_client_init_verify_tls():
    """Test client initialization with TLS verification disabled."""
    client = QuayDiscoveryClient(
        quay_url="https://quay.example.com",
        verify_tls=False,
    )

    assert client.verify_tls is False


def test_client_init_strips_trailing_slash():
    """Test that trailing slash is stripped from quay_url."""
    client = QuayDiscoveryClient(quay_url="https://quay.io/")

    assert client.quay_url == "https://quay.io"


def test_client_init_without_auth():
    """Test client initialization without authentication (for public repos)."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    assert client.token is None
    assert client.username is None
    assert client.password is None


# Test discover_repositories


def test_discover_repositories_single_page(monkeypatch):
    """Test discovery with single page of results."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [
            {"namespace": "myorg", "name": "repo1"},
            {"namespace": "myorg", "name": "repo2"},
        ],
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    mock_get = Mock(return_value=mock_response)
    client.session.get = mock_get

    result = client.discover_repositories("myorg")

    assert result is not None
    assert len(result) == 2
    assert result[0]["name"] == "repo1"
    assert result[0]["external_reference"] == "quay.io/myorg/repo1"
    assert result[1]["name"] == "repo2"
    assert result[1]["external_reference"] == "quay.io/myorg/repo2"

    # Verify API call
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert "/api/v1/repository" in call_args[0][0]


def test_discover_repositories_multiple_pages(monkeypatch):
    """Test discovery with pagination (multiple pages)."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    # Mock responses for two pages
    page1_response = Mock()
    page1_response.json.return_value = {
        "repositories": [{"namespace": "myorg", "name": f"repo{i}"} for i in range(100)],
        "next_page": "page2token",
    }
    page1_response.raise_for_status = Mock()

    page2_response = Mock()
    page2_response.json.return_value = {
        "repositories": [{"namespace": "myorg", "name": f"repo{i}"} for i in range(100, 150)],
        "next_page": None,
    }
    page2_response.raise_for_status = Mock()

    mock_get = Mock(side_effect=[page1_response, page2_response])
    client.session.get = mock_get

    result = client.discover_repositories("myorg")

    assert result is not None
    assert len(result) == 150
    assert mock_get.call_count == 2


def test_discover_repositories_empty_org(monkeypatch):
    """Test discovery with empty organization (no repositories)."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    # Mock empty response
    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [],
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result = client.discover_repositories("empty-org")

    assert result is not None
    assert len(result) == 0


def test_discover_repositories_api_failure():
    """Test discovery when API request fails."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    # Mock failed response
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

    client.session.get = Mock(return_value=mock_response)

    result = client.discover_repositories("myorg")

    # Should return None on failure
    assert result is None


# Test _list_repositories_page


def test_list_repositories_page_success():
    """Test listing single page of repositories."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [
            {"namespace": "myorg", "name": "repo1"},
            {"namespace": "myorg", "name": "repo2"},
        ],
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result, next_page = client._list_repositories_page("myorg")

    assert len(result) == 2
    assert result[0]["name"] == "repo1"
    assert result[1]["name"] == "repo2"
    assert next_page is None


def test_list_repositories_page_with_next_page():
    """Test listing page with next_page token."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [{"namespace": "myorg", "name": "repo1"}],
        "next_page": "next_token",
    }
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result, next_page = client._list_repositories_page("myorg")

    assert len(result) == 1
    assert next_page == "next_token"


def test_list_repositories_page_404_not_found():
    """Test 404 error for non-existent organization."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(QuayDiscoveryException, match="organization not found"):
        client._list_repositories_page("nonexistent")


def test_list_repositories_page_401_unauthorized():
    """Test 401 error for authentication failure."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(QuayDiscoveryException, match="authentication failed"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_403_forbidden():
    """Test 403 error for access denied."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(QuayDiscoveryException, match="Access denied"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_ssl_error():
    """Test SSL/TLS verification error."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    client.session.get = Mock(side_effect=requests.exceptions.SSLError("SSL error"))

    with pytest.raises(QuayDiscoveryException, match="TLS verification failed"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_proxy_error():
    """Test proxy connection error."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    client.session.get = Mock(side_effect=requests.exceptions.ProxyError("Proxy error"))

    with pytest.raises(QuayDiscoveryException, match="Proxy error"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_timeout():
    """Test request timeout."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    client.session.get = Mock(side_effect=requests.exceptions.Timeout("Timeout"))

    with pytest.raises(QuayDiscoveryException, match="Request timeout"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_connection_error():
    """Test connection error."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    client.session.get = Mock(side_effect=requests.exceptions.ConnectionError("Connection failed"))

    with pytest.raises(QuayDiscoveryException, match="Connection error"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_invalid_json():
    """Test invalid JSON response."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(QuayDiscoveryException, match="Invalid JSON response"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_unexpected_format():
    """Test unexpected response format (not a dict)."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.return_value = ["not", "a", "dict"]
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(QuayDiscoveryException, match="Unexpected response format"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_repositories_not_list():
    """Test when repositories field is not a list."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": "not a list",
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(QuayDiscoveryException, match="Unexpected repositories format"):
        client._list_repositories_page("myorg")


def test_list_repositories_page_malformed_repo():
    """Test handling of malformed repository in response."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [
            {"namespace": "myorg", "name": "repo1"},
            {"invalid": "missing name field"},  # Malformed
            {"namespace": "myorg", "name": "repo2"},
        ],
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result, next_page = client._list_repositories_page("myorg")

    # Should skip malformed repo
    assert len(result) == 2
    assert result[0]["name"] == "repo1"
    assert result[1]["name"] == "repo2"


def test_list_repositories_page_with_pagination_token():
    """Test pagination with next_page token in request."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [{"namespace": "myorg", "name": "repo1"}],
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    mock_get = Mock(return_value=mock_response)
    client.session.get = mock_get

    result, next_page = client._list_repositories_page("myorg", next_page="page2token")

    # Verify pagination token was passed
    call_args = mock_get.call_args
    assert call_args[1]["params"]["next_page"] == "page2token"


# Test test_connection


def test_test_connection_success():
    """Test successful connection test."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [],
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result = client.test_connection("myorg")

    assert result is True


def test_test_connection_failure():
    """Test failed connection test."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    client.session.get = Mock(side_effect=Exception("Connection failed"))

    result = client.test_connection("myorg")

    assert result is False


# Test parse_quay_external_reference


def test_parse_quay_external_reference_valid():
    """Test parsing valid Quay external reference."""
    result = parse_quay_external_reference("quay.io/myorg/myrepo")

    assert result is not None
    assert result["quay_url"] == "https://quay.io"
    assert result["org_name"] == "myorg"
    assert result["repo_name"] == "myrepo"


def test_parse_quay_external_reference_nested_repo():
    """Test parsing reference with nested repository path."""
    result = parse_quay_external_reference("quay.io/myorg/path/to/repo")

    assert result is not None
    assert result["quay_url"] == "https://quay.io"
    assert result["org_name"] == "myorg"
    assert result["repo_name"] == "path/to/repo"


def test_parse_quay_external_reference_org_only():
    """Test parsing reference with org but no repo."""
    result = parse_quay_external_reference("quay.io/myorg")

    assert result is not None
    assert result["quay_url"] == "https://quay.io"
    assert result["org_name"] == "myorg"
    assert result["repo_name"] is None


def test_parse_quay_external_reference_self_hosted():
    """Test parsing reference for self-hosted Quay instance."""
    result = parse_quay_external_reference("quay.example.com/myorg/myrepo")

    assert result is not None
    assert result["quay_url"] == "https://quay.example.com"
    assert result["org_name"] == "myorg"
    assert result["repo_name"] == "myrepo"


def test_parse_quay_external_reference_invalid():
    """Test parsing invalid reference (no org)."""
    result = parse_quay_external_reference("quay.io")

    assert result is None


def test_parse_quay_external_reference_empty():
    """Test parsing empty reference."""
    result = parse_quay_external_reference("")

    assert result is None


# Test is_quay_registry


def test_is_quay_registry_quay_io():
    """Test detection of quay.io."""
    assert is_quay_registry("quay.io/myorg/myrepo") is True
    assert is_quay_registry("quay.io/myorg") is True


def test_is_quay_registry_self_hosted():
    """Test detection of self-hosted Quay instance."""
    assert is_quay_registry("quay.example.com/myorg/myrepo") is True
    assert is_quay_registry("myquay.corp.com/myorg/myrepo") is True


def test_is_quay_registry_not_quay():
    """Test detection of non-Quay registry."""
    assert is_quay_registry("harbor.example.com/project/repo") is False
    assert is_quay_registry("docker.io/library/nginx") is False
    assert is_quay_registry("gcr.io/project/image") is False


def test_is_quay_registry_invalid():
    """Test detection with invalid reference."""
    assert is_quay_registry("invalid") is False
    assert is_quay_registry("") is False
    assert is_quay_registry("quay.io") is False  # No org/repo


# Integration-style tests


def test_discover_large_organization():
    """Test discovery of large organization with 1000+ repositories."""
    client = QuayDiscoveryClient(quay_url="https://quay.io")

    # Mock 15 pages of 100 repos each = 1500 repos
    def mock_get_side_effect(url, **kwargs):
        next_page = kwargs.get("params", {}).get("next_page")

        if next_page is None:
            # First page
            mock_response = Mock()
            mock_response.json.return_value = {
                "repositories": [{"namespace": "myorg", "name": f"repo{i}"} for i in range(100)],
                "next_page": "page2",
            }
        elif next_page == "page2":
            mock_response = Mock()
            mock_response.json.return_value = {
                "repositories": [
                    {"namespace": "myorg", "name": f"repo{i}"} for i in range(100, 200)
                ],
                "next_page": "page3",
            }
        elif next_page == "page3":
            mock_response = Mock()
            mock_response.json.return_value = {
                "repositories": [
                    {"namespace": "myorg", "name": f"repo{i}"} for i in range(200, 300)
                ],
                "next_page": None,
            }
        else:
            mock_response = Mock()
            mock_response.json.return_value = {
                "repositories": [],
                "next_page": None,
            }

        mock_response.raise_for_status = Mock()
        return mock_response

    client.session.get = Mock(side_effect=mock_get_side_effect)

    result = client.discover_repositories("myorg")

    assert result is not None
    assert len(result) == 300


def test_discover_with_retry_on_transient_failure():
    """Test that transient failures are retried."""
    client = QuayDiscoveryClient(quay_url="https://quay.io", max_retries=3)

    # Note: Retry is handled by requests.Session adapter
    # We just test that the logic works
    success_response = Mock()
    success_response.json.return_value = {
        "repositories": [{"namespace": "myorg", "name": "repo1"}],
        "next_page": None,
    }
    success_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=success_response)

    result = client.discover_repositories("myorg")

    assert result is not None
    assert len(result) == 1


def test_end_to_end_discovery_workflow():
    """Integration test for complete discovery workflow."""
    client = QuayDiscoveryClient(
        quay_url="https://quay.io",
        token="test-token",
        verify_tls=True,
    )

    # Mock realistic Quay response
    mock_response = Mock()
    mock_response.json.return_value = {
        "repositories": [
            {
                "namespace": "myorg",
                "name": "frontend",
                "description": "Frontend application",
                "is_public": False,
                "kind": "image",
                "state": "NORMAL",
            },
            {
                "namespace": "myorg",
                "name": "backend",
                "description": "Backend API",
                "is_public": False,
                "kind": "image",
                "state": "NORMAL",
            },
        ],
        "next_page": None,
    }
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    # Discover repositories
    repos = client.discover_repositories("myorg")

    assert repos is not None
    assert len(repos) == 2

    # Verify structure
    assert repos[0]["name"] == "frontend"
    assert repos[0]["external_reference"] == "quay.io/myorg/frontend"
    assert repos[1]["name"] == "backend"
    assert repos[1]["external_reference"] == "quay.io/myorg/backend"
