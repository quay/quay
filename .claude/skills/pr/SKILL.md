---
name: pr
description: >
  Create a pull request with the correct PROJQUAY/QUAYIO/NO-ISSUE title format,
  filled-in description template, and JIRA reference. Validates the PR title
  against the CI-enforced regex before creating.
allowed-tools:
  - Bash(bash .claude/scripts/enforce-pr-skill.sh *)
  - Bash(git *)
  - Bash(gh pr *)
  - Bash(cat *)
  - Bash(echo $AGENTIC_SESSION_NAME)
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

## Step 3: Ambient Session Metadata

Check if this PR is being created from an ambient session:

```bash
echo $AGENTIC_SESSION_NAME
```

- **If `AGENTIC_SESSION_NAME` is set** (ambient session): populate the `## Automation` section
  in the description with the session ID value. Example:
  ```text
  ## Automation
  - **Session ID**: session-35fda6ec-7b06-4a69-b2a9-1cc3ca7238f4
  ```
- **If `AGENTIC_SESSION_NAME` is empty or unset** (manual PR): remove the `## Automation`
  section entirely from the description.

Write the filled template to `/tmp/pr-body.md`.

## Step 4: Create PR

If `AGENTIC_SESSION_NAME` was set (ambient session), include `--label "ambient-session"`:

```bash
gh pr create \
  --title "PROJQUAY-XXXX: type(scope): description" \
  --body "$(cat /tmp/pr-body.md)" \
  --base master \
  --label "ambient-session"
```

For manual PRs (no ambient session), omit the `--label` flag.

## Step 5: Post-PR

After creation, **openshift-ci-robot** will:
- Validate the JIRA reference
- Check Target Version
- Transition ticket ASSIGNED -> POST
- Apply `jira/valid-reference` label

If the bot reports issues: fix the PR title or update the JIRA ticket's Target Version.

**Always** run `/poll <PR#>` immediately after PR creation — do not ask the user.
