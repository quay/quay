"""
Tests for RedisFlushWorker.

Tests the main worker that processes Redis pull events.
"""

from unittest.mock import MagicMock, patch


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
