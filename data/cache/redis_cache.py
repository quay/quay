from redis import RedisError, StrictRedis
from redis.cluster import ClusterNode, RedisCluster


class ReadEndpointSupportedRedis(object):
    """Wrapper class for Redis to split read/write requests between separate endpoints."""

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
        return self.read_client.get(key, *args, **kwargs)

    def set(self, key, val, *args, **kwargs):
        return self.write_client.set(key, val, *args, **kwargs)

    def delete(self, key, *args, **kwargs):
        return self.write_client.delete(key, *args, **kwargs)

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
    Anything that can be set in StrictRedis() can also be set under the redis_config structure.

    NOTE: redis-py 4.1+ has built-in cluster support. Use read_from_replicas=True to allow
          reading from replicas in cluster mode.
    """
    driver = cache_config.get("engine", None)
    if driver is None or driver.lower() not in REDIS_DRIVERS.keys():
        raise ValueError("Invalid Redis driver for cache model")

    driver_cls = REDIS_DRIVERS[driver]

    redis_config = cache_config.get("redis_config", None)
    if not redis_config:
        raise ValueError("Invalid Redis config for %s" % driver)

    if driver == "rediscluster":
        redis_config = redis_config.copy()
        if "startup_nodes" in redis_config:
            # redis-py expects a different format from redis-py-cluster hence this conversion is required
            redis_config["startup_nodes"] = [
                ClusterNode(host=node["host"], port=int(node["port"]))
                for node in redis_config["startup_nodes"]
            ]
        if "readonly_mode" in redis_config:
            # `readonly_mode` was renamed to `read_from_replicas` in redis-py
            redis_config["read_from_replicas"] = redis_config.pop("readonly_mode")

    return driver_cls(**redis_config)
