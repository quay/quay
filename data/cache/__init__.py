from data.cache.redis_cache import redis_cache_from_config
from data.cache.impl import (
    NoopDataModelCache,
    InMemoryDataModelCache,
    MemcachedModelCache,
    RedisDataModelCache,
    DisconnectWrapper,
)


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

    if engine == "redis" or engine == "redis-cluster":
        redis_client = redis_cache_from_config(cache_config)

        return RedisDataModelCache(cache_config, redis_client)

    raise Exception("Unknown model cache engine `%s`" % engine)
