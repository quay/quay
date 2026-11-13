from unittest.mock import MagicMock

import pytest
from peewee import DatabaseError, OperationalError

from data.database import db
from data.model.health import check_health, sql_timeout
from test.fixtures import *


def _mock_database():
    """
    Create a mocked database for tests.
    """
    database = MagicMock()
    return database


def test_sql_timeout_postgres_uses_set_config():
    """
    Verifies that the sql_timeout limit is executed properly with the correct
    parameters.
    """
    database = _mock_database()
    with sql_timeout({"DB_URI": "postgresql://u@h/db"}, database, 5000) as yielded:
        assert yielded is database
        database.atomic.assert_called_once()

    database.execute_sql.assert_called_once_with(
        "SELECT set_config('statement_timeout', %s, true);", ("5000",)
    )


def test_sql_timeout_postgres_never_uses_bare_set():
    """
    Verifies tghat the sql_timeout never calls bare SET TIMEOUT and instead uses
    the set_config exclusively.
    """
    database = _mock_database()
    with sql_timeout({"DB_URI": "postgresql://u@h/db"}, database, 5000):
        pass

    sql = database.execute_sql.call_args[0][0]
    assert not sql.lstrip().upper().startswith("SET")


def test_sql_timeout_skips_non_postgresql_schemas():
    """
    Verifies that the timeout is not run on database systems that are not PostgreSQL.
    """
    database = _mock_database()

    with sql_timeout({"DB_URI": "sqlite:///tmp.db"}, database, 5000) as yielded:
        assert yielded is database

    database.execute_sql.assert_not_called()
    database.atomic.assert_not_called()


def test_check_health_reports_timeout_failure(monkeypatch):
    """
    Verifies that the health check reports a timeout failure if it's reached.
    """
    # replace validate_database_url with a dummy function
    monkeypatch.setattr("data.model.health.validate_database_url", lambda *a, **k: None)

    def boom(*a, **k):
        raise OperationalError("cancelling statement due to statement timeout")

    monkeypatch.setattr("data.model.health.sql_timeout", boom)

    okay, message = check_health({"DB_URI": "postgresql://u@h/db", "DB_CONNECTION_ARGS": {}})

    # verify result
    assert okay is False
    assert "statement timeout" in message


def test_sql_timeout_postgresql_integration(initialized_db, appconfig):
    """
    Runs only if the real PostgreSQL database is present. The timeout must cancel
    the slow query and must not leak out of the transaction.
    """
    if not appconfig["DB_URI"].startswith("postgresql"):
        pytest.skip("requires a real PostgreSQL backend")

    # record the original statement timeout
    cursor = db.execute_sql("SHOW statement_timeout")
    original_timeout = cursor.fetchone()[0]

    with pytest.raises((OperationalError, DatabaseError)) as excinfo:
        with sql_timeout(appconfig, db, 100):
            db.execute_sql("SELECT pg_sleep(1)")

    # verify that the timeout caused the error to occur
    assert "statement timeout" in str(excinfo.value)

    cursor = db.execute_sql("SHOW statement_timeout")

    # assert that the statement timeout is back to the default value
    assert cursor.fetchone()[0] == original_timeout
