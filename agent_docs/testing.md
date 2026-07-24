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

## Database-Specific Testing (SQLite vs PostgreSQL)

Unit tests use an in-memory SQLite database by default. This is fast and
sufficient for most features, but **SQLite silently degrades several
PostgreSQL-specific behaviors**. If your change depends on any of these,
SQLite-only tests do not validate correctness.

### PostgreSQL features that silently degrade on SQLite

| Feature | PostgreSQL behavior | SQLite behavior |
|---------|-------------------|-----------------|
| `SELECT FOR UPDATE SKIP LOCKED` | Acquires row locks, skips locked rows | No-op — `null_for_update` in `data/database.py` returns the query unchanged |
| `FOR UPDATE` (row locking) | Acquires exclusive row locks for concurrent access control | No-op on SQLite |
| Advisory locks | Process-level coordination locks | Not available |
| Transaction isolation levels | `SERIALIZABLE`, `REPEATABLE READ` supported | Only `DEFERRED`, `IMMEDIATE`, `EXCLUSIVE` |
| `EXPLAIN ANALYZE` performance | Reflects real query planning with indexes | Different query planner, no meaningful comparison |

The `SCHEME_SPECIALIZED_FOR_UPDATE` dict in `data/database.py` maps
`"sqlite"` to `null_for_update`, which silently returns the query without
any locking clause. Code using `db_for_update()` will appear to work in
SQLite tests but the locking behavior — often the entire point of the
feature — is never exercised.

### When SQLite tests are insufficient

If your code touches any of these areas, you need PostgreSQL integration
tests:

- **`data/secscan_model/`** — security scanner models using `SKIP LOCKED`
  for distributed worker coordination
- **`data/model/`** — query modules using `db_for_update()` for row
  locking (e.g., `autoprune.py`, `gc.py`, `repository.py`, `user.py`)
- **`data/queue.py`** — queue implementations relying on row locking
- **`workers/`** — background workers using locking for coordination
- Any new code calling `db_for_update()`, `for_update()`, or referencing
  `SKIP LOCKED`

### What to do

1. **Add PostgreSQL integration tests** using `make test_postgres`:
   ```bash
   make test_postgres TESTS=path/to/test_file.py
   ```
   This starts a PostgreSQL container and runs tests against it. The
   `E2E Postgres Test` CI job also runs tests against PostgreSQL.

2. **If PostgreSQL tests are not feasible**, explicitly:
   - Mark SQLite-only tests as "structural tests" in their docstrings
     (they verify code paths and error handling, not locking behavior)
   - Document the PostgreSQL testing gap in the PR description
   - File a follow-up issue for PostgreSQL integration tests

3. **Search for silent degradation** before submitting a PR:
   ```bash
   # Check if your code uses features that degrade on SQLite
   grep -rn "db_for_update\|for_update\|SKIP.LOCKED\|FOR UPDATE" \
       path/to/your/changes/
   ```

### Example: structural vs integration test

```python
# Structural test (SQLite) — verifies code path, NOT locking behavior
def test_scanner_processes_manifest(initialized_db):
    """Structural test: verifies processing logic.
    NOTE: SKIP LOCKED is a no-op on SQLite. PostgreSQL integration
    tests are required to validate distributed locking behavior.
    """
    result = process_next_manifest()
    assert result is not None

# Integration test (PostgreSQL) — verifies actual locking
# Run with: make test_postgres TESTS=path/to/this/test.py
def test_scanner_skip_locked_skips_locked_rows(pg_initialized_db):
    """Requires PostgreSQL: verifies SKIP LOCKED actually skips
    rows locked by concurrent transactions."""
    # Start a transaction that locks a row
    # Verify a second query with SKIP LOCKED skips that row
    ...
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
