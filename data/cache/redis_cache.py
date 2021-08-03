from redis import StrictRedis, RedisError
from rediscluster import RedisCluster


class ReadEndpointSupportedRedis(object):
    """ Wrapper class for Redis to split read/write requests between separate endpoints."""

    def __init__(self, primary=None, replica=None):
        if not primary or primary.get("host") is None:
            raise Exception("Missing primary host for Redis model cache configuration")

        self.write_client = StrictRedis(
            socket_connect_timeout=1,
            socket_timeout=2,
            health_check_interval=2,
            **primary,
        )

        if not replica:
            self.read_client = self.write_client
        else:
            self.read_client = StrictRedis(
                socket_connect_timeout=1,
                socket_timeout=2,
                health_check_interval=2,
                **replica,
            )

    def get(self, key, *args, **kwargs):
        return self.read_client(key, *args, **kwargs)

    def set(self, key, val, *args, **kwargs):
        return self.write_client(key, val, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.write_client, name, None)


REDIS_DRIVERS = {
    "redis": ReadEndpointSupportedRedis,
    "rediscluster": RedisCluster,
}


def redis_cache_from_config(cache_config):
    """Return the Redis class to use based on the cache config.

    redis:

      DATA_MODEL_CACHE_CONFIG
        engine: redis,
        redis_config:
          primary:
            host: localhost
            pass: password
          replica:
            host: localhost
            pass: password

    rediscluster:

      DATA_MODEL_CACHE_CONFIG:
        engine: rediscluster
        redis_config:
          startup_nodes:
          - host: "test"
            port: 6379
          readonly_mode: true

    rediscluster uses the same client as redis internally for commands.
    Anything that can be set in StricRedis() can also be set under the redis_config structure.

    NOTE: Known issue - To allow read from replicas in redis cluster mode, set read_from_replicas instead
          of readonly_mode.
          Ref: https://github.com/Grokzen/redis-py-cluster/issues/339
    """
    driver = cache_config.get("engine", None)
    if driver is None or driver.lower() not in REDIS_DRIVERS.keys():
        raise ValueError("Invalid Redis driver for cache model")

    driver_cls = REDIS_DRIVERS[driver]

    redis_config = cache_config.get("redis_config", None)
    if not redis_config:
        raise ValueError("Invalid Redis config for %s" % driver)

    return driver_cls(**redis_config)
