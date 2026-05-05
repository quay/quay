# AGENTS.md

AI-optimized guide for working with Project Quay container registry.

## Project Overview

Enterprise container registry supporting Docker Registry Protocol v2, OCI spec v1.1. Provides authentication, ACLs, team management, geo-replicated storage, and security scanning via Clair.

**Stack:** Python 3.12, Flask, SQLAlchemy, PostgreSQL, Redis, Alembic migrations

**Frontend:** Legacy Angular (`static/js/`) + New React/PatternFly (`web/`) - see `web/AGENTS.md` for React details

**Config:** YAML at `conf/stack/config.yaml` (local dev), validated via JSON Schema

## Workflow Skills

Use these skills for common tasks — they encode the full workflow so short prompts produce correct results:

| Skill | When to use |
|-------|-------------|
| `/start PROJQUAY-XXXX` | Begin any ticketed task: assigns ticket, creates branch, loads context |
| `/code` | Implement changes: reads conventions, writes code, runs quality checks, commits |
| `/pr` | Open a pull request: validates title format, fills description template, sets labels |
| `/poll PR#` | Monitor CI and reviews: loops until all checks pass, fixes failures automatically |
| `/backport PR# [branch]` | Cherry-pick a merged PR to a release branch |
| `/jira PROJQUAY-XXXX [action]` | View or update a JIRA ticket (assign, transition, set-version) |
| `/ci PR#` | Quick CI status snapshot for a PR |
| `/migration` | Create an Alembic migration: scaffolds file, guides upgrade/downgrade, validates |
| `/test [path]` | Run targeted tests for a file or area |
| `/cluster-provision` | Provision an ephemeral OpenShift cluster for integration testing |
| `/remote-playwright` | Deploy a remote Playwright browser on a cluster for E2E testing |

**Full ticket workflow:** `/start PROJQUAY-XXXX` → `/code` → `/pr` → `/poll PR#` → `/backport PR# branch` (if needed)

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
| Frontend E2E tests, Playwright fixtures | `web/playwright/MIGRATION.md` |
| Dev workflow, JIRA, PRs, CI | `agent_docs/workflow.md` |

## Universal Conventions

1. **Testing:** Always run relevant tests before committing
2. **Formatting:** Rely on pre-commit hook to format code on commit
3. **No secrets:** Never commit credentials, API keys, or sensitive config
4. **Imports:** Follow existing import ordering patterns in each file
5. **Error handling:** Use appropriate exception types from `endpoints/exception.py`
6. **Alembic migrations:** Never write migration files from scratch or fabricate revision IDs. Always run `alembic revision -m "description"` to scaffold the file first, then edit the generated file to add `upgrade()` and `downgrade()` logic. Hand-crafted revision IDs cause conflicts when multiple contributors independently generate migrations.

## Contributing

### PR & Commit Format

- **PR title:** `PROJQUAY-XXXXX: type(scope): lowercase description`
  - Use `NO-ISSUE:` when there is no associated Jira ticket
  - Types: `fix`, `feat`, `test`, `refactor`, `docs`, `chore`
  - `PROJQUAY-10983: fix(mirroring): add isRequired to robot user field`
  - `NO-ISSUE: docs(agents): add contributing guide`
- **Branch naming:** `<type>/projquay-XXXXX-short-description` where `<type>` matches the PR type

### Fork Workflow

**Never push directly to `quay/quay`.** Always use a fork.

```bash
gh repo list <your-user> --fork   # check for existing fork
git remote add fork https://github.com/<your-user>/quay.git
git push -u fork <branch>
gh pr create --repo quay/quay --head <your-user>:<branch>
```

Use the `/pr` skill — it handles fork detection, auth, and fallbacks automatically.

### Jira Integration

After opening a PR, comment `/jira refresh` to link the ticket and validate the target version. Set **Target Version** to the current development release (check the active versions in Jira) on the Jira ticket before opening the PR, or the bot will block merging.

### Code Review (CodeRabbit)

Resolve every inline CodeRabbit comment — either fix the code or reply explaining why it's not actionable. The bot re-reviews on each push.

### Worktrees (Frontend)

Git worktrees don't inherit `node_modules`. Pre-commit hooks (Prettier, ESLint) will fail silently without this symlink:

```bash
ln -sf "$(git -C /path/to/main/repo rev-parse --show-toplevel)/web/node_modules" \
       "$(git rev-parse --show-toplevel)/web/node_modules"
```

## Local Dev URLs

- Quay UI: http://localhost:8080
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Clair: localhost:6000 (from Quay container, when enabled)
