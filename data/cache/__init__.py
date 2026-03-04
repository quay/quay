from data.cache.impl import (
    DisconnectWrapper,
    InMemoryDataModelCache,
    MemcachedModelCache,
    NoopDataModelCache,
    RedisDataModelCache,
)
from data.cache.redis_cache import redis_cache_from_config
from data.cache.revocation_list import PermissionRevocationList


def _build_revocation_list(cache):
    redis_client = getattr(cache, "client", None)
    if redis_client is not None:
        return PermissionRevocationList(redis_client)

    return None


def get_model_cache(config):
    """
    Returns a data model cache matching the given configuration.
    """
    cache_config = config.get("DATA_MODEL_CACHE_CONFIG", {})
    engine = cache_config.get("engine", "noop")

    if engine == "noop":
        cache = NoopDataModelCache(cache_config)

    elif engine == "inmemory":
        cache = InMemoryDataModelCache(cache_config)

    elif engine == "memcached":
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

    elif engine == "redis" or engine == "rediscluster":
        redis_client = redis_cache_from_config(cache_config)
        cache = RedisDataModelCache(cache_config, redis_client)

    else:
        raise Exception("Unknown model cache engine `%s`" % engine)

    cache.revocation_list = _build_revocation_list(cache)
    return cache
