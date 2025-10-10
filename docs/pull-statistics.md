# Image Pull Statistics Feature

This document describes the Image Pull Statistics feature that provides real-time tracking of image pull metrics using Redis.

## Overview

The Image Pull Statistics feature tracks pull events for both tags and manifests, storing metrics in Redis for real-time access. This provides better performance and lower latency for pull statistics updates compared to traditional database-based approaches.

## Architecture

```
Pull Events → Redis Cache → Background Worker → Persistent Database
     ↓             ↓              ↓                    ↓
Real-time      Temporary        Periodic          Long-term
capture        storage          aggregation       storage
```

## Configuration

### Feature Flag

Enable the feature by setting the following in your configuration:

```yaml
FEATURE_IMAGE_PULL_STATS: true
```

### Redis Configuration

Configure Redis for pull metrics tracking:

```yaml
PULL_METRICS_REDIS:
  host: your-redis-host
  port: 6379
  password: your-redis-password  # optional
  ssl: false  # optional
```

If `PULL_METRICS_REDIS` is not configured, the system will fall back to `USER_EVENTS_REDIS` configuration.

## API Endpoints

### Tag Pull Statistics

**GET** `/api/v1/repository/{repository}/tag/{tagname}/pull_statistics`

Returns pull statistics for a specific tag.

**Response:**
```json
{
  "tag_name": "v1.0",
  "tag_pull_count": 150,
  "last_tag_pull_date": "2024-09-08T10:15:00Z",
  "current_manifest_digest": "sha256:abc123...",
  "manifest_pull_count": 500,
  "last_manifest_pull_date": "2024-09-08T10:20:00Z"
}
```

### Manifest Pull Statistics

**GET** `/api/v1/repository/{repository}/manifest/{digest}/pull_statistics`

Returns pull statistics for a specific manifest.

**Response:**
```json
{
  "manifest_digest": "sha256:abc123...",
  "manifest_pull_count": 500,
  "last_manifest_pull_date": "2024-09-08T10:20:00Z"
}
```

## Data Storage

### Redis Keys

The system uses the following Redis key patterns:

- Tag metrics: `pull_metrics/tag/{repository}/{tag_name}`
- Manifest metrics: `pull_metrics/manifest/{repository}/{manifest_digest}`

### Data Structure

Each Redis key contains a hash with the following fields:

- `pull_count`: Number of pulls (integer)
- `last_pull_date`: ISO timestamp of last pull (string)
- `current_manifest_digest`: Current manifest digest for tags (string, tags only)

## Implementation Details

### Async Tracking

Pull events are tracked asynchronously to avoid impacting pull performance:

```python
# Tag pull tracking
pullmetrics.track_tag_pull(repository, tag_name, manifest_digest)

# Manifest pull tracking
pullmetrics.track_manifest_pull(repository, manifest_digest)
```

### Integration Points

The system automatically tracks pulls at these integration points:

1. **Tag Fetch** (`/v2/{repository}/manifests/{tag}`)
2. **Manifest Fetch** (`/v2/{repository}/manifests/{digest}`)

### Error Handling

- Pull tracking failures are logged but do not affect the pull operation
- Missing Redis configuration falls back to user events Redis
- Feature flag controls enable/disable functionality

## Usage Examples

### Enable the Feature

```python
# In your configuration
FEATURE_IMAGE_PULL_STATS = True
PULL_METRICS_REDIS = {
    "host": "localhost",
    "port": 6379
}
```

### Query Tag Statistics

```bash
curl -H "Authorization: Bearer <token>" \
  "https://quay.io/api/v1/repository/myorg/myrepo/tag/latest/pull_statistics"
```

### Query Manifest Statistics

```bash
curl -H "Authorization: Bearer <token>" \
  "https://quay.io/api/v1/repository/myorg/myrepo/manifest/sha256:abc123.../pull_statistics"
```

## Monitoring

### Redis Metrics

Monitor Redis for:
- Memory usage of pull metrics keys
- Connection health
- Performance impact

### Application Metrics

The system logs:
- Pull tracking success/failure
- Redis connection issues
- Feature flag status

## Troubleshooting

### Feature Not Enabled

If you get a 404 error, ensure `FEATURE_IMAGE_PULL_STATS` is set to `true`.

### No Data Available

If statistics return zero values, verify:
1. Feature is enabled
2. Redis is accessible
3. Pull events are being tracked
4. Repository/tag/manifest exists

### Redis Connection Issues

Check:
1. Redis configuration is correct
2. Redis service is running
3. Network connectivity
4. Authentication credentials

## Future Enhancements

- Background worker for persistent storage
- Aggregated statistics across time periods
- Export capabilities for analytics
- Integration with monitoring systems
