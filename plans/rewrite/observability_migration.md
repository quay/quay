# Observability Migration Plan

Status: Draft
Last updated: 2026-02-16

## 1. Purpose

Define how Prometheus metrics, structured logging, distributed tracing, and health checks migrate from Python to Go, ensuring zero gaps in production visibility during and after the rewrite.

Implementation references:
- `plans/rewrite/quay_rewrite.md` (quality gate: observability parity)
- `plans/rewrite/quay_distribution_reconciliation.md` §3.6 (existing Go observability)
- `plans/rewrite/runtime_support_components.md` (PrometheusPlugin, PullMetricsBuilderModule)

## 2. Current Python observability inventory

### 2.1 Prometheus metrics (19 defined)

| Metric name | Type | Labels | Source |
|---|---|---|---|
| `quay_request_duration_seconds` | Histogram | method, route, status, namespace_name | `util/metrics/prometheus.py` |
| `quay_registry_image_pulls_total` | Counter | protocol, ref, status | `endpoints/metrics.py` |
| `quay_registry_image_pushes_total` | Counter | protocol, status, media_type | `endpoints/metrics.py` |
| `quay_registry_image_pulled_estimated_bytes_total` | Counter | protocol | `endpoints/metrics.py` |
| `quay_db_pooled_connections_in_use` | Gauge | — | `util/metrics/prometheus.py` |
| `quay_db_pooled_connections_available` | Gauge | — | `util/metrics/prometheus.py` |
| `quay_db_connect_calls` | Counter | — | `util/metrics/prometheus.py` |
| `quay_db_close_calls` | Counter | — | `util/metrics/prometheus.py` |
| `quay_gc_table_rows_deleted` | Counter | table | `util/metrics/prometheus.py` |
| `quay_gc_storage_blobs_deleted` | Counter | — | `util/metrics/prometheus.py` |
| `quay_gc_repos_purged` | Counter | — | `util/metrics/prometheus.py` |
| `quay_gc_namespaces_purged` | Counter | — | `util/metrics/prometheus.py` |
| `quay_gc_iterations` | Counter | — | `util/metrics/prometheus.py` |
| `quay_secscan_request_duration_seconds` | Histogram | method, action, status | `util/metrics/prometheus.py` |
| `quay_secscan_index_layer_size_bytes` | Histogram | — | `util/metrics/prometheus.py` |
| `quay_secscan_result_duration_seconds` | Histogram | — | `util/metrics/prometheus.py` |
| `quay_repository_rows` | Gauge | — | `workers/globalpromstats/` |
| `quay_user_rows` | Gauge | — | `workers/globalpromstats/` |
| `quay_org_rows` | Gauge | — | `workers/globalpromstats/` |
| `quay_robot_rows` | Gauge | — | `workers/globalpromstats/` |

### 2.2 Metric collection infrastructure

| Component | Behavior | Source |
|---|---|---|
| `ThreadPusher` | Daemon thread pushes all metrics to Pushgateway every 30s | `util/metrics/prometheus.py:173-211` |
| `timed_blueprint()` | Flask decorator records per-request duration with namespace bucketing | `util/metrics/prometheus.py:244-305` |
| `TRACKED_NAMESPACES` | Config-driven namespace-to-bucket mapping to control cardinality | `util/metrics/prometheus.py:19-64` |
| `GlobalPrometheusStatsWorker` | Hourly worker reports DB row counts under global lock | `workers/globalpromstats/` |
| `PullMetrics` | Redis-backed async pull tracking via thread pool + Lua scripts | `util/pullmetrics.py:69-492` |

### 2.3 Logging

| Format | Config file | Trigger |
|---|---|---|
| Text, INFO | `conf/logging.conf` | Default |
| Text, DEBUG | `conf/logging_debug.conf` | `DEBUGLOG=true` |
| JSON, INFO | `conf/logging_json.conf` | `JSONLOG=true` |
| JSON, DEBUG | `conf/logging_debug_json.conf` | Both |

Formatter: `%(asctime)s [%(process)d] [%(levelname)s] [%(name)s] %(message)s` (text) or `loghandler.JsonFormatter` (JSON).

Sensitive field filtering via `util/log.py:filter_logs()`.

### 2.4 Distributed tracing (OpenTelemetry)

- Feature flag: `FEATURE_OTEL_TRACING`
- Sample rate: 1/1000 (TraceIdRatioBased)
- Exporters: Dynatrace OTLP or Jaeger OTLP (default `http://jaeger:4317`)
- Instrumentors: `FlaskInstrumentor`, `Psycopg2Instrumentor`
- Span decorator: `@traced()` on individual functions
- URL exclusion: `OTEL_TRACING_EXCLUDED_URLS` (comma-separated regex)

### 2.5 Health check endpoints

| Path | Purpose | Checks |
|---|---|---|
| `/health`, `/health/instance` | Instance liveness | DB, Redis, storage, auth, service key, disk |
| `/status`, `/health/endtoend` | Full cluster readiness | All checks, no skips |
| `/health/warning` | Degraded detection | Disk space warnings |
| `/health/dbrevision` | Schema version match | Alembic head vs DB |
| `/health/enabledebug/<secret>` | Debug toggle | Session-based |

Variants: `LocalHealthCheck` (skips Redis/storage), `RDSAwareHealthCheck` (tolerates RDS outages).

## 3. Existing Go observability (quay-distribution)

From `quay_distribution_reconciliation.md` §3.6, the prototype already provides:

| Component | Location | Status |
|---|---|---|
| HTTP metrics (requests, duration, in-flight) | `pkg/metrics/middleware.go` | Adopt as-is |
| DB pool metrics (connections, wait time) | `pkg/metrics/` | Adopt as-is |
| Cache metrics (hits/misses, duration) | `pkg/metrics/` | Adopt as-is |
| Metrics cardinality normalization | `pkg/metrics/middleware.go` | Adopt as-is |
| OpenTelemetry with OTLP export | `internal/tracing/` | Adopt as-is |
| Structured logging (`slog`) | `pkg/utils/logging.go` | Adopt as-is |
| Secret redaction in logs | `pkg/utils/logging.go` | Adopt as-is |

## 4. Migration policy

### 4.1 Metric name compatibility

**Hard rule**: Go must emit the same metric names and label sets as Python for all metrics listed in §2.1.

Rationale: Existing Prometheus recording rules, Grafana dashboards, and Alertmanager routes reference these metric names. Changing names silently breaks alerting.

During coexistence (M1-M4), both runtimes emit the same metric names. To distinguish origin:

- Add label `runtime="python"` or `runtime="go"` to all metrics emitted by either runtime.
- Dashboards can filter or aggregate by runtime label.
- After M5 (Python deactivation), the runtime label remains with value `"go"` for compatibility. It can be dropped in a later release with a documented breaking change.

### 4.2 Pushgateway migration

Python uses `ThreadPusher` to push metrics to Pushgateway every 30s. Go should **not** replicate this pattern.

Target: Go exposes a `/metrics` HTTP endpoint (standard `promhttp.Handler()`). Prometheus scrapes directly.

During coexistence, both mechanisms coexist:
- Python workers continue pushing to Pushgateway.
- Go services expose `/metrics` for scrape.
- Prometheus config must include both scrape targets and the Pushgateway.

After M5: Pushgateway is retired. All metrics are scraped directly from Go processes.

Action required: Update Prometheus scrape config to add Go service targets before M2. Verify no dashboard depends on Pushgateway-specific labels (`job`, `instance` from push grouping key) that would change semantics under direct scrape.

### 4.3 Logging format

Go uses `slog` with JSON output by default (already implemented in quay-distribution).

Compatibility requirements:
- JSON field names must match Python's `JsonFormatter` output where fields overlap: `asctime`, `levelname`, `name`, `message`.
- If exact field name parity is impractical (Go `slog` uses `time`, `level`, `msg` by default), document the mapping and update log aggregation parsers (e.g., CloudWatch Logs Insights queries, Splunk extractions) before M2 cutover.
- Secret redaction: quay-distribution's `pkg/utils/logging.go` already redacts S3 keys, DB passwords, and Akamai secrets. Verify coverage matches Python's `util/log.py:filter_logs()`.

### 4.4 Distributed tracing

Go adopts quay-distribution's OpenTelemetry setup (`internal/tracing/`).

Compatibility requirements:
- Same config keys: `FEATURE_OTEL_TRACING`, `OTEL_CONFIG`, `OTEL_TRACING_EXCLUDED_URLS`.
- Same service name attribute (`service.name: "quay"`) so traces from both runtimes appear in the same service in Jaeger/Dynatrace.
- During coexistence, propagate trace context (W3C `traceparent` header) between nginx, Python, and Go so cross-runtime requests produce connected traces.
- Replace Python instrumentors with Go equivalents:
  - `FlaskInstrumentor` → `otelhttp` middleware (already in quay-distribution)
  - `Psycopg2Instrumentor` → `otelpgx` for pgx/v5

### 4.5 Health check endpoints

Go must implement all 5 health endpoints with the same paths and response semantics.

| Python endpoint | Go equivalent | Notes |
|---|---|---|
| `/health`, `/health/instance` | Same paths | Check: DB (pgxpool), Redis, storage driver, service key |
| `/status`, `/health/endtoend` | Same paths | Full check, no skips |
| `/health/warning` | Same paths | Disk space |
| `/health/dbrevision` | Same paths | Compare Alembic head to `alembic_version` table |
| `/health/enabledebug/<secret>` | Same paths | Session or token-based debug toggle |

During coexistence: nginx routes `/health` to whichever runtime is the primary owner. Both runtimes expose health checks; monitoring should check both.

`RDSAwareHealthCheck` variant: evaluate whether this is still needed. If yes, port the RDS status check logic.

## 5. New metrics required for migration

These metrics do not exist in Python but are required for safe cutover operations.

| Metric name | Type | Labels | Purpose |
|---|---|---|---|
| `quay_switch_snapshot_age_seconds` | Gauge | process_name | Time since last successful switch config poll. Alert if >30s (propagation SLO). |
| `quay_switch_owner_decision_total` | Counter | capability, owner, source | Tracks owner resolution decisions. Detect unexpected fallbacks. |
| `quay_switch_parse_failures_total` | Counter | process_name | Config parse failures triggering last-known-good fallback. |
| `quay_dal_read_replica_routing_total` | Counter | target (primary/replica), reason | Track read-replica routing decisions per `data_access_layer_design.md`. |
| `quay_dal_replica_fallback_total` | Counter | reason | Replica-to-primary fallback events. |

## 6. Pull metrics migration

`PullMetrics` (`util/pullmetrics.py`) is a Redis-backed async pull tracking system with its own thread pool and Lua scripts. This is a runtime support component marked "High" risk in `runtime_support_components.md`.

Migration approach:
1. Port Redis key schema and Lua scripts to Go with byte-for-byte key compatibility.
2. Replace Python `ThreadPoolExecutor` with Go goroutine pool (e.g., `errgroup` or channel-based worker pool).
3. During coexistence, both runtimes write to the same Redis keys. Verify no double-counting by confirming pull tracking is tied to the route owner (only the runtime serving the pull writes the metric).
4. Test: Python writes a pull metric, Go reads it back correctly, and vice versa.

## 7. Dashboard and alert migration checklist

Before each milestone's cutover:

- [ ] Verify all Grafana dashboards render correctly with `runtime="go"` label filter
- [ ] Verify Alertmanager rules fire correctly on Go-emitted metrics
- [ ] Verify Prometheus recording rules produce correct results with mixed-runtime data
- [ ] Update log aggregation queries for Go's `slog` JSON field names if different from Python
- [ ] Verify trace continuity across Python → Go → Python request chains in staging
- [ ] Verify PagerDuty/OpsGenie integration receives alerts from Go-emitted metrics
- [ ] Document any metric semantics changes (e.g., histogram bucket boundaries) in release notes

## 8. Milestone delivery sequence

| Milestone | Observability actions |
|---|---|
| M0 | Inventory complete (this document). Go scaffold emits `/metrics` endpoint. CI validates metric registration. |
| M1 | Switch metrics (§5) implemented and dashboarded. Prometheus scrape config updated for Go targets. Trace context propagation validated between runtimes. |
| M2 | Registry metrics (`image_pulls_total`, `image_pushes_total`, `pulled_estimated_bytes_total`, `request_duration_seconds`) emitted by Go registryd with `runtime="go"` label. Dashboard dual-runtime view operational. |
| M3 | API and secscan metrics emitted by Go api-service. Health endpoints ported to Go. |
| M4 | Worker metrics (GC counters, global stats gauges) emitted by Go workers. Pull metrics ported. Pushgateway removal plan finalized. |
| M5 | Pushgateway retired. All metrics scraped directly. `runtime` label hardened to `"go"`. Log format migration complete. |

## 9. Exit criteria

- All 19 Python metrics emitted by Go with identical names and label sets.
- Switch propagation metric (`switch_snapshot_age_seconds`) dashboarded and alerting at >30s.
- Health check endpoints return identical response schemas and status codes.
- No Grafana dashboard or Alertmanager rule references a metric that only Python emits, after M5.
- Log aggregation pipelines parse Go `slog` JSON output without errors.
- Trace spans from Go appear in the same Jaeger/Dynatrace service as Python spans.
