# Repository Mirror Metrics and Health Endpoints

This document describes the comprehensive metrics and health endpoints available for monitoring Quay's repository mirroring functionality.

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
quay_repository_mirror_sync_failures_total{namespace="org1",repository="repo1",reason="network_timeout"} 3
quay_repository_mirror_sync_failures_total{namespace="org2",repository="repo2",reason="auth_failed"} 7
```

**Type:** Counter  
**Labels:**
- `namespace`: Organization or user namespace
- `repository`: Repository name
- `reason`: Categorized failure reason (see error reasons above)

**Description:** Cumulative counter of synchronization failures per repository. Increments on each failed sync attempt, with failures categorized by reason.

**Use Cases:**
- Set up alerts based on failure thresholds
- Track failure rates over time
- Identify consistently problematic repositories
- Analyze failure patterns by type

**Example Queries:**
```promql
# Failure rate per repository over 5 minutes
rate(quay_repository_mirror_sync_failures_total[5m])

# Repositories with more than 10 total failures
quay_repository_mirror_sync_failures_total > 10

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
**Description:** Number of currently active mirror worker processes.

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
quay_repository_mirror_sync_duration_seconds_bucket{namespace="org1",repository="repo1",le="30"} 45
quay_repository_mirror_sync_duration_seconds_bucket{namespace="org1",repository="repo1",le="60"} 82
quay_repository_mirror_sync_duration_seconds_bucket{namespace="org1",repository="repo1",le="+Inf"} 100
```

**Type:** Histogram  
**Labels:**
- `namespace`: Organization or user namespace
- `repository`: Repository name

**Buckets:** 30s, 60s, 120s, 300s (5m), 600s (10m), 1200s (20m), 1800s (30m), 3600s (1h), 7200s (2h), +Inf

**Description:** Duration of synchronization operations, allowing percentile calculations and performance analysis.

**Use Cases:**
- Calculate 95th/99th percentile sync times
- Identify slow mirrors
- Track performance trends over time
- Capacity planning

**Example Queries:**
```promql
# 95th percentile sync duration
histogram_quantile(0.95, rate(quay_repository_mirror_sync_duration_seconds_bucket[5m]))

# Average sync duration per repository
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

### Response Schema

#### Basic Response

```json
{
  "healthy": true,
  "workers": {
    "active": 5,
    "configured": 5,
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

```json
{
  "healthy": true,
  "workers": { ... },
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
        "last_sync": "2025-12-09T09:00:00Z",
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

The `healthy` field and HTTP status (`503` when unhealthy) are driven by repository **failure rate**: more than **20%** of mirrors that have left `NEVER_RUN` are in `FAIL`, i.e. `failed / (total - never_run) > 0.2` when `(total - never_run) > 0`. Mirrors still in `NEVER_RUN` are counted in `repositories.never_run` and are excluded from that denominator so new configurations do not count as failures.

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

### Panel 2: Failure Rate

```promql
# Failures per second by repository
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

# Average duration by repository
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

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboard Examples](https://grafana.com/grafana/dashboards/)
- [Quay Configuration Documentation](https://docs.projectquay.io/)
- [Repository Mirroring Guide](https://docs.projectquay.io/repo_mirror.html)
