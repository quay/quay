# Mirror Metrics and Health Endpoints

This document describes the comprehensive metrics and health endpoints available for monitoring Quay's **repository** and **organization** mirroring functionality.

## Overview

Quay exposes detailed Prometheus metrics and a dedicated health endpoint for repository mirroring operations. These provide visibility into:

- Synchronization status and progress per repository
- Failure tracking and categorization
- Performance metrics (duration, throughput)
- Overall system health

## Prometheus Metrics

All metrics are exposed via the standard Quay metrics endpoint (typically available at the Prometheus PushGateway on port `9091`).

**Names in this document match the worker export:** the pending-tags gauge is exported as `quay_repository_mirror_pending_tags` (internal Python name `repo_mirror_tags_pending` in `workers/repomirrorworker`). There is no `quay_repository_mirror_tags_pending` symbol.

**`quay_repository_mirror_last_sync_status`:** the implementation uses labels `namespace`, `repository`, and `last_error_reason` only—there is no `status` label and values are **0** (failed), **1** (success), and **2** (in progress), not a −2..3 range. The canonical series uses `last_error_reason=""`; failures may also set a second series with `last_error_reason=<category>` for the same value.

### Core Mirroring Metrics

#### 1. Tags Pending Synchronization

```text
quay_repository_mirror_pending_tags{namespace="org1",repository="repo1"} 5
```

**Type:** Gauge
**Labels:**
- `namespace`: Organization or user namespace
- `repository`: Repository name

**Description:** Total number of tags pending synchronization for each mirrored repository. This decreases as tags are synced during a mirroring operation.

**Use Cases:**
- Monitor synchronization progress in real-time
- Identify repositories with large numbers of pending tags
- Track workload distribution across mirrors

---

#### 2. Last Synchronization Status

```text
quay_repository_mirror_last_sync_status{namespace="org1",repository="repo1",last_error_reason=""} 1
quay_repository_mirror_last_sync_status{namespace="org2",repository="repo2",last_error_reason="auth_failed"} 0
```

**Type:** Gauge
**Labels:**
- `namespace`: Organization or user namespace
- `repository`: Repository name
- `last_error_reason`: Empty string (`""`) on the **canonical** time series for each repository (use this for counts and high-level alerts). When a sync fails, the worker also emits a **detail** time series with the same `namespace` / `repository` and `last_error_reason=<category>` for drill-down.

**Values:**
- `0` = Failed
- `1` = Success
- `2` = In Progress

**Description:** Status of the last synchronization attempt. The canonical series (`last_error_reason=""`) always reflects the current status for that repo. On failure, a second series with a non-empty `last_error_reason` is set to the same value so you can attribute failures by category without double-counting repos—use the canonical label for `sum` / `count`, and the specific reason label for breakdowns.

**Error Reason Categories:**
- `auth_failed`: Authentication or authorization failures
- `network_timeout`: Network timeout errors
- `connection_error`: General connection issues
- `not_found`: Repository or resource not found (404)
- `tls_error`: TLS/SSL certificate errors
- `decryption_failed`: Failed to decrypt credentials
- `preempted`: Mirror job was preempted by another worker
- `unknown_error`: Other unclassified errors

**Use Cases:**
- Alert on failed synchronizations
- Identify patterns in failure types
- Quickly determine current sync state without checking multiple metrics

**Example Queries:**
```promql
# Failing repositories (canonical series only — one sample per repo)
quay_repository_mirror_last_sync_status{last_error_reason=""} == 0

# Successful repositories by namespace
sum by (namespace) (quay_repository_mirror_last_sync_status{last_error_reason=""} == 1)

# Failures attributed to auth (detail series)
quay_repository_mirror_last_sync_status{last_error_reason="auth_failed"} == 0
```

---

#### 3. Complete Synchronization Status

```text
quay_repository_mirror_sync_complete{namespace="org1",repository="repo1"} 1
quay_repository_mirror_sync_complete{namespace="org2",repository="repo2"} 0
```

**Type:** Gauge
**Labels:**
- `namespace`: Organization or user namespace
- `repository`: Repository name

**Values:**
- `0` = Incomplete (some tags failed to sync)
- `1` = Complete (all tags successfully synchronized)

**Description:** Indicates if all tags have been successfully synchronized in the last sync operation.

**Use Cases:**
- Alert on incomplete synchronizations
- Track overall mirror health
- Distinguish between complete failures and partial successes

---

#### 4. Synchronization Failure Counter

```text
quay_repository_mirror_sync_failures_total{namespace="org1",reason="network_timeout"} 3
quay_repository_mirror_sync_failures_total{namespace="org2",reason="auth_failed"} 7
```

**Type:** Counter
**Labels:**
- `namespace`: Organization or user namespace
- `reason`: Categorized failure reason (see error reasons above)

**Description:** Cumulative counter of synchronization failures aggregated by namespace. Increments on each failed sync attempt, with failures categorized by reason. Per-repository failure detail is available via the health endpoint.

**Use Cases:**
- Set up alerts based on failure thresholds
- Track failure rates over time per namespace
- Analyze failure patterns by type

**Example Queries:**
```promql
# Failure rate per namespace over 5 minutes
rate(quay_repository_mirror_sync_failures_total[5m])

# Namespaces with more than 10 total failures
sum by (namespace) (quay_repository_mirror_sync_failures_total) > 10

# Most common failure types
topk(5, sum by (reason) (quay_repository_mirror_sync_failures_total))
```

---

### Supporting Metrics

#### 5. Active Mirror Workers

```text
quay_repository_mirror_workers_active 5
```

**Type:** Gauge
**Description:** Set to **1** in each Quay process while a `RepoMirrorWorker` is running (see `workers/repomirrorworker/repomirrorworker.py`). Prometheus should scrape every mirror worker target; **`sum(quay_repository_mirror_workers_active)`** across those targets approximates the number of active worker processes.

**Use Cases:**
- Verify worker processes are running
- Monitor worker scaling
- Alert when no workers are active

---

#### 6. Last Synchronization Timestamp

```text
quay_repository_mirror_last_sync_timestamp{namespace="org1",repository="repo1"} 1697385600
```

**Type:** Gauge
**Labels:**
- `namespace`: Organization or user namespace
- `repository`: Repository name

**Description:** Unix timestamp of when the last synchronization attempt started.

**Use Cases:**
- Alert on stale synchronizations
- Track sync frequency
- Identify mirrors that haven't run recently

**Example Query:**
```promql
# Repositories that haven't synced in over an hour
(time() - quay_repository_mirror_last_sync_timestamp) > 3600
```

---

#### 7. Synchronization Duration

```text
quay_repository_mirror_sync_duration_seconds_bucket{namespace="org1",le="60"} 45
quay_repository_mirror_sync_duration_seconds_bucket{namespace="org1",le="300"} 82
quay_repository_mirror_sync_duration_seconds_bucket{namespace="org1",le="+Inf"} 100
```

**Type:** Histogram
**Labels:**
- `namespace`: Organization or user namespace

**Buckets:** 60s (1m), 300s (5m), 900s (15m), 3600s (1h), +Inf

**Description:** Duration of synchronization operations aggregated by namespace, allowing percentile calculations and performance analysis. Per-repository granularity is omitted to control time series cardinality at scale.

**Use Cases:**
- Calculate 95th/99th percentile sync times per namespace
- Track performance trends over time
- Capacity planning

**Example Queries:**
```promql
# 95th percentile sync duration
histogram_quantile(0.95, rate(quay_repository_mirror_sync_duration_seconds_bucket[5m]))

# Average sync duration per namespace
rate(quay_repository_mirror_sync_duration_seconds_sum[5m]) /
rate(quay_repository_mirror_sync_duration_seconds_count[5m])
```

---

### Legacy Metric

#### Unmirrored Repositories

```text
quay_repository_rows_unmirrored 42
```

**Type:** Gauge
**Description:** Number of repositories in the database that have not yet been mirrored. This metric is maintained for backward compatibility.

---

## Health Endpoint

### Endpoint Details

**Path:** `/v1/repository/mirror/health`
**Method:** GET
**Authentication:** Required (fresh login)
**Response Format:** JSON

### HTTP Status Codes

- `200 OK`: System is healthy
- `503 Service Unavailable`: System is unhealthy (critical issues detected)
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: `namespace` query parameter names a user or organization that does not exist

### Query Parameters

- `namespace` (optional): Filter health check to specific namespace
- `detailed` (optional, boolean): Include per-repository breakdown (default: false)
- `limit` (optional, integer): Maximum repositories returned in `repositories.details` when `detailed=true` (default: 100, max: 1000)
- `offset` (optional, integer): Offset into the sorted mirror list for paginated details (default: 0)

The JSON field `tags_pending` is the sum of `quay_repository_mirror_pending_tags` samples in **this** process’s Prometheus registry. On typical deployments the API does not run the mirror worker, so that sum is often `0` unless metrics are shared with the worker process.

The `workers.active` field is `quay_repository_mirror_workers_active` from **this** process’s registry (again often `0` on API-only pods). `workers.configured` is **`REPO_MIRROR_WORKER_REPLICAS`** when that config is set; otherwise it mirrors `workers.active` (both from the same in-process gauge). When `REPO_MIRROR_WORKER_REPLICAS` is set and exceeds `workers.active` while at least one enabled mirror exists, the response includes a warning issue and `healthy` may be `false` (HTTP **503**).

All `repositories` totals (`total`, `syncing`, `completed`, `failed`, `never_run`) and the optional `repositories.details` list include **enabled** mirror configurations only; disabled mirrors are omitted.

### Response Schema

#### Basic Response

```json
{
  "healthy": true,
  "workers": {
    "active": 1,
    "configured": 1,
    "status": "healthy"
  },
  "repositories": {
    "total": 150,
    "syncing": 3,
    "completed": 145,
    "failed": 2,
    "never_run": 0
  },
  "tags_pending": 47,
  "last_check": "2025-12-09T10:30:00Z",
  "issues": []
}
```

#### Unhealthy Response

```json
{
  "healthy": false,
  "workers": {
    "active": 3,
    "configured": 5,
    "status": "degraded"
  },
  "repositories": {
    "total": 100,
    "syncing": 2,
    "completed": 54,
    "failed": 19,
    "never_run": 25
  },
  "tags_pending": 234,
  "last_check": "2025-12-09T10:30:00Z",
  "issues": [
    {
      "severity": "critical",
      "message": "25.3% of repositories are failing (threshold: 20.0%)",
      "timestamp": "2025-12-09T10:30:00Z"
    },
    {
      "severity": "error",
      "message": "Repository org2/repo2 has exhausted all retry attempts",
      "timestamp": "2025-12-09T10:20:00Z"
    },
    {
      "severity": "warning",
      "message": "Repository org1/repo1 hasn't synced in over 24 hours",
      "timestamp": "2025-12-09T10:25:00Z"
    }
  ]
}
```

#### Detailed Response

When `detailed=true` is specified:

Each `repositories.details[]` item includes `last_sync`, which is either an ISO-8601 UTC timestamp string ending in `Z` or **`null`**. The API reads `quay_repository_mirror_last_sync_timestamp` from the in-process Prometheus registry in `endpoints/api/mirrorhealth.py`; when that metric has no sample for the repo in this process (typical when the mirror worker runs elsewhere), `last_sync` is `null`. Clients must treat the field as nullable.

The `workers.status` field reflects aggregate health: repository mirror row state plus optional replica mismatch when `REPO_MIRROR_WORKER_REPLICAS` is configured.

```json
{
  "healthy": true,
  "workers": {
    "active": 1,
    "configured": 1,
    "status": "healthy"
  },
  "repositories": {
    "total": 150,
    "syncing": 3,
    "completed": 145,
    "failed": 2,
    "never_run": 0,
    "details": [
      {
        "namespace": "org1",
        "repository": "repo1",
        "sync_status": "SUCCESS",
        "is_enabled": true,
        "last_sync": "2025-12-09T10:15:00Z",
        "retries_remaining": 3
      },
      {
        "namespace": "org2",
        "repository": "repo2",
        "sync_status": "FAIL",
        "is_enabled": true,
        "last_sync": null,
        "retries_remaining": 0
      }
    ],
    "pagination": {
      "limit": 100,
      "offset": 0,
      "has_more": false
    }
  },
  "tags_pending": 47,
  "last_check": "2025-12-09T10:30:00Z",
  "issues": []
}
```

### Health Determination Logic

The `healthy` field and HTTP status (`503` when unhealthy) are driven by repository **failure rate** over **enabled** mirrors only: more than **20%** of enabled mirrors that have left `NEVER_RUN` are in `FAIL`, i.e. `failed / (total - never_run) > 0.2` when `(total - never_run) > 0`. Mirrors still in `NEVER_RUN` are counted in `repositories.never_run` and are excluded from that denominator so new configurations do not count as failures.

The `issues` array may additionally include **warnings** (stale sync, never synced), **errors** (retry exhaustion), and **critical** entries when the failure-rate threshold is exceeded. Other health services may apply further rules (for example long-running `SYNCING` states).

### Example Usage

```bash
# Basic health check
curl -X GET "https://quay.example.com/v1/repository/mirror/health" \
  -H "Authorization: Bearer $TOKEN"

# Health check for specific namespace
curl -X GET "https://quay.example.com/v1/repository/mirror/health?namespace=myorg" \
  -H "Authorization: Bearer $TOKEN"

# Detailed health check
curl -X GET "https://quay.example.com/v1/repository/mirror/health?detailed=true" \
  -H "Authorization: Bearer $TOKEN"

# Paginated detailed view
curl -X GET "https://quay.example.com/v1/repository/mirror/health?detailed=true&limit=50&offset=50" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Organization Mirror Metrics

Organization-level mirroring (`FEATURE_ORG_MIRROR`) discovers repositories from an external registry namespace and syncs tags into a target Quay organization. Per-repository and discovery metrics are defined in `workers/repomirrorworker/org_mirror_metrics.py` and updated by instrumented worker hooks installed from `workers/repomirrorworker/repomirrorworker.py`. Shared update helpers live in `workers/repomirrorworker/metrics.py`.

Metrics are pushed to PushGateway on port **9091** from the **mirror worker process** (`repomirrorworker`), same as repository mirroring. Scrape mirror worker pods in production; API pods typically do not expose org mirror gauge samples.

### Existing aggregate metrics (unchanged)

- `quay_org_mirror_repo_sync_total{status}`
- `quay_org_mirror_repo_sync_duration_seconds`
- `quay_org_mirror_discovery_total{status}`
- `quay_org_mirror_discovery_duration_seconds`
- `quay_org_mirror_repos_discovered`
- `quay_org_mirror_repos_created_total`
- `quay_org_mirror_configs_pending_discovery`
- `quay_org_mirror_repositories_unmirrored`

### Per-repository sync gauges

#### Tags pending synchronization

```text
quay_org_mirror_pending_tags{namespace="coreos",repository="etcd"} 3
```

**Type:** Gauge
**Labels:** `namespace` (target Quay organization username), `repository` (discovered repo name)

**Description:** Tags remaining in the current org mirror sync for each discovered repository.

---

#### Last synchronization status

```text
quay_org_mirror_last_sync_status{namespace="coreos",repository="etcd",last_error_reason=""} 1
quay_org_mirror_last_sync_status{namespace="coreos",repository="etcd",last_error_reason="auth_failed"} 0
```

**Type:** Gauge
**Labels:** `namespace`, `repository`, `last_error_reason`

**Values:** `0` = failed, `1` = success, `2` = in progress

The canonical series uses `last_error_reason=""`. On failure, a detail series may also be set with `last_error_reason=<category>`.

**Repository sync failure categories (`last_error_reason`):**

| Reason | Description |
|--------|-------------|
| `auth_failed` | Authentication failure (401/403, invalid credentials) |
| `network_timeout` | Connection or skopeo timeout |
| `not_found` | Image or tag not found (404) |
| `registry_error` | Registry-side 5xx or unavailable |
| `image_error` | Corrupted manifest or invalid layer |
| `permission_denied` | Insufficient permissions on target namespace |
| `config_error` | TLS, proxy, or credential decryption issues |
| `unknown` | Unclassified error |

---

#### Complete synchronization status

```text
quay_org_mirror_sync_complete{namespace="coreos",repository="etcd"} 1
```

**Type:** Gauge
**Values:** `0` = incomplete, `1` = all tags synced successfully in the last run

---

#### Synchronization failure counter

```text
quay_org_mirror_sync_failures_total{namespace="coreos",reason="network_timeout"} 2
```

**Type:** Counter
**Labels:** `namespace`, `reason` only — **no `repository` label** (cardinality control when orgs discover 100+ repos)

---

#### Last synchronization timestamp

```text
quay_org_mirror_last_sync_timestamp{namespace="coreos",repository="etcd"} 1718712345
```

**Type:** Gauge
**Labels:** `namespace`, `repository`

Unix timestamp of the last sync attempt start.

---

### Discovery gauges (config-level)

#### Last discovery status

```text
quay_org_mirror_last_discovery_status{namespace="coreos"} 1
```

**Type:** Gauge
**Labels:** `namespace`

**Values:** `0` = failed, `1` = success, `2` = in progress

---

#### Last discovery timestamp

```text
quay_org_mirror_last_discovery_timestamp{namespace="coreos"} 1718712000
```

**Type:** Gauge
**Labels:** `namespace`

Unix timestamp of the last discovery attempt.

**Discovery failure categories** (used internally when mapping registry API errors; reflected in `last_discovery_status`):

| Reason | Description |
|--------|-------------|
| `auth_failed` | Registry API authentication failure |
| `network_timeout` | Timeout during API pagination |
| `api_error` | 5xx or malformed JSON from registry API |
| `rate_limited` | HTTP 429 |
| `not_found` | External namespace/org not found |
| `permission_denied` | Insufficient scope to list repositories |
| `pagination_error` | Broken pagination token |
| `config_error` | Invalid registry URL or reference format |
| `unknown` | Unclassified error |

---

### Parity with repository mirror metrics

| Repository mirror | Organization mirror | Label notes |
|-------------------|---------------------|-------------|
| `quay_repository_mirror_pending_tags` | `quay_org_mirror_pending_tags` | Same: `namespace`, `repository` |
| `quay_repository_mirror_last_sync_status` | `quay_org_mirror_last_sync_status` | Same: `namespace`, `repository`, `last_error_reason` |
| `quay_repository_mirror_sync_complete` | `quay_org_mirror_sync_complete` | Same |
| `quay_repository_mirror_sync_failures_total` | `quay_org_mirror_sync_failures_total` | Org counter: `namespace`, `reason` only |
| `quay_repository_mirror_last_sync_timestamp` | `quay_org_mirror_last_sync_timestamp` | Same |
| — | `quay_org_mirror_last_discovery_status` | Org-only: `namespace` |
| — | `quay_org_mirror_last_discovery_timestamp` | Org-only: `namespace` |

Worker liveness uses shared `quay_repository_mirror_workers_active` (one worker process handles both repo and org mirror jobs).

**Example PromQL (multi-org dashboards):**

```promql
# Per-org success count (canonical series)
sum by (namespace) (quay_org_mirror_last_sync_status{last_error_reason=""} == 1)

# Orgs with discovery failures
quay_org_mirror_last_discovery_status == 0

# Failure rate by namespace (counter)
sum by (namespace) (rate(quay_org_mirror_sync_failures_total[5m]))
```

There is **no global org-mirror health API**; multi-org visibility is Prometheus/Grafana only.

---

## Organization Mirror Health Endpoint

### Endpoint details

**Path:** `/v1/organization/<orgname>/mirror/health`
**Method:** GET
**Feature gate:** `FEATURE_ORG_MIRROR`
**Authentication:** Required (fresh login)

### HTTP status codes

- `200 OK`: `"healthy": true`
- `503 Service Unavailable`: `"healthy": false`
- `401 Unauthorized`: Not authenticated, not an org member, or stale session
- `404 Not Found`: Organization does not exist, or org has no mirror configuration

### Query parameters

- `detailed` (optional, boolean): Include paginated per-discovered-repo rows (default: `false`)
- `limit` (optional, integer): Page size when `detailed=true` (default: 100, max: 1000)
- `offset` (optional, integer): Offset into sorted discovered-repo list (default: 0)

No `namespace` filter — the organization is already in the path.

### Response schema (summary)

```json
{
  "healthy": true,
  "workers": {
    "active": 0,
    "configured": 0,
    "status": "healthy"
  },
  "organization": {
    "syncing": 0,
    "completed": 1,
    "failed": 0,
    "never_run": 0,
    "last_discovery_status": 1,
    "last_discovery_timestamp": "2026-06-18T10:34:59.935806Z",
    "repositories": {
      "total": 12,
      "syncing": 0,
      "completed": 11,
      "failed": 1,
      "never_run": 0,
      "skipped": 0,
      "tags_pending": 0
    }
  },
  "last_check": "2026-06-18T11:10:24.403211Z",
  "issues": []
}
```

**Config-level indicators:** `syncing`, `completed`, `failed`, and `never_run` are always present as `0` or `1`; exactly one is `1` for the current `OrgMirrorConfig.sync_status`.

**`last_discovery_status`:** integer `0` = failed, `1` = success, `2` = in progress (from `quay_org_mirror_last_discovery_status` when available in this process, else derived from config state).

**`organization.repositories`:** aggregates over discovered repos (`SYNCING` + `SYNC_NOW` → `syncing`, `SKIP` → `skipped`). `tags_pending` sums `quay_org_mirror_pending_tags` from the in-process registry (often `0` on API pods).

### Detailed response

When `detailed=true`, `organization.repositories` includes `details[]` and `pagination`:

```json
{
  "namespace": "coreos",
  "repository": "etcd",
  "sync_status": "SUCCESS",
  "last_sync": "2026-06-18T11:08:12.000000Z",
  "retries_remaining": 3,
  "status_message": null
}
```

`last_sync` prefers `quay_org_mirror_last_sync_timestamp` from the registry when present; otherwise falls back to `OrgMirrorRepository.last_sync_date`.

### Health determination

Same semantics as repository mirror health where applicable:

- **Critical:** `failed / (total - never_run - skipped) > 0.2` when denominator &gt; 0
- **Warning:** worker replica mismatch when `REPO_MIRROR_WORKER_REPLICAS` is set, org mirror enabled, and `workers.active < workers.configured`
- **Warning:** discovered repos not synced in 24+ hours (from metric timestamps)
- **Warning:** discovered repos still `NEVER_RUN` after discovery completed
- **Error:** `FAIL` with `sync_retries_remaining == 0`
- **Error:** `OrgMirrorConfig.sync_status == FAIL`

### Example usage

```bash
# Org member or superuser (fresh session)
curl -s -b "$COOKIES" -w "\nHTTP %{http_code}\n" \
  "$QUAY_URL/api/v1/organization/coreos/mirror/health" | jq

# Per-repo breakdown
curl -s -b "$COOKIES" \
  "$QUAY_URL/api/v1/organization/coreos/mirror/health?detailed=true&limit=50" | jq
```

Manual Podman/OpenShift validation steps: [mirror-health-test-podman.md](mirror-health-test-podman.md).

---

## Example Prometheus Alert Rules

### Critical Alerts

```yaml
groups:
  - name: quay_mirror_critical
    interval: 30s
    rules:
      - alert: QuayMirrorWorkersDown
        expr: quay_repository_mirror_workers_active == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "No active mirror workers"
          description: "All mirror workers are down or not responding"

      - alert: QuayMirrorHighFailureCount
        expr: quay_repository_mirror_sync_failures_total > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High number of mirror synchronization failures"
          description: "Repository {{ $labels.namespace }}/{{ $labels.repository }} has {{ $value }} total failures"
```

### Warning Alerts

```yaml
      - alert: QuayMirrorSyncFailures
        expr: rate(quay_repository_mirror_sync_failures_total[5m]) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Repository mirroring failures detected"
          description: "Repository {{ $labels.namespace }}/{{ $labels.repository }} has {{ $value }} failures per second (reason: {{ $labels.reason }})"

      - alert: QuayMirrorSyncStale
        expr: time() - quay_repository_mirror_last_sync_timestamp > 3600
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Mirror synchronization is stale"
          description: "Repository {{ $labels.namespace }}/{{ $labels.repository }} hasn't synced in over an hour"

      - alert: QuayMirrorHighPendingTags
        expr: sum(quay_repository_mirror_pending_tags) > 1000
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High number of pending tags"
          description: "There are {{ $value }} tags pending synchronization across all repositories"

      - alert: QuayMirrorAuthFailures
        expr: increase(quay_repository_mirror_sync_failures_total{reason="auth_failed"}[1h]) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Mirror authentication failures"
          description: "Repository {{ $labels.namespace }}/{{ $labels.repository }} has had {{ $value }} authentication failures in the last hour"
```

### Organization mirror alerts

```yaml
      - alert: QuayOrgMirrorDiscoveryFailed
        expr: quay_org_mirror_last_discovery_status == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Org mirror discovery failed"
          description: "Organization {{ $labels.namespace }} last discovery failed"

      - alert: QuayOrgMirrorRepoSyncFailed
        expr: quay_org_mirror_last_sync_status{last_error_reason=""} == 0
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Org-mirrored repository sync failed"
          description: "Repository {{ $labels.namespace }}/{{ $labels.repository }} last sync failed"

      - alert: QuayOrgMirrorHighFailureRate
        expr: sum by (namespace) (rate(quay_org_mirror_sync_failures_total[5m])) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Elevated org mirror failure rate"
          description: "Organization {{ $labels.namespace }} org mirror failures: {{ $value }}/s"
```

---

## Example Grafana Dashboard Queries

### Panel 1: Synchronization Status Overview

```promql
# Count of repositories by sync status (canonical series: last_error_reason="")
sum by(namespace) (quay_repository_mirror_last_sync_status{last_error_reason=""} == 1)  # Success
sum by(namespace) (quay_repository_mirror_last_sync_status{last_error_reason=""} == 0)  # Failed
sum by(namespace) (quay_repository_mirror_last_sync_status{last_error_reason=""} == 2)  # In Progress
```

**Visualization:** Pie chart or time series

---

### Panel 1b: Organization mirror sync status (per org)

```promql
sum by (namespace) (quay_org_mirror_last_sync_status{last_error_reason=""} == 1)  # Success
sum by (namespace) (quay_org_mirror_last_sync_status{last_error_reason=""} == 0)  # Failed
sum by (namespace) (quay_org_mirror_last_discovery_status == 0)                   # Discovery failed
```

**Visualization:** Table or time series (multi-org deployments)

---

### Panel 2: Failure Rate

```promql
# Failures per second by namespace
rate(quay_repository_mirror_sync_failures_total[5m])

# Total failure rate
sum(rate(quay_repository_mirror_sync_failures_total[5m]))
```

**Visualization:** Time series

---

### Panel 3: Failures by Reason

```promql
# Count failures by reason
sum by (reason) (quay_repository_mirror_sync_failures_total)

# Failure rate by reason
sum by (reason) (rate(quay_repository_mirror_sync_failures_total[5m]))
```

**Visualization:** Bar chart or table

---

### Panel 4: Pending Tags by Repository

```promql
# Top 10 repositories by pending tags
topk(10, quay_repository_mirror_pending_tags)

# Total pending tags
sum(quay_repository_mirror_pending_tags)
```

**Visualization:** Bar chart or gauge

---

### Panel 5: Active Mirror Workers

```promql
quay_repository_mirror_workers_active
```

**Visualization:** Gauge or single stat

---

### Panel 6: Synchronization Duration

```promql
# 95th percentile sync duration
histogram_quantile(0.95, rate(quay_repository_mirror_sync_duration_seconds_bucket[5m]))

# 99th percentile sync duration
histogram_quantile(0.99, rate(quay_repository_mirror_sync_duration_seconds_bucket[5m]))

# Average duration by namespace
rate(quay_repository_mirror_sync_duration_seconds_sum{namespace="myorg"}[5m]) /
rate(quay_repository_mirror_sync_duration_seconds_count{namespace="myorg"}[5m])
```

**Visualization:** Time series or heatmap

---

### Panel 7: Incomplete Syncs

```promql
# Count of incomplete synchronizations
count(quay_repository_mirror_sync_complete == 0)

# List of repositories with incomplete syncs
quay_repository_mirror_sync_complete == 0
```

**Visualization:** Single stat and table

---

## Best Practices

### Metric Collection

1. **Scrape Interval**: Set Prometheus scrape interval to 30-60 seconds for mirror metrics
2. **Retention**: Keep at least 30 days of history for trend analysis
3. **Cardinality Management**: Monitor the number of mirrored repositories; consider aggregating by namespace for very large deployments (100+ mirrors)

### Alerting

1. **Failure Thresholds**: Set alerts based on your SLA requirements
2. **Notification Routing**: Route auth failures to security teams, network failures to infrastructure
3. **Alert Fatigue**: Use appropriate `for` durations to avoid transient alert noise
4. **Escalation**: Set up tiered alerts (warning → critical) based on failure count and duration

### Monitoring

1. **Dashboard Organization**: Create separate dashboards for:
   - Overview (system-wide health)
   - Per-namespace views
   - Troubleshooting (detailed failure analysis)
2. **Correlate Metrics**: Combine mirror metrics with system metrics (CPU, memory, network) for root cause analysis
3. **Regular Review**: Weekly review of failure patterns and trends

### Capacity Planning

1. Monitor sync duration trends to predict when additional workers are needed
2. Track total pending tags to understand workload
3. Use histogram metrics to identify performance degradation before it impacts SLAs

---

## Troubleshooting Guide

### High Failure Rate

1. Check `quay_repository_mirror_sync_failures_total` broken down by `reason`
2. For auth failures: Verify credentials, check token expiration
3. For network timeouts: Check network connectivity, consider increasing `skopeo_timeout_interval`
4. For TLS errors: Verify certificate validity, check `verify_tls` settings

### Stale Synchronizations

1. Query `quay_repository_mirror_last_sync_timestamp` to find affected repositories
2. Check if `sync_interval` is appropriate for the repository update frequency
3. Verify mirror workers are running and processing jobs
4. Check if repositories are disabled

### Slow Synchronization

1. Use `quay_repository_mirror_sync_duration_seconds` histogram to identify slow mirrors
2. Check repository size (number of tags, layer sizes)
3. Verify network bandwidth between Quay and external registry
4. Consider adjusting `skopeo_timeout_interval` for large images

### Incomplete Synchronizations

1. Query `quay_repository_mirror_sync_complete == 0` to find affected repositories
2. Check logs for specific tag failures
3. Review `quay_repository_mirror_sync_failures_total` by reason
4. Verify tag patterns in mirror configuration are correct

---

## Integration with Existing Health Checks

The mirror health service is automatically integrated into Quay's existing health check infrastructure:

- Available via `/health/endtoend` endpoint (includes all services)
- Can be monitored separately via the dedicated `/v1/repository/mirror/health` endpoint
- Organization mirror health: `/v1/organization/<orgname>/mirror/health` (per-org only)
- Follows the same patterns as other Quay health services

---

## Backward Compatibility

All existing metrics remain unchanged:
- `quay_repository_rows_unmirrored` continues to function as before
- New metrics are additive and don't affect existing monitoring setups
- Old monitoring configurations will continue to work without modification

---

## Security Considerations

1. **Authentication**: Both metrics and health endpoints require authentication
2. **Namespace Filtering**: Users can only view health for namespaces they have access to
3. **Sensitive Information**: Credentials and passwords are never exposed in metrics or health responses
4. **Error Messages**: Failure reasons are categorized generically to avoid leaking sensitive details

---

## Additional Resources

- [Mirror health manual QA (Podman / OpenShift)](mirror-health-test-podman.md)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboard Examples](https://grafana.com/grafana/dashboards/)
- [Quay Configuration Documentation](https://docs.projectquay.io/)
- [Repository Mirroring Guide](https://docs.projectquay.io/repo_mirror.html)
