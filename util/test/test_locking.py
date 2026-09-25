"""
Tests for util/locking.py — Redis-backed global locking.

Covers engine-config routing through create_redis_client.
"""

from functools import partial
from unittest.mock import MagicMock, patch

import redis_lock

from util.locking import _redis_lock_factory


class TestRedisLockFactory:
    """Tests for _redis_lock_factory()."""

    @patch("util.locking.Redis")
    def test_legacy_config_uses_redis_directly(self, mock_redis_class):
        """Legacy config (no engine) should instantiate Redis directly."""
        mock_conn = MagicMock()
        mock_redis_class.return_value = mock_conn

        config = {"USER_EVENTS_REDIS": {"host": "localhost", "port": 6379}}
        factory = _redis_lock_factory(config)

        mock_redis_class.assert_called_once()
        call_kwargs = mock_redis_class.call_args[1]
        assert call_kwargs["host"] == "localhost"
        assert call_kwargs["socket_connect_timeout"] == 5
        assert isinstance(factory, partial)

    @patch("util.locking.create_redis_client")
    def test_engine_config_uses_factory(self, mock_create_client):
        """Engine-based config should route through create_redis_client."""
        mock_conn = MagicMock()
        mock_create_client.return_value = mock_conn

        engine_config = {
            "engine": "redis",
            "redis_config": {"host": "redis.example.com", "port": 6379},
        }
        config = {"USER_EVENTS_REDIS": engine_config}
        factory = _redis_lock_factory(config)

        mock_create_client.assert_called_once_with(engine_config, default_timeout=5)
        assert isinstance(factory, partial)

    @patch("util.locking.create_redis_client")
    def test_cluster_config_uses_factory(self, mock_create_client):
        """Cluster config should also route through create_redis_client."""
        mock_conn = MagicMock()
        mock_create_client.return_value = mock_conn

        cluster_config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
            },
        }
        config = {"USER_EVENTS_REDIS": cluster_config}
        factory = _redis_lock_factory(config)

        mock_create_client.assert_called_once_with(cluster_config, default_timeout=5)
        assert isinstance(factory, partial)
