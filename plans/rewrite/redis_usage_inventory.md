# Redis Usage Inventory and Migration Plan

Status: Draft (blocking)
Last updated: 2026-02-09

## 1. Purpose

Document all Redis usage patterns that must remain compatible during mixed Python/Go operation.

## 2. Usage patterns

| Pattern | Source anchors | Redis primitive(s) | Compatibility concerns |
|---|---|---|---|
| Build logs | `data/buildlogs.py` | lists, key TTL | log ordering and retention behavior |
| User events | `data/userevent.py` | pub/sub | fanout timing and delivery loss handling |
| Pull metrics | `util/pullmetrics.py` | Lua + hash counters | script atomicity and key naming |
| Data model cache | `data/cache/impl.py` | get/set, optional cluster | cache stampede/fallback behavior |
| Distributed locks | `util/locking.py` | lock keys/leases | lease expiry and re-entrancy assumptions |
| Build orchestration | `buildman/orchestrator.py` | keyspace notifications, coordination keys | event ordering and watcher resilience |
| Pull metrics flush worker | `workers/pullstatsredisflushworker.py` | SCAN, RENAME, HGETALL, DELETE | atomic key-claim + retry semantics on DB failure |
| Read/write split cache client | `data/cache/redis_cache.py` | separate read + write clients | replica lag/staleness handling and read fallback behavior |
| Redis health checks | `health/services.py`, `data/buildlogs.py` | ping, set/get | deployment readiness depends on reachable configured Redis endpoint(s) |

## 3. Go client baseline

- Client: `go-redis` (single, sentinel, cluster support).
- Lua scripts: checked in as explicit assets with SHA pinning.
- Key schema: preserve existing prefixes and key composition unless explicitly versioned.

## 4. Migration rules

1. No key naming changes in mixed mode without dual-read/dual-write plan.
2. Preserve Lua script atomicity for pull metrics.
3. Preserve lock TTL defaults and lock-loss behavior.
4. Preserve pub/sub channels and payload schemas.
5. Keep explicit fallback behavior when Redis is degraded.
6. Preserve atomic claim semantics in pull-stats flush (`RENAME` before DB write, delete after success).
7. Preserve read/write endpoint split semantics for model cache drivers.
8. Treat orchestrator `CONFIG SET notify-keyspace-events` as an operational prerequisite and document fallback when privileges are denied.
9. Replace production `KEYS` usage with `SCAN` where applicable before Go cutover.
10. Preserve current lock-connection behavior or explicitly migrate it: distributed locks currently use the `USER_EVENTS_REDIS` configuration path.

## 5. Test plan

- Mixed producer/consumer tests for each pattern.
- Lua behavior parity tests using recorded inputs/outputs.
- Lock-contention and lock-expiry tests.
- Redis-failure chaos tests (timeouts, reconnects, failover).
- Pullstats flush tests covering orphaned `:processing:` keys and DB-failure retries.
- Read-replica staleness tests for `ReadEndpointSupportedRedis` behavior.
- Health-check parity tests for Redis dependency monitoring and failure reporting.

## 6. Exit criteria (gate G12)

- All Redis patterns mapped to Go code owners.
- Lua script parity tests green.
- Orchestrator/keyspace notification behavior validated in staging.
- Operational dashboards include per-pattern errors and latency.
- Pullstats flush worker parity validated for SCAN/RENAME/DELETE lifecycle.
- Redis lock-path and health-check behavior documented for chosen Go topology.

## 7. Improvement opportunities (non-blocking)

- Pullmetrics Lua currently executes via inline `EVAL`; evaluate `SCRIPT LOAD` + `EVALSHA` once parity baseline is stable.
