# Repository Mirror Metrics Implementation Summary

This document summarizes the implementation of repository mirror metrics and health endpoints according to the enhancement proposal in `repository-mirror-metrics.md`.

## Implementation Overview

All components of the enhancement have been implemented:

### ✅ 1. Core Prometheus Metrics (4 Primary Metrics)

#### Tags Pending Synchronization
- **Metric**: `quay_repository_mirror_pending_tags`
- **Type**: Gauge
- **Labels**: `namespace`, `repository`
- **Location**: `workers/repomirrorworker/__init__.py` (lines 42-46)
- **Updates**: Real-time during sync operations, decrements as each tag is processed

#### Last Synchronization Status  
- **Metric**: `quay_repository_mirror_last_sync_status`
- **Type**: Gauge
- **Labels**: `namespace`, `repository`, `last_error_reason`
- **Values**: 0 (failed), 1 (success), 2 (in_progress)
- **Location**: `workers/repomirrorworker/__init__.py` (lines 48-52)
- **Enhancement**: Includes `last_error_reason` label for immediate failure diagnosis

#### Complete Synchronization Status
- **Metric**: `quay_repository_mirror_sync_complete`  
- **Type**: Gauge
- **Labels**: `namespace`, `repository`
- **Values**: 0 (incomplete), 1 (complete)
- **Location**: `workers/repomirrorworker/__init__.py` (lines 54-58)

#### Synchronization Failure Counter
- **Metric**: `quay_repository_mirror_sync_failures_total`
- **Type**: Counter
- **Labels**: `namespace`, `repository`, `reason`
- **Location**: `workers/repomirrorworker/__init__.py` (lines 60-64)
- **Feature**: Categorizes failures by reason for better alerting

### ✅ 2. Supporting Metrics

#### Active Workers
- **Metric**: `quay_repository_mirror_workers_active`
- **Type**: Gauge
- **Location**: `workers/repomirrorworker/__init__.py` (lines 66-70)

#### Last Sync Timestamp
- **Metric**: `quay_repository_mirror_last_sync_timestamp`
- **Type**: Gauge
- **Labels**: `namespace`, `repository`
- **Location**: `workers/repomirrorworker/__init__.py` (lines 72-76)

#### Sync Duration Histogram
- **Metric**: `quay_repository_mirror_sync_duration_seconds`
- **Type**: Histogram
- **Labels**: `namespace`, `repository`
- **Buckets**: 30s, 60s, 120s, 300s, 600s, 1200s, 1800s, 3600s, 7200s, +Inf
- **Location**: `workers/repomirrorworker/__init__.py` (lines 78-83)

### ✅ 3. Health Endpoint

#### API Endpoint
- **Path**: `/v1/repository/mirror/health`
- **Method**: GET
- **Authentication**: Required (fresh login)
- **Status Codes**: 
  - 200 (healthy)
  - 503 (unhealthy)
  - 401/403 (auth errors)
- **Query Parameters**:
  - `namespace` (optional): Filter to specific namespace
  - `detailed` (optional): Include per-repository breakdown
- **Location**: `endpoints/api/mirrorhealth.py`
- **Registered in**: `endpoints/api/__init__.py`

#### Health Response Format
```json
{
  "healthy": true/false,
  "workers": {
    "active": 5,
    "configured": 5,
    "status": "healthy|degraded"
  },
  "repositories": {
    "total": 150,
    "syncing": 3,
    "completed": 145,
    "failed": 2,
    "details": [...]  // when detailed=true
  },
  "tags_pending": 47,
  "last_check": "2025-12-09T10:30:00Z",
  "issues": [...]
}
```

### ✅ 4. Health Service Integration

- **Service**: `mirror_workers`
- **Location**: `health/services.py`
- **Checks**:
  - Mirror feature enabled
  - No repositories stuck in SYNCING state (>12 hours)
  - Failure rate under 50%
  - Retry attempts not exhausted
- **Integrated into**: Global health service checks (available via `/health/endtoend`)

### ✅ 5. Enhanced Worker Implementation

#### Failure Reason Categorization
- **Function**: `_map_failure_to_reason()`
- **Location**: `workers/repomirrorworker/__init__.py` (lines 93-110)
- **Categories**:
  - `auth_failed`: Authentication/authorization failures
  - `network_timeout`: Timeout errors
  - `connection_error`: Connection issues
  - `not_found`: 404 errors
  - `tls_error`: TLS/certificate errors
  - `decryption_failed`: Credential decryption failures
  - `preempted`: Job preemption
  - `unknown_error`: Unclassified errors

#### Metric Updates During Sync
- **Start of sync**: Sets status to in_progress (2), records timestamp
- **During sync**: Updates pending tags count after each tag
- **On success**: Sets status to success (1), records duration
- **On failure**: Sets status to failed (0), increments failure counter with reason, records duration
- **Partial failure**: Correctly tracks which tags failed

#### Metrics Cleanup
- **Function**: `cleanup_mirror_metrics()`
- **Location**: `workers/repomirrorworker/__init__.py` (lines 619-641)
- **Purpose**: Remove metrics for deleted/disabled repositories

### ✅ 6. Documentation

#### User-Facing Documentation
- **File**: `docs/mirroring-metrics.md`
- **Contents**:
  - Detailed metric descriptions with examples
  - Health endpoint documentation
  - Example Prometheus alert rules
  - Example Grafana dashboard queries
  - Best practices and troubleshooting guide
  - Security considerations

## Key Implementation Details

### Metric Label Strategy

According to the enhancement:
- The worker updates a canonical `last_error_reason=""` series plus an optional detail series (`last_error_reason=<category>` on failures) so PromQL can count repos without double-counting
- The `reason` label on `quay_repository_mirror_sync_failures_total` enables alerting on specific failure types
- All metrics use consistent `namespace` and `repository` labels for easy correlation

### Health Determination Logic

System is unhealthy when:
1. More than 20% of repositories are failing
2. Repositories are stuck in SYNCING for >12 hours
3. Repositories have exhausted retry attempts

### Backward Compatibility

- ✅ Existing `quay_repository_rows_unmirrored` metric preserved
- ✅ New metrics are additive
- ✅ Existing monitoring setups continue to work
- ✅ Health endpoint is new, doesn't affect existing endpoints

## Changes Made

### Modified Files

1. **workers/repomirrorworker/__init__.py**
   - Updated metric definitions to match spec
   - Added supporting metrics (timestamp, duration, workers)
   - Enhanced `perform_mirror()` with comprehensive metric collection
   - Added failure reason categorization
   - Updated metrics throughout sync lifecycle
   - Enhanced `_update_mirror_metrics_on_failure()` helper
   - Updated `cleanup_mirror_metrics()`

2. **endpoints/api/__init__.py**
   - Registered new `mirrorhealth` module

3. **health/services.py**
   - Added `_check_mirror_workers()` service
   - Integrated into global health checks

### New Files

1. **endpoints/api/mirrorhealth.py**
   - Health endpoint implementation
   - JSON response formatting
   - Namespace filtering
   - Detailed mode support

2. **docs/mirroring-metrics.md**
   - Comprehensive metrics documentation
   - Example queries and alerts
   - Troubleshooting guide
   - Best practices

## Testing Recommendations

### Unit Tests Needed
- [ ] Test metric collection in `perform_mirror()`
- [ ] Test failure reason categorization
- [ ] Test health endpoint with various states
- [ ] Test namespace filtering in health endpoint
- [ ] Test metrics cleanup function

### Integration Tests Needed
- [ ] Test metrics accuracy during sync
- [ ] Test metrics during failure scenarios
- [ ] Test health endpoint status codes
- [ ] Test detailed health response

### Manual Testing Checklist
- [ ] Verify metrics appear in Prometheus
- [ ] Trigger sync and observe metric changes
- [ ] Trigger failures and verify reason labels
- [ ] Test health endpoint with valid/invalid auth
- [ ] Test health endpoint with namespace filter
- [ ] Verify health service integration

## Prometheus Alert Examples

The documentation includes production-ready alert rules for:
- No active workers (critical)
- High failure counts (critical)
- Ongoing failure rate (warning)
- Stale synchronizations (warning)
- High pending tags (warning)
- Authentication failures (warning)

## Grafana Dashboard Examples

The documentation includes PromQL queries for:
- Synchronization status overview
- Failure rate tracking
- Failures by reason breakdown
- Pending tags monitoring
- Active workers display
- Sync duration percentiles
- Incomplete sync tracking

## Security Considerations

- ✅ Health endpoint requires authentication
- ✅ Namespace filtering respects permissions
- ✅ No credential exposure in metrics/responses
- ✅ Error reasons are categorized generically
- ✅ Follows existing Quay security patterns

## Cardinality Considerations

Potential cardinality with labels:
- `namespace` × `repository`: One series per mirrored repository
- `reason`: ~8 possible values, multiplied by repositories for counter
- `last_error_reason`: ~9 possible values (including empty), one active per repository

For deployments with 1000+ mirrored repositories:
- Consider aggregating by namespace
- Monitor Prometheus memory usage
- Use metric relabeling if needed

## Future Enhancements (Not in Scope)

These were explicitly marked as non-goals but could be added later:
- Automatic remediation of failed syncs
- Historical metric storage (handled by Prometheus)
- UI dashboard in Quay web interface
- Changes to mirroring functionality itself

## Deployment Notes

### Configuration Required
No additional configuration is required. The new metrics and endpoints will be automatically available after deployment.

### Upgrade Path
1. Deploy updated Quay with new code
2. Metrics become available immediately
3. Update Prometheus to scrape new metrics
4. Deploy alert rules
5. Create Grafana dashboards

### Rollback Considerations
- New metrics will disappear but old metric remains
- Health endpoint will return 404
- No impact on mirroring functionality

## Compliance with Enhancement Specification

| Requirement | Status | Notes |
|------------|--------|-------|
| Tags pending metric | ✅ Complete | Real-time updates |
| Last sync status | ✅ Complete | Enhanced with error reason |
| Sync complete metric | ✅ Complete | Boolean indicator |
| Failure counter | ✅ Complete | With reason categorization |
| Workers active | ✅ Complete | Gauge metric |
| Last sync timestamp | ✅ Complete | Unix timestamp |
| Sync duration | ✅ Complete | Histogram with appropriate buckets |
| Health endpoint | ✅ Complete | JSON response with 200/503 codes |
| Namespace filtering | ✅ Complete | Query parameter |
| Detailed mode | ✅ Complete | Per-repository breakdown |
| Health service | ✅ Complete | Integrated into global checks |
| Documentation | ✅ Complete | Comprehensive user guide |
| Alert examples | ✅ Complete | Production-ready rules |
| Dashboard examples | ✅ Complete | PromQL queries provided |
| Backward compatibility | ✅ Complete | Old metric preserved |

## Conclusion

All requirements from the enhancement proposal have been successfully implemented:
- ✅ 4 core metrics with enhanced labels
- ✅ 3 supporting metrics
- ✅ Health endpoint with comprehensive response
- ✅ Health service integration
- ✅ Failure categorization
- ✅ Complete documentation
- ✅ Example alerts and dashboards
- ✅ Backward compatibility maintained

The implementation provides operators with comprehensive observability into repository mirroring operations, enabling proactive monitoring, alerting, and troubleshooting.

