import json
from unittest.mock import Mock, patch

import pytest

from data.pullmetrics import PullMetrics, PullMetricsBuilder, PullMetricsBuilderModule


class TestPullMetrics:
    """Test cases for pull metrics functionality."""

    def test_pull_metrics_builder_initialization(self):
        """Test that PullMetricsBuilder initializes correctly."""
        redis_config = {"host": "localhost", "port": 6379}
        builder = PullMetricsBuilder(redis_config)

        assert builder._redis_config == redis_config
        assert hasattr(builder, "get_metrics")
        assert hasattr(builder, "get_listener")

    def test_pull_metrics_initialization(self):
        """Test that PullMetrics initializes correctly."""
        redis_config = {"host": "localhost", "port": 6379}
        with patch("data.pullmetrics.redis.StrictRedis") as mock_redis:
            metrics = PullMetrics(redis_config)
            mock_redis.assert_called_once_with(
                socket_connect_timeout=2, socket_timeout=2, **redis_config
            )

    def test_tag_pull_key_generation(self):
        """Test tag pull key generation."""
        redis_config = {"host": "localhost", "port": 6379}
        with patch("data.pullmetrics.redis.StrictRedis"):
            metrics = PullMetrics(redis_config)

            key = metrics._tag_pull_key("namespace/repo", "v1.0")
            assert key == "pull_metrics/tag/namespace/repo/v1.0"

    def test_manifest_pull_key_generation(self):
        """Test manifest pull key generation."""
        redis_config = {"host": "localhost", "port": 6379}
        with patch("data.pullmetrics.redis.StrictRedis"):
            metrics = PullMetrics(redis_config)

            key = metrics._manifest_pull_key("namespace/repo", "sha256:abc123")
            assert key == "pull_metrics/manifest/namespace/repo/sha256:abc123"

    @patch("data.pullmetrics.redis.StrictRedis")
    def test_track_tag_pull_sync(self, mock_redis_class):
        """Test synchronous tag pull tracking."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline

        redis_config = {"host": "localhost", "port": 6379}
        metrics = PullMetrics(redis_config)

        result = metrics.track_tag_pull_sync("namespace/repo", "v1.0", "sha256:abc123")

        assert result is True
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    @patch("data.pullmetrics.redis.StrictRedis")
    def test_track_manifest_pull_sync(self, mock_redis_class):
        """Test synchronous manifest pull tracking."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline

        redis_config = {"host": "localhost", "port": 6379}
        metrics = PullMetrics(redis_config)

        result = metrics.track_manifest_pull_sync("namespace/repo", "sha256:abc123")

        assert result is True
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    @patch("data.pullmetrics.redis.StrictRedis")
    def test_get_tag_pull_statistics(self, mock_redis_class):
        """Test getting tag pull statistics."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        # Mock Redis response
        mock_redis.hgetall.return_value = {
            b"pull_count": b"5",
            b"last_pull_date": b"2024-01-01T10:00:00Z",
            b"current_manifest_digest": b"sha256:abc123",
        }

        redis_config = {"host": "localhost", "port": 6379}
        metrics = PullMetrics(redis_config)

        stats = metrics.get_tag_pull_statistics("namespace/repo", "v1.0")

        assert stats is not None
        assert stats["pull_count"] == 5
        assert stats["last_pull_date"] == "2024-01-01T10:00:00Z"
        assert stats["current_manifest_digest"] == "sha256:abc123"

    @patch("data.pullmetrics.redis.StrictRedis")
    def test_get_manifest_pull_statistics(self, mock_redis_class):
        """Test getting manifest pull statistics."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        # Mock Redis response
        mock_redis.hgetall.return_value = {
            b"pull_count": b"10",
            b"last_pull_date": b"2024-01-01T10:00:00Z",
        }

        redis_config = {"host": "localhost", "port": 6379}
        metrics = PullMetrics(redis_config)

        stats = metrics.get_manifest_pull_statistics("namespace/repo", "sha256:abc123")

        assert stats is not None
        assert stats["pull_count"] == 10
        assert stats["last_pull_date"] == "2024-01-01T10:00:00Z"

    @patch("data.pullmetrics.redis.StrictRedis")
    def test_get_tag_pull_statistics_no_data(self, mock_redis_class):
        """Test getting tag pull statistics when no data exists."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.hgetall.return_value = {}

        redis_config = {"host": "localhost", "port": 6379}
        metrics = PullMetrics(redis_config)

        stats = metrics.get_tag_pull_statistics("namespace/repo", "v1.0")

        assert stats is None

    @patch("data.pullmetrics.redis.StrictRedis")
    def test_get_manifest_pull_statistics_no_data(self, mock_redis_class):
        """Test getting manifest pull statistics when no data exists."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.hgetall.return_value = {}

        redis_config = {"host": "localhost", "port": 6379}
        metrics = PullMetrics(redis_config)

        stats = metrics.get_manifest_pull_statistics("namespace/repo", "sha256:abc123")

        assert stats is None

    @patch("data.pullmetrics.threading.Thread")
    def test_track_tag_pull_async(self, mock_thread):
        """Test asynchronous tag pull tracking."""
        redis_config = {"host": "localhost", "port": 6379}
        with patch("data.pullmetrics.redis.StrictRedis"):
            metrics = PullMetrics(redis_config)
            metrics.track_tag_pull("namespace/repo", "v1.0", "sha256:abc123")

            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()

    @patch("data.pullmetrics.threading.Thread")
    def test_track_manifest_pull_async(self, mock_thread):
        """Test asynchronous manifest pull tracking."""
        redis_config = {"host": "localhost", "port": 6379}
        with patch("data.pullmetrics.redis.StrictRedis"):
            metrics = PullMetrics(redis_config)
            metrics.track_manifest_pull("namespace/repo", "sha256:abc123")

            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()


class TestPullMetricsBuilderModule:
    """Test cases for PullMetricsBuilderModule."""

    def test_init_app_with_pull_metrics_redis(self):
        """Test module initialization with PULL_METRICS_REDIS config."""
        app = Mock()
        app.config = {"PULL_METRICS_REDIS": {"host": "localhost", "port": 6379}}
        app.extensions = {}

        module = PullMetricsBuilderModule()
        result = module.init_app(app)

        assert result is not None
        assert "pullmetrics" in app.extensions

    def test_init_app_with_user_events_redis_fallback(self):
        """Test module initialization with USER_EVENTS_REDIS fallback."""
        app = Mock()
        app.config = {"USER_EVENTS_REDIS": {"host": "localhost", "port": 6379}}
        app.extensions = {}

        module = PullMetricsBuilderModule()
        result = module.init_app(app)

        assert result is not None
        assert "pullmetrics" in app.extensions

    def test_init_app_with_legacy_config(self):
        """Test module initialization with legacy USER_EVENTS_REDIS_HOSTNAME config."""
        app = Mock()
        app.config = {"USER_EVENTS_REDIS_HOSTNAME": "localhost"}
        app.extensions = {}

        module = PullMetricsBuilderModule()
        result = module.init_app(app)

        assert result is not None
        assert "pullmetrics" in app.extensions
