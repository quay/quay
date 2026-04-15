---
allowed-tools: Bash(bash:*), Bash(gh:*), Bash(curl:*), Bash(jq:*), Read, Grep
argument-hint: PR_NUMBER
description: Quick CI status check for a pull request
---

# CI Status Check

Quick CI status check for PR #$ARGUMENTS.

## Step 1: Run CI Check Script

```bash
bash workflow/scripts/check-ci.sh $ARGUMENTS
```

## Step 2: Interpret Results

Report the status of each CI job:
- **pass** — No action needed
- **fail** — Needs investigation (see `/poll` for common fixes)
- **pending** — Still running, check again later
- **skipping** — Not applicable to this PR

If any jobs have failed, suggest running `/poll $ARGUMENTS` to get the full feedback loop with actionable fixes.
