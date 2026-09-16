"""
Tests for util/redis_utils.py — shared Redis client factory.

Covers:
- Legacy single-node configuration (backward compatibility)
- Explicit engine=redis configuration
- engine=rediscluster configuration with startup_nodes
- readonly_mode → read_from_replicas migration
- Default timeout application
- Extra kwargs forwarding
- Error cases (missing config, invalid engine, etc.)
- is_cluster_config() helper
"""

from unittest.mock import MagicMock, call, patch

import pytest

from util.redis_utils import (
    REDIS_DRIVERS,
    create_redis_client,
    has_engine_config,
    is_cluster_config,
)


class TestIsClusterConfig:
    """Tests for the is_cluster_config() helper."""

    def test_none_config(self):
        assert is_cluster_config(None) is False

    def test_empty_config(self):
        assert is_cluster_config({}) is False

    def test_legacy_config(self):
        assert is_cluster_config({"host": "localhost", "port": 6379}) is False

    def test_engine_redis(self):
        assert is_cluster_config({"engine": "redis", "redis_config": {}}) is False

    def test_engine_rediscluster(self):
        assert is_cluster_config({"engine": "rediscluster", "redis_config": {}}) is True

    def test_engine_rediscluster_uppercase(self):
        assert is_cluster_config({"engine": "RedisCluster", "redis_config": {}}) is True


class TestCreateRedisClientLegacy:
    """Tests for legacy (no engine key) configuration."""

    @patch("util.redis_utils.StrictRedis")
    def test_legacy_host_port(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {"host": "localhost", "port": 6379}

        client = create_redis_client(config)

        mock_strict_redis.assert_called_once_with(host="localhost", port=6379)
        assert client is mock_strict_redis.return_value

    @patch("util.redis_utils.StrictRedis")
    def test_legacy_with_password(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {"host": "localhost", "port": 6379, "password": "secret"}

        create_redis_client(config)

        mock_strict_redis.assert_called_once_with(
            host="localhost", port=6379, password="secret"
        )

    @patch("util.redis_utils.StrictRedis")
    def test_legacy_with_default_timeout(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {"host": "localhost"}

        create_redis_client(config, default_timeout=5)

        mock_strict_redis.assert_called_once_with(
            host="localhost",
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    @patch("util.redis_utils.StrictRedis")
    def test_legacy_timeout_not_overridden(self, mock_strict_redis):
        """Existing timeout in config should not be overridden by default_timeout."""
        mock_strict_redis.return_value = MagicMock()
        config = {"host": "localhost", "socket_connect_timeout": 2}

        create_redis_client(config, default_timeout=5)

        call_kwargs = mock_strict_redis.call_args[1]
        assert call_kwargs["socket_connect_timeout"] == 2
        assert call_kwargs["socket_timeout"] == 5

    @patch("util.redis_utils.StrictRedis")
    def test_legacy_with_extra_kwargs(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {"host": "localhost"}

        create_redis_client(config, extra_kwargs={"decode_responses": True})

        mock_strict_redis.assert_called_once_with(
            host="localhost", decode_responses=True
        )


class TestCreateRedisClientSingleNode:
    """Tests for explicit engine=redis configuration."""

    @patch("util.redis_utils.StrictRedis")
    def test_engine_redis(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {
            "engine": "redis",
            "redis_config": {"host": "redis.example.com", "port": 6379, "password": "pw"},
        }

        client = create_redis_client(config)

        mock_strict_redis.assert_called_once_with(
            host="redis.example.com", port=6379, password="pw"
        )
        assert client is mock_strict_redis.return_value

    @patch("util.redis_utils.StrictRedis")
    def test_engine_redis_with_db(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {
            "engine": "redis",
            "redis_config": {"host": "localhost", "db": 1},
        }

        create_redis_client(config)

        mock_strict_redis.assert_called_once_with(host="localhost", db=1)

    @patch("util.redis_utils.StrictRedis")
    def test_engine_redis_with_ssl(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {
            "engine": "redis",
            "redis_config": {"host": "secure.redis.com", "ssl": True},
        }

        create_redis_client(config)

        mock_strict_redis.assert_called_once_with(host="secure.redis.com", ssl=True)


class TestCreateRedisClientCluster:
    """Tests for engine=rediscluster configuration."""

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_cluster_with_startup_nodes(self, mock_cluster_node, mock_redis_cluster):
        mock_redis_cluster.return_value = MagicMock()
        node_a = MagicMock()
        node_b = MagicMock()
        mock_cluster_node.side_effect = [node_a, node_b]

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [
                    {"host": "node1", "port": 6379},
                    {"host": "node2", "port": 6380},
                ],
                "read_from_replicas": True,
            },
        }

        client = create_redis_client(config)

        mock_cluster_node.assert_any_call(host="node1", port=6379)
        mock_cluster_node.assert_any_call(host="node2", port=6380)
        mock_redis_cluster.assert_called_once_with(
            startup_nodes=[node_a, node_b],
            read_from_replicas=True,
        )
        assert client is mock_redis_cluster.return_value

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_cluster_readonly_mode_migration(self, mock_cluster_node, mock_redis_cluster):
        """readonly_mode should be automatically converted to read_from_replicas."""
        mock_redis_cluster.return_value = MagicMock()
        mock_cluster_node.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
                "readonly_mode": True,
            },
        }

        create_redis_client(config)

        call_kwargs = mock_redis_cluster.call_args[1]
        assert "readonly_mode" not in call_kwargs
        assert call_kwargs["read_from_replicas"] is True

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_cluster_with_password_and_ssl(self, mock_cluster_node, mock_redis_cluster):
        mock_redis_cluster.return_value = MagicMock()
        mock_cluster_node.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
                "password": "cluster-secret",
                "ssl": True,
            },
        }

        create_redis_client(config)

        call_kwargs = mock_redis_cluster.call_args[1]
        assert call_kwargs["password"] == "cluster-secret"
        assert call_kwargs["ssl"] is True

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_cluster_with_default_timeout(self, mock_cluster_node, mock_redis_cluster):
        mock_redis_cluster.return_value = MagicMock()
        mock_cluster_node.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
            },
        }

        create_redis_client(config, default_timeout=3)

        call_kwargs = mock_redis_cluster.call_args[1]
        assert call_kwargs["socket_connect_timeout"] == 3
        assert call_kwargs["socket_timeout"] == 3

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_cluster_with_extra_kwargs(self, mock_cluster_node, mock_redis_cluster):
        mock_redis_cluster.return_value = MagicMock()
        mock_cluster_node.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
            },
        }

        create_redis_client(config, extra_kwargs={"decode_responses": True})

        call_kwargs = mock_redis_cluster.call_args[1]
        assert call_kwargs["decode_responses"] is True


class TestCreateRedisClientErrors:
    """Tests for error handling."""

    def test_none_config_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            create_redis_client(None)

    def test_empty_config_raises(self):
        with pytest.raises(ValueError, match="non-empty dict"):
            create_redis_client({})

    def test_invalid_engine_raises(self):
        config = {"engine": "memcache", "redis_config": {}}
        with pytest.raises(ValueError, match="Invalid Redis engine"):
            create_redis_client(config)

    def test_missing_redis_config_raises(self):
        config = {"engine": "rediscluster"}
        with pytest.raises(ValueError, match="redis_config.*required"):
            create_redis_client(config)

    def test_empty_redis_config_raises(self):
        config = {"engine": "redis", "redis_config": {}}
        with pytest.raises(ValueError, match="redis_config.*required"):
            create_redis_client(config)


class TestConfigIsolation:
    """Ensure the original config dict is not mutated."""

    @patch("util.redis_utils.StrictRedis")
    def test_legacy_config_not_mutated(self, mock_strict_redis):
        mock_strict_redis.return_value = MagicMock()
        config = {"host": "localhost", "port": 6379}
        original = dict(config)

        create_redis_client(config)

        assert config == original

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_cluster_config_not_mutated(self, mock_cluster_node, mock_redis_cluster):
        mock_redis_cluster.return_value = MagicMock()
        mock_cluster_node.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
                "readonly_mode": True,
            },
        }
        import copy

        original = copy.deepcopy(config)

        create_redis_client(config)

        assert config == original


class TestHasEngineConfig:
    """Tests for the has_engine_config() helper."""

    def test_none_config(self):
        assert has_engine_config(None) is False

    def test_empty_config(self):
        assert has_engine_config({}) is False

    def test_legacy_config(self):
        assert has_engine_config({"host": "localhost", "port": 6379}) is False

    def test_engine_redis(self):
        assert has_engine_config({"engine": "redis", "redis_config": {}}) is True

    def test_engine_rediscluster(self):
        assert has_engine_config({"engine": "rediscluster", "redis_config": {}}) is True


class TestSkipFullCoverageCheckMigration:
    """Tests for skip_full_coverage_check → require_full_coverage translation."""

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_skip_true_becomes_require_false(self, mock_cluster_node, mock_redis_cluster):
        """skip_full_coverage_check=True should translate to require_full_coverage=False."""
        mock_redis_cluster.return_value = MagicMock()
        mock_cluster_node.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
                "skip_full_coverage_check": True,
            },
        }

        create_redis_client(config)

        call_kwargs = mock_redis_cluster.call_args[1]
        assert "skip_full_coverage_check" not in call_kwargs
        assert call_kwargs["require_full_coverage"] is False

    @patch("util.redis_utils.RedisCluster")
    @patch("util.redis_utils.ClusterNode")
    def test_skip_false_becomes_require_true(self, mock_cluster_node, mock_redis_cluster):
        """skip_full_coverage_check=False should translate to require_full_coverage=True."""
        mock_redis_cluster.return_value = MagicMock()
        mock_cluster_node.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "startup_nodes": [{"host": "node1", "port": 6379}],
                "skip_full_coverage_check": False,
            },
        }

        create_redis_client(config)

        call_kwargs = mock_redis_cluster.call_args[1]
        assert call_kwargs["require_full_coverage"] is True


class TestClusterValidation:
    """Tests for cluster-specific validation."""

    def test_cluster_without_startup_nodes_or_host_raises(self):
        """rediscluster without startup_nodes or host should raise ValueError."""
        config = {
            "engine": "rediscluster",
            "redis_config": {
                "password": "secret",
            },
        }
        with pytest.raises(ValueError, match="startup_nodes.*host"):
            create_redis_client(config)

    @patch("util.redis_utils.RedisCluster")
    def test_cluster_with_host_only_accepted(self, mock_redis_cluster):
        """rediscluster with host (no startup_nodes) should work."""
        mock_redis_cluster.return_value = MagicMock()

        config = {
            "engine": "rediscluster",
            "redis_config": {
                "host": "cluster-node.example.com",
                "port": 6379,
            },
        }

        client = create_redis_client(config)
        assert client is mock_redis_cluster.return_value
