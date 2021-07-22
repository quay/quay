import pytest

from unittest.mock import patch, MagicMock
from rediscluster.nodemanager import NodeManager

from data.cache import (
    InMemoryDataModelCache,
    NoopDataModelCache,
    MemcachedModelCache,
    RedisDataModelCache,
)
from data.cache.cache_key import CacheKey
from data.cache.redis_cache import (
    redis_cache_from_config,
    REDIS_DRIVERS,
    ReadEndpointSupportedRedis,
)


DATA = {}

TEST_CACHE_CONFIG = {
    "repository_blob_cache_ttl": "240s",
    "catalog_page_cache_ttl": "240s",
    "namespace_geo_restrictions_cache_ttl": "240s",
    "active_repo_tags_cache_ttl": "240s",
    "appr_applications_list_cache_ttl": "3600s",
    "appr_show_package_cache_ttl": "3600s",
}


class MockClient(object):
    def __init__(self, **kwargs):
        pass

    def get(self, key, default=None):
        return DATA.get(key, default)

    def set(self, key, value, expire=None):
        DATA[key] = value

    def close(self):
        pass


@pytest.mark.parametrize(
    "cache_type",
    [
        (NoopDataModelCache),
        (InMemoryDataModelCache),
    ],
)
def test_caching(cache_type):
    key = CacheKey("foo", "60m")
    cache = cache_type(TEST_CACHE_CONFIG)

    # Perform two retrievals, and make sure both return.
    assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}
    assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}


def test_memcache():
    global DATA
    DATA = {}

    key = CacheKey("foo", "60m")
    with patch("data.cache.impl.PooledClient", MockClient):
        cache = MemcachedModelCache(TEST_CACHE_CONFIG, ("127.0.0.1", "-1"))
        assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}
        assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}


def test_memcache_should_cache():
    global DATA
    DATA = {}

    key = CacheKey("foo", None)

    def sc(value):
        return value["a"] != 1234

    with patch("data.cache.impl.PooledClient", MockClient):
        cache = MemcachedModelCache(TEST_CACHE_CONFIG, ("127.0.0.1", "-1"))
        assert cache.retrieve(key, lambda: {"a": 1234}, should_cache=sc) == {"a": 1234}

        # Ensure not cached since it was `1234`.
        assert cache._get_client_pool().get(key.key) is None

        # Ensure cached.
        assert cache.retrieve(key, lambda: {"a": 2345}, should_cache=sc) == {"a": 2345}
        assert cache._get_client_pool().get(key.key) is not None
        assert cache.retrieve(key, lambda: {"a": 2345}, should_cache=sc) == {"a": 2345}


def test_redis_cache():
    global DATA
    DATA = {}

    key = CacheKey("foo", "60m")
    cache = RedisDataModelCache(TEST_CACHE_CONFIG, MockClient())

    assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}
    assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}


@pytest.mark.parametrize(
    "cache_config, expected_exception",
    [
        pytest.param(
            {
                "engine": "rediscluster",
                "redis_config": {
                    "startup_nodes": [{"host": "127.0.0.1", "port": "6379"}],
                    "password": "redisPassword",
                },
            },
            None,
            id="rediscluster",
        ),
        pytest.param(
            {
                "engine": "redis",
                "redis_config": {
                    "primary": {"host": "127.0.0.1", "password": "redisPassword"},
                },
            },
            None,
            id="redis",
        ),
        pytest.param(
            {
                "engine": "memcached",
                "endpoint": "127.0.0.1",
            },
            (ValueError, "Invalid Redis driver for cache model"),
            id="invalid engine for redis",
        ),
        pytest.param(
            {
                "engine": "redis",
                "redis_config": {},
            },
            (ValueError, "Invalid Redis config for redis"),
            id="invalid config for redis",
        ),
    ],
)
def test_redis_cache_config(cache_config, expected_exception):
    with patch("rediscluster.nodemanager.NodeManager.initialize", MagicMock):
        if expected_exception is not None:
            with pytest.raises(expected_exception[0]) as e:
                rc = redis_cache_from_config(cache_config)
            assert str(e.value) == expected_exception[1]
        else:
            rc = redis_cache_from_config(cache_config)
            assert isinstance(rc, REDIS_DRIVERS[cache_config["engine"]])
