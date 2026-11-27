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

### Test Credentials

Never use a real credential in test code or fixtures. When the tested format
permits it, prefix dummy credential values with `QUAY_FIXTURE_ONLY-`. The root
`.gitleaks.toml` allowlists that explicit marker, not test paths, so an
unmarked realistic credential in a test file is still reported.

Use a same-line `gitleaks:allow` comment only when the test requires an exact
format, ciphertext, or protocol value that cannot carry the marker. Keep the
exception on the narrowest line and explain the format constraint nearby.

For a scanner report, first verify that the value is not real. Prefer
converting the value to the fixture convention; otherwise use a narrow inline
exception and mark the external report as a false positive. A HEAD change
does not suppress a finding from an older commit. Do not rewrite repository
history for that case; add an exact report fingerprint to `.gitleaksignore`
only if the scanner owner requires repository-side suppression. If the value
is real, revoke or rotate it and follow the security-response process instead
of allowlisting it.

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

## Test Assertion Quality

A test that passes when the code under test is replaced with `return None` provides
no protection against regressions. Three recent PRs — GC+quota recalculation (#5967),
mirror redaction (#7548), and proxy cache blob download (#7541) — were identified
during review for containing tests that were vacuous in this sense. The following
criteria apply to **all** backend tests.

### 1. Falsifiability check

Before committing a test, ask: could this assertion fail if the function under
test were replaced with `return None` (or an equivalent no-op)? If the answer is
no, the assertion is vacuous and must be strengthened or replaced.

### 2. No tautological assertions

Avoid assertions whose truth follows from the types or invariants of the objects
involved, not from the behavior of the code under test. Common examples:

```python
# BAD — Model.select().count() always returns a non-negative integer
assert tag_count >= 0

# BAD — len() of a list is always >= 0
assert len(items) >= 0

# GOOD — asserts a specific expected state
assert tag_count == 3
```

### 3. Assert the effect, not the precondition

Test the return value or state change **produced by** the code under test, not
state that existed before the call. Do not assert that input data is still
unchanged unless that invariant is itself what you are testing.

```python
# BAD — asserts input state, not the function's effect
result = compute_quota_usage(namespace)
assert namespace.quota_limit > 0   # existed before the call

# GOOD — asserts what the function returned/changed
result = compute_quota_usage(namespace)
assert result.bytes_used == expected_bytes
```

### 4. Worker and background-job tests must verify execution

When testing a worker or background job, assert that the worker actually ran and
changed application state. It is not sufficient to assert that pre-existing state
is unchanged.

Specifically:
- Do **not** zero a counter immediately before asserting it (this masks whether
  the worker recalculated).
- Check flags or metrics that the worker sets (e.g., `backfill_complete`,
  `quota_bytes_used`), not just that no exception was raised.

```python
# BAD — zeroes the counter before asserting, masking whether run_worker()
# recalculated anything
namespace.quota_bytes_used = 0
run_quota_worker()
assert namespace.quota_bytes_used >= 0   # always true after any execution

# GOOD — stores before-state, verifies after-state reflects worker's work
before = namespace.quota_bytes_used
run_quota_worker()
after = NamespaceQuota.get_by_id(namespace.id).quota_bytes_used
assert after == expected_recalculated_bytes
assert after != before or expected_recalculated_bytes == before  # or assert equality
```

### 5. Capture before-state for integration tests

Integration tests that verify a state transition must record the initial value
before invoking the code under test, then assert a meaningful difference
afterward. Asserting the final value alone is acceptable only when the final
value is fully predictable from inputs.

```python
# ACCEPTABLE when the final value is fully predictable
images_before = ImageStorage.select().count()
delete_tag(repo, tag)
images_after = ImageStorage.select().count()
assert images_after == images_before - expected_deleted_count

# BAD — checking count of an empty list guarantees 0 regardless of behavior
assert ImageStorage.select().where(...).count() == 0   # only if this list
                                                       # was already empty
```

### Auth permission test assertions

Tests that claim to verify permission limits are security-critical: a vacuous
assertion produces false confidence in enforcement. In addition to the general
criteria above:

- A test verifying that a token or user **cannot** perform an action must assert
  both the **positive grant** (permitted operations appear) and the **negative
  exclusion** (forbidden operations are absent). Checking only the count of
  access entries or the subject claim is insufficient.
- Reference `test_readonly_user_can_pull_but_not_push` in `test/test_auth_e2e.py`
  as the canonical correct pattern — it decodes the JWT and checks that the
  access entry includes `pull` and excludes `push`.
- Apply the same standard to Playwright `e2e/api/` auth tests.

```python
# BAD — only checks list length and subject, not the permitted/denied operations
assert len(decoded["access"]) == 1
assert decoded["sub"] == expected_user

# GOOD — asserts both the present (pull) and absent (push) operations
access_entry = decoded["access"][0]
assert "pull" in access_entry["actions"]
assert "push" not in access_entry["actions"]
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
