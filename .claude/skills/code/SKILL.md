---
name: code
description: >
  Implement changes following Quay conventions. Reads the relevant AGENTS.md
  and agent_docs/ for the area being worked on, then guides implementation,
  quality checks (pre-commit, tests), and commit with proper message format.
disable-model-invocation: true
allowed-tools:
  - Bash(bash workflow/scripts/format-and-lint.sh *)
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

## Step 3: Quality Checks

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
bash workflow/scripts/format-and-lint.sh            # staged files
bash workflow/scripts/format-and-lint.sh --all-files # all files
```

Run relevant tests:

```bash
TEST=true PYTHONPATH="." pytest path/to/test.py -v  # Single test
make unit-test                                       # All unit tests
make registry-test                                   # Registry protocol
make types-test                                      # mypy
```

## Step 4: Commit

Format:

```
<subsystem>: <what changed> (PROJQUAY-####)

<why this change was made>
```

See `.github/CONTRIBUTING.md` for full conventions. Pre-commit hooks run on commit — fix any failures and re-commit.
