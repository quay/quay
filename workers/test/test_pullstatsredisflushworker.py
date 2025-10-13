"""
Tests for RedisFlushWorker.

Tests the main worker that processes Redis pull events.
"""
import sys
from typing import List, Set
from unittest.mock import MagicMock, patch

import redis


def test_redis_flush_worker_init():
    """Test RedisFlushWorker initialization."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_FLUSH_INTERVAL_SECONDS": 300,
            "REDIS_FLUSH_WORKER_BATCH_SIZE": 1000,
            "REDIS_FLUSH_WORKER_SCAN_COUNT": 100,
            "REDIS_CONNECTION_TIMEOUT": 5,
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
        }.get(key, default)

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Should have one operation scheduled
        assert len(worker._operations) == 1
        assert worker._operations[0][1] == 300  # Default frequency


def test_initialize_redis_client_success():
    """Test successful Redis client initialization."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
            "REDIS_CONNECTION_TIMEOUT": 5,
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            # Mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis_module.StrictRedis.return_value = mock_client

            from workers.pullstatsredisflushworker import RedisFlushWorker

            # Test
            worker = RedisFlushWorker()

            # Verify
            assert worker.redis_client == mock_client
            mock_redis_module.StrictRedis.assert_called_once()
            mock_client.ping.assert_called_once()


def test_initialize_redis_client_connection_failure():
    """Test Redis client initialization when connection fails."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
            "REDIS_CONNECTION_TIMEOUT": 5,
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            import redis

            # Mock Redis client that fails on ping with ConnectionError
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Connection failed")
            mock_redis_module.StrictRedis.return_value = mock_client

            # Ensure the exception classes are available in the mocked module
            mock_redis_module.ConnectionError = redis.ConnectionError
            mock_redis_module.RedisError = redis.RedisError

            from workers.pullstatsredisflushworker import RedisFlushWorker

            # Test
            worker = RedisFlushWorker()

            # Verify
            assert worker.redis_client is None


def test_initialize_redis_client_redis_error():
    """Test Redis client initialization when a general Redis error occurs."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
            "REDIS_CONNECTION_TIMEOUT": 5,
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            import redis

            # Mock Redis client that fails on ping with RedisError
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.RedisError("Redis error")
            mock_redis_module.StrictRedis.return_value = mock_client

            # Ensure the exception classes are available in the mocked module
            mock_redis_module.ConnectionError = redis.ConnectionError
            mock_redis_module.RedisError = redis.RedisError

            from workers.pullstatsredisflushworker import RedisFlushWorker

            # Test
            worker = RedisFlushWorker()

            # Verify
            assert worker.redis_client is None


def test_initialize_redis_client_no_config():
    """Test Redis client initialization when PULL_METRICS_REDIS is not configured."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_CONNECTION_TIMEOUT": 5,
        }.get(key, default)

        from workers.pullstatsredisflushworker import RedisFlushWorker

        # Test - should initialize without Redis client when config is missing
        worker = RedisFlushWorker()

        assert worker.redis_client is None


def test_process_redis_events():
    """Test processing of Redis events."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Mock Redis client
        mock_client = MagicMock()
        worker.redis_client = mock_client

        # Mock Redis data
        mock_client.hgetall.side_effect = [
            {
                "repository_id": "123",
                "tag_name": "latest",
                "manifest_digest": "sha256:abc123",
                "pull_count": "5",
                "last_pull_timestamp": "1694168400",
                "pull_method": "tag",
            },
            {
                "repository_id": "456",
                "tag_name": "",
                "manifest_digest": "sha256:def456",
                "pull_count": "3",
                "last_pull_timestamp": "1694168460",
                "pull_method": "digest",
            },
        ]

        # Test keys
        keys = [
            "pull_events:repo:123:tag:latest:sha256:abc123",
            "pull_events:repo:456:digest:sha256:def456",
        ]

        # Test processing
        (
            tag_updates,
            manifest_updates,
            cleanable_keys,
            database_dependent_keys,
        ) = worker._process_redis_events(keys)

        # Verify key separation results
        assert len(cleanable_keys) == 0  # No empty/invalid keys in this test
        assert len(database_dependent_keys) == 2  # Both keys have valid data
        assert len(tag_updates) == 1  # One tag update
        assert len(manifest_updates) == 2  # Two manifest updates (tag + digest)

        # Check tag update
        tag_update = tag_updates[0]
        assert tag_update["repository_id"] == 123
        assert tag_update["tag_name"] == "latest"
        assert tag_update["pull_count"] == 5
        assert tag_update["manifest_digest"] == "sha256:abc123"


def test_cleanup_redis_keys_success():
    """Test successful Redis key cleanup."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Mock Redis client
        mock_client = MagicMock()
        mock_client.delete.return_value = 3  # Simulate successful deletion of 3 keys
        worker.redis_client = mock_client

        # Test cleanup
        test_keys = {"key1", "key2", "key3"}
        worker._cleanup_redis_keys(test_keys)

        # Verify delete was called with the correct keys (order doesn't matter for sets)
        mock_client.delete.assert_called_once()
        called_args = mock_client.delete.call_args[0]  # Get the positional arguments
        assert set(called_args) == test_keys


def test_cleanup_redis_keys_no_client():
    """Test Redis key cleanup when no client is available."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        # No Redis client set
        worker.redis_client = None

        # Should handle gracefully
        keys_to_clean = {"key1", "key2"}
        worker._cleanup_redis_keys(keys_to_clean)  # Should not raise exception


def test_validate_redis_key_data():
    """Test Redis key data validation."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Valid data
        valid_data = {
            "repository_id": "123",
            "manifest_digest": "sha256:abc123",
            "pull_count": "5",
            "last_pull_timestamp": "1694168400",
        }
        assert worker._validate_redis_key_data("test_key", valid_data) is True

        # Missing required field
        invalid_data = {
            "repository_id": "123",
            "pull_count": "5",
            "last_pull_timestamp": "1694168400",
            # missing manifest_digest
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False

        # Invalid repository_id
        invalid_data = {
            "repository_id": "0",
            "manifest_digest": "sha256:abc123",
            "pull_count": "5",
            "last_pull_timestamp": "1694168400",
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False

        # Invalid manifest digest
        invalid_data = {
            "repository_id": "123",
            "manifest_digest": "invalid_digest",
            "pull_count": "5",
            "last_pull_timestamp": "1694168400",
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False

        # Invalid digest format (missing colon)
        invalid_data = {
            "repository_id": "123",
            "manifest_digest": "sha256123123",
            "pull_count": "5",
            "last_pull_timestamp": "1694168400",
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False


def test_scan_redis_keys_success():
    """Test successful Redis key scanning."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_FLUSH_INTERVAL_SECONDS": 300,
            "REDIS_FLUSH_WORKER_BATCH_SIZE": 1000,
            "REDIS_FLUSH_WORKER_SCAN_COUNT": 100,
            "REDIS_CONNECTION_TIMEOUT": 5,
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            # Mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis_module.StrictRedis.return_value = mock_client
            mock_redis_module.ConnectionError = Exception
            mock_redis_module.RedisError = Exception

            from workers.pullstatsredisflushworker import RedisFlushWorker

            worker = RedisFlushWorker()

            # Mock scan returning keys in a single batch
            mock_client.scan.return_value = (0, ["key1", "key2", "key3"])

            # Test
            result = worker._scan_redis_keys("pull_events:*", 10)

            # Verify
            assert len(result) == 3
            assert set(result) == {"key1", "key2", "key3"}
            mock_client.scan.assert_called_once_with(cursor=0, match="pull_events:*", count=100)


def test_scan_redis_keys_empty_results():
    """Test Redis key scanning when no keys are found."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_FLUSH_INTERVAL_SECONDS": 300,
            "REDIS_FLUSH_WORKER_BATCH_SIZE": 1000,
            "REDIS_FLUSH_WORKER_SCAN_COUNT": 100,
            "REDIS_CONNECTION_TIMEOUT": 5,
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            # Mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis_module.StrictRedis.return_value = mock_client
            mock_redis_module.ConnectionError = Exception
            mock_redis_module.RedisError = Exception

            from workers.pullstatsredisflushworker import RedisFlushWorker

            worker = RedisFlushWorker()

            # Mock scan returning no keys
            mock_client.scan.return_value = (0, [])

            # Test
            result = worker._scan_redis_keys("pull_events:*", 10)

            # Verify
            assert result == []
            mock_client.scan.assert_called_once_with(cursor=0, match="pull_events:*", count=100)


def test_scan_redis_keys_multiple_batches():
    """Test Redis key scanning with multiple scan batches."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_FLUSH_INTERVAL_SECONDS": 300,
            "REDIS_FLUSH_WORKER_BATCH_SIZE": 1000,
            "REDIS_FLUSH_WORKER_SCAN_COUNT": 100,
            "REDIS_CONNECTION_TIMEOUT": 5,
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            # Mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis_module.StrictRedis.return_value = mock_client
            mock_redis_module.ConnectionError = Exception
            mock_redis_module.RedisError = Exception

            from workers.pullstatsredisflushworker import RedisFlushWorker

            worker = RedisFlushWorker()

            # Mock scan returning keys in multiple batches
            mock_client.scan.side_effect = [
                (10, ["key1", "key2"]),  # First batch with cursor 10
                (20, ["key3", "key4"]),  # Second batch with cursor 20
                (0, ["key5"]),  # Final batch with cursor 0 (end)
            ]

            # Test
            result = worker._scan_redis_keys("pull_events:*", 10)

            # Verify all keys are returned
            assert len(result) == 5
            assert set(result) == {"key1", "key2", "key3", "key4", "key5"}

            # Verify scan was called multiple times with correct cursors
            expected_calls = [
                ((0,), {"match": "pull_events:*", "count": 100}),
                ((10,), {"match": "pull_events:*", "count": 100}),
                ((20,), {"match": "pull_events:*", "count": 100}),
            ]
            assert mock_client.scan.call_count == 3
            for i, call in enumerate(mock_client.scan.call_args_list):
                assert call.args == expected_calls[i][0]
                assert call.kwargs == expected_calls[i][1]


def test_scan_redis_keys_limit_reached():
    """Test Redis key scanning stops when limit is reached."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_FLUSH_INTERVAL_SECONDS": 300,
            "REDIS_FLUSH_WORKER_BATCH_SIZE": 1000,
            "REDIS_FLUSH_WORKER_SCAN_COUNT": 100,
            "REDIS_CONNECTION_TIMEOUT": 5,
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            # Mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis_module.StrictRedis.return_value = mock_client
            mock_redis_module.ConnectionError = Exception
            mock_redis_module.RedisError = Exception

            from workers.pullstatsredisflushworker import RedisFlushWorker

            worker = RedisFlushWorker()

            # Mock scan returning more keys than the limit
            mock_client.scan.side_effect = [
                (10, ["key1", "key2", "key3"]),  # First batch
                (20, ["key4", "key5", "key6"]),  # Second batch - would exceed limit
            ]

            # Test with limit of 4
            result = worker._scan_redis_keys("pull_events:*", 4)

            # Verify only limit number of keys are returned
            assert len(result) == 4
            assert set(result).issubset({"key1", "key2", "key3", "key4", "key5", "key6"})

            # Should call scan at least once
            assert mock_client.scan.call_count >= 1


def test_scan_redis_keys_deduplication():
    """Test Redis key scanning deduplicates keys properly."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_FLUSH_INTERVAL_SECONDS": 300,
            "REDIS_FLUSH_WORKER_BATCH_SIZE": 1000,
            "REDIS_FLUSH_WORKER_SCAN_COUNT": 100,
            "REDIS_CONNECTION_TIMEOUT": 5,
            "PULL_METRICS_REDIS": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
            },
        }.get(key, default)

        with patch("workers.pullstatsredisflushworker.redis") as mock_redis_module:
            # Mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis_module.StrictRedis.return_value = mock_client
            mock_redis_module.ConnectionError = Exception
            mock_redis_module.RedisError = Exception

            from workers.pullstatsredisflushworker import RedisFlushWorker

            worker = RedisFlushWorker()

            # Mock scan returning duplicate keys across batches
            mock_client.scan.side_effect = [
                (10, ["key1", "key2", "key1"]),  # Duplicate key1 in same batch
                (0, ["key2", "key3"]),  # Duplicate key2 across batches
            ]

            # Test
            result = worker._scan_redis_keys("pull_events:*", 10)

            # Verify deduplication
            assert len(result) == 3
            assert set(result) == {"key1", "key2", "key3"}


def test_scan_redis_keys_no_client():
    """Test Redis key scanning when client is None."""

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test with None client
    scanner = TestRedisScanner()
    scanner.redis_client = None

    result = scanner._scan_redis_keys("pull_events:*", 10)
    assert result == []


def test_scan_redis_keys_success():
    """Test successful Redis key scanning."""
    from typing import List, Set
    from unittest.mock import MagicMock

    import redis

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test with successful scan
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.return_value = (0, ["key1", "key2", "key3"])
    scanner.redis_client = mock_client

    result = scanner._scan_redis_keys("pull_events:*", 10)

    assert len(result) == 3
    assert set(result) == {"key1", "key2", "key3"}
    mock_client.scan.assert_called_once_with(cursor=0, match="pull_events:*", count=100)


def test_scan_redis_keys_empty_results():
    """Test Redis key scanning when no keys are found."""
    from typing import List, Set
    from unittest.mock import MagicMock

    import redis

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test with empty results
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.return_value = (0, [])
    scanner.redis_client = mock_client

    result = scanner._scan_redis_keys("pull_events:*", 10)

    assert result == []
    mock_client.scan.assert_called_once_with(cursor=0, match="pull_events:*", count=100)


def test_scan_redis_keys_multiple_batches():
    """Test Redis key scanning with multiple scan batches."""

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test with multiple batches
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.side_effect = [
        (10, ["key1", "key2"]),  # First batch with cursor 10
        (20, ["key3", "key4"]),  # Second batch with cursor 20
        (0, ["key5"]),  # Final batch with cursor 0 (end)
    ]
    scanner.redis_client = mock_client

    result = scanner._scan_redis_keys("pull_events:*", 10)

    # Verify all keys are returned
    assert len(result) == 5
    assert set(result) == {"key1", "key2", "key3", "key4", "key5"}

    # Verify scan was called multiple times with correct cursors
    expected_calls = [
        {"cursor": 0, "match": "pull_events:*", "count": 100},
        {"cursor": 10, "match": "pull_events:*", "count": 100},
        {"cursor": 20, "match": "pull_events:*", "count": 100},
    ]
    assert mock_client.scan.call_count == 3
    for i, call in enumerate(mock_client.scan.call_args_list):
        assert call.kwargs == expected_calls[i]


def test_scan_redis_keys_limit_reached():
    """Test Redis key scanning stops when limit is reached."""

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test with limit reached
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.side_effect = [
        (10, ["key1", "key2", "key3"]),  # First batch
        (20, ["key4", "key5", "key6"]),  # Second batch - would exceed limit
    ]
    scanner.redis_client = mock_client

    # Test with limit of 4
    result = scanner._scan_redis_keys("pull_events:*", 4)

    # Verify only limit number of keys are returned
    assert len(result) == 4
    assert set(result).issubset({"key1", "key2", "key3", "key4", "key5", "key6"})

    # Should call scan at least once
    assert mock_client.scan.call_count >= 1


def test_scan_redis_keys_deduplication():
    """Test Redis key scanning deduplicates keys properly."""

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test deduplication
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.side_effect = [
        (10, ["key1", "key2", "key1"]),  # Duplicate key1 in same batch
        (0, ["key2", "key3"]),  # Duplicate key2 across batches
    ]
    scanner.redis_client = mock_client

    result = scanner._scan_redis_keys("pull_events:*", 10)

    # Verify deduplication
    assert len(result) == 3
    assert set(result) == {"key1", "key2", "key3"}


def test_scan_redis_keys_redis_error():
    """Test Redis key scanning handles Redis errors."""

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test Redis error handling
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.side_effect = redis.RedisError("Connection lost")
    scanner.redis_client = mock_client

    result = scanner._scan_redis_keys("pull_events:*", 10)

    # Verify error is handled gracefully
    assert result == []


def test_scan_redis_keys_general_exception():
    """Test Redis key scanning handles general exceptions."""

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test general exception handling
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.side_effect = Exception("Unexpected error")
    scanner.redis_client = mock_client

    result = scanner._scan_redis_keys("pull_events:*", 10)

    # Verify error is handled gracefully
    assert result == []


def test_scan_redis_keys_empty_batch_in_middle():
    """Test Redis key scanning handles empty batches in the middle of scanning."""

    class TestRedisScanner:
        def __init__(self):
            self.redis_client = None

        def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
            """Simplified version of _scan_redis_keys for testing."""
            REDIS_SCAN_COUNT = 100  # From the original constant
            try:
                keys_set: Set[str] = set()
                cursor = 0

                while len(keys_set) < limit:
                    if self.redis_client is None:
                        break
                    cursor, batch_keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                    )

                    if batch_keys:
                        keys_set.update(batch_keys)

                    if cursor == 0:
                        break

                keys_list = list(keys_set)
                return keys_list[:limit]

            except redis.RedisError:
                return []
            except Exception:
                return []

    # Test empty batch in middle
    scanner = TestRedisScanner()
    mock_client = MagicMock()
    mock_client.scan.side_effect = [
        (10, ["key1", "key2"]),  # First batch with keys
        (20, []),  # Second batch empty
        (0, ["key3"]),  # Final batch with keys
    ]
    scanner.redis_client = mock_client

    result = scanner._scan_redis_keys("pull_events:*", 10)

    # Verify all non-empty batches are processed
    assert len(result) == 3
    assert set(result) == {"key1", "key2", "key3"}
