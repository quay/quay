---
name: code
description: >
  Implement changes following Quay conventions. Reads the relevant AGENTS.md
  and agent_docs/ for the area being worked on, then guides implementation,
  testing, quality checks (pre-commit, tests), and commit with proper message format.
allowed-tools:
  - Bash(bash .claude/scripts/format-and-lint.sh *)
  - Bash(git *)
  - Bash(make *)
  - Bash(pytest *)
  - Bash(pre-commit *)
  - Bash(alembic *)
  - Bash(npm *)
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
---

# Implement Changes

Implement code changes following Quay project conventions.

## Step 1: Read Conventions

Read `AGENTS.md` for universal conventions. Then load the area-specific doc:

| Area | Doc |
|------|-----|
| API endpoints, auth | `agent_docs/api.md` |
| Database, migrations | `agent_docs/database.md` |
| Testing | `agent_docs/testing.md` |
| Architecture | `agent_docs/architecture.md` |
| React frontend | `web/AGENTS.md` |

## Step 2: Implement

Follow `AGENTS.md` conventions:
- Exception types from `endpoints/exception.py`
- Existing import ordering patterns
- Never hand-write migration files — run `alembic revision -m "description"` first
- No secrets in code

## Step 3: Write Tests

**Every code change must include tests.** Choose the right test type for the area:

### Backend (Python)

| Change | Test type | Location |
|--------|-----------|----------|
| API endpoint | pytest API test | `endpoints/api/test/` |
| Data model / query | pytest model test | `data/model/test/` |
| Worker logic | pytest unit test | `workers/test/` |
| Auth change | pytest auth test | `auth/test/` |
| Registry protocol | pytest registry test | `test/registry/` |

Run: `TEST=true PYTHONPATH="." pytest path/to/test.py -v`

### Frontend (React/TypeScript)

| Change | Test type | Location |
|--------|-----------|----------|
| UI interaction, page flow, bug fix | **Playwright E2E** | `web/playwright/e2e/` |
| Pure utility function | Vitest unit test | Co-located `*.test.ts` |
| Data transformation helper | Vitest unit test | Co-located `*.test.ts` |
| Custom hook (no UI) | Vitest unit test with `renderHook` | Co-located `*.test.tsx` |

**Default to Playwright E2E for frontend changes.** Use vitest only for pure logic with no UI interaction. Most bug fixes and feature work should have E2E coverage.

### Playwright E2E guidelines

- Read `web/playwright/MIGRATION.md` for conventions and patterns
- **Add to existing spec files** when the feature area already has one (check `web/playwright/e2e/`)
- Use the `api` fixture for test data setup (auto-cleanup)
- Use `data-testid` attributes for selectors — add them to components if missing
- Tag tests with `@PROJQUAY-XXXX` to link back to the JIRA ticket

### Test scope

- Cover the happy path of the change
- Cover the specific bug scenario for bug fixes (e.g. duplicate names, edge cases)
- Verify via API when possible (not just UI assertions)

## Step 4: Quality Checks

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
bash .claude/scripts/format-and-lint.sh            # staged files
bash .claude/scripts/format-and-lint.sh --all-files # all files
```

Run relevant tests:

```bash
TEST=true PYTHONPATH="." pytest path/to/test.py -v  # Single test
make unit-test                                       # All unit tests
make registry-test                                   # Registry protocol
make types-test                                      # mypy
```

## Step 5: Commit

Format:

```
<subsystem>: <what changed> (PROJQUAY-####)

<why this change was made>
```

See `.github/CONTRIBUTING.md` for full conventions. Pre-commit hooks run on commit — fix any failures and re-commit.

## Step 6: Continue — invoke /pr immediately

**Do not stop after committing.** Invoke the `/pr` skill immediately to create the pull request. The full workflow is a single uninterrupted pipeline:

```text
/code  →  /pr  →  /poll <PR#>
```

Only pause if there is a genuine blocker that requires a decision from the user (e.g. ambiguous scope, missing JIRA ticket number). Completing the implementation is not the end — the goal is a running poll loop.
