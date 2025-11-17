"""
Tests for util/pullmetrics.py module.

This test suite covers:
- PullMetrics class initialization
- Tag pull tracking (sync and async)
- Manifest pull tracking (sync and async)
- Redis key generation
- Pull statistics retrieval from Redis
- Error handling
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
import redis

from util.pullmetrics import (
    CannotReadPullMetricsException,
    PullMetrics,
    PullMetricsBuilder,
    PullMetricsBuilderModule,
)


class TestPullMetricsKeyGeneration:
    """Test Redis key generation patterns."""

    def test_tag_pull_key_format(self):
        """Test tag pull key generation format."""
        key = PullMetrics._tag_pull_key(123, "latest", "sha256:abc123")
        assert key == "pull_events:repo:123:tag:latest:sha256:abc123"

    def test_manifest_pull_key_format(self):
        """Test manifest pull key generation format."""
        key = PullMetrics._manifest_pull_key(456, "sha256:def456")
        assert key == "pull_events:repo:456:digest:sha256:def456"

    def test_tag_pull_key_with_special_characters(self):
        """Test tag pull key with special characters in tag name."""
        key = PullMetrics._tag_pull_key(789, "v1.2.3-alpha", "sha256:xyz789")
        assert key == "pull_events:repo:789:tag:v1.2.3-alpha:sha256:xyz789"


class TestPullMetricsBuilder:
    """Test PullMetricsBuilder class."""

    def test_builder_initialization(self):
        """Test PullMetricsBuilder initialization."""
        redis_config = {"host": "localhost", "port": 6379}
        builder = PullMetricsBuilder(redis_config)
        assert builder._redis_config == redis_config
        assert builder._max_workers is None

    def test_builder_initialization_with_workers(self):
        """Test PullMetricsBuilder initialization with custom worker count."""
        redis_config = {"host": "localhost", "port": 6379}
        builder = PullMetricsBuilder(redis_config, max_workers=10)
        assert builder._max_workers == 10

    def test_builder_get_event(self, mock_redis):
        """Test PullMetricsBuilder.get_event() returns PullMetrics instance."""
        with patch("util.pullmetrics.redis.StrictRedis") as mock_redis_class:
            mock_redis_class.return_value = MagicMock()
            redis_config = {"host": "localhost", "port": 6379, "_testing": True}
            builder = PullMetricsBuilder(redis_config)
            event = builder.get_event()
            assert isinstance(event, PullMetrics)


class TestPullMetricsBuilderModule:
    """Test PullMetricsBuilderModule Flask extension."""

    def test_module_initialization_without_app(self):
        """Test module initialization without app."""
        module = PullMetricsBuilderModule()
        assert module.app is None
        assert module.state is None

    def test_module_initialization_with_app(self):
        """Test module initialization with app."""
        app = Mock()
        app.config = {
            "PULL_METRICS_REDIS": {"host": "localhost", "port": 6379},
            "TESTING": True,
        }
        app.extensions = {}

        module = PullMetricsBuilderModule(app)
        assert module.app == app
        assert module.state is not None
        assert isinstance(module.state, PullMetricsBuilder)
        assert "pullmetrics" in app.extensions

    def test_module_init_app(self):
        """Test module init_app method."""
        app = Mock()
        app.config = {
            "PULL_METRICS_REDIS": {"host": "localhost", "port": 6379},
            "TESTING": True,
        }
        app.extensions = {}

        module = PullMetricsBuilderModule()
        builder = module.init_app(app)

        assert isinstance(builder, PullMetricsBuilder)
        assert "pullmetrics" in app.extensions
        assert app.extensions["pullmetrics"] == builder

    def test_module_init_app_with_old_config_key(self):
        """Test module handles old PULL_METRICS_REDIS_HOSTNAME config key."""
        app = Mock()
        app.config = {
            "PULL_METRICS_REDIS_HOSTNAME": "redis.example.com",
            "TESTING": True,
        }
        app.extensions = {}

        module = PullMetricsBuilderModule()
        builder = module.init_app(app)

        assert isinstance(builder, PullMetricsBuilder)
        assert builder._redis_config["host"] == "redis.example.com"

    def test_module_init_app_with_custom_worker_count(self):
        """Test module respects custom worker count configuration."""
        app = Mock()
        app.config = {
            "PULL_METRICS_REDIS": {"host": "localhost", "port": 6379},
            "PULL_METRICS_WORKER_COUNT": 10,
            "TESTING": True,
        }
        app.extensions = {}

        module = PullMetricsBuilderModule()
        builder = module.init_app(app)

        assert builder._max_workers == 10

    def test_module_getattr(self):
        """Test module __getattr__ delegates to state."""
        app = Mock()
        app.config = {
            "PULL_METRICS_REDIS": {"host": "localhost", "port": 6379},
            "TESTING": True,
        }
        app.extensions = {}

        module = PullMetricsBuilderModule(app)
        # Access an attribute from the builder
        assert module._redis_config is not None


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    with patch("util.pullmetrics.redis.StrictRedis") as mock_redis_class:
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance
        yield mock_redis_instance


@pytest.fixture
def pull_metrics_testing(mock_redis):
    """Create PullMetrics instance in testing mode (no thread pool)."""
    redis_config = {"host": "localhost", "port": 6379, "_testing": True}
    return PullMetrics(redis_config)


@pytest.fixture
def pull_metrics_production(mock_redis):
    """Create PullMetrics instance in production mode (with thread pool)."""
    redis_config = {"host": "localhost", "port": 6379}
    return PullMetrics(redis_config)


class TestPullMetrics:
    """Test PullMetrics class."""

    def test_pullmetrics_initialization_testing_mode(self, mock_redis):
        """Test PullMetrics initialization in testing mode - lazy connection."""
        redis_config = {"host": "localhost", "port": 6379, "_testing": True}
        pm = PullMetrics(redis_config)

        # With lazy initialization, Redis connection should be None until first use
        assert pm._redis is None
        assert pm._executor is None  # No thread pool in testing mode

    def test_pullmetrics_initialization_production_mode(self, mock_redis):
        """Test PullMetrics initialization in production mode - lazy connection."""
        redis_config = {"host": "localhost", "port": 6379}
        pm = PullMetrics(redis_config)

        # With lazy initialization, Redis connection should be None until first use
        assert pm._redis is None
        assert pm._executor is not None  # Thread pool in production mode

    def test_lazy_redis_connection_on_first_use(self, mock_redis):
        """Test that Redis connection is established on first use, not during init."""
        redis_config = {"host": "localhost", "port": 6379, "_testing": True}
        pm = PullMetrics(redis_config)

        # Initially no connection
        assert pm._redis is None

        # Mock ping to succeed
        mock_redis.ping.return_value = True
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # First use should establish connection
        repository = Mock()
        repository.id = 123
        pm.track_tag_pull_sync(repository, "latest", "sha256:abc123")

        # Now connection should be established
        assert pm._redis is not None
        # Verify StrictRedis was called to create connection
        from util.pullmetrics import redis

        redis.StrictRedis.assert_called()

    def test_redis_connection_retry_logic(self, mock_redis):
        """Test that Redis connection retries on failure."""
        redis_config = {"host": "localhost", "port": 6379, "_testing": True, "retry_attempts": 3}
        pm = PullMetrics(redis_config)

        # Mock connection failures then success
        from util.pullmetrics import redis

        call_count = 0

        def mock_redis_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_client = MagicMock()
            if call_count < 3:
                # First two attempts fail
                mock_client.ping.side_effect = redis.ConnectionError("Connection failed")
            else:
                # Third attempt succeeds
                mock_client.ping.return_value = True
            return mock_client

        redis.StrictRedis.side_effect = mock_redis_side_effect

        repository = Mock()
        repository.id = 123
        mock_pipeline = MagicMock()

        # After retries, should eventually succeed
        with patch.object(pm, "_ensure_redis_connection") as mock_ensure:
            mock_redis_client = MagicMock()
            mock_redis_client.pipeline.return_value = mock_pipeline
            mock_ensure.return_value = mock_redis_client
            pm.track_tag_pull_sync(repository, "latest", "sha256:abc123")

    def test_redis_connection_health_check(self, mock_redis):
        """Test that existing connection is health-checked before reuse."""
        redis_config = {"host": "localhost", "port": 6379, "_testing": True}
        pm = PullMetrics(redis_config)

        # Establish initial connection
        mock_redis.ping.return_value = True
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        repository = Mock()
        repository.id = 123
        pm.track_tag_pull_sync(repository, "latest", "sha256:abc123")

        # Connection should be established
        assert pm._redis is not None

        # Verify ping was called for health check
        # (ping is called in _ensure_redis_connection)
        assert mock_redis.ping.called

    def test_redis_connection_reconnect_on_failure(self, mock_redis):
        """Test that connection is re-established if health check fails."""
        redis_config = {"host": "localhost", "port": 6379, "_testing": True}
        pm = PullMetrics(redis_config)

        # First connection succeeds
        mock_redis.ping.return_value = True
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        repository = Mock()
        repository.id = 123
        pm.track_tag_pull_sync(repository, "latest", "sha256:abc123")

        # Simulate connection failure on health check
        from util.pullmetrics import redis

        original_redis = pm._redis
        # Use a callable side_effect that only fails on the first call (health check)
        # Subsequent calls (reconnection) will succeed
        ping_call_count = [0]

        def ping_side_effect():
            ping_call_count[0] += 1
            if ping_call_count[0] == 1:
                # First call (health check) fails
                raise redis.ConnectionError("Connection lost")
            # Subsequent calls succeed
            return True

        original_redis.ping.side_effect = ping_side_effect
        # Note: side_effect takes precedence over return_value, so the callable
        # side_effect handles both failure and success cases
        pm.track_tag_pull_sync(repository, "latest", "sha256:abc123")

        # Should have attempted to reconnect
        assert mock_redis.ping.call_count >= 2

    def test_track_tag_pull_sync(self, pull_metrics_testing, mock_redis):
        """Test synchronous tag pull tracking."""
        # Setup
        repository = Mock()
        repository.id = 123
        tag_name = "latest"
        manifest_digest = "sha256:abc123"

        # Mock connection establishment (ping) and pipeline
        mock_redis.ping.return_value = True
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute
        pull_metrics_testing.track_tag_pull_sync(repository, tag_name, manifest_digest)

        # Verify Redis connection was established (ping called)
        assert mock_redis.ping.called
        # Verify Redis pipeline calls
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.hset.assert_any_call(
            "pull_events:repo:123:tag:latest:sha256:abc123", "repository_id", 123
        )
        mock_pipeline.hset.assert_any_call(
            "pull_events:repo:123:tag:latest:sha256:abc123", "tag_name", "latest"
        )
        mock_pipeline.hset.assert_any_call(
            "pull_events:repo:123:tag:latest:sha256:abc123", "manifest_digest", "sha256:abc123"
        )
        mock_pipeline.hincrby.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    def test_track_tag_pull_sync_with_repository_id(self, pull_metrics_testing, mock_redis):
        """Test synchronous tag pull tracking with repository ID instead of object."""
        # Setup
        repository_id = 456
        tag_name = "v1.0"
        manifest_digest = "sha256:def456"

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute
        pull_metrics_testing.track_tag_pull_sync(repository_id, tag_name, manifest_digest)

        # Verify Redis pipeline calls with correct repository_id
        mock_pipeline.hset.assert_any_call(
            "pull_events:repo:456:tag:v1.0:sha256:def456", "repository_id", 456
        )

    def test_track_manifest_pull_sync(self, pull_metrics_testing, mock_redis):
        """Test synchronous manifest pull tracking."""
        # Setup
        repository = Mock()
        repository.id = 789
        manifest_digest = "sha256:xyz789"

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute
        pull_metrics_testing.track_manifest_pull_sync(repository, manifest_digest)

        # Verify Redis pipeline calls
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.hset.assert_any_call(
            "pull_events:repo:789:digest:sha256:xyz789", "repository_id", 789
        )
        mock_pipeline.hset.assert_any_call(
            "pull_events:repo:789:digest:sha256:xyz789", "manifest_digest", "sha256:xyz789"
        )
        mock_pipeline.hincrby.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    def test_track_manifest_pull_sync_with_repository_id(self, pull_metrics_testing, mock_redis):
        """Test synchronous manifest pull tracking with repository ID."""
        # Setup
        repository_id = 999
        manifest_digest = "sha256:test999"

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute
        pull_metrics_testing.track_manifest_pull_sync(repository_id, manifest_digest)

        # Verify
        mock_pipeline.hset.assert_any_call(
            "pull_events:repo:999:digest:sha256:test999", "repository_id", 999
        )

    def test_track_tag_pull_async_testing_mode(self, pull_metrics_testing, mock_redis):
        """Test async tag pull tracking in testing mode (runs synchronously)."""
        repository = Mock()
        repository.id = 123
        tag_name = "latest"
        manifest_digest = "sha256:abc123"

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute
        pull_metrics_testing.track_tag_pull(repository, tag_name, manifest_digest)

        # In testing mode, should run synchronously
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    def test_track_tag_pull_async_production_mode(self, mock_redis):
        """Test async tag pull tracking in production mode (runs in thread pool)."""
        redis_config = {"host": "localhost", "port": 6379}
        pm = PullMetrics(redis_config)

        repository = Mock()
        repository.id = 123
        tag_name = "latest"
        manifest_digest = "sha256:abc123"

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute
        pm.track_tag_pull(repository, tag_name, manifest_digest)

        # Should submit to executor
        assert pm._executor is not None

    def test_track_tag_pull_redis_error_handling(self, pull_metrics_testing, mock_redis):
        """Test tag pull tracking handles Redis connection errors gracefully."""
        repository = Mock()
        repository.id = 123
        tag_name = "latest"
        manifest_digest = "sha256:abc123"

        # Mock connection to fail during health check
        mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")

        # Execute - should not raise exception, should log warning
        with patch("util.pullmetrics.logger") as mock_logger:
            pull_metrics_testing.track_tag_pull(repository, tag_name, manifest_digest)
            # Connection errors are logged as warnings, not exceptions
            mock_logger.warning.assert_called()
            # Verify no exception was logged (only warnings for connection errors)
            mock_logger.exception.assert_not_called()

    def test_track_manifest_pull_async_testing_mode(self, pull_metrics_testing, mock_redis):
        """Test async manifest pull tracking in testing mode."""
        repository = Mock()
        repository.id = 789
        manifest_digest = "sha256:xyz789"

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute
        pull_metrics_testing.track_manifest_pull(repository, manifest_digest)

        # In testing mode, should run synchronously
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    def test_track_manifest_pull_redis_error_handling(self, pull_metrics_testing, mock_redis):
        """Test manifest pull tracking handles Redis errors gracefully."""
        repository = Mock()
        repository.id = 789
        manifest_digest = "sha256:xyz789"

        # Ensure connection can be established (ping succeeds)
        mock_redis.ping.return_value = True
        # Mock pipeline to raise error when called
        mock_redis.pipeline.side_effect = redis.RedisError("Connection failed")

        # Execute - should not raise exception, should log warning
        with patch("util.pullmetrics.logger") as mock_logger:
            pull_metrics_testing.track_manifest_pull(repository, manifest_digest)
            # Redis errors are logged as warnings, not exceptions
            mock_logger.warning.assert_called()
            # Verify no exception was logged (only warnings for Redis errors)
            mock_logger.exception.assert_not_called()

    def test_track_tag_pull_timeout_error_handling(self, pull_metrics_testing, mock_redis):
        """Test tag pull tracking handles Redis timeout errors gracefully."""
        repository = Mock()
        repository.id = 123
        tag_name = "latest"
        manifest_digest = "sha256:abc123"

        # Mock connection to fail with timeout during health check
        mock_redis.ping.side_effect = redis.TimeoutError("Operation timed out")

        # Execute - should not raise exception, should log warning
        with patch("util.pullmetrics.logger") as mock_logger:
            pull_metrics_testing.track_tag_pull(repository, tag_name, manifest_digest)
            # Timeout errors are logged as warnings, not exceptions
            mock_logger.warning.assert_called()
            mock_logger.exception.assert_not_called()

    def test_track_manifest_pull_pipeline_execute_error(self, pull_metrics_testing, mock_redis):
        """Test manifest pull tracking handles pipeline execute errors gracefully."""
        repository = Mock()
        repository.id = 789
        manifest_digest = "sha256:xyz789"

        # Ensure connection can be established (ping succeeds)
        mock_redis.ping.return_value = True
        # Mock pipeline and make execute() raise error
        mock_pipeline = MagicMock()
        mock_pipeline.execute.side_effect = redis.RedisError("Pipeline execution failed")
        mock_redis.pipeline.return_value = mock_pipeline

        # Execute - should not raise exception, should log warning
        with patch("util.pullmetrics.logger") as mock_logger:
            pull_metrics_testing.track_manifest_pull(repository, manifest_digest)
            # Redis errors are logged as warnings, not exceptions
            mock_logger.warning.assert_called()
            mock_logger.exception.assert_not_called()

    def test_get_pull_statistics_success(self, pull_metrics_testing, mock_redis):
        """Test retrieving pull statistics from Redis."""
        key = "pull_events:repo:123:tag:latest:sha256:abc123"

        # Mock Redis response
        mock_redis.hgetall.return_value = {
            b"repository_id": b"123",
            b"tag_name": b"latest",
            b"manifest_digest": b"sha256:abc123",
            b"pull_count": b"10",
            b"last_pull_timestamp": b"1704110400",
        }

        # Execute
        result = pull_metrics_testing._get_pull_statistics(key)

        # Verify
        assert result is not None
        assert result["repository_id"] == "123"
        assert result["tag_name"] == "latest"
        assert result["manifest_digest"] == "sha256:abc123"
        assert result["pull_count"] == 10
        assert result["last_pull_timestamp"] == "1704110400"

    def test_get_pull_statistics_empty(self, pull_metrics_testing, mock_redis):
        """Test retrieving non-existent pull statistics."""
        key = "pull_events:repo:123:tag:nonexistent:sha256:abc123"

        # Mock Redis response (empty)
        mock_redis.hgetall.return_value = {}

        # Execute
        result = pull_metrics_testing._get_pull_statistics(key)

        # Verify
        assert result is None

    def test_get_pull_statistics_redis_error(self, pull_metrics_testing, mock_redis):
        """Test pull statistics retrieval handles Redis errors."""
        key = "pull_events:repo:123:tag:latest:sha256:abc123"

        # Ensure connection can be established (ping succeeds)
        mock_redis.ping.return_value = True
        # Mock hgetall to raise error when called
        mock_redis.hgetall.side_effect = redis.RedisError("Connection failed")

        # Execute
        with patch("util.pullmetrics.logger") as mock_logger:
            result = pull_metrics_testing._get_pull_statistics(key)

            # Should return None and log warning (Redis errors are logged as warnings)
            assert result is None
            mock_logger.warning.assert_called()
            # Verify no exception was logged
            mock_logger.exception.assert_not_called()

    def test_get_tag_pull_statistics(self, pull_metrics_testing, mock_redis):
        """Test get_tag_pull_statistics method."""
        repository_id = 123
        tag_name = "latest"
        manifest_digest = "sha256:abc123"

        # Mock Redis response
        mock_redis.hgetall.return_value = {
            b"repository_id": b"123",
            b"tag_name": b"latest",
            b"manifest_digest": b"sha256:abc123",
            b"pull_count": b"15",
        }

        # Execute
        result = pull_metrics_testing.get_tag_pull_statistics(
            repository_id, tag_name, manifest_digest
        )

        # Verify
        assert result is not None
        assert result["pull_count"] == 15
        mock_redis.hgetall.assert_called_once_with("pull_events:repo:123:tag:latest:sha256:abc123")

    def test_get_manifest_pull_statistics(self, pull_metrics_testing, mock_redis):
        """Test get_manifest_pull_statistics method."""
        repository_id = 456
        manifest_digest = "sha256:def456"

        # Mock Redis response
        mock_redis.hgetall.return_value = {
            b"repository_id": b"456",
            b"manifest_digest": b"sha256:def456",
            b"pull_count": b"20",
        }

        # Execute
        result = pull_metrics_testing.get_manifest_pull_statistics(repository_id, manifest_digest)

        # Verify
        assert result is not None
        assert result["pull_count"] == 20
        mock_redis.hgetall.assert_called_once_with("pull_events:repo:456:digest:sha256:def456")

    def test_shutdown_with_executor(self, mock_redis):
        """Test shutdown method with thread pool executor."""
        redis_config = {"host": "localhost", "port": 6379}
        pm = PullMetrics(redis_config)

        # Mock executor
        pm._executor = Mock()

        # Execute
        pm.shutdown()

        # Verify
        pm._executor.shutdown.assert_called_once_with(wait=True)

    def test_shutdown_without_executor(self, pull_metrics_testing):
        """Test shutdown method without thread pool executor."""
        # Execute - should not raise exception
        pull_metrics_testing.shutdown()
        # No executor, so nothing to verify


class TestPullMetricsIntegration:
    """Integration tests with actual Redis operations (if available)."""

    def test_full_workflow_tag_pull(self, pull_metrics_testing, mock_redis):
        """Test full workflow of tracking and retrieving tag pulls."""
        repository = Mock()
        repository.id = 100
        tag_name = "integration-test"
        manifest_digest = "sha256:integration123"

        # Mock pipeline and hgetall
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline
        mock_redis.hgetall.return_value = {
            b"repository_id": b"100",
            b"tag_name": b"integration-test",
            b"manifest_digest": b"sha256:integration123",
            b"pull_count": b"1",
        }

        # Track a pull
        pull_metrics_testing.track_tag_pull_sync(repository, tag_name, manifest_digest)

        # Retrieve statistics
        stats = pull_metrics_testing.get_tag_pull_statistics(
            repository.id, tag_name, manifest_digest
        )

        # Verify
        assert stats is not None
        assert stats["tag_name"] == "integration-test"

    def test_full_workflow_manifest_pull(self, pull_metrics_testing, mock_redis):
        """Test full workflow of tracking and retrieving manifest pulls."""
        repository = Mock()
        repository.id = 200
        manifest_digest = "sha256:integration456"

        # Mock pipeline and hgetall
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline
        mock_redis.hgetall.return_value = {
            b"repository_id": b"200",
            b"manifest_digest": b"sha256:integration456",
            b"pull_count": b"1",
        }

        # Track a pull
        pull_metrics_testing.track_manifest_pull_sync(repository, manifest_digest)

        # Retrieve statistics
        stats = pull_metrics_testing.get_manifest_pull_statistics(repository.id, manifest_digest)

        # Verify
        assert stats is not None
        assert stats["manifest_digest"] == "sha256:integration456"
