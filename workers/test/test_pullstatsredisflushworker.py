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


def test_scan_redis_keys_no_client():
    """Test Redis key scanning when client is None."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        worker.redis_client = None

        result = worker._scan_redis_keys("pull_events:*", 10)
        assert result == []


def test_scan_redis_keys_success():
    """Test successful Redis key scanning."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, ["key1", "key2", "key3"])
        worker.redis_client = mock_client

        result = worker._scan_redis_keys("pull_events:*", 10)

        assert len(result) == 3
        assert set(result) == {"key1", "key2", "key3"}
        mock_client.scan.assert_called_once_with(cursor=0, match="pull_events:*", count=100)


def test_scan_redis_keys_empty_results():
    """Test Redis key scanning when no keys are found."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, [])
        worker.redis_client = mock_client

        result = worker._scan_redis_keys("pull_events:*", 10)

        assert result == []
        mock_client.scan.assert_called_once_with(cursor=0, match="pull_events:*", count=100)


def test_scan_redis_keys_multiple_batches():
    """Test Redis key scanning with multiple scan batches."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.side_effect = [
            (10, ["key1", "key2"]),  # First batch with cursor 10
            (20, ["key3", "key4"]),  # Second batch with cursor 20
            (0, ["key5"]),  # Final batch with cursor 0 (end)
        ]
        worker.redis_client = mock_client

        result = worker._scan_redis_keys("pull_events:*", 10)

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
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.side_effect = [
            (10, ["key1", "key2", "key3"]),  # First batch
            (20, ["key4", "key5", "key6"]),  # Second batch - would exceed limit
        ]
        worker.redis_client = mock_client

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
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.side_effect = [
            (10, ["key1", "key2", "key1"]),  # Duplicate key1 in same batch
            (0, ["key2", "key3"]),  # Duplicate key2 across batches
        ]
        worker.redis_client = mock_client

        result = worker._scan_redis_keys("pull_events:*", 10)

        # Verify deduplication
        assert len(result) == 3
        assert set(result) == {"key1", "key2", "key3"}


def test_scan_redis_keys_redis_error():
    """Test Redis key scanning handles Redis errors."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.side_effect = redis.RedisError("Connection lost")
        worker.redis_client = mock_client

        result = worker._scan_redis_keys("pull_events:*", 10)

        # Verify error is handled gracefully
        assert result == []


def test_scan_redis_keys_general_exception():
    """Test Redis key scanning handles general exceptions."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.side_effect = Exception("Unexpected error")
        worker.redis_client = mock_client

        result = worker._scan_redis_keys("pull_events:*", 10)

        # Verify error is handled gracefully
        assert result == []


def test_scan_redis_keys_empty_batch_in_middle():
    """Test Redis key scanning handles empty batches in the middle of scanning."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.side_effect = [
            (10, ["key1", "key2"]),  # First batch with keys
            (20, []),  # Second batch empty
            (0, ["key3"]),  # Final batch with keys
        ]
        worker.redis_client = mock_client

        result = worker._scan_redis_keys("pull_events:*", 10)

        # Verify all non-empty batches are processed
        assert len(result) == 3
        assert set(result) == {"key1", "key2", "key3"}


def test_flush_to_database_successful_tag_updates():
    """Test successful database flush with tag updates only."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            with patch(
                "workers.pullstatsredisflushworker.bulk_upsert_manifest_statistics"
            ) as mock_manifest_upsert:
                mock_tag_upsert.return_value = 2
                mock_manifest_upsert.return_value = 0

                from workers.pullstatsredisflushworker import RedisFlushWorker

                worker = RedisFlushWorker()

                tag_updates = [
                    {"repository_id": 123, "tag_name": "latest", "pull_count": 5},
                    {"repository_id": 124, "tag_name": "v1.0", "pull_count": 3},
                ]
                manifest_updates = []

                result = worker._flush_to_database(tag_updates, manifest_updates)

                assert result is True
                mock_tag_upsert.assert_called_once_with(tag_updates)
                mock_manifest_upsert.assert_not_called()


def test_flush_to_database_successful_manifest_updates():
    """Test successful database flush with manifest updates only."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            with patch(
                "workers.pullstatsredisflushworker.bulk_upsert_manifest_statistics"
            ) as mock_manifest_upsert:
                mock_tag_upsert.return_value = 0
                mock_manifest_upsert.return_value = 3

                from workers.pullstatsredisflushworker import RedisFlushWorker

                worker = RedisFlushWorker()

                tag_updates = []
                manifest_updates = [
                    {"repository_id": 123, "manifest_digest": "sha256:abc", "pull_count": 5},
                    {"repository_id": 124, "manifest_digest": "sha256:def", "pull_count": 3},
                    {"repository_id": 125, "manifest_digest": "sha256:ghi", "pull_count": 2},
                ]

                result = worker._flush_to_database(tag_updates, manifest_updates)

                assert result is True
                mock_tag_upsert.assert_not_called()
                mock_manifest_upsert.assert_called_once_with(manifest_updates)


def test_flush_to_database_successful_both_updates():
    """Test successful database flush with both tag and manifest updates."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            with patch(
                "workers.pullstatsredisflushworker.bulk_upsert_manifest_statistics"
            ) as mock_manifest_upsert:
                mock_tag_upsert.return_value = 1
                mock_manifest_upsert.return_value = 2

                from workers.pullstatsredisflushworker import RedisFlushWorker

                worker = RedisFlushWorker()

                tag_updates = [
                    {"repository_id": 123, "tag_name": "latest", "pull_count": 5},
                ]
                manifest_updates = [
                    {"repository_id": 123, "manifest_digest": "sha256:abc", "pull_count": 5},
                    {"repository_id": 124, "manifest_digest": "sha256:def", "pull_count": 3},
                ]

                result = worker._flush_to_database(tag_updates, manifest_updates)

                assert result is True
                mock_tag_upsert.assert_called_once_with(tag_updates)
                mock_manifest_upsert.assert_called_once_with(manifest_updates)


def test_flush_to_database_empty_updates():
    """Test database flush with no updates (empty batch)."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            with patch(
                "workers.pullstatsredisflushworker.bulk_upsert_manifest_statistics"
            ) as mock_manifest_upsert:
                from workers.pullstatsredisflushworker import RedisFlushWorker

                worker = RedisFlushWorker()

                tag_updates = []
                manifest_updates = []

                result = worker._flush_to_database(tag_updates, manifest_updates)

                # Should return True for empty batch (no updates needed)
                assert result is True
                mock_tag_upsert.assert_not_called()
                mock_manifest_upsert.assert_not_called()


def test_flush_to_database_exception_handling():
    """Test database flush handles exceptions."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            with patch(
                "workers.pullstatsredisflushworker.bulk_upsert_manifest_statistics"
            ) as mock_manifest_upsert:
                mock_tag_upsert.side_effect = Exception("Database error")

                from workers.pullstatsredisflushworker import RedisFlushWorker

                worker = RedisFlushWorker()

                tag_updates = [
                    {"repository_id": 123, "tag_name": "latest", "pull_count": 5},
                ]
                manifest_updates = []

                result = worker._flush_to_database(tag_updates, manifest_updates)

                assert result is False
                mock_tag_upsert.assert_called_once_with(tag_updates)


def test_flush_to_database_partial_success():
    """Test database flush with partial success (zero updates returned)."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            with patch(
                "workers.pullstatsredisflushworker.bulk_upsert_manifest_statistics"
            ) as mock_manifest_upsert:
                mock_tag_upsert.return_value = 0
                mock_manifest_upsert.return_value = 0

                from workers.pullstatsredisflushworker import RedisFlushWorker

                worker = RedisFlushWorker()

                tag_updates = [
                    {"repository_id": 123, "tag_name": "latest", "pull_count": 5},
                ]
                manifest_updates = [
                    {"repository_id": 123, "manifest_digest": "sha256:abc", "pull_count": 5},
                ]

                result = worker._flush_to_database(tag_updates, manifest_updates)

                # Should return False since no actual updates were made
                assert result is False
                mock_tag_upsert.assert_called_once_with(tag_updates)
                mock_manifest_upsert.assert_called_once_with(manifest_updates)


def test_create_gunicorn_worker():
    """Test the create_gunicorn_worker function."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch("workers.pullstatsredisflushworker.GunicornWorker") as mock_gunicorn_worker:
            with patch("workers.pullstatsredisflushworker.features") as mock_features:
                mock_features.IMAGE_PULL_STATS = True
                mock_gunicorn_instance = MagicMock()
                mock_gunicorn_worker.return_value = mock_gunicorn_instance

                from workers.pullstatsredisflushworker import create_gunicorn_worker

                # Test
                result = create_gunicorn_worker()

                # Verify
                assert result is not None
                mock_gunicorn_worker.assert_called_once()
                call_args = mock_gunicorn_worker.call_args
                assert call_args[0][0] == "workers.pullstatsredisflushworker"
                assert call_args[0][3] is True  # IMAGE_PULL_STATS feature flag


def test_flush_pull_metrics_no_redis_client():
    """Test _flush_pull_metrics when Redis client is not initialized."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        worker.redis_client = None

        # Should return early without error
        worker._flush_pull_metrics()  # No assertions needed - just verifies no exception


def test_flush_pull_metrics_no_keys_found():
    """Test _flush_pull_metrics when no Redis keys are found."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, [])
        worker.redis_client = mock_client

        # Should return early when no keys found
        worker._flush_pull_metrics()

        # Verify scan was called
        mock_client.scan.assert_called_once()


def test_flush_pull_metrics_successful_processing():
    """Test successful _flush_pull_metrics execution."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            with patch(
                "workers.pullstatsredisflushworker.bulk_upsert_manifest_statistics"
            ) as mock_manifest_upsert:
                mock_tag_upsert.return_value = 1
                mock_manifest_upsert.return_value = 1

                from workers.pullstatsredisflushworker import RedisFlushWorker

                worker = RedisFlushWorker()
                mock_client = MagicMock()

                # Mock scan to return a key
                mock_client.scan.return_value = (0, ["pull_events:repo:123:tag:latest:sha256:abc"])

                # Mock hgetall to return valid data
                mock_client.hgetall.return_value = {
                    "repository_id": "123",
                    "tag_name": "latest",
                    "manifest_digest": "sha256:abc123",
                    "pull_count": "5",
                    "last_pull_timestamp": "1694168400",
                    "pull_method": "tag",
                }

                # Mock delete to succeed
                mock_client.delete.return_value = 1

                worker.redis_client = mock_client

                worker._flush_pull_metrics()

                # Verify database operations were called
                mock_tag_upsert.assert_called_once()
                mock_manifest_upsert.assert_called_once()

                # Verify cleanup was called
                mock_client.delete.assert_called()


def test_flush_pull_metrics_with_redis_error():
    """Test _flush_pull_metrics handles Redis errors gracefully."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.scan.side_effect = redis.RedisError("Connection lost")
        worker.redis_client = mock_client

        # Should handle error gracefully
        worker._flush_pull_metrics()  # No exception should be raised


def test_cleanup_redis_keys_batch_processing():
    """Test _cleanup_redis_keys processes keys in batches."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.delete.return_value = 100  # Successful deletion
        worker.redis_client = mock_client

        # Create 250 keys (should be split into 3 batches of 100, 100, 50)
        keys = {f"key{i}" for i in range(250)}
        worker._cleanup_redis_keys(keys)

        # Verify delete was called 3 times (3 batches)
        assert mock_client.delete.call_count == 3


def test_cleanup_redis_keys_partial_deletion():
    """Test _cleanup_redis_keys when some keys fail to delete."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        # Return fewer deletions than requested
        mock_client.delete.return_value = 50  # Only 50 out of 100 deleted
        worker.redis_client = mock_client

        keys = {f"key{i}" for i in range(100)}
        worker._cleanup_redis_keys(keys)

        # Should still complete without raising exception
        mock_client.delete.assert_called_once()


def test_cleanup_redis_keys_batch_exception():
    """Test _cleanup_redis_keys handles batch exceptions."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        # First batch fails, second succeeds
        mock_client.delete.side_effect = [
            Exception("First batch error"),
            100,  # Second batch succeeds
        ]
        worker.redis_client = mock_client

        keys = {f"key{i}" for i in range(150)}
        worker._cleanup_redis_keys(keys)

        # Should handle error and continue
        assert mock_client.delete.call_count == 2


def test_cleanup_redis_keys_redis_error():
    """Test _cleanup_redis_keys handles Redis errors."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.delete.side_effect = redis.RedisError("Connection error")
        worker.redis_client = mock_client

        keys = {"key1", "key2"}
        # Should handle error gracefully
        worker._cleanup_redis_keys(keys)


def test_process_redis_events_invalid_key_format():
    """Test _process_redis_events handles invalid key formats."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        worker.redis_client = mock_client

        # Test with keys that don't start with pull_events:
        keys = ["invalid_key", "another_invalid"]
        tag_updates, manifest_updates, cleanable, db_dependent = worker._process_redis_events(keys)

        # Should skip invalid keys
        assert len(tag_updates) == 0
        assert len(manifest_updates) == 0


def test_process_redis_events_empty_hash_data():
    """Test _process_redis_events with empty hash data."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.hgetall.return_value = {}  # Empty data
        worker.redis_client = mock_client

        keys = ["pull_events:repo:123:tag:latest:sha256:abc"]
        tag_updates, manifest_updates, cleanable, db_dependent = worker._process_redis_events(keys)

        # Empty data should be marked as cleanable
        assert len(cleanable) == 1
        assert "pull_events:repo:123:tag:latest:sha256:abc" in cleanable


def test_process_redis_events_zero_pull_count():
    """Test _process_redis_events with zero pull count."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.hgetall.return_value = {
            "repository_id": "123",
            "tag_name": "latest",
            "manifest_digest": "sha256:abc123",
            "pull_count": "0",  # Zero pulls
            "last_pull_timestamp": "1694168400",
            "pull_method": "tag",
        }
        worker.redis_client = mock_client

        keys = ["pull_events:repo:123:tag:latest:sha256:abc"]
        tag_updates, manifest_updates, cleanable, db_dependent = worker._process_redis_events(keys)

        # Zero pull count should be cleanable
        assert len(cleanable) == 1
        assert len(tag_updates) == 0
        assert len(manifest_updates) == 0


def test_process_redis_events_redis_error_during_processing():
    """Test _process_redis_events handles Redis errors during key processing."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.hgetall.side_effect = redis.RedisError("Connection error")
        worker.redis_client = mock_client

        keys = ["pull_events:repo:123:tag:latest:sha256:abc"]
        tag_updates, manifest_updates, cleanable, db_dependent = worker._process_redis_events(keys)

        # Should handle error and continue
        assert len(tag_updates) == 0
        assert len(manifest_updates) == 0


def test_process_redis_events_digest_pull():
    """Test _process_redis_events with digest pull (no tag)."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()
        mock_client = MagicMock()
        mock_client.hgetall.return_value = {
            "repository_id": "123",
            "tag_name": "",  # No tag for digest pull
            "manifest_digest": "sha256:abc123",
            "pull_count": "5",
            "last_pull_timestamp": "1694168400",
            "pull_method": "digest",
        }
        worker.redis_client = mock_client

        keys = ["pull_events:repo:123:digest:sha256:abc"]
        tag_updates, manifest_updates, cleanable, db_dependent = worker._process_redis_events(keys)

        # Should only have manifest update, no tag update
        assert len(tag_updates) == 0
        assert len(manifest_updates) == 1
        assert len(db_dependent) == 1


def test_flush_to_database_pull_statistics_exception():
    """Test _flush_to_database handles PullStatisticsException."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        with patch(
            "workers.pullstatsredisflushworker.bulk_upsert_tag_statistics"
        ) as mock_tag_upsert:
            from data.model.pull_statistics import PullStatisticsException
            from workers.pullstatsredisflushworker import RedisFlushWorker

            mock_tag_upsert.side_effect = PullStatisticsException("DB error")

            worker = RedisFlushWorker()

            tag_updates = [{"repository_id": 123, "tag_name": "latest", "pull_count": 5}]
            manifest_updates = []

            result = worker._flush_to_database(tag_updates, manifest_updates)

            assert result is False


def test_initialize_redis_client_general_exception():
    """Test _initialize_redis_client handles general exceptions."""
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
            # Mock Redis client that fails with general exception
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Unexpected error")
            mock_redis_module.StrictRedis.return_value = mock_client

            # Ensure the exception classes are available
            mock_redis_module.ConnectionError = redis.ConnectionError
            mock_redis_module.RedisError = redis.RedisError

            from workers.pullstatsredisflushworker import RedisFlushWorker

            # Test
            worker = RedisFlushWorker()

            # Verify
            assert worker.redis_client is None


def test_validate_redis_key_data_type_error():
    """Test _validate_redis_key_data handles type conversion errors."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Invalid data types
        invalid_data = {
            "repository_id": "not_a_number",
            "manifest_digest": "sha256:abc123",
            "pull_count": "not_a_number",
            "last_pull_timestamp": "1694168400",
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False


def test_validate_redis_key_data_negative_values():
    """Test _validate_redis_key_data handles negative values correctly."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Negative pull count
        invalid_data = {
            "repository_id": "123",
            "manifest_digest": "sha256:abc123",
            "pull_count": "-1",
            "last_pull_timestamp": "1694168400",
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False

        # Negative timestamp
        invalid_data = {
            "repository_id": "123",
            "manifest_digest": "sha256:abc123",
            "pull_count": "5",
            "last_pull_timestamp": "-1",
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False


def test_validate_redis_key_data_empty_digest():
    """Test _validate_redis_key_data with empty manifest digest."""
    with patch("workers.pullstatsredisflushworker.app") as mock_app:
        mock_app.config.get.return_value = 300

        from workers.pullstatsredisflushworker import RedisFlushWorker

        worker = RedisFlushWorker()

        # Empty digest
        invalid_data = {
            "repository_id": "123",
            "manifest_digest": "",
            "pull_count": "5",
            "last_pull_timestamp": "1694168400",
        }
        assert worker._validate_redis_key_data("test_key", invalid_data) is False
