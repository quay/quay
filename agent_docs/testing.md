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

## Security Testing

When working on security-sensitive code (SSRF protection, input validation,
authentication, authorization), follow these patterns to avoid common rework
found during code review.

### DNS Mocking

Any test that exercises code paths calling `validate_external_registry_url()`
or other functions that perform DNS resolution **must** mock DNS. Real DNS
lookups make tests flaky in air-gapped CI environments and can produce
different results depending on the network.

**What to patch:** `util.security.ssrf._getaddrinfo` -- this is the module-
level reference to `socket.getaddrinfo` used by the SSRF validation logic.

**Fixture pattern** (used in `test_organization.py`, `test_logs.py`,
`test_org_mirror.py`):

```python
@pytest.fixture()
def _mock_dns_for_ssrf_validation():
    """
    Mock DNS resolution in the SSRF validation module so tests
    with hostnames don't fail due to DNS lookup failures.
    """
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns
```

Apply the fixture to test classes or functions with `@pytest.mark.usefixtures`:

```python
@pytest.mark.usefixtures("_mock_dns_for_ssrf_validation")
class TestProxyCacheSSRFProtection:
    ...
```

For parametric test suites like `test_api_security` that run many endpoints
in a loop, apply the mock inline since they do not use class-level fixtures:

```python
def test_api_security(resource, method, params, body, identity, expected, app):
    mock_dns = patch(
        "util.security.ssrf._getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    with mock_dns, client_with_identity(identity, app) as cl:
        conduct_api_call(cl, resource, method, params, body, expected)
```

**When to use this pattern:**

- Your code under test calls `validate_external_registry_url()`
- Your code instantiates `Proxy()` (which validates the upstream URL)
- Your code resolves external hostnames for any reason

**Canonical examples:**

- `endpoints/api/test/test_organization.py` -- fixture + `usefixtures` on
  class
- `endpoints/api/test/test_logs.py` -- fixture + `usefixtures` on class
  and standalone test functions
- `endpoints/api/test/test_org_mirror.py` -- fixture with detailed
  docstring explaining scope of the patch
- `endpoints/api/test/test_security.py` -- inline `patch()` in parametric
  test
- `util/security/test/test_ssrf.py` -- unit tests for the SSRF module
  itself, with per-test `patch()` calls to control DNS responses

### Exception Handling Audit

When introducing a new exception type (e.g., `SSRFBlockedError`), audit
**every** code path that can raise it and ensure each caller either catches
it or documents why propagation is intentional.

**Checklist:**

1. Identify all call sites of the function that raises the new exception.
   Use grep or your editor to find every import and invocation.
2. At each call site, verify the exception is caught and translated into
   an appropriate user-facing error (e.g., a 400 response, not a 500).
3. If a call site intentionally lets the exception propagate (e.g., a
   middleware layer catches it), add a comment explaining why.
4. Write tests that trigger the exception at each call site and assert
   the correct HTTP status code and error message.

**Example -- `SSRFBlockedError`:**

The `validate_external_registry_url()` function raises `SSRFBlockedError`
(a `ValueError` subclass). Every endpoint that calls this function or
instantiates `Proxy()` must catch it explicitly:

```python
from util.security.ssrf import SSRFBlockedError, validate_external_registry_url

try:
    validate_external_registry_url(url, allowed_hosts=_get_ssrf_allowed_hosts())
except SSRFBlockedError:
    raise request_error(SSRF_GENERIC_ERROR)
except ValueError as e:
    raise request_error(str(e))
```

Note that `SSRFBlockedError` is caught **before** `ValueError` because it is
a subclass. If only `ValueError` were caught, the generic error message would
leak validation details. If neither were caught, the exception would propagate
as an unhandled 500.

**Call sites that handle `SSRFBlockedError` today** (verify this list is
current when modifying SSRF code):

- `endpoints/api/organization.py` -- `_validate_proxy_cache_upstream_url()`
  and the `ProxyCacheVerifyConnection` resource
- `endpoints/api/org_mirror.py` -- `_validate_mirror_url()` and the
  `OrgMirrorVerify` resource
- `endpoints/api/logs.py` -- `_validate_callback_url()`

### File Permission Verification

Before committing, check for unintended file permission changes. Git tracks
the executable bit, and accidentally changing a file from 644 to 755 (or
vice versa) will be caught in code review.

**Pre-commit check:**

```bash
git diff --cached --stat
```

Look for lines like `mode change 100644 => 100755` in the output. If you
see mode changes on files that are not scripts (e.g., `.py` modules, `.md`
docs, `.yaml` configs), revert the permission change before committing:

```bash
git update-index --chmod=-x path/to/file
```

**Rule of thumb:** Only shell scripts (`*.sh`), entry-point scripts, and
files with shebangs (`#!/...`) should have 755 permissions. All other files
should be 644.
