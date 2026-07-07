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

## External Dependencies

Tests must never depend on external DNS resolution or network connectivity.
CI environments may be air-gapped or DNS-restricted, so any code path that
performs a DNS lookup will cause spurious failures.

### Mocking DNS for SSRF Validation

When testing code that calls `validate_external_registry_url()` (or any
function that resolves hostnames via `util.security.ssrf`), mock the
module-level `_getaddrinfo` wrapper instead of `socket.getaddrinfo`
directly. Use a deterministic IP address in the mock return value:

- `93.184.216.34` — a public IP (allows the SSRF check to pass)
- `10.0.0.1` — a private/reserved IP (triggers the SSRF block)

#### Fixture Pattern

Define a reusable pytest fixture and apply it via `usefixtures`:

```python
from unittest.mock import patch

@pytest.fixture()
def _mock_dns_for_ssrf_validation():
    """Mock DNS so SSRF validation never hits the network."""
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns

@pytest.mark.usefixtures("_mock_dns_for_ssrf_validation")
class TestMyFeature:
    def test_something(self, app, initialized_db):
        ...
```

See `endpoints/api/test/test_organization.py` and
`endpoints/api/test/test_org_mirror.py` for canonical examples.

#### Inline Pattern

For one-off usage (e.g., parametric test functions), use the context
manager directly:

```python
from unittest.mock import patch

def test_api_security(...):
    mock_dns = patch(
        "util.security.ssrf._getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    with mock_dns:
        ...
```

See `endpoints/api/test/test_security.py` (`test_api_security`) for a
canonical example.

### Parametric and Shared Test Suites

When modifying production code that is exercised by broad parametric tests
(such as `test_api_security`, which covers every API endpoint), verify
that the change does not introduce new external dependencies into those
suites. A common symptom is a test that passes in isolation but fails in
CI because the parametric suite triggers the new code path without the
necessary mocks.

**Checklist before opening a PR:**

1. Identify all test suites that exercise the modified code path.
2. Run those suites locally and confirm no DNS or network calls leak out.
3. If a suite needs a new mock, add it at the suite level (fixture or
   inline patch) rather than skipping the test.
