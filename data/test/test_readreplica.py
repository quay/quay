import logging
import os
import shutil
from unittest.mock import MagicMock

import pytest
from peewee import OperationalError

from data.database import User, configure, db_disallow_replica_use, read_only_config
from data.readreplica import AutomaticFailoverWrapper, ReadOnlyModeException
from test.fixtures import *
from test.testconfig import FakeTransaction


@pytest.mark.skipif(bool(os.environ.get("TEST_DATABASE_URI")), reason="Testing requires SQLite")
def test_readreplica(init_db_path, tmpdir_factory):
    primary_file = str(tmpdir_factory.mktemp("data").join("primary.db"))
    replica_file = str(tmpdir_factory.mktemp("data").join("replica.db"))

    # Copy the initialized database to two different locations.
    shutil.copy2(init_db_path, primary_file)
    shutil.copy2(init_db_path, replica_file)

    db_config = {
        "DB_URI": "sqlite:///{0}".format(primary_file),
        "DB_READ_REPLICAS": [
            {"DB_URI": "sqlite:///{0}".format(replica_file)},
        ],
        "DB_CONNECTION_ARGS": {
            "threadlocals": True,
            "autorollback": True,
        },
        "DB_TRANSACTION_FACTORY": lambda x: FakeTransaction(),
        "FOR_TESTING": True,
        "DATABASE_SECRET_KEY": "QUAY_FIXTURE_ONLY-anothercrazykey!",
    }

    # Initialize the DB with the primary and the replica.
    configure(db_config)
    assert not read_only_config.obj.is_readonly
    assert read_only_config.obj.read_replicas

    # Ensure we can read the data.
    devtable_user = User.get(username="devtable")
    assert devtable_user.username == "devtable"

    # Configure with a bad primary. Reading should still work since we're hitting the replica.
    db_config["DB_URI"] = "sqlite:///does/not/exist"
    configure(db_config)

    assert not read_only_config.obj.is_readonly
    assert read_only_config.obj.read_replicas

    devtable_user = User.get(username="devtable", can_use_read_replica=True)
    assert devtable_user.username == "devtable"

    # Force us to hit the master and ensure it doesn't work.
    with db_disallow_replica_use():
        with pytest.raises(OperationalError):
            User.get(username="devtable")

    # Explicitly disallow replica use and ensure it doesn't work.
    with pytest.raises(OperationalError):
        User.get(username="devtable", can_use_read_replica=False)

    # Default to hitting the master and ensure it doesn't work.
    with pytest.raises(OperationalError):
        User.get(username="devtable")

    # Test read replica again.
    devtable_user = User.get(username="devtable", can_use_read_replica=True)
    assert devtable_user.username == "devtable"

    # Try to change some data. This should fail because the primary is broken.
    with pytest.raises(OperationalError):
        devtable_user.email = "newlychanged"
        devtable_user.save()

    # Fix the primary and try again.
    db_config["DB_URI"] = "sqlite:///{0}".format(primary_file)
    configure(db_config)

    assert not read_only_config.obj.is_readonly
    assert read_only_config.obj.read_replicas

    devtable_user.email = "newlychanged"
    devtable_user.save()

    # Mark the system as readonly.
    db_config["DB_URI"] = "sqlite:///{0}".format(primary_file)
    db_config["REGISTRY_STATE"] = "readonly"
    configure(db_config)

    assert read_only_config.obj.is_readonly
    assert read_only_config.obj.read_replicas

    # Ensure all write operations raise a readonly mode exception.
    with pytest.raises(ReadOnlyModeException):
        devtable_user.email = "newlychanged2"
        devtable_user.save()

    with pytest.raises(ReadOnlyModeException):
        User.create(username="foo")

    with pytest.raises(ReadOnlyModeException):
        User.delete().where(User.username == "foo").execute()

    with pytest.raises(ReadOnlyModeException):
        User.update(username="bar").where(User.username == "foo").execute()

    # Reset the config on the DB, so we don't mess up other tests.
    configure(
        {
            "DB_URI": "sqlite:///{0}".format(primary_file),
            "DB_CONNECTION_ARGS": {
                "threadlocals": True,
                "autorollback": True,
            },
            "DB_TRANSACTION_FACTORY": lambda x: FakeTransaction(),
            "DATABASE_SECRET_KEY": "QUAY_FIXTURE_ONLY-anothercrazykey!",
        }
    )


class TestAutomaticFailoverWrapperLogging:
    def _wrapper(self, replica_error=None):
        replica = MagicMock()
        replica.connect_params = {"host": "replica.test", "port": 5001}
        if replica_error is not None:
            replica.execute_sql.side_effect = replica_error
        primary = MagicMock()
        return AutomaticFailoverWrapper(replica, primary), replica, primary

    def test_replica_use_is_logged_at_debug(self, caplog):
        wrapper, replica, primary = self._wrapper()

        with caplog.at_level(logging.DEBUG, logger="data.readreplica"):
            wrapper.execute_sql("SELECT 1", ())

        assert "Using read replica replica.test:5001" in caplog.text
        replica.execute_sql.assert_called_once_with("SELECT 1", ())
        primary.execute_sql.assert_not_called()

    def test_replica_failure_logs_warning_and_falls_back_to_primary(self, caplog):
        wrapper, replica, primary = self._wrapper(OperationalError("replica down"))

        with caplog.at_level(logging.DEBUG, logger="data.readreplica"):
            wrapper.execute_sql("SELECT 1", None)

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "replica.test:5001" in warnings[0].getMessage()
        assert "retrying query on the primary" in warnings[0].getMessage()
        primary.execute_sql.assert_called_once_with("SELECT 1", None)

    def test_query_parameters_are_never_logged(self, caplog):
        wrapper, _, _ = self._wrapper()

        with caplog.at_level(logging.DEBUG, logger="data.readreplica"):
            wrapper.execute_sql("SELECT * FROM user WHERE email = %s", ("secret@example.com",))

        assert "secret@example.com" not in caplog.text

    def test_logged_sql_is_truncated(self, caplog):
        wrapper, _, _ = self._wrapper()

        with caplog.at_level(logging.DEBUG, logger="data.readreplica"):
            wrapper.execute_sql("SELECT " + "x" * 500, ())

        assert "x" * 200 not in caplog.text
