import redis

from data.cache.impl import (
    DisconnectWrapper,
    InMemoryDataModelCache,
    MemcachedModelCache,
    NoopDataModelCache,
    RedisDataModelCache,
)
from data.cache.redis_cache import redis_cache_from_config
from data.cache.revocation_list import PermissionRevocationList


def get_model_cache(config):
    """
    Returns a data model cache matching the given configuration.
    """
    cache_config = config.get("DATA_MODEL_CACHE_CONFIG", {})
    engine = cache_config.get("engine", "noop")

    if engine == "noop":
        return NoopDataModelCache(cache_config)

    if engine == "inmemory":
        return InMemoryDataModelCache(cache_config)

    if engine == "memcached":
        endpoint = cache_config.get("endpoint", None)
        if endpoint is None:
            raise Exception("Missing `endpoint` for memcached model cache configuration")

        timeout = cache_config.get("timeout")
        connect_timeout = cache_config.get("connect_timeout")
        predisconnect = cache_config.get("predisconnect_from_db")

        cache = MemcachedModelCache(
            cache_config, endpoint, timeout=timeout, connect_timeout=connect_timeout
        )
        if predisconnect:
            cache = DisconnectWrapper(cache, config)

        return cache

    if engine == "redis" or engine == "rediscluster":
        redis_client = redis_cache_from_config(cache_config)

        return RedisDataModelCache(cache_config, redis_client)

    raise Exception("Unknown model cache engine `%s`" % engine)


def get_revocation_list(config, model_cache=None):
    """
    Returns a PermissionRevocationList backed by Redis.

    Tries PERMISSION_REVOCATION_REDIS config first (dedicated shared Redis).
    Falls back to the model_cache's Redis client if model_cache is Redis-based.
    Returns None if no Redis is available.
    """
    revocation_config = config.get("PERMISSION_REVOCATION_REDIS")
    if revocation_config:
        args = dict(revocation_config)
        args.setdefault("socket_connect_timeout", 1)
        args.setdefault("socket_timeout", 2)
        redis_client = redis.StrictRedis(**args)
        return PermissionRevocationList(redis_client)

    # Fall back to model_cache's Redis client
    if model_cache is not None:
        redis_client = getattr(model_cache, "client", None)
        if redis_client is not None:
            return PermissionRevocationList(redis_client)

    return None
