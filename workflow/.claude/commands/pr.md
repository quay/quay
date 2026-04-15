---
allowed-tools: Bash(bash:*), Bash(git:*), Bash(gh:*), Bash(cat:*), Read, Write, Edit, Glob, Grep, AskUserQuestion
description: Create a PR with correct title format, description template, and JIRA reference
---

# Create Pull Request

Create a pull request with the correct title format, description template, and JIRA reference.

## Step 1: Validate PR Title

The PR title **must** match this regex (enforced by CI):

```
^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
```

Examples:
- `PROJQUAY-1234: fix(api): add pagination to tag listing`
- `NO-ISSUE: chore: update dependencies`
- `[redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination`

Validate the title before creating the PR:

```bash
bash workflow/scripts/validate-pr-title.sh "PROJQUAY-1234: fix(api): add pagination to tag listing"
```

## Step 2: Build PR Description

Use the template at `workflow/templates/pr-description.md`. Fill in:
- **Summary**: What this PR does
- **Root Cause / Rationale**: Why this change is needed
- **Changes**: List of changes made
- **Test Plan**: How to verify the changes
- **JIRA Link**: `https://redhat.atlassian.net/browse/PROJQUAY-XXXX`
- **Backport**: Whether backporting is required (from `/start` step)

Write the filled-in template to `/tmp/pr-body.md`.

## Step 3: Create the PR

```bash
gh pr create \
  --title "PROJQUAY-XXXX: type(scope): description" \
  --body "$(cat /tmp/pr-body.md)" \
  --base master
```

## Step 4: Post-PR Notes

After PR creation, **openshift-ci-robot** (JIRA Lifecycle Plugin) will:
- Validate the JIRA reference in the PR title
- Check that the ticket targets the correct version
- Transition the ticket status from ASSIGNED to POST
- Apply labels like `jira/valid-reference`

If the bot reports issues: fix the PR title, or update the JIRA ticket's "Target Version".

Suggest next step: run `/poll <PR#>` to monitor CI and review feedback.
