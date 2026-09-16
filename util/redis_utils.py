"""
Shared Redis client factory for creating Redis or RedisCluster clients.

Supports two configuration formats:

1. **Legacy (single-node)** — backward-compatible, ``engine`` key absent::

       USER_EVENTS_REDIS:
         host: localhost
         port: 6379
         password: mypassword

2. **Cluster-aware** — ``engine`` key present::

       USER_EVENTS_REDIS:
         engine: rediscluster
         redis_config:
           startup_nodes:
             - host: node1
               port: 6379
             - host: node2
               port: 6380
           read_from_replicas: true
           require_full_coverage: true
           ssl: true
           password: mypassword

   Or explicit single-node::

       USER_EVENTS_REDIS:
         engine: redis
         redis_config:
           host: localhost
           port: 6379
           password: mypassword

When ``engine`` is absent the config dict is passed directly to
``redis.StrictRedis`` (legacy behavior).  When ``engine`` is ``redis`` or
``rediscluster``, the ``redis_config`` sub-dict is used to instantiate the
appropriate driver class.
"""

import logging

from redis import StrictRedis
from redis.cluster import ClusterNode, RedisCluster

logger = logging.getLogger(__name__)

REDIS_DRIVERS = {
    "redis": StrictRedis,
    "rediscluster": RedisCluster,
}


def create_redis_client(redis_config, default_timeout=None, extra_kwargs=None):
    """Create a Redis or RedisCluster client based on configuration.

    Parameters
    ----------
    redis_config : dict
        Configuration dictionary.  May be either a legacy flat dict
        (``host``/``port``/…) or a cluster-aware dict with ``engine`` and
        ``redis_config`` keys.
    default_timeout : int, optional
        Default ``socket_connect_timeout`` / ``socket_timeout`` applied when
        not already present in *redis_config*.
    extra_kwargs : dict, optional
        Additional keyword arguments merged into the driver constructor call
        (e.g. ``{"decode_responses": True}``).

    Returns
    -------
    redis.StrictRedis | redis.cluster.RedisCluster
        A connected Redis client instance.
    """
    if not redis_config:
        raise ValueError("redis_config must be a non-empty dict")

    redis_config = dict(redis_config)

    engine = redis_config.pop("engine", None)

    if engine is None:
        return _create_legacy_client(redis_config, default_timeout, extra_kwargs)

    engine = engine.lower()
    if engine not in REDIS_DRIVERS:
        raise ValueError(
            "Invalid Redis engine %r, expected one of %s" % (engine, list(REDIS_DRIVERS))
        )

    inner_config = redis_config.pop("redis_config", None)
    if not inner_config:
        raise ValueError("'redis_config' is required when 'engine' is set")

    inner_config = dict(inner_config)

    if engine == "rediscluster":
        return _create_cluster_client(inner_config, default_timeout, extra_kwargs)
    else:
        return _create_single_node_client(inner_config, default_timeout, extra_kwargs)


def _apply_defaults(config, default_timeout, extra_kwargs):
    """Merge *default_timeout* and *extra_kwargs* into *config* (in-place)."""
    if default_timeout is not None:
        config.setdefault("socket_connect_timeout", default_timeout)
        config.setdefault("socket_timeout", default_timeout)
    if extra_kwargs:
        config.update(extra_kwargs)


def _create_legacy_client(redis_config, default_timeout, extra_kwargs):
    """Create a ``StrictRedis`` client from a legacy flat config dict."""
    _apply_defaults(redis_config, default_timeout, extra_kwargs)
    return StrictRedis(**redis_config)


def _create_single_node_client(redis_config, default_timeout, extra_kwargs):
    """Create a ``StrictRedis`` client from an explicit ``engine: redis`` config."""
    _apply_defaults(redis_config, default_timeout, extra_kwargs)
    return StrictRedis(**redis_config)


def _create_cluster_client(redis_config, default_timeout, extra_kwargs):
    """Create a ``RedisCluster`` client from an ``engine: rediscluster`` config."""
    if not redis_config.get("startup_nodes") and not redis_config.get("host"):
        raise ValueError(
            "RedisCluster requires 'startup_nodes' or 'host' in redis_config"
        )

    if "startup_nodes" in redis_config:
        redis_config["startup_nodes"] = [
            ClusterNode(host=node["host"], port=int(node["port"]))
            for node in redis_config["startup_nodes"]
        ]

    if "readonly_mode" in redis_config:
        redis_config["read_from_replicas"] = redis_config.pop("readonly_mode")

    if "skip_full_coverage_check" in redis_config:
        redis_config["require_full_coverage"] = not redis_config.pop(
            "skip_full_coverage_check"
        )

    _apply_defaults(redis_config, default_timeout, extra_kwargs)
    return RedisCluster(**redis_config)


def is_cluster_config(redis_config):
    """Return ``True`` if *redis_config* selects the ``rediscluster`` engine."""
    if not redis_config:
        return False
    engine = redis_config.get("engine", None)
    return engine is not None and engine.lower() == "rediscluster"


def has_engine_config(redis_config):
    """Return ``True`` if *redis_config* contains an ``engine`` key.

    When ``engine`` is present the config uses the cluster-aware schema
    (``engine`` + ``redis_config``) regardless of whether the engine is
    ``redis`` or ``rediscluster``.  These configs must be routed through
    :func:`create_redis_client` instead of being passed directly to
    ``redis.StrictRedis``.
    """
    if not redis_config:
        return False
    return redis_config.get("engine", None) is not None
