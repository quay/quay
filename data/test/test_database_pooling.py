from unittest.mock import MagicMock, patch

import pytest
from peewee import OperationalError
from playhouse.pool import MaxConnectionsExceeded, PooledSqliteDatabase

from data.database import ObservablePooledDatabase


# Create a concrete test database class combining the mixin with SQLite
class _TestPooledDB(ObservablePooledDatabase, PooledSqliteDatabase):
    """Test database class for unit testing pool pre-ping functionality."""

    pass


class TestObservablePooledDatabase:
    """Tests for connection pool pre-ping functionality."""

    def test_connect_does_not_probe_connection(self):
        """
        Peewee is responsible for the connection liveness so we just need to verify here
        that our override does not run its own query.
        """
        # Create a concrete instance with in-memory SQLite
        db = _TestPooledDB(":memory:")

        # Mock the parent _connect to return a mock connection
        mock_conn = MagicMock()

        # Mock parent's _connect to return our mock connection
        with patch.object(PooledSqliteDatabase, "_connect", return_value=mock_conn):
            # Call _connect to initialize the connection
            result = db._connect()

            # Verify the same connection is returned (not closed)
            assert result == mock_conn
            mock_conn.close.assert_not_called()
            mock_conn.cursor.assert_not_called()

    def test_connect_handles_pool_exhaustion_with_backoff(self):
        """Test that MaxConnectionsExceeded triggers exponential backoff retry."""
        db = _TestPooledDB(":memory:")

        # Mock fresh connection that passes liveness check
        fresh_conn = MagicMock()

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

    def test_connect_raises_after_max_retries(self):
        """
        Verifies that _connect raises an exception if the max number of retries has been
        reached. This happens when the pool is permanently exhausted.
        """
        db = _TestPooledDB("::memory::")

        with patch.object(
            PooledSqliteDatabase, "_connect", side_effect=MaxConnectionsExceeded("Pool exhausted")
        ):
            with patch("data.database.time.sleep") as mock_sleep:
                with pytest.raises(OperationalError, match="Unable to obtain"):
                    db._connect()

        assert mock_sleep.call_count == 7
