---
allowed-tools: Bash(bash:*), Bash(git:*), Bash(gh:*), Bash(curl:*), Bash(jq:*), Read, Grep, AskUserQuestion
argument-hint: PR_NUMBER BRANCH (e.g. 5738 redhat-3.12)
description: Trigger cherry-pick bot to backport a merged PR to a release branch
---

# Backport PR

Trigger the cherry-pick bot to backport PR #$ARGUMENTS to a release branch.

Parse `$ARGUMENTS` to extract:
- **PR_NUMBER**: The first argument (e.g. `5738`)
- **BRANCH**: The second argument (e.g. `redhat-3.12`)

If only a PR number is provided, check the JIRA ticket for the Target Version to determine the branch.

## Step 1: Verify PR is Merged

```bash
gh pr view <PR_NUMBER> --json state,mergedAt
```

The PR must be merged before backporting. If not merged, inform the user.

## Step 2: Check Target Version

If no branch was specified, look up the JIRA ticket from the PR title:

```bash
bash workflow/scripts/jira-ops.sh check-version <PROJQUAY-XXXX>
```

Map the Target Version to a release branch (e.g. `quay-v3.12.0` maps to `redhat-3.12`).

## Step 3: Trigger Cherry-Pick Bot

```bash
gh pr comment <PR_NUMBER> --body "/cherrypick <BRANCH>"
```

The `openshift-cherrypick-robot` will create a new PR against the release branch. The JIRA lifecycle plugin clones the parent ticket for the target release.

## Step 4: Confirm

Report:
- Cherry-pick command posted on PR #<PR_NUMBER>
- Target branch: <BRANCH>
- The bot will create a new backport PR automatically
- Monitor the backport PR for CI results
