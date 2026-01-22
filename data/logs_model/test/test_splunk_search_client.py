"""
Unit tests for SplunkSearchClient.
"""

import ssl
from unittest.mock import MagicMock, Mock, patch

import pytest

from data.logs_model.splunk_search_client import (
    SplunkAuthenticationError,
    SplunkConnectionError,
    SplunkSearchClient,
    SplunkSearchError,
    SplunkSearchResults,
    SplunkSearchTimeoutError,
)

FAKE_SPLUNK_HOST = "fakesplunk.example.com"
FAKE_SPLUNK_PORT = 8089
FAKE_SPLUNK_TOKEN = "fake_bearer_token"
FAKE_INDEX_PREFIX = "quay_logs"


@pytest.fixture
def mock_splunk_service():
    """Create a mock Splunk service."""
    mock_service = Mock()
    mock_service.jobs = Mock()
    return mock_service


@pytest.fixture
def search_client():
    """Create a SplunkSearchClient instance without connecting."""
    return SplunkSearchClient(
        host=FAKE_SPLUNK_HOST,
        port=FAKE_SPLUNK_PORT,
        bearer_token=FAKE_SPLUNK_TOKEN,
        index_prefix=FAKE_INDEX_PREFIX,
        search_timeout=60,
        max_results=1000,
    )


class TestSplunkSearchClientInit:
    """Tests for SplunkSearchClient initialization."""

    def test_init_stores_parameters(self):
        """Test that init stores all parameters correctly."""
        client = SplunkSearchClient(
            host=FAKE_SPLUNK_HOST,
            port=FAKE_SPLUNK_PORT,
            bearer_token=FAKE_SPLUNK_TOKEN,
            url_scheme="https",
            verify_ssl=True,
            ssl_ca_path="/path/to/ca.pem",
            index_prefix=FAKE_INDEX_PREFIX,
            search_timeout=120,
            max_results=5000,
        )

        assert client._host == FAKE_SPLUNK_HOST
        assert client._port == FAKE_SPLUNK_PORT
        assert client._bearer_token == FAKE_SPLUNK_TOKEN
        assert client._url_scheme == "https"
        assert client._verify_ssl is True
        assert client._ssl_ca_path == "/path/to/ca.pem"
        assert client._index_prefix == FAKE_INDEX_PREFIX
        assert client._search_timeout == 120
        assert client._max_results == 5000
        assert client._service is None

    def test_init_with_defaults(self):
        """Test that init uses default values correctly."""
        client = SplunkSearchClient(
            host=FAKE_SPLUNK_HOST,
            port=FAKE_SPLUNK_PORT,
            bearer_token=FAKE_SPLUNK_TOKEN,
        )

        assert client._url_scheme == "https"
        assert client._verify_ssl is True
        assert client._ssl_ca_path is None
        assert client._index_prefix is None
        assert client._search_timeout == 60
        assert client._max_results == 10000


class TestSplunkSearchClientConnection:
    """Tests for SplunkSearchClient connection handling."""

    def test_get_connection_creates_connection(self, search_client, mock_splunk_service):
        """Test that _get_connection creates a new connection."""
        with patch("data.logs_model.splunk_search_client.client.connect") as mock_connect:
            mock_connect.return_value = mock_splunk_service

            service = search_client._get_connection()

            assert service == mock_splunk_service
            mock_connect.assert_called_once()
            assert search_client._service == mock_splunk_service

    def test_get_connection_returns_cached_connection(self, search_client, mock_splunk_service):
        """Test that _get_connection returns cached connection."""
        search_client._service = mock_splunk_service

        with patch("data.logs_model.splunk_search_client.client.connect") as mock_connect:
            service = search_client._get_connection()

            assert service == mock_splunk_service
            mock_connect.assert_not_called()

    def test_get_connection_handles_auth_error(self, search_client):
        """Test that _get_connection raises SplunkAuthenticationError on auth failure."""
        from io import BytesIO

        from splunklib.binding import AuthenticationError, HTTPError  # type: ignore[import]

        # Create a mock HTTP response that AuthenticationError expects
        mock_response = Mock()
        mock_response.body = BytesIO(b"Authentication failed")
        mock_response.status = 401
        mock_response.reason = "Unauthorized"

        # Create the HTTPError cause
        mock_cause = HTTPError(mock_response)

        with patch("data.logs_model.splunk_search_client.client.connect") as mock_connect:
            mock_connect.side_effect = AuthenticationError("Invalid token", cause=mock_cause)

            with pytest.raises(SplunkAuthenticationError) as exc_info:
                search_client._get_connection()

            assert "Authentication to Splunk failed" in str(exc_info.value)

    def test_get_connection_handles_connection_refused(self, search_client):
        """Test that _get_connection raises SplunkConnectionError on connection refused."""
        with patch("data.logs_model.splunk_search_client.client.connect") as mock_connect:
            mock_connect.side_effect = ConnectionRefusedError("Connection refused")

            with pytest.raises(SplunkConnectionError) as exc_info:
                search_client._get_connection()

            assert "Connection to Splunk refused" in str(exc_info.value)

    def test_get_connection_handles_generic_error(self, search_client):
        """Test that _get_connection raises SplunkConnectionError on generic errors."""
        with patch("data.logs_model.splunk_search_client.client.connect") as mock_connect:
            mock_connect.side_effect = Exception("Network error")

            with pytest.raises(SplunkConnectionError) as exc_info:
                search_client._get_connection()

            assert "Failed to connect to Splunk" in str(exc_info.value)


class TestSplunkSearchClientSSL:
    """Tests for SSL configuration."""

    def test_ssl_context_with_verify_enabled(self):
        """Test SSL context configuration with verification enabled."""
        client = SplunkSearchClient(
            host=FAKE_SPLUNK_HOST,
            port=FAKE_SPLUNK_PORT,
            bearer_token=FAKE_SPLUNK_TOKEN,
            verify_ssl=True,
        )

        with patch("data.logs_model.splunk_search_client.client.connect") as mock_connect:
            mock_connect.return_value = Mock()

            client._get_connection()

            call_kwargs = mock_connect.call_args[1]
            context = call_kwargs["context"]
            assert context.check_hostname is True
            assert context.verify_mode == ssl.CERT_REQUIRED

    def test_ssl_context_with_verify_disabled(self):
        """Test SSL context configuration with verification disabled."""
        client = SplunkSearchClient(
            host=FAKE_SPLUNK_HOST,
            port=FAKE_SPLUNK_PORT,
            bearer_token=FAKE_SPLUNK_TOKEN,
            verify_ssl=False,
        )

        with patch("data.logs_model.splunk_search_client.client.connect") as mock_connect:
            mock_connect.return_value = Mock()

            client._get_connection()

            call_kwargs = mock_connect.call_args[1]
            context = call_kwargs["context"]
            assert context.check_hostname is False
            assert context.verify_mode == ssl.CERT_NONE

    def test_ssl_ca_path_invalid_raises_error(self):
        """Test that invalid SSL CA path raises SplunkConnectionError."""
        client = SplunkSearchClient(
            host=FAKE_SPLUNK_HOST,
            port=FAKE_SPLUNK_PORT,
            bearer_token=FAKE_SPLUNK_TOKEN,
            ssl_ca_path="/nonexistent/path/ca.pem",
        )

        with pytest.raises(SplunkConnectionError) as exc_info:
            client._get_connection()

        assert "Path to cert file is not valid" in str(exc_info.value)


class TestSplunkSearchClientSearch:
    """Tests for search method."""

    def test_search_returns_results(self, search_client, mock_splunk_service):
        """Test that search returns SplunkSearchResults."""
        mock_job = Mock()
        mock_job.__getitem__ = Mock(return_value="2")
        mock_job.results = Mock(return_value=Mock())
        mock_splunk_service.jobs.create = Mock(return_value=mock_job)

        with (
            patch.object(search_client, "_get_connection", return_value=mock_splunk_service),
            patch.object(
                search_client,
                "_get_results_from_job",
                return_value=[{"kind": "push_repo", "account": "user1"}],
            ),
        ):
            result = search_client.search("kind=push_repo")

            assert isinstance(result, SplunkSearchResults)
            assert len(result.results) == 1
            assert result.results[0]["kind"] == "push_repo"
            assert result.total_count == 2
            assert result.offset == 0

    def test_search_with_pagination(self, search_client, mock_splunk_service):
        """Test search with pagination parameters."""
        mock_job = Mock()
        mock_job.__getitem__ = Mock(return_value="10")
        mock_job.results = Mock(return_value=Mock())
        mock_splunk_service.jobs.create = Mock(return_value=mock_job)

        with (
            patch.object(search_client, "_get_connection", return_value=mock_splunk_service),
            patch.object(
                search_client,
                "_get_results_from_job",
                return_value=[{"kind": "push_repo"}] * 5,
            ),
        ):
            result = search_client.search("kind=push_repo", max_count=5, offset=5)

            assert result.offset == 5
            assert len(result.results) == 5
            assert result.has_more is False  # 5 + 5 = 10 = total

    def test_search_with_time_range(self, search_client, mock_splunk_service):
        """Test search with time range parameters."""
        mock_job = Mock()
        mock_job.__getitem__ = Mock(return_value="1")
        mock_job.results = Mock(return_value=Mock())
        mock_splunk_service.jobs.create = Mock(return_value=mock_job)

        with (
            patch.object(search_client, "_get_connection", return_value=mock_splunk_service),
            patch.object(search_client, "_get_results_from_job", return_value=[]),
        ):
            search_client.search(
                "kind=push_repo",
                earliest_time="-24h",
                latest_time="now",
            )

            call_kwargs = mock_splunk_service.jobs.create.call_args[1]
            assert call_kwargs["earliest_time"] == "-24h"
            assert call_kwargs["latest_time"] == "now"

    def test_search_handles_error(self, search_client, mock_splunk_service):
        """Test that search raises SplunkSearchError on failure."""
        mock_splunk_service.jobs.create = Mock(side_effect=Exception("Search failed"))

        with patch.object(search_client, "_get_connection", return_value=mock_splunk_service):
            with pytest.raises(SplunkSearchError) as exc_info:
                search_client.search("kind=push_repo")

            assert "Search execution failed" in str(exc_info.value)


class TestSplunkSearchClientSearchWithStats:
    """Tests for search_with_stats method."""

    def test_search_with_stats_returns_results(self, search_client, mock_splunk_service):
        """Test that search_with_stats returns list of dictionaries."""
        mock_job = Mock()
        mock_job.results = Mock(return_value=Mock())
        mock_splunk_service.jobs.create = Mock(return_value=mock_job)

        expected_results = [
            {"kind": "push_repo", "count": "10"},
            {"kind": "pull_repo", "count": "20"},
        ]

        with (
            patch.object(search_client, "_get_connection", return_value=mock_splunk_service),
            patch.object(search_client, "_get_results_from_job", return_value=expected_results),
        ):
            result = search_client.search_with_stats("| stats count by kind")

            assert result == expected_results

    def test_search_with_stats_handles_error(self, search_client, mock_splunk_service):
        """Test that search_with_stats raises SplunkSearchError on failure."""
        mock_splunk_service.jobs.create = Mock(side_effect=Exception("Stats failed"))

        with patch.object(search_client, "_get_connection", return_value=mock_splunk_service):
            with pytest.raises(SplunkSearchError) as exc_info:
                search_client.search_with_stats("| stats count by kind")

            assert "Stats search execution failed" in str(exc_info.value)


class TestSplunkSearchClientCount:
    """Tests for count method."""

    def test_count_returns_integer(self, search_client, mock_splunk_service):
        """Test that count returns an integer count."""
        mock_job = Mock()
        mock_job.is_done = Mock(return_value=True)
        mock_job.results = Mock(return_value=Mock())
        mock_splunk_service.jobs.create = Mock(return_value=mock_job)

        with (
            patch.object(search_client, "_get_connection", return_value=mock_splunk_service),
            patch.object(search_client, "_get_results_from_job", return_value=[{"count": "42"}]),
        ):
            result = search_client.count("kind=push_repo")

            assert result == 42
            assert isinstance(result, int)

    def test_count_returns_zero_for_empty_results(self, search_client, mock_splunk_service):
        """Test that count returns 0 when no results."""
        mock_job = Mock()
        mock_job.is_done = Mock(return_value=True)
        mock_job.results = Mock(return_value=Mock())
        mock_splunk_service.jobs.create = Mock(return_value=mock_job)

        with (
            patch.object(search_client, "_get_connection", return_value=mock_splunk_service),
            patch.object(search_client, "_get_results_from_job", return_value=[]),
        ):
            result = search_client.count("kind=nonexistent")

            assert result == 0

    def test_count_handles_timeout(self, search_client, mock_splunk_service):
        """Test that count raises SplunkSearchTimeoutError on timeout."""
        mock_job = Mock()
        mock_job.is_done = Mock(return_value=False)
        mock_job.refresh = Mock()
        mock_job.cancel = Mock()
        mock_splunk_service.jobs.create = Mock(return_value=mock_job)

        with (
            patch.object(search_client, "_get_connection", return_value=mock_splunk_service),
            patch("data.logs_model.splunk_search_client.time.time") as mock_time,
            patch("data.logs_model.splunk_search_client.time.sleep"),
        ):
            mock_time.side_effect = [0, 0, 35]  # Start, check, timeout exceeded

            with pytest.raises(SplunkSearchTimeoutError) as exc_info:
                search_client.count("kind=push_repo", timeout=30)

            assert "exceeded timeout" in str(exc_info.value)
            mock_job.cancel.assert_called_once()

    def test_count_handles_error(self, search_client, mock_splunk_service):
        """Test that count raises SplunkSearchError on failure."""
        mock_splunk_service.jobs.create = Mock(side_effect=Exception("Count failed"))

        with patch.object(search_client, "_get_connection", return_value=mock_splunk_service):
            with pytest.raises(SplunkSearchError) as exc_info:
                search_client.count("kind=push_repo")

            assert "Count query failed" in str(exc_info.value)


class TestSplunkSearchClientHelpers:
    """Tests for helper methods."""

    def test_build_search_query_with_index(self, search_client):
        """Test that _build_search_query includes index prefix."""
        query = search_client._build_search_query("kind=push_repo")
        assert query == f"search index={FAKE_INDEX_PREFIX} kind=push_repo"

    def test_build_search_query_without_index(self):
        """Test that _build_search_query works without index prefix."""
        client = SplunkSearchClient(
            host=FAKE_SPLUNK_HOST,
            port=FAKE_SPLUNK_PORT,
            bearer_token=FAKE_SPLUNK_TOKEN,
        )

        query = client._build_search_query("kind=push_repo")
        assert query == "search kind=push_repo"

    def test_get_results_from_job(self, search_client):
        """Test that _get_results_from_job extracts results correctly."""
        mock_job = Mock()

        mock_result_data = [
            {"kind": "push_repo", "account": "user1"},
            {"kind": "pull_repo", "account": "user2"},
        ]

        with patch("data.logs_model.splunk_search_client.results.JSONResultsReader") as mock_reader:
            mock_reader.return_value = iter(mock_result_data)

            results = search_client._get_results_from_job(mock_job)

            assert len(results) == 2
            assert results[0]["kind"] == "push_repo"
            assert results[1]["kind"] == "pull_repo"

    def test_get_results_from_job_filters_non_dict(self, search_client):
        """Test that _get_results_from_job filters out non-dict results."""
        mock_job = Mock()

        mock_result_data = [
            {"kind": "push_repo"},
            "not a dict",
            {"kind": "pull_repo"},
            None,
        ]

        with patch("data.logs_model.splunk_search_client.results.JSONResultsReader") as mock_reader:
            mock_reader.return_value = iter(mock_result_data)

            results = search_client._get_results_from_job(mock_job)

            assert len(results) == 2
            assert all(isinstance(r, dict) for r in results)
