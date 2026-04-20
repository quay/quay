---
name: pr
description: >
  Create a pull request with the correct PROJQUAY/QUAYIO/NO-ISSUE title format,
  filled-in description template, and JIRA reference. Validates the PR title
  against the CI-enforced regex before creating.
allowed-tools:
  - Bash(bash .claude/scripts/validate-pr-title.sh *)
  - Bash(git *)
  - Bash(gh pr *)
  - Bash(cat *)
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# Create Pull Request

Create a PR with the correct title format, description, and JIRA reference.

## Step 1: Validate PR Title

Title **must** match (enforced by CI):

```
^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
```

Examples:
- `PROJQUAY-1234: fix(api): add pagination to tag listing`
- `NO-ISSUE: chore: update dependencies`
- `[redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination`

```bash
bash .claude/scripts/validate-pr-title.sh "PROJQUAY-1234: fix(api): description here"
```

## Step 2: Build Description

Read the template at `.claude/templates/pr-description.md`. Fill in:
- **Summary**: What this PR does
- **Root Cause / Rationale**: Why
- **Changes**: What changed
- **Test Plan**: How to verify
- **JIRA Link**: `https://redhat.atlassian.net/browse/PROJQUAY-XXXX`
- **Backport**: Required or not (from `/start`)

Write the filled template to `/tmp/pr-body.md`.

## Step 3: Create PR

```bash
gh pr create \
  --title "PROJQUAY-XXXX: type(scope): description" \
  --body "$(cat /tmp/pr-body.md)" \
  --base master
```

## Step 4: Post-PR

After creation, **openshift-ci-robot** will:
- Validate the JIRA reference
- Check Target Version
- Transition ticket ASSIGNED → POST
- Apply `jira/valid-reference` label

If the bot reports issues: fix the PR title or update the JIRA ticket's Target Version.

Next step: `/poll <PR#>`
