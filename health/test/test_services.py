"""Unit tests for health.storage_engines.check_storage_engines."""

from unittest.mock import MagicMock

import pytest

from health.storage_engines import check_storage_engines


def _make_storage(locations, preferred_locations):
    """Return a mock DistributedStorage with the given location lists."""
    s = MagicMock()
    s.locations = list(locations)
    s.preferred_locations = list(preferred_locations)
    return s


_HTTP_CLIENT = MagicMock()


@pytest.mark.parametrize(
    "locations,preferred,failing,expected_ok,expect_warning",
    [
        pytest.param(["s3", "azure"], ["s3"], [], True, False, id="all-healthy"),
        pytest.param(["s3", "azure"], ["s3"], ["azure"], True, True, id="non-preferred-fails"),
        pytest.param(["s3", "azure"], ["s3"], ["s3"], False, False, id="preferred-fails"),
        pytest.param(["s3", "azure"], ["s3"], ["s3", "azure"], False, True, id="both-fail"),
        pytest.param(["s3"], ["s3"], [], True, False, id="single-preferred-healthy"),
        pytest.param(["s3"], ["s3"], ["s3"], False, False, id="single-preferred-fails"),
    ],
)
def test_check_storage_engines(locations, preferred, failing, expected_ok, expect_warning):
    """Parametrized: verify ok/warning/failure outcomes for all location combinations."""
    mock_storage = _make_storage(locations, preferred)

    def validate_side_effect(locs, client):
        if locs[0] in failing:
            raise Exception("unavailable")

    mock_storage.validate.side_effect = validate_side_effect

    ok, msg = check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert ok == expected_ok

    if expected_ok and expect_warning:
        assert msg is not None
    elif expected_ok:
        assert msg is None
    else:
        assert msg is not None
        for loc in failing:
            if loc in preferred:
                assert loc in msg


def test_warning_includes_failing_location_name():
    """Non-preferred location name must appear in the warning message."""
    mock_storage = _make_storage(["s3", "azure"], ["s3"])

    def validate_side_effect(locs, client):
        if locs[0] == "azure":
            raise Exception("connection refused")

    mock_storage.validate.side_effect = validate_side_effect

    ok, msg = check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert ok is True
    assert "azure" in msg


def test_failure_message_includes_warning_info_when_both_fail():
    """When preferred and non-preferred both fail, the failure message embeds warnings."""
    mock_storage = _make_storage(["s3", "azure"], ["s3"])
    mock_storage.validate.side_effect = Exception("unavailable")

    ok, msg = check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert ok is False
    assert "warnings" in msg
    assert "azure" in msg


def test_all_locations_are_checked():
    """validate is called exactly once per configured location."""
    mock_storage = _make_storage(["s3", "azure", "gcs"], ["s3"])
    mock_storage.validate.return_value = None

    check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert mock_storage.validate.call_count == 3


def test_fail_closed_when_no_preferred_configured():
    """With no preferred locations set, all failures are treated as critical."""
    mock_storage = _make_storage(["s3", "azure"], [])
    mock_storage.validate.side_effect = Exception("unavailable")

    ok, msg = check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert ok is False
    assert "s3" in msg or "azure" in msg
