from unittest.mock import MagicMock, Mock, patch

import pytest
from peewee import InterfaceError, OperationalError, SqliteDatabase
from playhouse.pool import MaxConnectionsExceeded, PooledSqliteDatabase

from data.database import ObservablePooledDatabase


# Create a concrete test database class combining the mixin with SQLite
class _TestPooledDB(ObservablePooledDatabase, PooledSqliteDatabase):
    """Test database class for unit testing pool pre-ping functionality."""

    pass


class TestObservablePooledDatabase:
    """Tests for connection pool pre-ping functionality."""

    def test_connect_reuses_healthy_connection(self):
        """Test that a healthy connection from the pool is reused."""
        # Create a concrete instance with in-memory SQLite
        db = _TestPooledDB(":memory:")

        # Mock the parent _connect to return a mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # Mock parent's _connect to return our mock connection
        with patch.object(PooledSqliteDatabase, "_connect", return_value=mock_conn):
            # Call _connect which should perform the liveness check
            result = db._connect()

            # Verify SELECT 1 was executed (liveness check)
            mock_cursor.execute.assert_called_once_with("SELECT 1")

            # Verify the same connection is returned (not closed)
            assert result == mock_conn
            mock_conn.close.assert_not_called()

    def test_connect_discards_stale_connection(self):
        """Test that a stale connection is discarded and a new one is created."""
        db = _TestPooledDB(":memory:")

        # Mock stale connection that fails liveness check
        stale_conn = MagicMock()
        stale_cursor = MagicMock()
        stale_cursor.execute.side_effect = OperationalError("connection lost")
        stale_conn.cursor.return_value.__enter__ = Mock(return_value=stale_cursor)
        stale_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # Mock fresh connection that passes liveness check
        fresh_conn = MagicMock()
        fresh_cursor = MagicMock()
        fresh_conn.cursor.return_value.__enter__ = Mock(return_value=fresh_cursor)
        fresh_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # First call returns stale connection, second (recursive) call returns fresh connection
        with patch.object(PooledSqliteDatabase, "_connect", side_effect=[stale_conn, fresh_conn]):
            # Execute the _connect method
            result = db._connect()

            # Verify SELECT 1 was attempted on stale connection
            stale_cursor.execute.assert_called_once_with("SELECT 1")

            # Verify SELECT 1 was also attempted on fresh connection (and succeeded)
            fresh_cursor.execute.assert_called_once_with("SELECT 1")

            # Verify fresh connection is returned
            assert result == fresh_conn

    def test_connect_handles_interface_error(self):
        """Test that InterfaceError during liveness check triggers new connection."""
        db = _TestPooledDB(":memory:")

        # Mock stale connection that fails with InterfaceError
        stale_conn = MagicMock()
        stale_cursor = MagicMock()
        stale_cursor.execute.side_effect = InterfaceError("interface error")
        stale_conn.cursor.return_value.__enter__ = Mock(return_value=stale_cursor)
        stale_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # Mock fresh connection that passes liveness check
        fresh_conn = MagicMock()
        fresh_cursor = MagicMock()
        fresh_conn.cursor.return_value.__enter__ = Mock(return_value=fresh_cursor)
        fresh_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # First call returns stale connection, second (recursive) call returns fresh connection
        with patch.object(PooledSqliteDatabase, "_connect", side_effect=[stale_conn, fresh_conn]):
            result = db._connect()

            # Verify SELECT 1 was attempted on stale connection
            stale_cursor.execute.assert_called_once_with("SELECT 1")

            # Verify fresh connection is returned
            assert result == fresh_conn

    def test_connect_handles_close_exception(self):
        """Test that exceptions during connection.close() are handled gracefully."""
        db = _TestPooledDB(":memory:")

        # Mock stale connection that fails liveness check
        stale_conn = MagicMock()
        stale_cursor = MagicMock()
        stale_cursor.execute.side_effect = OperationalError("connection lost")
        stale_conn.cursor.return_value.__enter__ = Mock(return_value=stale_cursor)
        stale_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # Mock fresh connection that passes liveness check
        fresh_conn = MagicMock()
        fresh_cursor = MagicMock()
        fresh_conn.cursor.return_value.__enter__ = Mock(return_value=fresh_cursor)
        fresh_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # First call returns stale connection, second (recursive) call returns fresh connection
        with patch.object(PooledSqliteDatabase, "_connect", side_effect=[stale_conn, fresh_conn]):
            # Make _close raise an exception to test error handling
            with patch.object(
                PooledSqliteDatabase, "_close", side_effect=Exception("close failed")
            ):
                # Should not raise despite close() failing
                result = db._connect()

                # Should still create and return fresh connection
                assert result == fresh_conn

    def test_connect_handles_pool_exhaustion_with_backoff(self):
        """Test that MaxConnectionsExceeded triggers exponential backoff retry."""
        db = _TestPooledDB(":memory:")

        # Mock fresh connection that passes liveness check
        fresh_conn = MagicMock()
        fresh_cursor = MagicMock()
        fresh_conn.cursor.return_value.__enter__ = Mock(return_value=fresh_cursor)
        fresh_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # First two calls raise MaxConnectionsExceeded, third succeeds
        with patch.object(
            PooledSqliteDatabase,
            "_connect",
            side_effect=[
                MaxConnectionsExceeded("Pool exhausted"),
                MaxConnectionsExceeded("Pool exhausted"),
                fresh_conn,
            ],
        ):
            # Mock time.sleep to verify backoff is happening
            with patch("data.database.time.sleep") as mock_sleep:
                result = db._connect()

                # Verify sleep was called for backoff (2 times for 2 failures)
                assert mock_sleep.call_count == 2

                # Verify delays are increasing (exponential backoff)
                calls = mock_sleep.call_args_list
                delay1 = calls[0][0][0]
                delay2 = calls[1][0][0]
                assert delay2 > delay1  # Second delay should be longer

                # Verify fresh connection is eventually returned
                assert result == fresh_conn
