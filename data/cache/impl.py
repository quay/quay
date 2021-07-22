import logging
import json
import os

from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pymemcache.client.base import PooledClient
from prometheus_client import Counter
from redis import StrictRedis, RedisError
from six import add_metaclass

from data.database import CloseForLongOperation
from data.cache.redis_cache import redis_cache_from_config
from util.expiresdict import ExpiresDict
from util.timedeltastring import convert_to_timedelta
from util.workers import get_worker_connections_count

logger = logging.getLogger(__name__)

cache_count = Counter(
    "quay_model_cache", "number of attempts to retrieve from the model cache", labelnames=["type"]
)


def is_not_none(value):
    return value is not None


def lock_key_for(cache_key):
    return "LOCK_" + cache_key


@add_metaclass(ABCMeta)
class DataModelCache(object):
    """
    Defines an interface for cache storing and returning tuple data model objects.
    """

    cache_config = None

    def __init__(self, cache_config):
        self.cache_config = cache_config

    @abstractmethod
    def retrieve(self, cache_key, loader, should_cache=is_not_none):
        """
        Checks the cache for the specified cache key and returns the value found (if any).

        If none found, the loader is called to get a result and populate the cache.
        """
        pass


class DisconnectWrapper(DataModelCache):
    """
    Wrapper around another data model cache that disconnects from the database before
    invoking the cache, in case the cache call takes too long.
    """

    def __init__(self, cache_config, cache, app_config):
        super(DisconnectWrapper, self).__init__(cache_config)
        self.cache = cache
        self.app_config = app_config

    def retrieve(self, cache_key, loader, should_cache=is_not_none):
        with CloseForLongOperation(self.app_config):
            return self.cache.retrieve(cache_key, loader, should_cache)


class NoopDataModelCache(DataModelCache):
    """
    Implementation of the data model cache which does nothing.
    """

    def retrieve(self, cache_key, loader, should_cache=is_not_none):
        return loader()


class InMemoryDataModelCache(DataModelCache):
    """
    Implementation of the data model cache backed by an in-memory dictionary.
    """

    def __init__(self, cache_config):
        super(InMemoryDataModelCache, self).__init__(cache_config)
        self.cache = ExpiresDict()

    def empty_for_testing(self):
        self.cache = ExpiresDict()

    def retrieve(self, cache_key, loader, should_cache=is_not_none):
        not_found = [None]
        logger.debug("Checking cache for key %s", cache_key.key)
        result = self.cache.get(cache_key.key, default_value=not_found)
        if result != not_found:
            logger.debug("Found result in cache for key %s: %s", cache_key.key, result)
            cache_count.labels("hit").inc()

            return json.loads(result)
        else:
            cache_count.labels("miss").inc()

        logger.debug("Found no result in cache for key %s; calling loader", cache_key.key)
        result = loader()
        logger.debug("Got loaded result for key %s: %s", cache_key.key, result)
        if should_cache(result):
            logger.debug(
                "Caching loaded result for key %s with expiration %s: %s",
                cache_key.key,
                result,
                cache_key.expiration,
            )
            expires = convert_to_timedelta(cache_key.expiration) + datetime.now()
            self.cache.set(cache_key.key, json.dumps(result), expires=expires)
            logger.debug(
                "Cached loaded result for key %s with expiration %s: %s",
                cache_key.key,
                result,
                cache_key.expiration,
            )
        else:
            logger.debug("Not caching loaded result for key %s: %s", cache_key.key, result)

        return result


_DEFAULT_MEMCACHE_TIMEOUT = 1  # second
_DEFAULT_MEMCACHE_CONNECT_TIMEOUT = 1  # second

_STRING_TYPE = 1
_JSON_TYPE = 2


class MemcachedModelCache(DataModelCache):
    """
    Implementation of the data model cache backed by a memcached.
    """

    def __init__(
        self,
        cache_config,
        endpoint,
        timeout=_DEFAULT_MEMCACHE_TIMEOUT,
        connect_timeout=_DEFAULT_MEMCACHE_CONNECT_TIMEOUT,
    ):
        super(MemcachedModelCache, self).__init__(cache_config)
        max_pool_size = int(
            os.environ.get("MEMCACHE_POOL_MAX_SIZE", get_worker_connections_count("registry"))
        )

        self.endpoint = endpoint
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.client_pool = self._get_client_pool(max_pool_size)

    def _get_client_pool(self, max_pool_size=None):
        try:
            # Copied from the doc comment for Client.
            def serialize_json(key, value):
                if type(value) == str:
                    return value, _STRING_TYPE

                return json.dumps(value), _JSON_TYPE

            def deserialize_json(key, value, flags):
                if flags == _STRING_TYPE:
                    return value

                if flags == _JSON_TYPE:
                    return json.loads(value)

                raise Exception("Unknown flags for value: {1}".format(flags))

            return PooledClient(
                server=self.endpoint,
                no_delay=True,
                timeout=self.timeout,
                connect_timeout=self.connect_timeout,
                key_prefix="data_model_cache__",
                serializer=serialize_json,
                deserializer=deserialize_json,
                max_pool_size=max_pool_size,
                ignore_exc=False,
            )
        except:
            logger.exception("Got exception when creating memcached client to %s", self.endpoint)
            return None

    def retrieve(self, cache_key, loader, should_cache=is_not_none):
        not_found = [None]
        client = self.client_pool
        if client is not None:
            logger.debug("Checking cache for key %s", cache_key.key)
            try:
                result = client.get(cache_key.key, default=not_found)
                if result != not_found:
                    logger.debug("Found result in cache for key %s: %s", cache_key.key, result)
                    cache_count.labels("hit").inc()

                    return result
                else:
                    cache_count.labels("miss").inc()
            except:
                logger.warning("Got exception when trying to retrieve key %s", cache_key.key)

        logger.debug("Found no result in cache for key %s; calling loader", cache_key.key)
        result = loader()
        logger.debug("Got loaded result for key %s: %s", cache_key.key, result)
        if client is not None and should_cache(result):
            try:
                logger.debug(
                    "Caching loaded result for key %s with expiration %s: %s",
                    cache_key.key,
                    result,
                    cache_key.expiration,
                )
                expires = (
                    convert_to_timedelta(cache_key.expiration) if cache_key.expiration else None
                )
                client.set(
                    cache_key.key,
                    result,
                    expire=int(expires.total_seconds()) if expires else None,
                )
                logger.debug(
                    "Cached loaded result for key %s with expiration %s: %s",
                    cache_key.key,
                    result,
                    cache_key.expiration,
                )
            except:
                logger.warning(
                    "Got exception when trying to set key %s to %s", cache_key.key, result
                )
        else:
            logger.debug("Not caching loaded result for key %s: %s", cache_key.key, result)

        return result


class RedisDataModelCache(DataModelCache):
    """
    Implementation of the data model cache backed by a Redis service.
    """

    def __init__(self, cache_config, redis_client):
        super(RedisDataModelCache, self).__init__(cache_config)
        self.client = redis_client

    def retrieve(self, cache_key, loader, should_cache=is_not_none):
        # TODO: We might want to have different behavior based on `cache_key` (using "sets" for `/tags/list`, single value for others...)
        not_found = None
        if self.client is not None:
            logger.debug("Checking cache for key %s", cache_key.key)
            try:
                cached_result = self.client.get(cache_key.key)
                if cached_result != not_found:
                    cache_count.labels("hit").inc()
                    logger.debug("Found result in cache for key %s", cache_key.key)

                    return json.loads(cached_result)
                else:
                    cache_count.labels("miss").inc()
            except RedisError as re:
                logger.warning("Got exception when trying to retrieve key %s", cache_key.key)

        logger.debug("Found no result in cache for key %s; calling loader", cache_key.key)
        result = loader()
        logger.debug("Got loaded result for key %s: %s", cache_key.key, result)
        if self.client is not None and should_cache(result):
            try:
                logger.debug(
                    "Caching loaded result for key %s with expiration %s: %s",
                    cache_key.key,
                    result,
                    cache_key.expiration,
                )
                expires = (
                    convert_to_timedelta(cache_key.expiration) if cache_key.expiration else None
                )
                self.client.set(
                    cache_key.key,
                    json.dumps(result),
                    ex=int(expires.total_seconds()) if expires else None,
                    nx=True,
                )
                logger.debug(
                    "Cached loaded result for key %s with expiration %s: %s",
                    cache_key.key,
                    result,
                    cache_key.expiration,
                )
            except:
                logger.warning(
                    "Got exception when trying to set key %s to %s", cache_key.key, result
                )
        else:
            logger.debug("Not caching loaded result for key %s: %s", cache_key.key, result)

        return result
