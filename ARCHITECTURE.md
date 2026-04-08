# Repository Mirror Metrics Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          External Registry                               │
│                      (docker.io, quay.io, etc.)                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ Pulls images/tags
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Repository Mirror Worker                           │
│  (workers/repomirrorworker/__init__.py)                                 │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  perform_mirror()                                               │    │
│  │  • Tracks sync start time                                       │    │
│  │  • Updates metrics during sync:                                 │    │
│  │    - Sets status to in_progress (2)                            │    │
│  │    - Updates tags_pending after each tag                       │    │
│  │    - Records timestamp                                          │    │
│  │  • Categorizes failures with _map_failure_to_reason()         │    │
│  │  • Records final metrics:                                       │    │
│  │    - last_sync_status (with error_reason)                      │    │
│  │    - sync_complete                                              │    │
│  │    - sync_failures_total (with reason)                         │    │
│  │    - sync_duration_seconds                                      │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└────────────┬────────────────────────────────────────────┬───────────────┘
             │                                             │
             │ Exposes Metrics                            │ Database writes
             │                                             │
             ▼                                             ▼
┌──────────────────────────────────┐      ┌─────────────────────────────┐
│   Prometheus Metrics Endpoint    │      │      Quay Database          │
│   (via PushGateway :9091)        │      │                             │
│                                  │      │  • RepoMirrorConfig         │
│  Core Metrics:                   │      │  • sync_status              │
│  • quay_repository_mirror_pending_tags (Gauge) │      │  • sync_start_date          │
│  • last_sync_status (Gauge)      │      │  • sync_retries_remaining   │
│    └─ last_error_reason label    │      │  • Repository state         │
│  • sync_complete (Gauge)         │      │                             │
│  • sync_failures_total (Counter) │      └─────────────┬───────────────┘
│    └─ reason label                │                    │
│                                  │                    │ Queries
│  Supporting Metrics:             │                    │
│  • workers_active (Gauge)        │                    ▼
│  • last_sync_timestamp (Gauge)   │      ┌─────────────────────────────┐
│  • sync_duration (Histogram)     │      │   Health Service             │
│                                  │      │   (health/services.py)       │
└──────────────┬───────────────────┘      │                             │
               │                          │  _check_mirror_workers()    │
               │ Scraped by               │  • Checks stuck syncs       │
               │                          │  • Calculates failure rate  │
               ▼                          │  • Detects exhausted retries│
┌──────────────────────────────────┐      │                             │
│       Prometheus Server          │      └─────────────┬───────────────┘
│                                  │                    │
│  • Collects metrics              │                    │ Included in
│  • Evaluates alert rules         │                    │
│  • Stores time series            │                    ▼
│                                  │      ┌─────────────────────────────┐
└──────────────┬───────────────────┘      │  Global Health Checks       │
               │                          │  (/health/endtoend)         │
               │ Alerts                   │                             │
               │                          │  Returns overall health:    │
               ▼                          │  • database                 │
┌──────────────────────────────────┐      │  • redis                    │
│       AlertManager               │      │  • storage                  │
│                                  │      │  • auth                     │
│  • Receives alerts               │      │  • mirror_workers ✨ NEW    │
│  • Routes notifications          │      │                             │
│  • Deduplicates/groups           │      └─────────────────────────────┘
│                                  │
└──────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         API Endpoints                                    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  GET /v1/repository/mirror/health                              │    │
│  │  (endpoints/api/mirrorhealth.py)                               │    │
│  │                                                                 │    │
│  │  Query Parameters:                                              │    │
│  │  • namespace (optional) - Filter to specific org               │    │
│  │  • detailed (optional) - Include per-repo details              │    │
│  │                                                                 │    │
│  │  Response (200 OK / 503 Service Unavailable):                  │    │
│  │  {                                                              │    │
│  │    "healthy": true/false,                                       │    │
│  │    "workers": { "active": N, "status": "..." },                │    │
│  │    "repositories": {                                            │    │
│  │      "total": N, "syncing": N,                                 │    │
│  │      "completed": N, "failed": N,                              │    │
│  │      "details": [...] // if detailed=true                      │    │
│  │    },                                                           │    │
│  │    "tags_pending": N,                                           │    │
│  │    "last_check": "timestamp",                                   │    │
│  │    "issues": [...]                                              │    │
│  │  }                                                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
               │
               │ Used by
               │
               ▼
┌──────────────────────────────────┐      ┌─────────────────────────────┐
│   Monitoring Dashboards          │      │   Automation Tools          │
│   (Grafana)                      │      │                             │
│                                  │      │  • CI/CD pipelines          │
│  Panels showing:                 │      │  • Health checkers          │
│  • Sync status overview          │      │  • Automated remediation    │
│  • Failure rates                 │      │  • Capacity planning        │
│  • Pending tags                  │      │                             │
│  • Sync duration trends          │      │                             │
│  • Failures by reason            │      │                             │
│                                  │      │                             │
└──────────────────────────────────┘      └─────────────────────────────┘
```

## Key Features

### 1. Real-Time Metric Updates
- Metrics update throughout the sync lifecycle
- Status changes from in_progress → success/failed
- Tags pending decrements as each tag syncs

### 2. Failure Categorization
```
Skopeo/Network Error
        │
        ▼
_map_failure_to_reason()
        │
        ├─► auth_failed
        ├─► network_timeout
        ├─► connection_error
        ├─► not_found
        ├─► tls_error
        ├─► decryption_failed
        ├─► preempted
        └─► unknown_error
        │
        ▼
Metrics with 'reason' label
```

### 3. Health Determination Flow
```
Query RepoMirrorConfig
        │
        ├─► Count by status
        ├─► Check for stale syncs (>24h)
        ├─► Check for exhausted retries
        └─► Check failure rate
        │
        ▼
Calculate overall health
        │
        ├─► healthy = true  → HTTP 200
        └─► healthy = false → HTTP 503
```

### 4. Multi-Level Monitoring

```
Level 1: Prometheus Metrics (Real-time)
   └─► Raw metrics, time-series data, histograms

Level 2: Prometheus Alerts (Automated)
   └─► Alert rules evaluate metrics, fire notifications

Level 3: Health Endpoint (Operational)
   └─► High-level health status, issues summary

Level 4: Health Service (System Integration)
   └─► Part of global health checks, affects load balancers
```

## Data Flow Examples

### Success Case
```
1. Worker starts sync
   └─► last_sync_status = 2 (in_progress)
   └─► last_sync_timestamp = now
   └─► tags_pending = 10

2. Worker processes tags
   └─► tags_pending = 9, 8, 7, ... 0

3. Worker completes
   └─► last_sync_status = 1 (success)
   └─► sync_complete = 1
   └─► sync_duration = 120s
```

### Failure Case
```
1. Worker starts sync
   └─► last_sync_status = 2 (in_progress)
   └─► last_sync_timestamp = now
   └─► tags_pending = 10

2. Worker encounters error
   └─► _map_failure_to_reason("auth failed")
       └─► reason = "auth_failed"

3. Worker fails
   └─► last_sync_status{last_error_reason="auth_failed"} = 0
   └─► sync_complete = 0
   └─► sync_failures_total{reason="auth_failed"}++
   └─► sync_duration = 15s
   └─► tags_pending = 0
```

## Integration Points

### With Existing Systems
- **Prometheus**: Standard metrics endpoint, existing scrape config works
- **Health Checks**: New service added to existing health infrastructure  
- **Database**: Uses existing RepoMirrorConfig table
- **Authentication**: Uses existing auth decorators

### New Components
- **mirrorhealth.py**: New API endpoint module
- **Failure categorization**: New logic in worker
- **Enhanced metrics**: Extended existing metric definitions

## Benefits

1. **Observability**: Comprehensive view of mirror operations
2. **Alerting**: Actionable alerts with failure reasons
3. **Troubleshooting**: Clear error categorization
4. **Performance**: Duration metrics for optimization
5. **Health Monitoring**: Automated health checks
6. **Capacity Planning**: Trend analysis from histograms

