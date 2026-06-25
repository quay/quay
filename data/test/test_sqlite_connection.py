"""Tests for SQLite PRAGMA configuration.

These tests verify that SQLite databases are correctly configured with
PRAGMA statements using peewee's built-in mechanism.
"""

import os
import tempfile

import pytest

from data.database import _db_from_url


class TestSqlitePragmaConfiguration:
    """Tests for SQLite PRAGMA statement configuration."""

    def test_pragma_applied_on_new_connection(self):
        """PRAGMA statements should be applied when a new connection is established."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = _db_from_url(f"sqlite:///{db_path}", {})
            db.connect()

            # Verify PRAGMA settings were applied by querying them
            result = db.execute_sql("PRAGMA busy_timeout;")
            busy_timeout = result.fetchone()[0]
            assert busy_timeout == 10000

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
            db.connect()  # First connection - PRAGMAs applied by peewee

            # When reusing connection, connect() returns False and no PRAGMAs are re-applied
            result = db.connect(reuse_if_open=True)
            assert result is False, "connect(reuse_if_open=True) should return False"

            # Connection should still be open and functional
            assert not db.is_closed()

            # Verify PRAGMAs are still in effect
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
        """After closing, a new connection should have PRAGMAs applied again."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = _db_from_url(f"sqlite:///{db_path}", {})

            # First connection
            db.connect()
            result = db.execute_sql("PRAGMA journal_mode;")
            assert result.fetchone()[0].lower() == "wal"
            db.close()

            # Second connection - PRAGMAs should be applied again
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
        """User-provided db_kwargs should be preserved alongside PRAGMA settings."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            # Pass custom pragmas that should be merged
            custom_kwargs = {"pragmas": {"cache_size": -64000}}
            db = _db_from_url(f"sqlite:///{db_path}", custom_kwargs)
            db.connect()

            # Our default PRAGMAs should be applied
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
