from unittest.mock import MagicMock, patch

import pytest

from endpoints.api.superuser_models_interface import BuildTrigger


@pytest.mark.parametrize(
    "trigger,expected",
    [
        (None, None),
        (MagicMock(uuid=None), None),
        (MagicMock(uuid=""), None),
    ],
)
def test_build_trigger_to_dict_returns_none_without_trigger(trigger, expected):
    """to_dict() must return None when trigger is absent or has no UUID."""
    bt = BuildTrigger(
        trigger=trigger,
        pull_robot=None,
        can_read=False,
        can_admin=False,
        for_build=True,
    )
    assert bt.to_dict() is expected


@patch("endpoints.api.superuser_models_interface.BuildTriggerHandler")
def test_build_trigger_to_dict_returns_dict_with_valid_trigger(mock_handler_cls):
    trigger = MagicMock(uuid="abc-123", service=MagicMock(name="github"))
    handler = MagicMock()
    handler.config = {"build_source": "https://github.com/org/repo"}
    handler.is_active.return_value = True
    handler.get_repository_url.return_value = "https://github.com/org/repo"
    mock_handler_cls.get_handler.return_value = handler

    bt = BuildTrigger(
        trigger=trigger,
        pull_robot=None,
        can_read=True,
        can_admin=False,
        for_build=True,
    )
    result = bt.to_dict()

    assert result is not None
    assert result["id"] == "abc-123"
    assert result["service"] == "github"
    assert result["is_active"] is True
    assert result["build_source"] == "https://github.com/org/repo"
    assert result["can_invoke"] is False
