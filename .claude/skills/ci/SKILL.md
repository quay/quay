---
name: ci
description: >
  Quick CI status check for a pull request. Shows pass/fail/pending status
  for all GitHub Actions jobs, Prow, and Konflux checks.
argument-hint: PR_NUMBER
allowed-tools:
  - Bash(bash .claude/scripts/check-ci.sh *)
  - Bash(gh *)
  - Read
  - Grep
---

# CI Status Check

Quick CI check for PR #$ARGUMENTS.

## Step 1: Check

```bash
bash .claude/scripts/check-ci.sh $ARGUMENTS
```

## Step 2: Report

Summarize each job:
- **pass** — No action needed
- **fail** — Needs investigation
- **pending** — Still running
- **skipping** — Not applicable

If any jobs failed, suggest `/poll $ARGUMENTS` for the full feedback loop with fixes.
