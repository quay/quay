"""Fixtures for Redis integration tests (standalone and cluster).

Standalone tests use the docker-compose ``redis`` service on port 6379.
Cluster tests require the Redis Cluster overlay (``docker-compose.redis-cluster.yaml``)
and use ports 7000-7005.

Set the environment variable ``REDIS_CLUSTER_URL=localhost`` to enable cluster tests.
If the variable is unset, cluster tests are automatically skipped.
"""

import os

import pytest
import redis
import redis.cluster

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_CLUSTER_URL = os.environ.get("REDIS_CLUSTER_URL", "")
REDIS_CLUSTER_PORT = int(os.environ.get("REDIS_CLUSTER_PORT", 7000))


def _redis_reachable(host, port):
    """Return True if a standalone Redis is reachable at *host*:*port*."""
    try:
        c = redis.StrictRedis(host=host, port=port, socket_connect_timeout=2)
        c.ping()
        c.close()
        return True
    except Exception:
        return False


def _cluster_reachable(host, port):
    """Return True if a Redis Cluster is reachable at *host*:*port*."""
    try:
        c = redis.cluster.RedisCluster(
            host=host,
            port=port,
            socket_connect_timeout=2,
            require_full_coverage=False,
        )
        c.ping()
        c.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def redis_standalone():
    """Yield a ``StrictRedis`` client connected to the local standalone Redis.

    Skips if no Redis is listening on ``REDIS_HOST:REDIS_PORT``.
    """
    if not _redis_reachable(REDIS_HOST, REDIS_PORT):
        pytest.skip(f"Standalone Redis not available at {REDIS_HOST}:{REDIS_PORT}")
    client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    yield client
    client.close()


@pytest.fixture(scope="session")
def redis_cluster():
    """Yield a ``RedisCluster`` client connected to the local Redis Cluster.

    Skips if ``REDIS_CLUSTER_URL`` is not set or the cluster is not reachable.
    """
    if not REDIS_CLUSTER_URL:
        pytest.skip("REDIS_CLUSTER_URL not set; skipping Redis Cluster tests")
    if not _cluster_reachable(REDIS_CLUSTER_URL, REDIS_CLUSTER_PORT):
        pytest.skip(f"Redis Cluster not available at {REDIS_CLUSTER_URL}:{REDIS_CLUSTER_PORT}")
    client = redis.cluster.RedisCluster(
        host=REDIS_CLUSTER_URL,
        port=REDIS_CLUSTER_PORT,
        decode_responses=True,
        require_full_coverage=False,
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def redis_cluster_config():
    """Return an engine-based config dict suitable for ``create_redis_client``.

    Skips if ``REDIS_CLUSTER_URL`` is not set.
    """
    if not REDIS_CLUSTER_URL:
        pytest.skip("REDIS_CLUSTER_URL not set; skipping Redis Cluster tests")
    return {
        "engine": "rediscluster",
        "redis_config": {
            "startup_nodes": [
                {"host": REDIS_CLUSTER_URL, "port": str(REDIS_CLUSTER_PORT)},
                {"host": REDIS_CLUSTER_URL, "port": str(REDIS_CLUSTER_PORT + 1)},
                {"host": REDIS_CLUSTER_URL, "port": str(REDIS_CLUSTER_PORT + 2)},
            ],
            "require_full_coverage": False,
        },
    }


@pytest.fixture(scope="session")
def redis_standalone_config():
    """Return an engine-based config dict for standalone Redis.

    Skips if standalone Redis is not reachable.
    """
    if not _redis_reachable(REDIS_HOST, REDIS_PORT):
        pytest.skip(f"Standalone Redis not available at {REDIS_HOST}:{REDIS_PORT}")
    return {
        "engine": "redis",
        "redis_config": {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
        },
    }
