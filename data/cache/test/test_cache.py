import pytest

from mock import patch

from data.cache import InMemoryDataModelCache, NoopDataModelCache, MemcachedModelCache
from data.cache.cache_key import CacheKey


class MockClient(object):
    def __init__(self, server, **kwargs):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value, expire=None):
        self.data[key] = value


@pytest.mark.parametrize("cache_type", [(NoopDataModelCache), (InMemoryDataModelCache),])
def test_caching(cache_type):
    key = CacheKey("foo", "60m")
    cache = cache_type()

    # Perform two retrievals, and make sure both return.
    assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}
    assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}


def test_memcache():
    key = CacheKey("foo", "60m")
    with patch("data.cache.impl.Client", MockClient):
        cache = MemcachedModelCache(("127.0.0.1", "-1"))
        assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}
        assert cache.retrieve(key, lambda: {"a": 1234}) == {"a": 1234}


def test_memcache_should_cache():
    key = CacheKey("foo", None)

    def sc(value):
        return value["a"] != 1234

    with patch("data.cache.impl.Client", MockClient):
        cache = MemcachedModelCache(("127.0.0.1", "-1"))
        assert cache.retrieve(key, lambda: {"a": 1234}, should_cache=sc) == {"a": 1234}

        # Ensure not cached since it was `1234`.
        assert cache._get_client().get(key.key) is None

        # Ensure cached.
        assert cache.retrieve(key, lambda: {"a": 2345}, should_cache=sc) == {"a": 2345}
        assert cache._get_client().get(key.key) is not None
        assert cache.retrieve(key, lambda: {"a": 2345}, should_cache=sc) == {"a": 2345}
