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
        host = cache_config.get("host", None)
        if host is None:
            raise Exception("Missing `host` for Redis model cache configuration")

        return RedisDataModelCache(
            cache_config,
            host=host,
            port=cache_config.get("port", 6379),
            password=cache_config.get("password", None),
            db=cache_config.get("db", 0),
            ca_cert=cache_config.get("ca_cert", None),
            ssl=cache_config.get("ssl", False),
        )

    raise Exception("Unknown model cache engine `%s`" % engine)
