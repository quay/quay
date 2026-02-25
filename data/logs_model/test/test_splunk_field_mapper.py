"""
Unit tests for SplunkLogMapper.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from data.logs_model.datatypes import Log
from data.logs_model.splunk_field_mapper import SplunkLogMapper

FAKE_LOG_ENTRY_KINDS = {
    "push_repo": 1,
    "pull_repo": 2,
    "create_repo": 3,
    1: "push_repo",
    2: "pull_repo",
    3: "create_repo",
}

FAKE_USERS = {
    "user1": Mock(
        id=1,
        username="user1",
        email="user1@example.com",
        organization=False,
        robot=False,
    ),
    "user2": Mock(
        id=2,
        username="user2",
        email="user2@example.com",
        organization=True,
        robot=False,
    ),
    "robot1": Mock(
        id=3,
        username="org1+robot1",
        email=None,
        organization=False,
        robot=True,
    ),
}


def _mock_get_namespace_users_by_usernames(usernames):
    """Mock batch user lookup."""
    return {name: FAKE_USERS.get(name) for name in usernames}


@pytest.fixture
def mock_model():
    """Mock the data.model module."""
    model = Mock(
        log=Mock(get_log_entry_kinds=Mock(return_value=FAKE_LOG_ENTRY_KINDS)),
        user=Mock(
            get_namespace_user=lambda _name: FAKE_USERS.get(_name),
            get_namespace_users_by_usernames=_mock_get_namespace_users_by_usernames,
        ),
        repository=Mock(get_repository=lambda _ns, _name: Mock(id=1) if _name == "repo1" else None),
    )
    with patch("data.logs_model.splunk_field_mapper.model", model):
        yield model


@pytest.fixture
def field_mapper(mock_model):
    """Create a SplunkLogMapper instance with mocked model."""
    _ = mock_model  # Fixture dependency for patch context
    return SplunkLogMapper()


@pytest.fixture
def sample_splunk_result():
    """Create a sample Splunk result dictionary."""
    return {
        "kind": "push_repo",
        "account": "user1",
        "performer": "user2",
        "repository": "repo1",
        "ip": "192.168.1.1",
        "metadata_json": {"tag": "latest", "digest": "sha256:abc123"},
        "datetime": "2024-01-15T10:30:00Z",
    }


class TestSplunkLogMapperMapLogs:
    """Tests for map_logs method."""

    def test_map_logs_returns_log_list(self, field_mapper, sample_splunk_result):
        """Test that map_logs returns a list of Log objects."""
        results = [sample_splunk_result]

        logs = field_mapper.map_logs(results)

        assert isinstance(logs, list)
        assert len(logs) == 1
        assert isinstance(logs[0], Log)

    def test_map_logs_maps_all_fields(self, field_mapper, sample_splunk_result):
        """Test that map_logs correctly maps all fields."""
        results = [sample_splunk_result]

        logs = field_mapper.map_logs(results)
        log = logs[0]

        assert log.kind_id == 1  # push_repo
        assert log.account_username == "user1"
        assert log.account_email == "user1@example.com"
        assert log.performer_username == "user2"
        assert log.performer_email == "user2@example.com"
        assert log.ip == "192.168.1.1"
        assert json.loads(log.metadata_json) == {"tag": "latest", "digest": "sha256:abc123"}

    def test_map_logs_handles_empty_list(self, field_mapper):
        """Test that map_logs returns empty list for empty input."""
        logs = field_mapper.map_logs([])
        assert logs == []

    def test_map_logs_handles_multiple_results(self, field_mapper, sample_splunk_result):
        """Test that map_logs handles multiple results."""
        result2 = sample_splunk_result.copy()
        result2["kind"] = "pull_repo"
        result2["performer"] = "user1"

        logs = field_mapper.map_logs([sample_splunk_result, result2])

        assert len(logs) == 2
        assert logs[0].kind_id == 1  # push_repo
        assert logs[1].kind_id == 2  # pull_repo

    def test_map_logs_handles_missing_performer(self, field_mapper, sample_splunk_result):
        """Test that map_logs handles missing performer."""
        sample_splunk_result["performer"] = None

        logs = field_mapper.map_logs([sample_splunk_result])

        assert len(logs) == 1
        assert logs[0].performer_username is None
        assert logs[0].performer_email is None

    def test_map_logs_handles_missing_account(self, field_mapper, sample_splunk_result):
        """Test that map_logs handles missing account."""
        sample_splunk_result["account"] = None

        logs = field_mapper.map_logs([sample_splunk_result])

        assert len(logs) == 1
        assert logs[0].account_username is None
        assert logs[0].account_email is None

    def test_map_logs_batch_lookups_users(self, field_mapper):
        """Test that map_logs uses batch user lookups."""
        results = [
            {"kind": "push_repo", "account": "user1", "performer": "user2"},
            {"kind": "pull_repo", "account": "user1", "performer": "user1"},
        ]

        logs = field_mapper.map_logs(results)

        assert len(logs) == 2


class TestSplunkLogMapperGetKindId:
    """Tests for _get_kind_id method."""

    def test_get_kind_id_valid_kind(self, field_mapper):
        """Test that _get_kind_id returns correct ID for valid kind."""
        kind_id = field_mapper._get_kind_id("push_repo")
        assert kind_id == 1

    def test_get_kind_id_unknown_kind_returns_zero(self, field_mapper):
        """Test that _get_kind_id returns 0 for unknown kind."""
        kind_id = field_mapper._get_kind_id("unknown_kind")
        assert kind_id == 0

    def test_get_kind_id_caches_kind_map(self, field_mapper, mock_model):
        """Test that _get_kind_id caches the kind map."""
        field_mapper._get_kind_id("push_repo")
        field_mapper._get_kind_id("pull_repo")

        mock_model.log.get_log_entry_kinds.assert_called_once()


class TestSplunkLogMapperParseDatetime:
    """Tests for _parse_datetime method."""

    def test_parse_datetime_iso_format(self, field_mapper):
        """Test parsing ISO format datetime string."""
        dt = field_mapper._parse_datetime("2024-01-15T10:30:00Z")

        assert isinstance(dt, datetime)
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_datetime_with_timezone(self, field_mapper):
        """Test parsing datetime with timezone."""
        dt = field_mapper._parse_datetime("2024-01-15T10:30:00+05:30")

        assert isinstance(dt, datetime)
        assert dt.year == 2024

    def test_parse_datetime_already_datetime(self, field_mapper):
        """Test that _parse_datetime returns datetime objects as-is."""
        original = datetime(2024, 1, 15, 10, 30)
        dt = field_mapper._parse_datetime(original)

        assert dt == original

    def test_parse_datetime_none_returns_none(self, field_mapper):
        """Test that _parse_datetime returns None for None input."""
        dt = field_mapper._parse_datetime(None)
        assert dt is None

    def test_parse_datetime_invalid_returns_none(self, field_mapper):
        """Test that _parse_datetime returns None for invalid input."""
        dt = field_mapper._parse_datetime("not a date")
        assert dt is None


class TestSplunkLogMapperParseMetadata:
    """Tests for _parse_metadata method."""

    def test_parse_metadata_dict_input(self, field_mapper):
        """Test parsing dict metadata."""
        metadata = {"key": "value", "count": 42}
        result = field_mapper._parse_metadata(metadata)

        assert result == metadata

    def test_parse_metadata_json_string(self, field_mapper):
        """Test parsing JSON string metadata."""
        metadata_str = '{"key": "value", "count": 42}'
        result = field_mapper._parse_metadata(metadata_str)

        assert result == {"key": "value", "count": 42}

    def test_parse_metadata_none_returns_empty_dict(self, field_mapper):
        """Test that _parse_metadata returns empty dict for None."""
        result = field_mapper._parse_metadata(None)
        assert result == {}

    def test_parse_metadata_invalid_json_returns_empty_dict(self, field_mapper):
        """Test that _parse_metadata returns empty dict for invalid JSON."""
        result = field_mapper._parse_metadata("not valid json")
        assert result == {}

    def test_parse_metadata_non_dict_json_returns_empty_dict(self, field_mapper):
        """Test that _parse_metadata returns empty dict for non-dict JSON."""
        result = field_mapper._parse_metadata("[1, 2, 3]")
        assert result == {}


class TestSplunkLogMapperBatchLookupUsers:
    """Tests for _batch_lookup_users method."""

    def test_batch_user_lookup(self, field_mapper):
        """Test that _batch_lookup_users returns user mapping."""
        result = field_mapper._batch_lookup_users(["user1", "user2"])

        assert "user1" in result
        assert "user2" in result
        assert result["user1"].username == "user1"
        assert result["user2"].username == "user2"

    def test_batch_user_lookup_handles_missing_user(self, field_mapper):
        """Test that _batch_lookup_users handles missing users."""
        result = field_mapper._batch_lookup_users(["user1", "nonexistent"])

        assert "user1" in result
        assert "nonexistent" in result
        assert result["user1"] is not None
        assert result["nonexistent"] is None

    def test_batch_user_lookup_empty_list(self, field_mapper):
        """Test that _batch_lookup_users handles empty list."""
        result = field_mapper._batch_lookup_users([])
        assert result == {}

    def test_batch_user_lookup_falls_back_on_exception(self, field_mapper, mock_model):
        """Test that _batch_lookup_users returns None values when query raises."""
        mock_model.user.get_namespace_users_by_usernames = Mock(side_effect=Exception("db error"))

        result = field_mapper._batch_lookup_users(["user1", "user2"])

        assert result == {"user1": None, "user2": None}


class TestSplunkLogMapperHandlesDeletedUser:
    """Tests for handling deleted users."""

    def test_handles_deleted_performer(self, field_mapper, sample_splunk_result):
        """Test that mapper handles deleted performer gracefully.

        When a performer user has been deleted, we preserve the username from the
        log for audit purposes, but email/robot fields will be None.
        """
        sample_splunk_result["performer"] = "deleted_user"

        logs = field_mapper.map_logs([sample_splunk_result])

        assert len(logs) == 1
        assert logs[0].performer_username == "deleted_user"
        assert logs[0].performer_email is None
        assert logs[0].performer_robot is None

    def test_handles_deleted_account(self, field_mapper, sample_splunk_result):
        """Test that mapper handles deleted account gracefully.

        When an account user has been deleted, we preserve the username from the
        log for audit purposes, but email/organization/robot fields will be None.
        """
        sample_splunk_result["account"] = "deleted_user"

        logs = field_mapper.map_logs([sample_splunk_result])

        assert len(logs) == 1
        assert logs[0].account_username == "deleted_user"
        assert logs[0].account_email is None
        assert logs[0].account_organization is None
