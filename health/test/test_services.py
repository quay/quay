import mock

import pytest

from health.services import _check_zombie_process_count
from test.fixtures import *
from test.testconfig import TestConfig


@mock.patch("health.services.get_all_zombies")
def test_check_zombie_process_count(mock_get_all_zombies, app):
    """
    Verifies the correct status is returned given a quantity of Zombies.
    """
    mock_get_all_zombies.return_value = ["p1", "p2"]

    # Verify default threshold
    app.config.from_object(TestConfig())  # Includes the default for MAX_DEFUNCT_PROCESS_COUNT
    assert _check_zombie_process_count(app) == (False, "Found 2 zombie processes.")

    # Too many zombies
    app.config["MAX_DEFUNCT_PROCESS_COUNT"] = 0
    assert _check_zombie_process_count(app) == (False, "Found 2 zombie processes.")

    # Quantity of zombies within threshold
    app.config["MAX_DEFUNCT_PROCESS_COUNT"] = 3
    assert _check_zombie_process_count(app) == (True, "Found 2 zombie processes.")
