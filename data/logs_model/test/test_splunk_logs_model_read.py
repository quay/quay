"""
Unit tests for SplunkLogsModel read methods.

Tests for lookup_logs, lookup_latest_logs, get_aggregated_log_counts,
count_repository_actions, yield_logs_for_export, and helper methods.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from data.logs_model.datatypes import AggregatedLogCount, Log, LogEntriesPage
from data.logs_model.interface import LogsIterationTimeout
from data.logs_model.shared import InvalidLogsDateRangeError
from data.logs_model.splunk_logs_model import SplunkLogsModel
from data.logs_model.splunk_search_client import SplunkSearchResults

# Fake data for testing
FAKE_SPLUNK_HOST = "fakesplunk"
FAKE_SPLUNK_PORT = 443
FAKE_SPLUNK_TOKEN = "fake_token"
FAKE_INDEX_PREFIX = "test_index"

FAKE_LOG_ENTRY_KINDS = {
    "push_repo": 1,
    "pull_repo": 2,
    "create_repo": 3,
    "delete_repo": 4,
    1: "push_repo",
    2: "pull_repo",
    3: "create_repo",
    4: "delete_repo",
}

FAKE_USERS = {
    "testorg": Mock(
        id=1,
        username="testorg",
        email="testorg@example.com",
        organization=True,
        robot=False,
    ),
    "testuser": Mock(
        id=2,
        username="testuser",
        email="testuser@example.com",
        organization=False,
        robot=False,
    ),
}


def _mock_get_namespace_users_by_usernames(usernames):
    """Mock batch user lookup."""
    return {name: FAKE_USERS.get(name) for name in usernames}


@pytest.fixture
def splunk_config():
    """Splunk configuration for testing."""
    return {
        "host": FAKE_SPLUNK_HOST,
        "port": FAKE_SPLUNK_PORT,
        "bearer_token": FAKE_SPLUNK_TOKEN,
        "url_scheme": "https",
        "verify_ssl": False,
        "index_prefix": FAKE_INDEX_PREFIX,
    }


@pytest.fixture
def mock_search_client():
    """Mock SplunkSearchClient."""
    client = Mock()
    client.search.return_value = SplunkSearchResults(
        results=[],
        total_count=0,
        offset=0,
        has_more=False,
    )
    client.search_with_stats.return_value = []
    client.count.return_value = 0
    return client


@pytest.fixture
def mock_field_mapper():
    """Mock SplunkLogMapper."""
    mapper = Mock()
    mapper.map_logs.return_value = []
    return mapper


def _make_mock_repository(rid, repo_name="testrepo", namespace_name="testorg"):
    """Create a repository mock with proper .name attribute."""
    repo = Mock()
    repo.id = rid
    repo.name = repo_name
    repo.namespace_user = Mock(username=namespace_name)
    return repo


@pytest.fixture
def mock_model():
    """Mock the data.model module."""
    model_mock = Mock(
        log=Mock(get_log_entry_kinds=Mock(return_value=FAKE_LOG_ENTRY_KINDS)),
        user=Mock(
            get_namespace_user=lambda name: FAKE_USERS.get(name),
            get_namespace_users_by_usernames=_mock_get_namespace_users_by_usernames,
            get_user_by_id=lambda uid: Mock(username="testorg") if uid == 1 else None,
        ),
        repository=Mock(
            get_repository=lambda ns, name: _make_mock_repository(1, name) if name else None,
            lookup_repository=lambda rid: _make_mock_repository(rid) if rid else None,
        ),
    )
    return model_mock


@pytest.fixture
def splunk_model(splunk_config, mock_search_client, mock_field_mapper, mock_model):
    """Create SplunkLogsModel with mocked dependencies."""
    with patch("data.logs_model.splunk_logs_model.model", mock_model):
        with patch("data.logs_model.splunk_logs_model.SplunkLogsProducer") as mock_producer:
            with patch("splunklib.client.connect"):
                with patch("ssl.SSLContext.load_verify_locations"):
                    mock_producer.return_value = Mock()
                    model_instance = SplunkLogsModel(producer="splunk", splunk_config=splunk_config)
                    model_instance._search_client = mock_search_client
                    model_instance._field_mapper = mock_field_mapper
                    return model_instance


class TestBuildBaseQuery:
    """Tests for _build_base_query helper method."""

    def test_builds_empty_query_with_no_filters(self, splunk_model):
        result = splunk_model._build_base_query()
        assert result == ""

    def test_includes_namespace_filter(self, splunk_model):
        result = splunk_model._build_base_query(namespace_name="testorg")
        assert result == 'account="testorg"'

    def test_includes_performer_filter(self, splunk_model):
        result = splunk_model._build_base_query(performer_name="testuser")
        assert result == 'performer="testuser"'

    def test_includes_repository_filter(self, splunk_model):
        result = splunk_model._build_base_query(repository_name="testrepo")
        assert result == 'repository="testrepo"'

    def test_excludes_filter_kinds(self, splunk_model):
        result = splunk_model._build_base_query(filter_kinds=["push_repo", "pull_repo"])
        assert 'kind!="push_repo"' in result
        assert 'kind!="pull_repo"' in result

    def test_combines_multiple_filters(self, splunk_model):
        result = splunk_model._build_base_query(
            namespace_name="testorg",
            performer_name="testuser",
            repository_name="testrepo",
        )
        assert 'account="testorg"' in result
        assert 'performer="testuser"' in result
        assert 'repository="testrepo"' in result


class TestBuildLookupQuery:
    """Tests for _build_lookup_query helper method."""

    def test_adds_sort_to_base_query(self, splunk_model):
        result = splunk_model._build_lookup_query(namespace_name="testorg")
        assert result == 'account="testorg" | sort -_time'

    def test_handles_empty_base_query(self, splunk_model):
        result = splunk_model._build_lookup_query()
        assert result == "| sort -_time"


class TestLookupLogs:
    """Tests for lookup_logs method."""

    def test_returns_log_entries_page(self, splunk_model, mock_search_client):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        result = splunk_model.lookup_logs(start, end)

        assert isinstance(result, LogEntriesPage)
        assert result.logs == []
        assert result.next_page_token is None

    def test_applies_date_range_filter(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        splunk_model.lookup_logs(start, end)

        mock_search_client.search.assert_called_once()
        call_kwargs = mock_search_client.search.call_args.kwargs
        assert call_kwargs["earliest_time"] == start.isoformat()
        assert call_kwargs["latest_time"] == end.isoformat()

    def test_applies_namespace_filter(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        splunk_model.lookup_logs(start, end, namespace_name="testorg")

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert 'account="testorg"' in call_kwargs["query"]

    def test_applies_performer_filter(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        splunk_model.lookup_logs(start, end, performer_name="testuser")

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert 'performer="testuser"' in call_kwargs["query"]

    def test_applies_repository_filter(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        splunk_model.lookup_logs(start, end, repository_name="testrepo")

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert 'repository="testrepo"' in call_kwargs["query"]

    def test_applies_filter_kinds(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        splunk_model.lookup_logs(start, end, filter_kinds=["push_repo"])

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert 'kind!="push_repo"' in call_kwargs["query"]

    def test_pagination_with_page_token(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        page_token = {"offset": 20, "page_number": 1}

        splunk_model.lookup_logs(start, end, page_token=page_token)

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert call_kwargs["offset"] == 20

    def test_max_page_count_limits_pages(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        page_token = {"offset": 40, "page_number": 2}

        result = splunk_model.lookup_logs(start, end, page_token=page_token, max_page_count=2)

        assert result.logs == []
        assert result.next_page_token is None
        mock_search_client.search.assert_not_called()

    def test_empty_results_returns_empty_page(
        self, splunk_model, mock_search_client, mock_field_mapper
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        mock_search_client.search.return_value = SplunkSearchResults(
            results=[], total_count=0, offset=0, has_more=False
        )

        result = splunk_model.lookup_logs(start, end)

        assert result.logs == []
        assert result.next_page_token is None

    def test_handles_readwrite_page_token(
        self, splunk_model, mock_search_client, mock_field_mapper
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        page_token = {"readwrite_page_token": {"offset": 20, "page_number": 1}}

        splunk_model.lookup_logs(start, end, page_token=page_token)

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert call_kwargs["offset"] == 20

    def test_returns_next_page_token_when_more_results(
        self, splunk_model, mock_search_client, mock_field_mapper
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        # Simulate 21 results (more than PAGE_SIZE of 20)
        mock_search_client.search.return_value = SplunkSearchResults(
            results=[{"kind": "push_repo"}] * 21,
            total_count=100,
            offset=0,
            has_more=True,
        )
        mock_field_mapper.map_logs.return_value = [Mock()] * 20

        result = splunk_model.lookup_logs(start, end)

        assert result.next_page_token is not None
        assert result.next_page_token["offset"] == 20
        assert result.next_page_token["page_number"] == 1


class TestLookupLatestLogs:
    """Tests for lookup_latest_logs method."""

    def test_returns_log_list(self, splunk_model, mock_search_client, mock_field_mapper):
        mock_field_mapper.map_logs.return_value = []
        result = splunk_model.lookup_latest_logs()

        assert isinstance(result, list)

    def test_default_size_is_20(self, splunk_model, mock_search_client, mock_field_mapper):
        splunk_model.lookup_latest_logs()

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert call_kwargs["max_count"] == 20

    def test_custom_size_parameter(self, splunk_model, mock_search_client, mock_field_mapper):
        splunk_model.lookup_latest_logs(size=50)

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert call_kwargs["max_count"] == 50

    def test_uses_32_day_window(self, splunk_model, mock_search_client, mock_field_mapper):
        splunk_model.lookup_latest_logs()

        call_kwargs = mock_search_client.search.call_args.kwargs
        earliest = datetime.fromisoformat(call_kwargs["earliest_time"])
        latest = datetime.fromisoformat(call_kwargs["latest_time"])

        # Should be approximately 32 days
        delta = latest - earliest
        assert 31 <= delta.days <= 32

    def test_applies_all_filters(self, splunk_model, mock_search_client, mock_field_mapper):
        splunk_model.lookup_latest_logs(
            namespace_name="testorg",
            performer_name="testuser",
            repository_name="testrepo",
            filter_kinds=["delete_repo"],
        )

        call_kwargs = mock_search_client.search.call_args.kwargs
        query = call_kwargs["query"]
        assert 'account="testorg"' in query
        assert 'performer="testuser"' in query
        assert 'repository="testrepo"' in query
        assert 'kind!="delete_repo"' in query


class TestGetAggregatedLogCounts:
    """Tests for get_aggregated_log_counts method."""

    def test_returns_aggregated_count_list(
        self, splunk_model, mock_search_client, mock_field_mapper, mock_model
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 15)

        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            result = splunk_model.get_aggregated_log_counts(start, end)

        assert isinstance(result, list)

    def test_groups_by_kind_and_date(
        self, splunk_model, mock_search_client, mock_field_mapper, mock_model
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 15)

        mock_search_client.search_with_stats.return_value = [
            {"kind": "push_repo", "log_date": "2024-01-05", "count": "10"},
            {"kind": "pull_repo", "log_date": "2024-01-05", "count": "25"},
        ]

        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            result = splunk_model.get_aggregated_log_counts(start, end)

        assert len(result) == 2
        assert all(isinstance(item, AggregatedLogCount) for item in result)

    def test_raises_error_for_long_date_range(self, splunk_model):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 1)  # More than 32 days

        with pytest.raises(InvalidLogsDateRangeError):
            splunk_model.get_aggregated_log_counts(start, end)

    def test_maps_kind_to_kind_id(
        self, splunk_model, mock_search_client, mock_field_mapper, mock_model
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 15)

        mock_search_client.search_with_stats.return_value = [
            {"kind": "push_repo", "log_date": "2024-01-05", "count": "10"},
        ]

        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            result = splunk_model.get_aggregated_log_counts(start, end)

        assert result[0].kind_id == 1  # push_repo maps to 1

    def test_applies_all_filters(
        self, splunk_model, mock_search_client, mock_field_mapper, mock_model
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 15)

        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            splunk_model.get_aggregated_log_counts(
                start,
                end,
                namespace_name="testorg",
                performer_name="testuser",
                filter_kinds=["delete_repo"],
            )

        call_kwargs = mock_search_client.search_with_stats.call_args.kwargs
        query = call_kwargs["query"]
        assert 'account="testorg"' in query
        assert 'performer="testuser"' in query
        assert 'kind!="delete_repo"' in query
        assert "stats count by kind, log_date" in query


class TestCountRepositoryActions:
    """Tests for count_repository_actions method."""

    def _make_repository_mock(self, repo_name="testrepo", namespace_name="testorg"):
        """Create a repository mock with proper .name attribute."""
        repository = Mock()
        repository.name = repo_name
        repository.namespace_user = Mock(username=namespace_name)
        return repository

    def test_returns_integer_count(self, splunk_model, mock_search_client):
        mock_search_client.count.return_value = 42
        repository = self._make_repository_mock()
        day = datetime(2024, 1, 15)

        result = splunk_model.count_repository_actions(repository, day)

        assert result == 42
        assert isinstance(result, int)

    def test_filters_by_repository_and_day(self, splunk_model, mock_search_client):
        repository = self._make_repository_mock()
        day = datetime(2024, 1, 15, 10, 30, 0)  # Include time component

        splunk_model.count_repository_actions(repository, day)

        call_kwargs = mock_search_client.count.call_args.kwargs
        assert 'account="testorg"' in call_kwargs["query"]
        assert 'repository="testrepo"' in call_kwargs["query"]

    def test_returns_zero_on_timeout(self, splunk_model, mock_search_client):
        from data.logs_model.splunk_search_client import SplunkSearchTimeoutError

        mock_search_client.count.side_effect = SplunkSearchTimeoutError("Timeout")
        repository = self._make_repository_mock()
        day = datetime(2024, 1, 15)

        result = splunk_model.count_repository_actions(repository, day)

        assert result == 0

    def test_returns_zero_on_exception(self, splunk_model, mock_search_client):
        mock_search_client.count.side_effect = Exception("Connection error")
        repository = self._make_repository_mock()
        day = datetime(2024, 1, 15)

        result = splunk_model.count_repository_actions(repository, day)

        assert result == 0

    def test_handles_datetime_day_parameter(self, splunk_model, mock_search_client):
        repository = self._make_repository_mock()
        day = datetime(2024, 1, 15, 14, 30, 45)

        splunk_model.count_repository_actions(repository, day)

        call_kwargs = mock_search_client.count.call_args.kwargs
        # Should start at midnight
        assert "2024-01-15T00:00:00" in call_kwargs["earliest_time"]

    def test_handles_date_day_parameter(self, splunk_model, mock_search_client):
        from datetime import date

        repository = self._make_repository_mock()
        day = date(2024, 1, 15)

        splunk_model.count_repository_actions(repository, day)

        call_kwargs = mock_search_client.count.call_args.kwargs
        assert call_kwargs["timeout"] == 30


class TestYieldLogsForExport:
    """Tests for yield_logs_for_export method."""

    def test_returns_generator(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        result = splunk_model.yield_logs_for_export(start, end)

        # Check it's a generator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_yields_log_batches(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        mock_search_client.search.return_value = SplunkSearchResults(
            results=[{"kind": "push_repo"}] * 100,
            total_count=100,
            offset=0,
            has_more=False,
        )
        mock_field_mapper.map_logs.return_value = [Mock()] * 100

        batches = list(splunk_model.yield_logs_for_export(start, end))

        assert len(batches) == 1
        assert len(batches[0]) == 100

    def test_raises_timeout_error(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        # Simulate slow responses that exceed timeout
        def slow_search(*args, **kwargs):
            import time

            time.sleep(0.1)
            return SplunkSearchResults(
                results=[{"kind": "push_repo"}] * 100,
                total_count=10000,
                offset=0,
                has_more=True,
            )

        mock_search_client.search.side_effect = slow_search
        mock_field_mapper.map_logs.return_value = [Mock()] * 100

        # Use very short timeout to trigger error
        with pytest.raises(LogsIterationTimeout):
            gen = splunk_model.yield_logs_for_export(
                start, end, max_query_time=timedelta(seconds=0.05)
            )
            # Need to consume generator to trigger timeout
            for _ in gen:
                pass

    def test_respects_max_query_time(self, splunk_model, mock_search_client, mock_field_mapper):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        mock_search_client.search.return_value = SplunkSearchResults(
            results=[{"kind": "push_repo"}] * 100,
            total_count=100,
            offset=0,
            has_more=False,
        )
        mock_field_mapper.map_logs.return_value = [Mock()] * 100

        # Should complete quickly within timeout
        batches = list(
            splunk_model.yield_logs_for_export(start, end, max_query_time=timedelta(seconds=60))
        )

        assert len(batches) == 1

    def test_resolves_namespace_id_to_name(
        self, splunk_model, mock_search_client, mock_field_mapper, mock_model
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            list(splunk_model.yield_logs_for_export(start, end, namespace_id=1))

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert 'account="testorg"' in call_kwargs["query"]

    def test_resolves_repository_id_to_name(
        self, splunk_model, mock_search_client, mock_field_mapper, mock_model
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            list(splunk_model.yield_logs_for_export(start, end, repository_id=1))

        call_kwargs = mock_search_client.search.call_args.kwargs
        assert 'repository="testrepo"' in call_kwargs["query"]
        assert 'account="testorg"' in call_kwargs["query"]

    def test_empty_results_returns_no_batches(
        self, splunk_model, mock_search_client, mock_field_mapper
    ):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        mock_search_client.search.return_value = SplunkSearchResults(
            results=[], total_count=0, offset=0, has_more=False
        )

        batches = list(splunk_model.yield_logs_for_export(start, end))

        assert batches == []


class TestYieldLogRotationContext:
    """Tests for yield_log_rotation_context method."""

    def test_returns_empty_generator(self, splunk_model):
        """Splunk handles log rotation internally, so this should yield nothing."""
        cutoff_date = datetime(2024, 1, 1)
        min_logs = 1000

        result = list(splunk_model.yield_log_rotation_context(cutoff_date, min_logs))

        assert result == []


class TestSplunkLogsModelConfiguration:
    """Tests for SplunkLogsModel configuration parsing."""

    def test_init_stores_splunk_config(self, splunk_config, mock_model):
        """Test that __init__ stores splunk_config."""
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkLogsProducer") as mock_producer:
                mock_producer.return_value = Mock()
                model_instance = SplunkLogsModel(producer="splunk", splunk_config=splunk_config)

                assert model_instance._splunk_config == splunk_config
                assert model_instance._producer == "splunk"

    def test_init_stores_hec_config(self, mock_model):
        """Test that __init__ stores splunk_hec_config."""
        hec_config = {
            "host": "hec.splunk.example",
            "hec_token": "hec_token_123",
        }
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkHECLogsProducer") as mock_producer:
                mock_producer.return_value = Mock()
                model_instance = SplunkLogsModel(
                    producer="splunk_hec", splunk_hec_config=hec_config
                )

                assert model_instance._splunk_hec_config == hec_config
                assert model_instance._producer == "splunk_hec"

    def test_get_search_client_with_splunk_config(self, splunk_config, mock_model):
        """Test that _get_search_client uses splunk_config directly."""
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkLogsProducer") as mock_producer:
                with patch(
                    "data.logs_model.splunk_logs_model.SplunkSearchClient"
                ) as mock_search_client:
                    mock_producer.return_value = Mock()
                    mock_search_client.return_value = Mock()

                    model_instance = SplunkLogsModel(producer="splunk", splunk_config=splunk_config)
                    search_client = model_instance._get_search_client()

                    mock_search_client.assert_called_once_with(**splunk_config)
                    assert search_client is not None

    def test_get_search_client_with_hec_config_fallback(self, mock_model):
        """Test that _get_search_client falls back to HEC host/token when search_* not provided."""
        hec_config = {
            "host": "hec.splunk.example",
            "hec_token": "hec_token_123",
            "url_scheme": "https",
            "verify_ssl": True,
            "index": "quay_logs",
        }
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkHECLogsProducer") as mock_producer:
                with patch(
                    "data.logs_model.splunk_logs_model.SplunkSearchClient"
                ) as mock_search_client:
                    mock_producer.return_value = Mock()
                    mock_search_client.return_value = Mock()

                    model_instance = SplunkLogsModel(
                        producer="splunk_hec", splunk_hec_config=hec_config
                    )
                    model_instance._get_search_client()

                    # Should use HEC host and token as fallback
                    call_kwargs = mock_search_client.call_args[1]
                    assert call_kwargs["host"] == "hec.splunk.example"
                    assert call_kwargs["bearer_token"] == "hec_token_123"
                    assert call_kwargs["port"] == 8089  # Default search port
                    assert call_kwargs["index_prefix"] == "quay_logs"

    def test_get_search_client_with_hec_config_explicit_search_options(self, mock_model):
        """Test that _get_search_client uses explicit search_* options from HEC config."""
        hec_config = {
            "host": "hec.splunk.example",
            "hec_token": "hec_token_123",
            "search_host": "mgmt.splunk.example",
            "search_port": 9089,
            "search_token": "search_token_456",
            "search_timeout": 120,
            "max_results": 20000,
        }
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkHECLogsProducer") as mock_producer:
                with patch(
                    "data.logs_model.splunk_logs_model.SplunkSearchClient"
                ) as mock_search_client:
                    mock_producer.return_value = Mock()
                    mock_search_client.return_value = Mock()

                    model_instance = SplunkLogsModel(
                        producer="splunk_hec", splunk_hec_config=hec_config
                    )
                    model_instance._get_search_client()

                    # Should use explicit search_* options
                    call_kwargs = mock_search_client.call_args[1]
                    assert call_kwargs["host"] == "mgmt.splunk.example"
                    assert call_kwargs["port"] == 9089
                    assert call_kwargs["bearer_token"] == "search_token_456"
                    assert call_kwargs["search_timeout"] == 120
                    assert call_kwargs["max_results"] == 20000

    def test_get_export_batch_size_from_splunk_config(self, splunk_config, mock_model):
        """Test that _get_export_batch_size reads from splunk_config."""
        splunk_config["export_batch_size"] = 2000
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkLogsProducer") as mock_producer:
                mock_producer.return_value = Mock()
                model_instance = SplunkLogsModel(producer="splunk", splunk_config=splunk_config)

                batch_size = model_instance._get_export_batch_size()

                assert batch_size == 2000

    def test_get_export_batch_size_from_hec_config(self, mock_model):
        """Test that _get_export_batch_size reads from splunk_hec_config."""
        hec_config = {
            "host": "hec.splunk.example",
            "hec_token": "hec_token_123",
            "export_batch_size": 3000,
        }
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkHECLogsProducer") as mock_producer:
                mock_producer.return_value = Mock()
                model_instance = SplunkLogsModel(
                    producer="splunk_hec", splunk_hec_config=hec_config
                )

                batch_size = model_instance._get_export_batch_size()

                assert batch_size == 3000

    def test_get_export_batch_size_default(self, splunk_config, mock_model):
        """Test that _get_export_batch_size returns default when not configured."""
        # No export_batch_size in config
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkLogsProducer") as mock_producer:
                mock_producer.return_value = Mock()
                model_instance = SplunkLogsModel(producer="splunk", splunk_config=splunk_config)

                batch_size = model_instance._get_export_batch_size()

                assert batch_size == 5000  # Default value

    def test_backward_compatible_config_without_new_options(self, mock_model):
        """Test that existing configs without new options still work."""
        # Minimal config without any of the new options
        minimal_config = {
            "host": "splunk.example.com",
            "port": 8089,
            "bearer_token": "token123",
        }
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkLogsProducer") as mock_producer:
                with patch(
                    "data.logs_model.splunk_logs_model.SplunkSearchClient"
                ) as mock_search_client:
                    mock_producer.return_value = Mock()
                    mock_search_client.return_value = Mock()

                    model_instance = SplunkLogsModel(
                        producer="splunk", splunk_config=minimal_config
                    )

                    # Should not raise any errors
                    search_client = model_instance._get_search_client()
                    assert search_client is not None

                    # Export batch size should use default
                    batch_size = model_instance._get_export_batch_size()
                    assert batch_size == 5000

    def test_yield_logs_for_export_uses_configured_batch_size(
        self, mock_model, mock_search_client, mock_field_mapper
    ):
        """Test that yield_logs_for_export uses the configured batch size."""
        splunk_config = {
            "host": "splunk.example.com",
            "port": 8089,
            "bearer_token": "token123",
            "export_batch_size": 1000,  # Custom batch size
        }
        with patch("data.logs_model.splunk_logs_model.model", mock_model):
            with patch("data.logs_model.splunk_logs_model.SplunkLogsProducer") as mock_producer:
                mock_producer.return_value = Mock()
                model_instance = SplunkLogsModel(producer="splunk", splunk_config=splunk_config)
                model_instance._search_client = mock_search_client
                model_instance._field_mapper = mock_field_mapper

                start = datetime(2024, 1, 1)
                end = datetime(2024, 1, 31)

                # Consume the generator
                list(model_instance.yield_logs_for_export(start, end))

                # Verify the batch size was used
                call_kwargs = mock_search_client.search.call_args[1]
                assert call_kwargs["max_count"] == 1000
