# AGENTS.md

AI-optimized guide for working with Project Quay container registry.

## Project Overview

Enterprise container registry supporting Docker Registry Protocol v2, OCI spec v1.1. Provides authentication, ACLs, team management, geo-replicated storage, and security scanning via Clair.

**Stack:** Python 3.12, Flask, SQLAlchemy, PostgreSQL, Redis, Alembic migrations

**Frontend:** Legacy Angular (`static/js/`) + New React/PatternFly (`web/`) - see `web/AGENTS.md` for React details

**Config:** YAML at `conf/stack/config.yaml` (local dev), validated via JSON Schema

## Quick Commands

```bash
# Local Dev
make local-dev-up                    # Start Quay + PostgreSQL + Redis
make local-dev-up-with-clair         # Include Clair security scanner
make local-dev-down                  # Shutdown
podman restart quay-quay             # Apply code changes

# Testing
TEST=true PYTHONPATH="." pytest path/to/test.py -v                    # Single test file
TEST=true PYTHONPATH="." pytest path/to/test.py::TestClass::test_fn -v # Single test
make unit-test                       # All unit tests
make registry-test                   # Registry protocol tests

# Code Quality
make black                           # Format with Black
make types-test                      # Type checking (mypy)
```

## Key Directories

- `endpoints/api/` - REST API v1 (Flask)
- `endpoints/v2/` - OCI/Docker registry protocol
- `data/model/` - SQLAlchemy models
- `data/migrations/` - Alembic migrations
- `workers/` - Background job processors
- `auth/` - Authentication & authorization
- `storage/` - Storage backends (S3, Azure, Swift, local)
- `web/` - React frontend (see `web/AGENTS.md`)

## Documentation by Task

**Read the relevant doc before starting work:**

| If working on... | Read... |
|------------------|---------|
| API endpoints, authentication | `agent_docs/api.md` |
| Database models, migrations | `agent_docs/database.md` |
| Testing patterns, fixtures | `agent_docs/testing.md` |
| Architecture, key files | `agent_docs/architecture.md` |
| Global readonly superuser feature | `agent_docs/global_readonly_superuser.md` |
| Local development setup | `agent_docs/development.md` |
| React frontend | `web/AGENTS.md` |

## Universal Conventions

1. **Testing:** Always run relevant tests before committing
2. **Formatting:** Use `make black` for Python, follow existing patterns
3. **No secrets:** Never commit credentials, API keys, or sensitive config
4. **Imports:** Follow existing import ordering patterns in each file
5. **Error handling:** Use appropriate exception types from `endpoints/exception.py`

## Local Dev URLs

- Quay UI: http://localhost:8080
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Clair: localhost:6000 (from Quay container, when enabled)
