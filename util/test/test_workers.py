from mock import patch

import pytest

from util.workers import get_worker_count


@pytest.mark.parametrize(
    "kind_name,env_vars,cpu_affinity,multiplier,minimum,maximum,expected",
    [
        # No override and CPU affinity * multiplier is between min and max => cpu affinity * multiplier.
        ("registry", {}, [0, 1], 10, 8, 64, 20),
        # No override and CPU affinity * multiplier is below min => min.
        ("registry", {}, [0], 1, 8, 64, 8),
        # No override and CPU affinity * multiplier is above max => max.
        ("registry", {}, [0, 1, 2, 3], 20, 8, 64, 64),
        # Override based on specific env var.
        (
            "registry",
            {
                "WORKER_COUNT_REGISTRY": 12,
            },
            [0, 1],
            10,
            8,
            64,
            12,
        ),
        # Override based on specific env var (ignores maximum).
        (
            "registry",
            {
                "WORKER_COUNT_REGISTRY": 120,
            },
            [0, 1],
            10,
            8,
            64,
            120,
        ),
        # Override based on specific env var (respects minimum).
        (
            "registry",
            {
                "WORKER_COUNT_REGISTRY": 1,
            },
            [0, 1],
            10,
            8,
            64,
            8,
        ),
        # Override based on generic env var.
        (
            "registry",
            {
                "WORKER_COUNT": 12,
            },
            [0, 1],
            10,
            8,
            64,
            12,
        ),
        # Override based on generic env var (ignores maximum).
        (
            "registry",
            {
                "WORKER_COUNT": 120,
            },
            [0, 1],
            10,
            8,
            64,
            120,
        ),
        # Override based on generic env var (respects minimum).
        (
            "registry",
            {
                "WORKER_COUNT": 1,
            },
            [0, 1],
            10,
            8,
            64,
            8,
        ),
        # Override always uses specific first.
        (
            "registry",
            {
                "WORKER_COUNT_REGISTRY": 120,
                "WORKER_COUNT": 12,
            },
            [0, 1],
            10,
            8,
            64,
            120,
        ),
    ],
)
def test_get_worker_count(
    kind_name, env_vars, cpu_affinity, multiplier, minimum, maximum, expected
):
    class FakeProcess(object):
        def __init__(self, pid):
            pass

        def cpu_affinity(self):
            return cpu_affinity

    with patch("os.environ.get", env_vars.get):
        with patch("psutil.Process", FakeProcess):
            assert get_worker_count(kind_name, multiplier, minimum, maximum) == expected
