import os
import tempfile

import pytest
from filelock import FileLock

# Fixed paths for golden database - shared across all workers
GOLDEN_DB_DIR = os.path.join(tempfile.gettempdir(), "quay_test_golden_db")
GOLDEN_DB_PATH = os.path.join(GOLDEN_DB_DIR, "golden.db")
GOLDEN_DB_LOCK = os.path.join(GOLDEN_DB_DIR, "golden.lock")
GOLDEN_DB_READY = os.path.join(GOLDEN_DB_DIR, "golden.ready")


def pytest_configure(config):
    """
    Create golden DB on controller BEFORE workers spawn.

    This runs before test collection and before xdist spawns worker processes.
    By creating the DB here, all workers will find it when they import testconfig.py.
    """
    worker_id = getattr(config, "workerinput", {}).get("workerid", None)
    if worker_id is None:  # Only on controller/master
        _create_golden_db_if_needed()


def _create_golden_db_if_needed():
    """Create a fresh golden database for this test run."""
    os.makedirs(GOLDEN_DB_DIR, exist_ok=True)

    with FileLock(GOLDEN_DB_LOCK, timeout=300):
        # Always start fresh - remove any existing golden DB
        for f in [GOLDEN_DB_READY, GOLDEN_DB_PATH]:
            if os.path.exists(f):
                os.remove(f)

        # Create golden DB - import inside function to control timing
        os.environ.setdefault("TEST", "1")

        from peewee import SqliteDatabase

        from app import app as application
        from data.database import close_db_filter, db
        from initdb import initialize_database, populate_database

        # Configure and initialize DB
        sqlitedb = f"sqlite:///{GOLDEN_DB_PATH}"
        conf = {
            "TESTING": True,
            "DEBUG": True,
            "SECRET_KEY": "superdupersecret!!!1",
            "DATABASE_SECRET_KEY": "anothercrazykey!",
            "DB_URI": sqlitedb,
        }
        os.environ["DB_URI"] = sqlitedb
        db.initialize(SqliteDatabase(GOLDEN_DB_PATH))
        application.config.update(conf)

        initialize_database()
        db.obj.execute_sql("PRAGMA foreign_keys = ON;")
        db.obj.execute_sql('PRAGMA encoding="UTF-8";')
        populate_database()

        close_db_filter(None)

        # Mark as ready
        with open(GOLDEN_DB_READY, "w") as f:
            f.write(GOLDEN_DB_PATH)


def pytest_collection_modifyitems(config, items):
    """
    Modifies collected test items:
    1. Marks legacy unittest-style tests with 'legacy' marker for separate sequential runs
    2. Adds shard markers for CI parallelization

    Legacy tests have SQLite locking issues when run in parallel with xdist.
    They are marked with 'legacy' so they can be run separately with -n 0.

    Usage:
    $ py.test -m "not legacy"  # Run modern tests (can use -n auto)
    $ py.test -m legacy -n 0   # Run legacy tests sequentially

    Sharding usage:
    $ py.test -m shard_1_of_3
    $ py.test -m shard_2_of_3
    $ py.test -m shard_3_of_3

    This code was originally adopted from the MIT-licensed ansible/molecule@9e7b79b:
    Copyright (c) 2015-2018 Cisco Systems, Inc.
    Copyright (c) 2018 Red Hat, Inc.
    """
    # Mark legacy unittest-style tests that have SQLite locking issues with xdist
    legacy_files = {
        "test_v1_endpoint_security.py",
        "test_v2_endpoint_security.py",
        "test_endpoints.py",
        "test_api_usage.py",
        "test_ldap.py",
        "test_keystone_auth.py",
        "test_external_jwt_authn.py",
        "test_external_oidc.py",
        "test_registry_jwt.py",
    }

    for item in items:
        if item.fspath.basename in legacy_files:
            item.add_marker(pytest.mark.legacy)

    # Handle sharding for CI parallelization
    mark_opt = config.getoption("-m")
    if not mark_opt.startswith("shard_"):
        return

    desired_shard, _, total_shards = mark_opt[len("shard_") :].partition("_of_")
    if not total_shards or not desired_shard:
        return

    desired_shard = int(desired_shard)
    total_shards = int(total_shards)

    if not 0 < desired_shard <= total_shards:
        raise ValueError("desired_shard must be greater than 0 and not bigger than total_shards")

    for test_counter, item in enumerate(items):
        shard = test_counter % total_shards + 1
        marker = getattr(pytest.mark, "shard_{}_of_{}".format(shard, total_shards))
        item.add_marker(marker)

    print("Running sharded test group #{} out of {}".format(desired_shard, total_shards))
