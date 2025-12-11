# Repository Mirroring Metrics

This document describes the Prometheus metrics available for monitoring repository mirroring operations in Quay.

## Available Metrics

### 1. Tags Pending Synchronization

**Metric Name:** `quay_repository_mirror_pending_tags`  
**Type:** Gauge  
**Labels:** `namespace`, `repository`  
**Description:** Total number of tags not yet synchronized for each mirrored repository.

This metric shows how many tags remain to be synced during an active synchronization run. It starts at the total number of matching tags and decrements as each tag is processed. Between sync runs, it will be 0.

**Example Query:**
```promql
# Show pending tags for all repositories
quay_repository_mirror_pending_tags

# Show repositories with pending tags
quay_repository_mirror_pending_tags > 0

# Show average pending tags per namespace
avg by (namespace) (quay_repository_mirror_pending_tags)
```

### 2. Last Synchronization Status

**Metric Name:** `quay_repository_mirror_last_sync_status`  
**Type:** Gauge  
**Labels:** `namespace`, `repository`, `status`  
**Description:** Indicates the status of the latest synchronization attempt per repository.

**Status Values:**
- `1` = SUCCESS - All tags synchronized successfully
- `0` = NEVER_RUN - Repository has never been synchronized
- `-1` = FAIL - Synchronization failed
- `-2` = CANCEL - Synchronization was cancelled
- `2` = SYNCING - Currently synchronizing
- `3` = SYNC_NOW - Queued for immediate synchronization

**Example Query:**
```promql
# Show all repositories with failed sync
quay_repository_mirror_last_sync_status{status="FAIL"} == -1

# Show repositories currently syncing
quay_repository_mirror_last_sync_status{status="SYNCING"} == 2

# Count repositories by status
sum by (status) (quay_repository_mirror_last_sync_status)
```

### 3. Complete Synchronization Indicator

**Metric Name:** `quay_repository_mirror_sync_complete`  
**Type:** Gauge  
**Labels:** `namespace`, `repository`  
**Description:** Boolean indicator of whether all tags were successfully synchronized in the last run.

**Values:**
- `1` = Complete - All tags successfully synchronized
- `0` = Incomplete - Some or all tags failed to synchronize

**Example Query:**
```promql
# Show repositories with incomplete syncs
quay_repository_mirror_sync_complete == 0

# Calculate percentage of successful syncs
(sum(quay_repository_mirror_sync_complete) / count(quay_repository_mirror_sync_complete)) * 100
```

### 4. Synchronization Failure Counter

**Metric Name:** `quay_repository_mirror_sync_failures_total`  
**Type:** Counter  
**Labels:** `namespace`, `repository`  
**Description:** Total number of synchronization failures per repository. This counter increments each time a sync fails.

This is the key metric for alerting on mirroring issues. It accumulates over time and never decreases.

**Example Query:**
```promql
# Show repositories with failures in the last hour
increase(quay_repository_mirror_sync_failures_total[1h]) > 0

# Show repositories with multiple recent failures (alert condition)
increase(quay_repository_mirror_sync_failures_total[1h]) >= 3

# Show failure rate
rate(quay_repository_mirror_sync_failures_total[5m])
```

## Alerting Examples

### Critical: Multiple Consecutive Failures

```yaml
- alert: RepositoryMirrorMultipleFailures
  expr: increase(quay_repository_mirror_sync_failures_total[1h]) >= 3
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Repository {{ $labels.namespace }}/{{ $labels.repository }} has failed to sync 3+ times in the last hour"
    description: "Multiple mirror sync failures detected. Check repository configuration and external registry connectivity."
```

### Warning: Sync Incomplete

```yaml
- alert: RepositoryMirrorIncompleteSync
  expr: quay_repository_mirror_sync_complete == 0
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Repository {{ $labels.namespace }}/{{ $labels.repository }} has incomplete synchronization"
    description: "Not all tags were successfully synchronized in the last run."
```

### Warning: Long-Running Sync

```yaml
- alert: RepositoryMirrorSyncTakingTooLong
  expr: quay_repository_mirror_pending_tags > 0
  for: 2h
  labels:
    severity: warning
  annotations:
    summary: "Repository {{ $labels.namespace }}/{{ $labels.repository }} sync is taking longer than expected"
    description: "{{ $value }} tags still pending after 2 hours. Sync may be stuck."
```

### Info: Sync Currently Running

```yaml
- alert: RepositoryMirrorSyncInProgress
  expr: quay_repository_mirror_last_sync_status{status="SYNCING"} == 2
  for: 0m
  labels:
    severity: info
  annotations:
    summary: "Repository {{ $labels.namespace }}/{{ $labels.repository }} is currently syncing"
    description: "This is informational only. Check pending tags metric for progress."
```

## Grafana Dashboard Examples

### Panel: Sync Status Overview

```promql
# Single stat panel showing total mirrored repositories
count(quay_repository_mirror_sync_complete)

# Single stat panel showing repositories with issues
count(quay_repository_mirror_sync_complete == 0)
```

### Panel: Failure Rate

```promql
# Graph panel showing failure rate over time
rate(quay_repository_mirror_sync_failures_total[5m])
```

### Panel: Sync Progress

```promql
# Bar gauge showing pending tags per repository
quay_repository_mirror_pending_tags
```

### Table: Repository Status

Use the following query with the "Table" visualization:
```promql
max by (namespace, repository, status) (quay_repository_mirror_last_sync_status)
```

## Metric Lifecycle

### Initialization
Metrics are automatically initialized when a mirror sync begins. No manual initialization is required.

### Updates
- **Pending Tags**: Updated in real-time as each tag is processed
- **Last Status**: Updated at the end of each sync run
- **Complete Indicator**: Updated at the end of each sync run
- **Failure Counter**: Incremented each time a sync fails

### Cleanup
The `cleanup_mirror_metrics()` function can be called to remove metrics for deleted repositories:

```python
from workers.repomirrorworker import cleanup_mirror_metrics

cleanup_mirror_metrics("myorg", "myrepo")
```

**Note:** Counter metrics (`quay_repository_mirror_sync_failures_total`) cannot be removed due to prometheus_client library limitations. They will naturally expire when the Quay process restarts or when Prometheus scrapes expire them.

## Cardinality Considerations

These metrics use `namespace` and `repository` labels, which creates one time series per mirrored repository. For deployments with hundreds or thousands of mirrored repositories:

1. **Monitor cardinality:** Track the number of unique label combinations
2. **Set retention policies:** Configure Prometheus retention based on your storage capacity
3. **Consider federation:** Use Prometheus federation for large deployments
4. **Use aggregation:** Pre-aggregate metrics in recording rules when possible

Example recording rule for aggregation:
```yaml
groups:
  - name: mirror_aggregates
    interval: 30s
    rules:
      - record: namespace:quay_repository_mirror_failures:sum
        expr: sum by (namespace) (increase(quay_repository_mirror_sync_failures_total[5m]))
```

## Troubleshooting

### Metrics Not Appearing

1. Verify that repository mirroring is enabled: `FEATURE_REPO_MIRROR=true`
2. Check that at least one mirror sync has run
3. Verify Prometheus is scraping the PushGateway on port 9091
4. Check that `PROMETHEUS_PUSHGATEWAY_URL` is configured

### Stale Metrics

Metrics persist in Prometheus/PushGateway until explicitly removed or until they expire. If you see metrics for deleted repositories:

1. Call `cleanup_mirror_metrics()` for the deleted repository
2. Restart the Quay worker processes to clear all metrics
3. Configure Prometheus to drop old series based on staleness

### Incorrect Values

If metrics show unexpected values:

1. Check worker logs for errors during metric updates
2. Verify the mirror sync is completing (check logs for "repo_mirror_sync_success" or "repo_mirror_sync_failed")
3. Ensure multiple workers aren't processing the same repository simultaneously
4. Check for race conditions in high-frequency sync scenarios

## Related Documentation

- [Prometheus Metrics Overview](prometheus.md)
- [Repository Mirroring Configuration](https://access.redhat.com/documentation/en-us/red_hat_quay/3/html/manage_red_hat_quay/repo-mirroring-in-red-hat-quay)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)


