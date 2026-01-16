"""Tests for APSW SQLite database configuration.

These tests verify that APSW SQLite databases are correctly configured with
appropriate settings using peewee's playhouse.apsw_ext module.

APSW (Another Python SQLite Wrapper) provides thread-safe connections,
which helps prevent "database is locked" errors in concurrent environments.
"""

import os
import tempfile
import threading

import pytest

from data.database import _db_from_url


class TestAPSWSqliteConfiguration:
    """Tests for APSW SQLite configuration."""

    def test_pragma_applied_on_new_connection(self):
        """PRAGMA statements should be applied when a new connection is established."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = _db_from_url(f"sqlite:///{db_path}", {})
            db.connect()

            # Verify PRAGMA settings were applied
            # Note: APSW uses setbusytimeout() which sets the same underlying
            # SQLite setting as PRAGMA busy_timeout
            result = db.execute_sql("PRAGMA busy_timeout;")
            busy_timeout = result.fetchone()[0]
            assert busy_timeout == 10000  # 10 seconds in ms

            result = db.execute_sql("PRAGMA journal_mode;")
            journal_mode = result.fetchone()[0]
            assert journal_mode.lower() == "wal"

            result = db.execute_sql("PRAGMA synchronous;")
            synchronous = result.fetchone()[0]
            # NORMAL = 1
            assert synchronous == 1

            db.close()
        finally:
            # WAL mode creates additional files
            for ext in ["", "-wal", "-shm"]:
                try:
                    os.unlink(db_path + ext)
                except FileNotFoundError:
                    pass

    def test_pragma_not_applied_on_reused_connection(self):
        """PRAGMA statements should NOT be re-applied when reusing existing connection."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = _db_from_url(f"sqlite:///{db_path}", {})
            db.connect()  # First connection - settings applied

            # When reusing connection, connect() returns False and no settings re-applied
            result = db.connect(reuse_if_open=True)
            assert result is False, "connect(reuse_if_open=True) should return False"

            # Connection should still be open and functional
            assert not db.is_closed()

            # Verify settings are still in effect
            result = db.execute_sql("PRAGMA busy_timeout;")
            busy_timeout = result.fetchone()[0]
            assert busy_timeout == 10000

            db.close()
        finally:
            for ext in ["", "-wal", "-shm"]:
                try:
                    os.unlink(db_path + ext)
                except FileNotFoundError:
                    pass

    def test_connection_can_be_reestablished(self):
        """After closing, a new connection should have settings applied again."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = _db_from_url(f"sqlite:///{db_path}", {})

            # First connection
            db.connect()
            result = db.execute_sql("PRAGMA journal_mode;")
            assert result.fetchone()[0].lower() == "wal"
            db.close()

            # Second connection - settings should be applied again
            db.connect()
            result = db.execute_sql("PRAGMA journal_mode;")
            assert result.fetchone()[0].lower() == "wal"

            result = db.execute_sql("PRAGMA busy_timeout;")
            assert result.fetchone()[0] == 10000

            db.close()
        finally:
            for ext in ["", "-wal", "-shm"]:
                try:
                    os.unlink(db_path + ext)
                except FileNotFoundError:
                    pass

    def test_db_kwargs_preserved(self):
        """User-provided db_kwargs should be preserved alongside default settings."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            # Pass custom pragmas that should be merged
            custom_kwargs = {"pragmas": {"cache_size": -64000}}
            db = _db_from_url(f"sqlite:///{db_path}", custom_kwargs)
            db.connect()

            # Our default settings should be applied
            result = db.execute_sql("PRAGMA busy_timeout;")
            assert result.fetchone()[0] == 10000

            # User's custom PRAGMA should also be applied
            result = db.execute_sql("PRAGMA cache_size;")
            cache_size = result.fetchone()[0]
            assert cache_size == -64000

            db.close()
        finally:
            for ext in ["", "-wal", "-shm"]:
                try:
                    os.unlink(db_path + ext)
                except FileNotFoundError:
                    pass

    def test_concurrent_access_thread_safe(self):
        """APSW should handle concurrent access without locking errors."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        errors = []

        try:
            db = _db_from_url(f"sqlite:///{db_path}", {})
            db.connect()

            # Create a test table
            db.execute_sql("CREATE TABLE test_concurrent (id INTEGER PRIMARY KEY, val TEXT)")

            def writer_thread(thread_id, iterations):
                try:
                    for i in range(iterations):
                        db.execute_sql(
                            "INSERT INTO test_concurrent (val) VALUES (?)",
                            (f"thread_{thread_id}_iter_{i}",),
                        )
                except Exception as e:
                    errors.append((thread_id, str(e)))

            # Launch multiple concurrent writers
            threads = []
            for tid in range(5):
                t = threading.Thread(target=writer_thread, args=(tid, 20))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Verify no errors occurred
            assert len(errors) == 0, f"Concurrent write errors: {errors}"

            # Verify all rows were inserted
            result = db.execute_sql("SELECT COUNT(*) FROM test_concurrent")
            count = result.fetchone()[0]
            assert count == 100  # 5 threads * 20 iterations

            db.close()
        finally:
            for ext in ["", "-wal", "-shm"]:
                try:
                    os.unlink(db_path + ext)
                except FileNotFoundError:
                    pass
