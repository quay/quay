---
allowed-tools: Bash(bash:*), Bash(git:*), Bash(make:*), Bash(pytest:*), Bash(pre-commit:*), Bash(npm:*), Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
description: Implement changes following Quay conventions — code, test, commit
---

# Implement Changes

Implement code changes following Quay project conventions. Read the relevant docs, write code, run quality checks, and commit.

## Step 1: Read Conventions

Read `AGENTS.md` for universal conventions. Then read the area-specific doc from `agent_docs/`:

| If working on... | Read... |
|------------------|---------|
| API endpoints, authentication | `agent_docs/api.md` |
| Database models, migrations | `agent_docs/database.md` |
| Testing patterns, fixtures | `agent_docs/testing.md` |
| Architecture, key files | `agent_docs/architecture.md` |
| React frontend | `web/AGENTS.md` |

## Step 2: Implement

Follow `AGENTS.md` conventions:
- Use appropriate exception types from `endpoints/exception.py`
- Follow existing import ordering patterns
- Never write migration files from scratch — always run `alembic revision -m "description"` first
- No secrets in code

## Step 3: Quality Checks

Pre-commit hooks handle formatting and linting automatically on `git commit`. To run manually:

```bash
bash workflow/scripts/format-and-lint.sh            # staged files
bash workflow/scripts/format-and-lint.sh --all-files # all files
```

Run relevant tests:

```bash
TEST=true PYTHONPATH="." pytest path/to/test.py -v       # Single test file
make unit-test                                            # All unit tests
make registry-test                                        # Registry protocol tests
make types-test                                           # Type checking (mypy)
```

## Step 4: Commit

Commit message format:

```
<subsystem>: <what changed> (PROJQUAY-####)

<why this change was made>
```

See `.github/CONTRIBUTING.md` for full commit message conventions.

Pre-commit hooks will run automatically. If they fail, fix the issues and commit again.
