# Repository Mirror Metrics - Quick Start Guide

This guide helps you quickly get started with the new repository mirror metrics and health endpoints.

## Prerequisites

- Quay with REPO_MIRROR feature enabled
- Prometheus configured to scrape Quay metrics
- (Optional) Grafana for dashboards

## 5-Minute Setup

### Step 1: Verify Metrics Are Available

After upgrading Quay, check that new metrics appear:

```bash
# If using PushGateway
curl http://your-pushgateway:9091/metrics | grep quay_repository_mirror

# You should see:
# quay_repository_mirror_pending_tags
# quay_repository_mirror_last_sync_status
# quay_repository_mirror_sync_complete
# quay_repository_mirror_sync_failures_total
# quay_repository_mirror_workers_active
# quay_repository_mirror_last_sync_timestamp
# quay_repository_mirror_sync_duration_seconds
```

### Step 2: Test the Health Endpoint

```bash
# Get auth token (adjust for your setup)
TOKEN="your-bearer-token"

# Check overall health
curl -H "Authorization: Bearer $TOKEN" \
  https://quay.example.com/v1/repository/mirror/health | jq

# Check specific namespace
curl -H "Authorization: Bearer $TOKEN" \
  "https://quay.example.com/v1/repository/mirror/health?namespace=myorg" | jq

# Get detailed per-repository info
curl -H "Authorization: Bearer $TOKEN" \
  "https://quay.example.com/v1/repository/mirror/health?detailed=true" | jq
```

### Step 3: Add Basic Prometheus Alerts

Create a file `quay-mirror-alerts.yml`:

```yaml
groups:
  - name: quay_mirror_basic
    interval: 60s
    rules:
      # Alert if any workers are down
      - alert: QuayMirrorNoWorkers
        expr: quay_repository_mirror_workers_active == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "No mirror workers active"
          
      # Alert if any repository is failing
      - alert: QuayMirrorFailures
        expr: quay_repository_mirror_last_sync_status{last_error_reason=""} == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Mirror failing for {{ $labels.namespace }}/{{ $labels.repository }}"
          description: "Canonical status is failed; check detail series last_error_reason for cause"
```

Load into Prometheus:

```bash
# Add to prometheus.yml
rule_files:
  - "quay-mirror-alerts.yml"

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload
```

### Step 4: Create a Basic Grafana Dashboard

Import this JSON or create panels manually:

**Panel 1: Sync Status Pie Chart**
```promql
# Success (canonical series: one series per repo)
count(quay_repository_mirror_last_sync_status{last_error_reason=""} == 1)

# Failed
count(quay_repository_mirror_last_sync_status{last_error_reason=""} == 0)

# In Progress
count(quay_repository_mirror_last_sync_status{last_error_reason=""} == 2)
```

**Panel 2: Failure Rate Graph**
```promql
sum(rate(quay_repository_mirror_sync_failures_total[5m]))
```

**Panel 3: Top Failing Repositories**
```promql
topk(10, quay_repository_mirror_sync_failures_total)
```

## Common Use Cases

### Use Case 1: "Which mirrors are currently failing?"

**Query (one result per repo):**
```promql
quay_repository_mirror_last_sync_status{last_error_reason=""} == 0
```

**Drill-down by failure category:**
```promql
quay_repository_mirror_last_sync_status{last_error_reason="auth_failed"} == 0
```

### Use Case 2: "What's causing most failures?"

**Query:**
```promql
topk(5, sum by (reason) (quay_repository_mirror_sync_failures_total))
```

**Result:**
```
{reason="auth_failed"} 25
{reason="network_timeout"} 12
{reason="tls_error"} 5
```

### Use Case 3: "How long do syncs typically take?"

**Query:**
```promql
histogram_quantile(0.95, rate(quay_repository_mirror_sync_duration_seconds_bucket[5m]))
```

**Result:**
```
120.5  # 95% of syncs complete within 120.5 seconds
```

### Use Case 4: "Which mirrors haven't synced recently?"

**Query:**
```promql
(time() - quay_repository_mirror_last_sync_timestamp) > 3600
```

**Result:**
```
{namespace="org3",repository="stale-repo"} 7200  # 2 hours since last sync
```

### Use Case 5: "Are we experiencing auth issues?"

**Query:**
```promql
increase(quay_repository_mirror_sync_failures_total{reason="auth_failed"}[1h]) > 0
```

**Alert Rule:**
```yaml
- alert: QuayMirrorAuthFailures
  expr: increase(quay_repository_mirror_sync_failures_total{reason="auth_failed"}[1h]) > 3
  labels:
    severity: warning
  annotations:
    summary: "Multiple auth failures for {{ $labels.namespace }}/{{ $labels.repository }}"
```

## Troubleshooting Scenarios

### Scenario 1: Sync is Failing

1. Check the current status (canonical):
   ```promql
   quay_repository_mirror_last_sync_status{namespace="myorg",repository="myrepo",last_error_reason=""}
   ```

2. If status is 0, check the detail series for categorized reason, e.g.:
   ```promql
   quay_repository_mirror_last_sync_status{namespace="myorg",repository="myrepo",last_error_reason="auth_failed"}
   ```

3. Common fixes:
   - `auth_failed`: Update credentials in mirror config
   - `network_timeout`: Increase skopeo_timeout_interval
   - `tls_error`: Check verify_tls setting
   - `connection_error`: Verify network connectivity

### Scenario 2: Slow Syncs

1. Check sync duration:
   ```promql
   quay_repository_mirror_sync_duration_seconds{namespace="myorg",repository="myrepo"}
   ```

2. Compare to average:
   ```promql
   avg(rate(quay_repository_mirror_sync_duration_seconds_sum[1h]) / 
       rate(quay_repository_mirror_sync_duration_seconds_count[1h]))
   ```

3. Investigation steps:
   - Check number of tags: High pending tags → slower sync
   - Check network bandwidth
   - Review external registry performance
   - Consider increasing resources

### Scenario 3: High Number of Pending Tags

1. Check total pending:
   ```promql
   sum(quay_repository_mirror_pending_tags)
   ```

2. Find repositories with most pending:
   ```promql
   topk(10, quay_repository_mirror_pending_tags)
   ```

3. Possible causes:
   - Normal: Sync in progress
   - Problem: Worker crashed mid-sync
   - Problem: Very large upstream repository

### Scenario 4: No Workers Active

1. Check worker count:
   ```promql
   quay_repository_mirror_workers_active
   ```

2. If zero, check:
   - Worker process is running: `ps aux | grep repomirrorworker`
   - Worker logs for errors
   - Database connectivity
   - Feature flag: REPO_MIRROR is enabled

## Integration Examples

### Webhook on Failure

Use AlertManager to call a webhook when mirrors fail:

```yaml
# alertmanager.yml
receivers:
  - name: mirror-webhook
    webhook_configs:
      - url: 'https://your-automation.com/mirror-failed'
        send_resolved: true

route:
  routes:
    - match:
        alertname: QuayMirrorFailures
      receiver: mirror-webhook
```

### Slack Notifications

```yaml
# alertmanager.yml
receivers:
  - name: slack-mirrors
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#quay-alerts'
        title: 'Mirror Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'

route:
  routes:
    - match_re:
        alertname: QuayMirror.*
      receiver: slack-mirrors
```

### PagerDuty Escalation

```yaml
# alertmanager.yml  
receivers:
  - name: pagerduty-critical
    pagerduty_configs:
      - service_key: YOUR_SERVICE_KEY
        severity: critical

route:
  routes:
    - match:
        severity: critical
        alertname: QuayMirrorNoWorkers
      receiver: pagerduty-critical
```

## Best Practices

### Alert Tuning

1. **Start conservative**: Begin with high thresholds, lower as you understand baseline
2. **Use 'for' duration**: Avoid alerts on transient issues
   ```yaml
   for: 10m  # Alert only if condition persists for 10 minutes
   ```
3. **Group by severity**: Critical = immediate action, Warning = investigate

### Dashboard Organization

1. **Overview dashboard**: System-wide health at a glance
2. **Namespace dashboards**: Per-organization views for users
3. **Troubleshooting dashboard**: Detailed metrics for debugging

### Metric Retention

- Keep at least 30 days for trend analysis
- Use Prometheus remote write for long-term storage
- Consider downsampling old data

### Capacity Planning

Monitor these trends monthly:
- Average sync duration (increasing = need more resources)
- Number of mirrored repositories (plan for growth)
- Failure rates by type (identify systemic issues)

## Quick Reference

### Key Metrics Cheat Sheet

| What You Want | PromQL Query |
|--------------|-------------|
| Failing repos | `quay_repository_mirror_last_sync_status{last_error_reason=""} == 0` |
| Success rate | `count(quay_repository_mirror_last_sync_status{last_error_reason=""} == 1) / count(quay_repository_mirror_last_sync_status{last_error_reason=""})` |
| Failures/min | `rate(quay_repository_mirror_sync_failures_total[1m])` |
| Avg sync time | `rate(quay_repository_mirror_sync_duration_seconds_sum[5m]) / rate(quay_repository_mirror_sync_duration_seconds_count[5m])` |
| Stale syncs | `(time() - quay_repository_mirror_last_sync_timestamp) > 3600` |
| Failures by type | `sum by (reason) (quay_repository_mirror_sync_failures_total)` |

### Health Endpoint Cheat Sheet

| Want to Know | Command |
|-------------|---------|
| Overall health | `curl $URL/v1/repository/mirror/health` |
| Org health | `curl $URL/v1/repository/mirror/health?namespace=org1` |
| All details | `curl $URL/v1/repository/mirror/health?detailed=true` |
| Just HTTP code | `curl -o /dev/null -w '%{http_code}' $URL/v1/repository/mirror/health` |

## Next Steps

1. ✅ Verify metrics are being collected
2. ✅ Set up basic alerts
3. ✅ Create a simple dashboard
4. 📖 Read full documentation: `docs/mirroring-metrics.md`
5. 🔧 Tune alerts based on your environment
6. 📊 Build organization-specific dashboards
7. 🔄 Integrate with your incident management system

## Getting Help

- **Metrics not appearing?** Check Prometheus scrape configuration
- **Health endpoint 401?** Verify authentication token
- **High cardinality?** Consider namespace-level aggregation
- **More questions?** See full documentation in `docs/mirroring-metrics.md`

## Summary

You now have:
- ✅ Real-time visibility into mirror operations
- ✅ Categorized failure tracking
- ✅ Performance metrics
- ✅ Automated health monitoring
- ✅ Foundation for alerts and dashboards

Start with the basics above, then expand based on your needs!

