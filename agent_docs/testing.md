# Testing Guide

## Test Commands

```bash
# Single test file
TEST=true PYTHONPATH="." pytest path/to/test.py -v

# Single test function
TEST=true PYTHONPATH="." pytest path/to/test.py::TestClass::test_function -v

# With short traceback
TEST=true PYTHONPATH="." pytest path/to/test.py -v --tb=short

# Quiet output (just pass/fail)
TEST=true PYTHONPATH="." pytest path/to/test.py -q --tb=no

# Pattern matching
TEST=true PYTHONPATH="." pytest path/to/test.py -k "keyword" -v
```

## Test Types

### Unit Tests
```bash
make unit-test
```
- Located throughout codebase in `test/` subdirectories
- Use SQLite in-memory database
- Fast, isolated tests

### Registry Tests
```bash
make registry-test
```
- Located in `test/registry/`
- Test Docker/OCI registry protocol
- Simulate Docker client operations

### Integration Tests
```bash
make integration-test
```
- Located in `test/integration/`
- Require running services

### E2E Tests (Frontend)
```bash
# Playwright (all new E2E tests must use Playwright)
cd web && pnpm run test:e2e

```

## Test Database

Tests use SQLite by default. For PostgreSQL tests:

```bash
make test_postgres TESTS=test/test_file.py
```

## Test Fixtures

### Common Test Users

Defined in `test/testconfig.py` and used throughout tests:
- `devtable` - Standard test user
- `public` - Public user
- `reader` - Read-only user
- `admin` - Admin user

### Test Repositories

- `devtable/simple` - Basic test repo
- `public/publicrepo` - Public repository
- `buynlarge/orgrepo` - Organization repository

## Writing Tests

### API Tests

```python
import pytest
from test.fixtures import *

class TestMyFeature:
    def test_example(self, app, initialized_db):
        with client_with_identity('devtable', app) as cl:
            result = cl.get('/api/v1/endpoint')
            assert result.status_code == 200
```

### Database Tests

```python
from data.model import user

def test_user_creation(initialized_db):
    new_user = user.create_user('testuser', 'password', 'test@example.com')
    assert new_user.username == 'testuser'
```

## Test Configuration

- `conftest.py` files contain pytest fixtures
- `test/testconfig.py` - Test user/repo configuration
- `tox.ini` - Tox test environments

## Key Test Directories

- `test/` - Main test directory
- `endpoints/api/test/` - API endpoint tests
- `endpoints/v2/test/` - Registry v2 tests
- `data/model/test/` - Model tests
- `auth/test/` - Auth tests
- `workers/test/` - Worker tests
- `web/playwright/` - Frontend Playwright tests (all new E2E tests go here)

## Performance and Infrastructure Testing

Standard CI checks (unit tests, Playwright E2E, CodeRabbit review) validate functional correctness but do not catch
performance regressions or infrastructure configuration issues that only manifest under production load. This section
documents when and how to validate performance-critical changes before merging.

### When Performance Testing is Required

Performance testing or load validation is required for:

- **Nginx, Envoy, or reverse proxy configuration changes** — timeout settings, keepalive behavior, connection pooling,
  buffer sizes
- **High-traffic request path modifications** — registry v2 protocol handlers (`/v2/.../blobs/`, `/v2/.../manifests/`),
  blob storage operations, authentication endpoints
- **Database query changes affecting high-QPS endpoints** — schema changes, index modifications, query rewrites on tables
  accessed by registry read paths (>1000 QPS in production)
- **Connection pooling, timeout, or keepalive parameter changes** — application-level connection management, database
  connection pool sizing, Redis client configuration
- **Caching strategy changes** — cache TTL modifications, cache key structure changes, cache invalidation logic on
  high-traffic paths

**Rationale:** Infrastructure configuration changes can pass all functional tests yet cause severe production issues.
Historical examples include PR #6947 (nginx keepalive timeout change) which passed CI, was merged, then reverted 43 hours
later with no documented production failure mode. Issue #6536 documented a blob upload/GC race with a 0.038% failure rate
only caught by a 3-hour soak test — standard test suites missed it entirely.

### Performance Testing Protocols

When performance testing is required, document the following in your PR description:

#### 1. Baseline Measurement

Establish current performance before changes:

- **Key metrics:** p50/p95/p99 latency (milliseconds), throughput (requests/sec), error rate (%), connection rate
  (connections/sec for proxy changes)
- **Measurement method:** Production metrics (preferred), staging environment load test, or local benchmark
- **Scope:** Which endpoints or operations were measured

Example:
```
Baseline (production, 2025-08-20 14:00-15:00 UTC):
- /v2/.../blobs/uploads/ p95 latency: 45ms
- Error rate: 0.02%
- Connection rate: 2,170 connections/sec
```

#### 2. Load Test Configuration

If load testing in a non-production environment:

- **Traffic volume:** Percentage of production load or absolute QPS
- **Duration:** Minimum 10 minutes for steady-state validation; 1+ hours recommended for timeout/keepalive changes
- **Test tool:** wrk, k6, Locust, or internal load generator (specify)

Example:
```
Load test: 50% production traffic (5,000 QPS) for 30 minutes using wrk
```

#### 3. Results and Regression Thresholds

Report post-change metrics using the same measurement method as baseline:

- **Acceptable regression:** p95 latency increase ≤10%, error rate increase ≤0.01%, throughput decrease ≤5%
- **Results:** Actual measurements with pass/fail assessment

Example:
```
Post-change results (staging, wrk 50% load, 30min):
- /v2/.../blobs/uploads/ p95 latency: 42ms (PASS: -6.7% vs baseline)
- Error rate: 0.01% (PASS: -0.01% vs baseline)
- Connection rate: 680 connections/sec (PASS: -68.7% — expected due to keepalive)
```

#### 4. Production Rollout Monitoring (if applicable)

For changes deployed to production without pre-merge load testing:

- **Canary/gradual rollout plan:** If infrastructure supports it (e.g., deploy to 10% of fleet, monitor for 2 hours,
  proceed if metrics stable)
- **Monitoring duration:** How long to observe metrics before considering the change stable
- **Rollback criteria:** Specific metric thresholds that trigger immediate revert (e.g., "p95 latency >100ms sustained
  for 5 minutes" or "error rate >0.1%")

#### 5. When Performance Testing is Not Feasible

If performance testing infrastructure is unavailable or the change cannot be validated pre-merge, explicitly document:

- **Why performance testing was skipped:** Infrastructure limitations, urgency due to production incident, etc.
- **Increased merge risk acknowledgment:** "This change was not performance-tested pre-merge and carries higher risk"
- **Enhanced monitoring plan:** Specific metrics to watch post-merge and for how long

### Production Rollout Requirements for Infrastructure Changes

When merging infrastructure configuration changes (nginx, Envoy, proxy settings):

1. **Monitor key metrics for 24-48 hours post-merge** — latency, error rate, connection rate, CPU/memory usage
2. **Document rollback procedure** — how to revert the change if production issues arise (config rollback, emergency PR,
   feature flag toggle)
3. **Establish on-call coverage** — ensure someone can respond to alerts during the monitoring window
4. **Set up alerts** — configure or verify existing alerts for the affected metrics with appropriate thresholds

### Incident Documentation Template

When reverting a merged PR due to production issues, the revert PR description or a comment on the original PR **must**
include:

#### What Happened (Required)

- **Production symptoms observed:** Specific metrics, error messages, or user-visible impact (e.g., "p95 latency spiked
  from 45ms to 300ms", "5xx error rate increased from 0.01% to 2.5%", "customer reported timeouts on blob uploads")
- **Affected systems/endpoints:** Which services or request paths were impacted
- **User impact severity:** Number of affected requests, percentage of traffic, duration of impact

#### Timeline (Required)

- **Change deployed:** When the original PR merged and deployed to production
- **Issue detected:** When the problem was first observed (manual observation, alert fired, customer report)
- **Revert initiated:** When the decision to revert was made
- **Revert completed:** When the revert was deployed and symptoms resolved

#### Root Cause Analysis (Best Effort)

- **Why the original change caused the issue:** Technical explanation if known (e.g., "keepalive_timeout 0 caused TLS
  connection storm", "new query triggered N+1 pattern under load")
- **Why CI/testing did not catch it:** What gap in testing allowed this to reach production

#### Revert Rationale (Required)

- **Why revert vs. forward fix:** Time pressure, lack of immediate fix, need to restore service quickly, unknown root
  cause requiring investigation

#### Links (Best Effort)

- **Internal incident report:** Link to postmortem, incident ticket, or runbook (if available)
- **Metrics dashboards:** Link to Grafana/Datadog/Prometheus showing the production impact (if accessible to external
  contributors, otherwise describe the metrics)

#### Example

```markdown
## What Happened

After PR #6947 deployed on Aug 24 at 20:00 UTC, production monitoring showed:
- p95 latency on /v2/.../blobs/ spiked from 45ms to 280ms
- Connection rate to nginx increased from 2,170/sec to 8,500/sec
- No error rate increase, but 60% of requests exceeded our 100ms SLA

## Timeline

- Aug 24 19:37 UTC: PR #6947 merged
- Aug 24 20:00 UTC: Change deployed to production fleet
- Aug 25 08:30 UTC: On-call engineer noticed latency alerts
- Aug 25 09:15 UTC: Correlated latency spike with PR #6947 deployment
- Aug 26 14:45 UTC: Revert PR #6984 merged and deployed
- Aug 26 15:00 UTC: Latency returned to baseline

## Root Cause

The keepalive_timeout change reduced connection reuse, causing higher upstream connection churn than expected. The
production fleet's CPU contention threshold was lower than anticipated.

## Why Revert

Forward fix would require additional performance testing under production load. Reverting immediately restored service
while we investigate the correct timeout value.

Links: [Internal Incident Report](https://example.com/incident/12345)
```

### Guidance on Missing Infrastructure

If the project does not have performance testing infrastructure (load generators, staging environment at production
scale, or performance benchmarking CI):

- **Document this constraint explicitly in PR descriptions** when merging infrastructure changes
- **Rely on production monitoring and gradual rollout** (if available) to catch issues
- **Increase scrutiny during code review** — require multiple reviewer approvals for high-risk changes
- **Maintain detailed incident documentation** (per template above) to build historical evidence for future
  infrastructure investment
