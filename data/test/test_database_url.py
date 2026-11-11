from contextlib import nullcontext

import pytest

from data.database import _db_from_url


@pytest.mark.parametrize(
    "scheme, expected_context",
    [
        ("postgresql+psycopg2", pytest.raises(ValueError, match="Unsupported database scheme")),
        ("postgresql", nullcontext()),
        ("oracle", pytest.raises(ValueError, match="Unsupported database scheme")),
        ("mysql+pymysql", nullcontext()),
    ],
)
def test_validate_db_schemes(scheme, expected_context):
    """
    Verifies that on unknown or unsupported db schemas we see the ValueError properly
    raised.
    """
    with expected_context:
        _db_from_url(f"{scheme}://user:pass@localhost/db", {})


@pytest.mark.parametrize("is_read_replica", [True, False])
def test_driver_autocommit_option_is_dropped(is_read_replica):
    """
    Verifies that the driver properly drops _driver_autocommit before calling the read replica
    given that Peewee sets it automatically on all connections now.
    """
    db = _db_from_url(
        "postgresql://user:pass@localhost/db",
        {"_driver_autocommit": True},
        is_read_replica=is_read_replica,
    )

    assert "_driver_autocommit" not in db.connect_params
