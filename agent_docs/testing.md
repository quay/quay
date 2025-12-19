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
# Cypress (legacy)
cd web && npm run test:integration

# Playwright (new)
cd web && npm run test:e2e
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
- `web/cypress/` - Frontend Cypress tests
- `web/playwright/` - Frontend Playwright tests
