from unittest.mock import MagicMock

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
