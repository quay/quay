"""Integration tests for ``util.redis_utils`` against real Redis instances.

These tests verify that ``create_redis_client`` produces working clients when
connected to either a standalone Redis (docker-compose ``redis`` service on
port 6379) or a Redis Cluster (``docker-compose.redis-cluster.yaml`` on
ports 7000-7005).

Run standalone tests::

    docker compose up -d redis
    TEST=true PYTHONPATH=. pytest util/test/test_redis_integration.py -v -k standalone

Run cluster tests::

    docker compose -f docker-compose.redis-cluster.yaml up -d \\
        redis-node-0 redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5
    # Wait ~5s for healthy, then form cluster (see compose file header):
    #   podman exec redis-node-0 redis-cli --cluster create \\
    #       127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \\
    #       127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \\
    #       --cluster-replicas 1 --cluster-yes
    TEST=true PYTHONPATH=. REDIS_CLUSTER_URL=localhost \\
        pytest util/test/test_redis_integration.py -v -m redis_cluster

Run all::

    TEST=true PYTHONPATH=. REDIS_CLUSTER_URL=localhost \\
        pytest util/test/test_redis_integration.py -v
"""

import uuid

import pytest

from util.redis_utils import create_redis_client, is_cluster_config


class TestStandaloneRedisIntegration:
    """Integration tests against a real standalone Redis."""

    def test_create_client_connects(self, redis_standalone_config):
        """create_redis_client with engine=redis should return a working client."""
        client = create_redis_client(redis_standalone_config, default_timeout=5)
        assert client.ping()
        client.close()

    def test_set_get_round_trip(self, redis_standalone_config):
        """Keys set via the factory-created client should be readable."""
        key = f"rfe9838:test:{uuid.uuid4().hex[:8]}"
        client = create_redis_client(redis_standalone_config, default_timeout=5)
        try:
            client.set(key, "hello")
            assert client.get(key) in (b"hello", "hello")
        finally:
            client.delete(key)
            client.close()

    def test_pipeline_operations(self, redis_standalone_config):
        """Pipeline operations should work through the factory-created client."""
        key = f"rfe9838:pipeline:{uuid.uuid4().hex[:8]}"
        client = create_redis_client(redis_standalone_config, default_timeout=5)
        try:
            pipe = client.pipeline()
            pipe.set(key, "42")
            pipe.incr(key)
            pipe.get(key)
            results = pipe.execute()
            assert results[-1] in (b"43", "43")
        finally:
            client.delete(key)
            client.close()

    def test_is_not_cluster_config(self, redis_standalone_config):
        """Standalone config should not be identified as cluster."""
        assert not is_cluster_config(redis_standalone_config)


@pytest.mark.redis_cluster
class TestClusterRedisIntegration:
    """Integration tests against a real Redis Cluster.

    Requires ``REDIS_CLUSTER_URL`` environment variable and a running cluster.
    """

    def test_create_client_connects(self, redis_cluster_config):
        """create_redis_client with engine=rediscluster should return a working client."""
        client = create_redis_client(redis_cluster_config, default_timeout=5)
        assert client.ping()
        client.close()

    def test_is_cluster_config(self, redis_cluster_config):
        """Cluster config should be identified as cluster."""
        assert is_cluster_config(redis_cluster_config)

    def test_set_get_round_trip(self, redis_cluster_config):
        """Keys set via a cluster client should be readable."""
        key = f"rfe9838:test:{uuid.uuid4().hex[:8]}"
        client = create_redis_client(redis_cluster_config, default_timeout=5)
        try:
            client.set(key, "world")
            assert client.get(key) in (b"world", "world")
        finally:
            client.delete(key)
            client.close()

    def test_hash_tagged_keys_same_slot(self, redis_cluster_config):
        """Hash-tagged keys with the same tag should land in the same slot."""
        tag = uuid.uuid4().hex[:8]
        key1 = f"pull_events:repo:{{{tag}}}:tag:latest:1"
        key2 = f"pull_events:repo:{{{tag}}}:tag:v1.0:2"
        client = create_redis_client(redis_cluster_config, default_timeout=5)
        try:
            pipe = client.pipeline()
            pipe.set(key1, "a")
            pipe.set(key2, "b")
            pipe.execute()
            assert client.get(key1) in (b"a", "a")
            assert client.get(key2) in (b"b", "b")
        finally:
            client.delete(key1, key2)
            client.close()

    def test_cluster_pipeline_within_hash_tag(self, redis_cluster_config):
        """Pipeline operations on keys sharing a hash tag should succeed."""
        tag = uuid.uuid4().hex[:8]
        key = f"rfe9838:pipe:{{{tag}}}:counter"
        client = create_redis_client(redis_cluster_config, default_timeout=5)
        try:
            pipe = client.pipeline()
            pipe.set(key, "0")
            pipe.incr(key)
            pipe.incr(key)
            pipe.get(key)
            results = pipe.execute()
            assert results[-1] in (b"2", "2")
        finally:
            client.delete(key)
            client.close()

    def test_scan_iter_across_cluster(self, redis_cluster_config):
        """scan_iter should discover keys spread across cluster shards."""
        prefix = f"rfe9838:scan:{uuid.uuid4().hex[:8]}"
        client = create_redis_client(redis_cluster_config, default_timeout=5)
        keys = [f"{prefix}:{i}" for i in range(10)]
        try:
            for k in keys:
                client.set(k, "v")
            found = list(client.scan_iter(match=f"{prefix}:*", count=100))
            found_decoded = {k.decode() if isinstance(k, bytes) else k for k in found}
            assert found_decoded == set(keys)
        finally:
            for k in keys:
                client.delete(k)
            client.close()

    def test_pubsub_in_cluster(self, redis_cluster):
        """Pub/Sub should work in cluster mode (sharded channels)."""
        channel = f"rfe9838:pubsub:{uuid.uuid4().hex[:8]}"
        pubsub = redis_cluster.pubsub()
        try:
            pubsub.subscribe(channel)
            msg = pubsub.get_message(timeout=1)
            assert msg is not None and msg["type"] == "subscribe"
            redis_cluster.publish(channel, "hello-cluster")
            msg = pubsub.get_message(timeout=2)
            assert msg is not None
            data = msg["data"]
            if isinstance(data, bytes):
                data = data.decode()
            assert data == "hello-cluster"
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()
