# Quay - Developer Agent Context

## Project Overview

Quay is a container registry that builds, stores, and distributes container images.
**Production**: quay.io | **Stage**: stage.quay.io | **Issues**: issues.redhat.com/projects/PROJQUAY

## Tech Stack

- **Backend**: Python 3.11+, Flask, Gunicorn, SQLAlchemy, Alembic, PeeWee
- **Frontend**: React 18, TypeScript, PatternFly 5, React Query (see `web/AGENTS.md`)
- **Database**: PostgreSQL (primary), Redis (caching/queuing)
- **Storage**: S3, GCS, Swift, Ceph, Azure, local filesystem

## Core Workflow

```bash
# Start local dev environment (Docker required)
make local-dev-up              # Quay + DB + Redis on localhost:8080
make local-dev-up-with-clair   # Above + Clair security scanner

# Testing
make unit-test                 # Python unit tests
make integration-test          # Integration tests (requires TEST_DATABASE_URI)
make test_postgres             # Full test suite with PostgreSQL container

# Frontend (in web/ directory)
npm start                      # Dev server on localhost:9000
npm test                       # Jest unit tests
npm run test:integration       # Cypress e2e tests

# Linting
make install-pre-commit-hook   # Install pre-commit hooks
pre-commit run --all-files     # Run all linters
```

## Documentation Map

Read specific documentation based on your task:

| Keywords | Documentation |
|----------|---------------|
| **UI, React, Component, PatternFly, frontend** | `web/AGENTS.md` |
| **API, endpoint, Flask, route, decorator** | `docs/agents/backend.md` |
| **Database, model, migration, schema, Alembic** | `docs/agents/database.md` |
| **Worker, background job, queue, async** | `docs/agents/workers.md` |
| **Test, pytest, Cypress, coverage** | `TESTING.md` |
| **Config, settings, environment** | `docs/agents/config.md` |
| **config-tool, field group, validation schema, Go** | `config-tool/AGENTS.md` |

## Directory Structure

```
# === Core Application ===
app.py              # Flask application factory
config.py           # Configuration loading and validation
boot.py             # Application bootstrap

# === API Layer ===
endpoints/          # API routes (Flask blueprints)
  ├── api/          # REST API v1 endpoints
  ├── v1/           # Docker Registry v1 protocol (deprecated)
  ├── v2/           # Docker Registry v2 protocol (OCI)
  ├── oauth/        # OAuth authorization endpoints
  └── keyserver/    # Key server endpoints

# === Data Layer ===
data/               # Data layer
  ├── database.py   # SQLAlchemy model definitions
  ├── model/        # Business logic layer
  ├── migrations/   # Alembic database migrations
  ├── cache/        # Redis caching
  ├── registry_model/   # Registry-specific data models
  ├── secscan_model/    # Security scanning models
  ├── logs_model/       # Audit logging models
  ├── test/          # unit tests
  └── users/        # User data providers (LDAP, Keystone, etc.)

# === Background Processing ===
workers/            # Background job processors

# === Build System ===
buildman/           # Container build orchestration
buildtrigger/       # Build trigger handlers (GitHub, GitLab, Bitbucket)
buildstatus/        # Build status SVG badges

# === Authentication & Authorization ===
auth/               # Authentication providers and decorators
oauth/              # OAuth service implementations
  └── services/     # OAuth provider services (GitHub, Google, etc.)

# === Image Handling ===
image/              # Container image format handling
  ├── docker/       # Docker image format
  ├── oci/          # OCI image format
  └── shared/       # Shared image utilities
digest/             # Content-addressable digest utilities
storage/            # Storage backend implementations (S3, GCS, etc.)
proxy/              # Pull-through cache proxy

# === Notifications & Events ===
notifications/      # Notification system
events/             # Event templates (HTML for notifications)
emails/             # Email templates

# === Frontend ===
web/                # React frontend (see web/AGENTS.md)
  ├── src/          # React components and pages
  ├── cypress/      # Cypress e2e tests
  └── locales/      # Internationalization
static/             # Legacy AngularJS frontend (deprecated)
  ├── js/           # JavaScript source
  ├── partials/     # HTML templates
  └── css/          # Stylesheets
templates/          # Jinja2 HTML templates (Flask views)

# === Configuration ===
config-tool/        # Go-based config validator (see config-tool/AGENTS.md)
conf/               # Runtime configuration files
  ├── nginx/        # Nginx configuration
  ├── init/         # Initialization scripts
  └── stack/        # Stack configuration templates
local-dev/          # Local development environment
  ├── clair/        # Clair scanner config
  ├── ldap/         # LDAP test server config
  └── stack/        # Local stack configuration

# === Utilities ===
util/               # Shared utility modules
  ├── config/       # Configuration utilities
  ├── metrics/      # Prometheus & OTEL metrics collection
  ├── security/     # Security utilities
  ├── secscan/      # Security scanning utilities
  ├── registry/     # Registry protocol utilities
  ├── repomirror/   # Repository mirroring utilities
avatars/            # User avatar generation
features/           # Feature flag management
health/             # Health check endpoints

# === Testing ===
test/               # Python unit and integration tests
  ├── data/         # Test fixtures and data
  ├── registry/     # Registry protocol tests
  └── integration/  # Integration test suites

Note that some unit tests are located in other directories under test/

# === DevOps & Tooling ===
deploy/             # Deployment configurations
  ├── openshift/    # OpenShift deployment manifests
  └── dashboards/   # Grafana dashboards
scripts/            # CI/CD and deployment scripts
hack/               # Development helper scripts
tools/              # Administrative CLI tools
plans/              # Architecture decision records
```

## Universal Conventions

- Follow existing code style (Python: PEP8/black, TypeScript: ESLint/Prettier)
- Commit messages: use conventional commits, here is the format:
```
<subsystem>: <what changed> (PROJQUAY-####)
<BLANK LINE>
<why this change was made>
```
- Never commit secrets or credentials
