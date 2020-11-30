import os
import shutil

import pytest

from peewee import OperationalError

from data.database import configure, User, read_only_config, db_disallow_replica_use
from data.readreplica import ReadOnlyModeException
from test.testconfig import FakeTransaction
from test.fixtures import *


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
        "DATABASE_SECRET_KEY": "anothercrazykey!",
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

    devtable_user = User.get(username="devtable")
    assert devtable_user.username == "devtable"

    # Force us to hit the master and ensure it doesn't work.
    with db_disallow_replica_use():
        with pytest.raises(OperationalError):
            User.get(username="devtable")

    # Test read replica again.
    devtable_user = User.get(username="devtable")
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
            "DATABASE_SECRET_KEY": "anothercrazykey!",
        }
    )
