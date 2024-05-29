from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from rediscluster.nodemanager import NodeManager

from data.cache import (
    InMemoryDataModelCache,
    MemcachedModelCache,
    NoopDataModelCache,
    RedisDataModelCache,
)
from data.cache.cache_key import CacheKey
from data.cache.redis_cache import (
    REDIS_DRIVERS,
    ReadEndpointSupportedRedis,
    redis_cache_from_config,
)

DATA: Dict[str, Any] = {}

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


def test_memcache_invalid_size_limit_config():
    invalid_cache_config = TEST_CACHE_CONFIG.copy()
    invalid_cache_config["value_size_limit"] = "invalid_size"

    with pytest.raises(ValueError) as excinfo:
        _ = MemcachedModelCache(invalid_cache_config, ("127.0.0.1", "-1"))

    assert "Invalid size string for memcached size limit" in str(excinfo.value)


def test_memcache_valid_size_limit_config():
    valid_cache_config = TEST_CACHE_CONFIG.copy()
    valid_cache_config["value_size_limit"] = "10MiB"

    cache = MemcachedModelCache(valid_cache_config, ("127.0.0.1", "-1"))

    assert cache.value_size_limit_bytes == 10 * 1024 * 1024


def test_memcache_default_size_limit_config():
    cache = MemcachedModelCache(TEST_CACHE_CONFIG, ("127.0.0.1", "-1"))

    assert cache.value_size_limit_bytes == 1024 * 1024


def test_memcache_handle_large_value():
    global DATA
    DATA = {}

    key = CacheKey("foo", "60m")
    large_value = "a" * (1024 * 1024 + 1)  # a string larger than 1MB

    with patch("data.cache.impl.PooledClient", MockClient):
        cache = MemcachedModelCache(TEST_CACHE_CONFIG, ("127.0.0.1", "-1"))

        with patch("logging.Logger.warning") as mock_warning:
            retrieved_value = cache.retrieve(key, lambda: large_value)
            assert retrieved_value == large_value

            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0]

            assert any("foo" in arg for arg in call_args if isinstance(arg, str))
            assert not any(large_value in arg for arg in call_args if isinstance(arg, str))


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
