"""
Unit tests for health.services storage check logic.

Tests target _check_storage_engines, which contains the core logic and accepts the
storage object explicitly — making it testable without the full Quay app import chain.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Stub out every module that health.services pulls in transitively before importing it.
_STUBS = [
    "app",
    "flask_login",
    "flask_principal",
    "flask_mail",
    "psutil",
    "resumablesha256",
    "data.database",
    "data.model",
    "data.model.health",
    "health.models_pre_oci",
]
for _mod in _STUBS:
    sys.modules.setdefault(_mod, MagicMock())

# health.services uses `from app import ... storage` and
# `from health.models_pre_oci import pre_oci_model as model`
_app_stub = MagicMock()
_app_stub.storage = MagicMock()
sys.modules["app"] = _app_stub

_models_stub = MagicMock()
sys.modules["health.models_pre_oci"] = _models_stub

from health.services import _check_storage_engines  # noqa: E402


def _make_storage(locations, preferred_locations):
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
    mock_storage = _make_storage(locations, preferred)

    def validate_side_effect(locs, client):
        if locs[0] in failing:
            raise Exception("unavailable")

    mock_storage.validate.side_effect = validate_side_effect

    ok, msg = _check_storage_engines(mock_storage, _HTTP_CLIENT)

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
    mock_storage = _make_storage(["s3", "azure"], ["s3"])

    def validate_side_effect(locs, client):
        if locs[0] == "azure":
            raise Exception("connection refused")

    mock_storage.validate.side_effect = validate_side_effect

    ok, msg = _check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert ok is True
    assert "azure" in msg


def test_failure_message_includes_warning_info_when_both_fail():
    """When preferred and non-preferred both fail, the failure message embeds warnings."""
    mock_storage = _make_storage(["s3", "azure"], ["s3"])
    mock_storage.validate.side_effect = Exception("unavailable")

    ok, msg = _check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert ok is False
    assert "warnings" in msg
    assert "azure" in msg


def test_all_locations_are_checked():
    """validate is called once per configured location."""
    mock_storage = _make_storage(["s3", "azure", "gcs"], ["s3"])
    mock_storage.validate.return_value = None

    _check_storage_engines(mock_storage, _HTTP_CLIENT)

    assert mock_storage.validate.call_count == 3
