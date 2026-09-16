# Redis Cluster Support for USER_EVENTS_REDIS and PULL_METRICS_REDIS

## Overview

Quay supports three independent Redis-backed configuration settings:

| Config key | Purpose | Cluster support |
|---|---|---|
| `DATA_MODEL_CACHE_CONFIG` | Model data cache | ✅ (since 3.x) |
| `USER_EVENTS_REDIS` | Real-time user events and global locking | ✅ (RFE-9838) |
| `PULL_METRICS_REDIS` | Image pull metrics / statistics | ✅ (RFE-9838) |

All three now support both **single-node Redis** and **Redis Cluster** backends.

## Configuration

### Legacy single-node format (backward compatible)

No changes needed for existing deployments. The legacy flat config continues to
work exactly as before:

```yaml
USER_EVENTS_REDIS:
  host: localhost
  port: 6379
  password: mypassword

PULL_METRICS_REDIS:
  host: localhost
  port: 6379
  password: mypassword
  db: 1
```

### Redis Cluster format

To use a Redis Cluster backend, set `engine: rediscluster` and provide
connection details under `redis_config`:

```yaml
USER_EVENTS_REDIS:
  engine: rediscluster
  redis_config:
    startup_nodes:
      - host: redis-node-1.example.com
        port: 6379
      - host: redis-node-2.example.com
        port: 6379
      - host: redis-node-3.example.com
        port: 6379
    read_from_replicas: true
    require_full_coverage: true
    ssl: true
    password: cluster-secret

PULL_METRICS_REDIS:
  engine: rediscluster
  redis_config:
    startup_nodes:
      - host: redis-node-1.example.com
        port: 6379
      - host: redis-node-2.example.com
        port: 6379
      - host: redis-node-3.example.com
        port: 6379
    read_from_replicas: true
    password: cluster-secret
```

### Explicit single-node format (engine: redis)

You can also use the `engine`/`redis_config` structure with a single-node
Redis backend:

```yaml
USER_EVENTS_REDIS:
  engine: redis
  redis_config:
    host: redis.example.com
    port: 6379
    password: mypassword
```

## Configuration reference

### Common fields

| Field | Type | Description |
|---|---|---|
| `engine` | `string` | `"redis"` for single-node, `"rediscluster"` for Redis Cluster. When absent, the legacy flat format is used. |
| `redis_config` | `object` | Connection settings passed to the chosen driver (required when `engine` is set). |

### `redis_config` fields — engine: redis

| Field | Type | Description |
|---|---|---|
| `host` | `string` | Redis hostname |
| `port` | `number` | Redis port (default 6379) |
| `password` | `string` | Redis password |
| `ssl` | `boolean` | Enable TLS |
| `db` | `number` | Database number (only for `PULL_METRICS_REDIS`) |

### `redis_config` fields — engine: rediscluster

| Field | Type | Description |
|---|---|---|
| `startup_nodes` | `array` | List of `{host, port}` seed nodes |
| `read_from_replicas` | `boolean` | Read from replica nodes |
| `require_full_coverage` | `boolean` | Require full hash-slot coverage (default true) |
| `password` | `string` | Cluster password |
| `ssl` | `boolean` | Enable TLS |

> **Note:** Redis Cluster does not support the `db` parameter (always uses
> database 0). The `readonly_mode` parameter is automatically converted to
> `read_from_replicas` for backward compatibility with older config files.

## Architecture

The cluster support is implemented through a shared utility module
`util/redis_utils.py` which provides:

- `create_redis_client(config)` — factory function that returns either a
  `redis.StrictRedis` or `redis.cluster.RedisCluster` instance based on the
  `engine` field in the config.
- `is_cluster_config(config)` — predicate to check if a config selects cluster
  mode.

The consuming modules have been updated to use this factory:

- `util/locking.py` — `_redis_lock_factory()` for global locks
- `data/userevent.py` — `UserEventBuilder` and `UserEventListener` for Pub/Sub
- `util/pullmetrics.py` — `PullMetrics._ensure_redis_connection()` for pull
  stats tracking
- `workers/pullstatsredisflushworker.py` — `RedisFlushWorker._initialize_redis_client()`
  for the background flush worker

## Notes for operators

- **Unified Redis Cluster**: With this change, all three Quay Redis features
  can target the same Redis Cluster, eliminating the need to run separate
  Redis topologies.
- **Pub/Sub in cluster mode**: Redis Cluster Pub/Sub messages are forwarded
  across the cluster. User events will work correctly.
- **Lua scripts**: The pull metrics Lua scripts operate on single keys, which
  is compatible with Redis Cluster's slot-based architecture.
- **SCAN operations**: The flush worker's key scanning works across all cluster
  nodes transparently.  A per-cycle time budget (`REDIS_FLUSH_WORKER_MAX_SCAN_SECONDS`,
  default 30 s) prevents a large cluster from blocking the worker indefinitely;
  remaining keys are picked up in the next flush cycle.
- **Hash-tagged keys**: Pull-event Redis keys embed the `repository_id` in a
  Redis Cluster hash tag (e.g. `pull_events:repo:{42}:tag:…`) so that
  `RENAME` during claim processing always stays within the same hash slot.
  Legacy keys written before this change are handled via an in-place
  fallback when `CROSSSLOT` is detected.
