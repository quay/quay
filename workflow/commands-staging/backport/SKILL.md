---
name: backport
description: >
  Trigger the openshift-cherrypick-robot to backport a merged PR to a release
  branch. Checks Target Version from JIRA if no branch is specified.
argument-hint: PR_NUMBER [BRANCH]
disable-model-invocation: true
allowed-tools:
  - Bash(bash workflow/scripts/jira-ops.sh *)
  - Bash(gh pr *)
  - Read
  - Grep
  - AskUserQuestion
---

# Backport PR

Backport merged PR #$ARGUMENTS[0] to a release branch.

- **PR number**: `$ARGUMENTS[0]`
- **Branch** (optional): `$ARGUMENTS[1]`

## Step 1: Verify Merged

```bash
gh pr view $ARGUMENTS[0] --json state,mergedAt,title
```

The PR must be merged. If not, inform the user and stop.

## Step 2: Determine Branch

If `$ARGUMENTS[1]` is provided, use it as the target branch.

Otherwise, extract the JIRA ticket key from the PR title and check Target Version:

```bash
bash workflow/scripts/jira-ops.sh check-version <PROJQUAY-XXXX>
```

Map Target Version to release branch (e.g. `quay-v3.12.0` → `redhat-3.12`). Ask the user if the mapping is ambiguous.

## Step 3: Trigger Cherry-Pick

```bash
gh pr comment $ARGUMENTS[0] --body "/cherrypick <BRANCH>"
```

## Step 4: Confirm

Report:
- Cherry-pick command posted on PR #$ARGUMENTS[0]
- Target branch
- The `openshift-cherrypick-robot` will create a backport PR automatically
- The JIRA lifecycle plugin clones the parent ticket for the target release
- Monitor the backport PR for CI results
