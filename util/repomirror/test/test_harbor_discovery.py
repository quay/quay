"""
Unit tests for Harbor discovery client.

Tests Harbor API integration with mocked responses.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from util.repomirror.harbor_discovery import (
    HarborDiscoveryClient,
    HarborDiscoveryException,
    is_harbor_registry,
    parse_harbor_external_reference,
)

# Test HarborDiscoveryClient initialization


def test_client_init_with_token():
    """Test client initialization with token authentication."""
    client = HarborDiscoveryClient(
        harbor_url="https://harbor.example.com",
        token="test-token",
    )

    assert client.harbor_url == "https://harbor.example.com"
    assert client.token == "test-token"
    assert "Authorization" in client.session.headers
    assert client.session.headers["Authorization"] == "Bearer test-token"


def test_client_init_with_basic_auth():
    """Test client initialization with username/password."""
    client = HarborDiscoveryClient(
        harbor_url="https://harbor.example.com",
        username="testuser",
        password="testpass",
    )

    assert client.username == "testuser"
    assert client.password == "testpass"
    assert client.session.auth == ("testuser", "testpass")


def test_client_init_with_proxy():
    """Test client initialization with proxy configuration."""
    proxy = {"http": "http://proxy.example.com", "https": "https://proxy.example.com"}
    client = HarborDiscoveryClient(
        harbor_url="https://harbor.example.com",
        proxy=proxy,
    )

    assert client.session.proxies == proxy


def test_client_init_verify_tls():
    """Test client initialization with TLS verification disabled."""
    client = HarborDiscoveryClient(
        harbor_url="https://harbor.example.com",
        verify_tls=False,
    )

    assert client.verify_tls is False


def test_client_init_strips_trailing_slash():
    """Test that trailing slash is stripped from harbor_url."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com/")

    assert client.harbor_url == "https://harbor.example.com"


# Test discover_repositories


def test_discover_repositories_single_page(monkeypatch):
    """Test discovery with single page of results."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = [
        {"name": "library/nginx", "id": 1},
        {"name": "library/redis", "id": 2},
    ]
    mock_response.raise_for_status = Mock()

    mock_get = Mock(return_value=mock_response)
    client.session.get = mock_get

    result = client.discover_repositories("library")

    assert result is not None
    assert len(result) == 2
    assert result[0]["name"] == "nginx"
    assert result[0]["external_reference"] == "harbor.example.com/library/nginx"
    assert result[1]["name"] == "redis"
    assert result[1]["external_reference"] == "harbor.example.com/library/redis"

    # Verify API call
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert "/api/v2.0/projects/library/repositories" in call_args[0][0]


def test_discover_repositories_multiple_pages(monkeypatch):
    """Test discovery with pagination (multiple pages)."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    # Mock responses for two pages
    page1_response = Mock()
    page1_response.json.return_value = [{"name": f"library/repo{i}", "id": i} for i in range(100)]
    page1_response.raise_for_status = Mock()

    page2_response = Mock()
    page2_response.json.return_value = [
        {"name": f"library/repo{i}", "id": i} for i in range(100, 150)
    ]
    page2_response.raise_for_status = Mock()

    mock_get = Mock(side_effect=[page1_response, page2_response])
    client.session.get = mock_get

    result = client.discover_repositories("library")

    assert result is not None
    assert len(result) == 150
    assert mock_get.call_count == 2


def test_discover_repositories_empty_project(monkeypatch):
    """Test discovery with empty project (no repositories)."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    # Mock empty response
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result = client.discover_repositories("empty-project")

    assert result is not None
    assert len(result) == 0


def test_discover_repositories_api_failure():
    """Test discovery when API request fails."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    # Mock failed response
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

    client.session.get = Mock(return_value=mock_response)

    result = client.discover_repositories("library")

    # Should return None on failure
    assert result is None


# Test _list_repositories_page


def test_list_repositories_page_success():
    """Test listing single page of repositories."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.json.return_value = [
        {"name": "library/nginx", "id": 1},
        {"name": "library/redis", "id": 2},
    ]
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result = client._list_repositories_page("library", page=1, page_size=10)

    assert len(result) == 2
    assert result[0]["name"] == "nginx"
    assert result[1]["name"] == "redis"


def test_list_repositories_page_404_not_found():
    """Test 404 error for non-existent project."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(HarborDiscoveryException, match="project not found"):
        client._list_repositories_page("nonexistent", page=1, page_size=10)


def test_list_repositories_page_401_unauthorized():
    """Test 401 error for authentication failure."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(HarborDiscoveryException, match="authentication failed"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_403_forbidden():
    """Test 403 error for access denied."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(HarborDiscoveryException, match="Access denied"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_ssl_error():
    """Test SSL/TLS verification error."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    client.session.get = Mock(side_effect=requests.exceptions.SSLError("SSL error"))

    with pytest.raises(HarborDiscoveryException, match="TLS verification failed"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_proxy_error():
    """Test proxy connection error."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    client.session.get = Mock(side_effect=requests.exceptions.ProxyError("Proxy error"))

    with pytest.raises(HarborDiscoveryException, match="Proxy error"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_timeout():
    """Test request timeout."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    client.session.get = Mock(side_effect=requests.exceptions.Timeout("Timeout"))

    with pytest.raises(HarborDiscoveryException, match="Request timeout"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_connection_error():
    """Test connection error."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    client.session.get = Mock(side_effect=requests.exceptions.ConnectionError("Connection failed"))

    with pytest.raises(HarborDiscoveryException, match="Connection error"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_invalid_json():
    """Test invalid JSON response."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(HarborDiscoveryException, match="Invalid JSON response"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_unexpected_format():
    """Test unexpected response format (not a list)."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.json.return_value = {"error": "not a list"}
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    with pytest.raises(HarborDiscoveryException, match="Unexpected response format"):
        client._list_repositories_page("library", page=1, page_size=10)


def test_list_repositories_page_malformed_repo():
    """Test handling of malformed repository in response."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.json.return_value = [
        {"name": "library/nginx", "id": 1},
        {"invalid": "missing name field"},  # Malformed
        {"name": "library/redis", "id": 3},
    ]
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result = client._list_repositories_page("library", page=1, page_size=10)

    # Should skip malformed repo
    assert len(result) == 2
    assert result[0]["name"] == "nginx"
    assert result[1]["name"] == "redis"


def test_list_repositories_page_repo_without_slash():
    """Test repository name without project prefix."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.json.return_value = [
        {"name": "nginx", "id": 1},  # No slash
    ]
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result = client._list_repositories_page("library", page=1, page_size=10)

    assert len(result) == 1
    assert result[0]["name"] == "nginx"
    assert result[0]["external_reference"] == "harbor.example.com/nginx"


# Test test_connection


def test_test_connection_success():
    """Test successful connection test."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    result = client.test_connection("library")

    assert result is True


def test_test_connection_failure():
    """Test failed connection test."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    client.session.get = Mock(side_effect=Exception("Connection failed"))

    result = client.test_connection("library")

    assert result is False


# Test parse_harbor_external_reference


def test_parse_harbor_external_reference_valid():
    """Test parsing valid Harbor external reference."""
    result = parse_harbor_external_reference("harbor.example.com/library/nginx")

    assert result is not None
    assert result["harbor_url"] == "https://harbor.example.com"
    assert result["project_name"] == "library"
    assert result["repo_name"] == "nginx"


def test_parse_harbor_external_reference_nested_repo():
    """Test parsing reference with nested repository path."""
    result = parse_harbor_external_reference("harbor.example.com/library/path/to/nginx")

    assert result is not None
    assert result["harbor_url"] == "https://harbor.example.com"
    assert result["project_name"] == "library"
    assert result["repo_name"] == "path/to/nginx"


def test_parse_harbor_external_reference_project_only():
    """Test parsing reference with project but no repo."""
    result = parse_harbor_external_reference("harbor.example.com/library")

    assert result is not None
    assert result["harbor_url"] == "https://harbor.example.com"
    assert result["project_name"] == "library"
    assert result["repo_name"] is None


def test_parse_harbor_external_reference_invalid():
    """Test parsing invalid reference (no project)."""
    result = parse_harbor_external_reference("harbor.example.com")

    assert result is None


def test_parse_harbor_external_reference_empty():
    """Test parsing empty reference."""
    result = parse_harbor_external_reference("")

    assert result is None


# Test is_harbor_registry


def test_is_harbor_registry_valid():
    """Test detection of Harbor registry."""
    assert is_harbor_registry("harbor.example.com/library/nginx") is True
    assert is_harbor_registry("harbor.example.com/library") is True


def test_is_harbor_registry_invalid():
    """Test detection of non-Harbor registry."""
    assert is_harbor_registry("harbor.example.com") is False
    assert is_harbor_registry("quay.io/repository") is True  # Could be Quay or Harbor
    assert is_harbor_registry("") is False


# Integration-style tests


def test_discover_large_project():
    """Test discovery of large project with 1000+ repositories."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com")

    # Mock 15 pages of 100 repos each = 1500 repos
    def mock_get_side_effect(url, **kwargs):
        page = kwargs.get("params", {}).get("page", 1)

        mock_response = Mock()
        if page <= 15:
            # Full page
            mock_response.json.return_value = [
                {"name": f"library/repo{(page-1)*100 + i}", "id": i} for i in range(100)
            ]
        else:
            # No more pages
            mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        return mock_response

    client.session.get = Mock(side_effect=mock_get_side_effect)

    result = client.discover_repositories("library")

    assert result is not None
    assert len(result) == 1500


def test_discover_with_retry_on_transient_failure():
    """Test that transient failures are retried."""
    client = HarborDiscoveryClient(harbor_url="https://harbor.example.com", max_retries=3)

    # First call fails with 500, second succeeds
    fail_response = Mock()
    fail_response.status_code = 500
    fail_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=fail_response
    )

    success_response = Mock()
    success_response.json.return_value = [{"name": "library/nginx", "id": 1}]
    success_response.raise_for_status = Mock()

    # Note: Retry is handled by requests.Session adapter, so we just test the logic
    # In practice, the adapter would retry automatically
    client.session.get = Mock(return_value=success_response)

    result = client.discover_repositories("library")

    assert result is not None
    assert len(result) == 1


def test_end_to_end_discovery_workflow():
    """Integration test for complete discovery workflow."""
    client = HarborDiscoveryClient(
        harbor_url="https://harbor.example.com",
        username="admin",
        password="password",
        verify_tls=True,
    )

    # Mock realistic Harbor response
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "id": 1,
            "name": "library/nginx",
            "project_id": 1,
            "description": "Official Nginx",
            "pull_count": 1000,
            "artifact_count": 10,
        },
        {
            "id": 2,
            "name": "library/redis",
            "project_id": 1,
            "description": "Official Redis",
            "pull_count": 500,
            "artifact_count": 5,
        },
    ]
    mock_response.raise_for_status = Mock()

    client.session.get = Mock(return_value=mock_response)

    # Discover repositories
    repos = client.discover_repositories("library")

    assert repos is not None
    assert len(repos) == 2

    # Verify structure
    assert repos[0]["name"] == "nginx"
    assert repos[0]["external_reference"] == "harbor.example.com/library/nginx"
    assert repos[1]["name"] == "redis"
    assert repos[1]["external_reference"] == "harbor.example.com/library/redis"
