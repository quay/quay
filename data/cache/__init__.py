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

    if engine == "redis":
        primary_config = cache_config.get("primary", None)
        replica_config = cache_config.get("replica", None)

        if not primary_config or primary_config.get("host") is None:
            raise Exception("Missing `primary_host` for Redis model cache configuration")

        return RedisDataModelCache(
            cache_config,
            primary_config=primary_config,
            replica_config=replica_config,
        )

    raise Exception("Unknown model cache engine `%s`" % engine)
