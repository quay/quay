"""
Tests for RedisFlushWorker.

Tests the main worker that processes Redis pull events.
"""

from unittest.mock import MagicMock, patch


def test_redis_flush_worker_init():
    """Test RedisFlushWorker initialization."""
    # Mock the app imports to avoid dependency issues
    with patch("workers.redisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "REDIS_FLUSH_INTERVAL_SECONDS": 300,
            "REDIS_FLUSH_WORKER_BATCH_SIZE": 1000,
            "REDIS_FLUSH_WORKER_SCAN_COUNT": 100,
            "REDIS_CONNECTION_TIMEOUT": 5,
            "PULL_METRICS_REDIS_HOST": "localhost",
            "PULL_METRICS_REDIS_PORT": 6379,
            "PULL_METRICS_REDIS_DB": 0,
            "PULL_METRICS_REDIS_PASSWORD": None,
        }.get(key, default)

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Should have one operation scheduled
        assert len(worker._operations) == 1
        assert worker._operations[0][1] == 300  # Default frequency


def test_initialize_redis_client_success():
    """Test successful Redis client initialization."""
    with patch("workers.redisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "PULL_METRICS_REDIS_HOST": "localhost",
            "PULL_METRICS_REDIS_PORT": 6379,
            "PULL_METRICS_REDIS_DB": 0,
            "PULL_METRICS_REDIS_PASSWORD": None,
            "REDIS_CONNECTION_TIMEOUT": 5,
        }.get(key, default)

        from workers.pullstatsredisflushworker import RedisFlushWorker

        with patch("workers.redisflushworker.redis") as mock_redis_module:
            # Mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis_module.StrictRedis.return_value = mock_client

            # Test
            worker = RedisFlushWorker()

            # Verify
            assert worker.redis_client == mock_client
            mock_redis_module.StrictRedis.assert_called_once()
            mock_client.ping.assert_called_once()


def test_initialize_redis_client_connection_failure():
    """Test Redis client initialization when connection fails."""
    with patch("workers.redisflushworker.app") as mock_app:
        mock_app.config.get.side_effect = lambda key, default=None: {
            "PULL_METRICS_REDIS_HOST": "localhost",
            "PULL_METRICS_REDIS_PORT": 6379,
            "PULL_METRICS_REDIS_DB": 0,
            "PULL_METRICS_REDIS_PASSWORD": None,
            "REDIS_CONNECTION_TIMEOUT": 5,
        }.get(key, default)

        from workers.pullstatsredisflushworker import RedisFlushWorker

        with patch("workers.redisflushworker.redis") as mock_redis_module:
            # Mock Redis client that fails on ping
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_redis_module.StrictRedis.return_value = mock_client

            # Test
            worker = RedisFlushWorker()

            # Verify
            assert worker.redis_client is None


def test_process_redis_events():
    """Test processing of Redis events."""
    with patch("workers.redisflushworker.app") as mock_app:
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
        tag_updates, manifest_updates, processed_keys = worker._process_redis_events(keys)

        # Verify results
        assert len(processed_keys) == 2
        assert len(tag_updates) == 1  # One tag update
        assert len(manifest_updates) == 2  # Two manifest updates (tag + digest)

        # Check tag update
        tag_update = tag_updates[0]
        assert tag_update["repository_id"] == 123
        assert tag_update["tag_name"] == "latest"
        assert tag_update["pull_count"] == 5
        assert tag_update["manifest_digest"] == "sha256:abc123"

        # Check manifest updates
        manifest_repos = [update["repository_id"] for update in manifest_updates]
        assert 123 in manifest_repos
        assert 456 in manifest_repos

        # Verify that we have the expected number of updates
        assert len(tag_updates) == 1  # One tag update
        assert len(manifest_updates) == 2  # Two manifest updates (tag + digest)
