---
name: test
description: >
  Run targeted tests for a file, directory, or area. Selects the right pytest
  command based on what's being tested (unit, registry, types, or frontend),
  reports results, and surfaces failures clearly.
argument-hint: "[path/to/test.py | area]"
allowed-tools:
  - Bash(TEST=true PYTHONPATH="." pytest *)
  - Bash(make unit-test)
  - Bash(make registry-test)
  - Bash(make types-test)
  - Bash(npm *)
  - Bash(git *)
  - Read
  - Glob
  - Grep
---

# Run Tests

Run tests for: `$ARGUMENTS`

## Step 1: Determine what to test

If `$ARGUMENTS` names a specific file, use it directly. Otherwise determine the
right scope from the area:

| Area | Command |
|------|---------|
| Specific test file | `TEST=true PYTHONPATH="." pytest <path> -v` |
| Specific test function | `TEST=true PYTHONPATH="." pytest <path>::<TestClass>::<test_fn> -v` |
| All unit tests | `make unit-test` |
| Registry protocol | `make registry-test` |
| Type checking (mypy) | `make types-test` |
| Frontend (Playwright) | `cd web && npm run test:e2e` |
| Frontend (Cypress) | `cd web && npm run test:integration` |

If no path is given, infer from recent changes:

```bash
git diff --name-only HEAD
```

Find the corresponding test file(s) based on the changed files.

## Step 2: Run the tests

Use the appropriate command from above. Add flags as needed:

```bash
# Short traceback for faster scanning
TEST=true PYTHONPATH="." pytest path/to/test.py -v --tb=short

# Filter by keyword
TEST=true PYTHONPATH="." pytest path/to/test.py -k "keyword" -v

# Quiet (just pass/fail counts)
TEST=true PYTHONPATH="." pytest path/to/test.py -q --tb=no
```

## Step 3: Report results

- **All pass**: confirm count and time
- **Failures**: show the failing test name, the assertion error, and the fix
  direction (do NOT show the full traceback unless it's needed to diagnose)
- **Collection errors**: usually a missing import or syntax error — show the
  exact file and line

## Step 4: Fix and re-run (if failures)

Fix the failure in the source or test file, then re-run the failing test only:

```bash
TEST=true PYTHONPATH="." pytest path/to/test.py::TestClass::test_fn -v
```

Confirm the fix passes before proceeding.
