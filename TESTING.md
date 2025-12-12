# Testing Quay

## Quick Reference

```bash
# Most common commands
make unit-test              # Fast unit tests (no DB required)
make test_postgres          # Full suite with PostgreSQL container
make registry-test          # Registry protocol tests

# Frontend (in web/ directory)
npm test                    # Jest unit tests
npm run test:integration    # Cypress e2e tests
```

## Backend Testing

### Test Commands

| Command | Purpose | Database |
|---------|---------|----------|
| `make unit-test` | Unit tests with coverage | SQLite |
| `make e2e-test` | End-to-end tests | SQLite |
| `make registry-test` | Registry protocol tests | SQLite |
| `make integration-test` | Integration tests | Requires TEST_DATABASE_URI |
| `make full-db-test` | Full suite against real DB | Requires TEST_DATABASE_URI |
| `make test_postgres` | Full suite with PostgreSQL container | PostgreSQL (auto) |
| `make buildman-test` | Build manager tests | SQLite |
| `make certs-test` | Certificate installation tests | None |
| `make types-test` | mypy type checking | None |

### Running Specific Tests

```bash
# Single test file
TEST=true PYTHONPATH="." pytest path/to/test_file.py -v

# Single test function
TEST=true PYTHONPATH="." pytest path/to/test_file.py::test_function -v

# Tests matching pattern
TEST=true PYTHONPATH="." pytest -k "test_pattern" -v

# With parallel execution
TEST=true PYTHONPATH="." pytest -n auto path/to/tests/ -v
```

### Test Markers

```bash
# Exclude e2e tests (faster)
pytest -m 'not e2e'

# Only e2e tests
pytest -m 'e2e'
```

### Using tox

```bash
tox -e py312-unit      # Unit tests
tox -e py312-e2e       # E2E tests
tox -e py312-registry  # Registry tests
tox -e py312-psql      # PostgreSQL tests (Docker)
tox -e py312-mysql     # MySQL tests (Docker)
```

### Test Database Options

**SQLite (default)**: Used automatically for unit tests

**PostgreSQL container**: `make test_postgres` spins up PostgreSQL 12.1 on port 5433

**Custom database**:
```bash
export TEST_DATABASE_URI="postgresql://user:pass@localhost:5432/quay_test"
make full-db-test
```

## Frontend Testing

All commands run from `web/` directory.

### Jest Unit Tests

```bash
npm test                           # Watch mode
npm test -- --coverage             # With coverage report
npm test -- --testPathPattern=ComponentName  # Single component
npm test -- --watchAll=false       # CI mode (no watch)
```

### Cypress E2E Tests

```bash
# Headless (CI)
npm run test:integration

# Interactive
npx cypress open

# Single spec file
npx cypress run --spec "cypress/e2e/org-list.cy.ts"
```

### E2E Test Setup

Cypress tests require a running Quay instance:

```bash
# Start local dev environment
make local-dev-up

# Seed test database and storage
npm run quay:seed

# Build frontend for testing
npm run build

# Serve and run tests
npm run start:integration &
npm run test:integration
```

## Test Directory Structure

```
test/                          # Main test directory
├── conftest.py                # Pytest configuration
├── fixtures.py                # Core test fixtures
├── registry/                  # Registry protocol tests
│   └── registry_tests.py      # Main registry tests
├── integration/               # Integration tests
└── clients/                   # Client library tests

# Component-specific tests (co-located)
auth/test/                     # Authentication tests
buildman/test/                 # Build manager tests
data/model/test/               # Data model tests
data/registry_model/test/      # Registry model tests
endpoints/api/test/            # API endpoint tests
endpoints/v2/test/             # Docker V2 API tests

# Frontend tests
web/src/**/*.test.tsx          # Jest unit tests (co-located)
web/cypress/e2e/               # Cypress e2e tests
```

## Writing Tests

For code examples and test patterns, see `docs/agents/testing.md`.

## CI/CD

GitHub Actions runs on every PR:

| Job | Description |
|-----|-------------|
| Format Check | Black formatting |
| Flake8 | Python linting |
| Unit Tests | `tox -e py312-unit` with Codecov |
| Type Tests | mypy type checking |
| E2E Tests | `tox -e py312-e2e` |
| Registry Tests | `tox -e py312-registry` |
| PostgreSQL Tests | `tox -e py312-psql` |
| Frontend Tests | Cypress e2e |

See: `.github/workflows/CI.yaml`

### Nightly Tests

Multi-architecture tests (amd64, ppc64le, s390x) run daily.

See: `.github/workflows/CI-nightly.yaml`

### OCI Conformance

OCI Distribution Spec conformance tests run on PRs.

See: `.github/workflows/oci-distribution-spec.yaml`

## Coverage

```bash
# Backend - generates htmlcov/
make unit-test
open htmlcov/index.html

# Frontend - generates coverage/
cd web && npm test -- --coverage
open coverage/lcov-report/index.html
```

## Pre-commit Hooks

```bash
# Install hooks
make install-pre-commit-hook

# Run manually
pre-commit run --all-files
```

Hooks include: black, isort, eslint, gitleaks (secret scanning)

## Local Development

```bash
# Start dev environment
make local-dev-up              # Quay + DB + Redis on localhost:8080
make local-dev-up-with-clair   # Above + Clair scanner

# Stop
make local-dev-down

# Rebuild test data
make update-testdata
```

## Troubleshooting

### Tests hang or timeout

```bash
# Increase timeout
pytest --timeout=7200 path/to/test.py

# Run without timeout
pytest --timeout=0 path/to/test.py
```

### Database connection issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Verify connection string
echo $TEST_DATABASE_URI

# Reset test database
make local-dev-down && make local-dev-up
```

### Cypress tests fail to start

```bash
# Ensure backend is running
curl http://localhost:8080/health

# Ensure frontend is built and served
cd web && npm run build && npm run start:integration
```
