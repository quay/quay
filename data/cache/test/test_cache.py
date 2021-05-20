import pytest

from mock import patch

from data.cache import (
    InMemoryDataModelCache,
    NoopDataModelCache,
    MemcachedModelCache,
    RedisDataModelCache,
)
from data.cache.cache_key import CacheKey


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

    redis_config = {
        "primary": {
            "host": "127.0.0.1",
            "port": 6279,
            "db": 0,
            "password": "",
            "ssl": False,
            "ssl_ca_certs": None,
        },
        "replica": {
            "host": "127.0.0.1",
            "port": 6279,
            "db": 0,
            "password": "",
            "ssl": False,
            "ssl_ca_certs": None,
        },
    }

    key = CacheKey("foo", "60m")
    with patch("data.cache.impl.StrictRedis", MockClient):
        cache = RedisDataModelCache(
            TEST_CACHE_CONFIG, redis_config.get("primary"), redis_config.get("replica")
        )

        assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}
        assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}
