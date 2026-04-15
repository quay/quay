---
name: jira
description: >
  View or update a JIRA ticket in the PROJQUAY/QUAYIO projects. Supports
  view, assign, transition, check-version, and set-version operations.
  Uses redhat.atlassian.net REST API.
argument-hint: PROJQUAY-XXXX [action]
disable-model-invocation: true
allowed-tools:
  - Bash(bash .claude/scripts/jira-ops.sh *)
  - Read
  - Grep
  - AskUserQuestion
---

# JIRA Ticket Operations

Manage JIRA ticket `$ARGUMENTS[0]`.

- **Issue key**: `$ARGUMENTS[0]`
- **Action** (optional): `$ARGUMENTS[1]` — defaults to `view`

## Operations

### View (default)

```bash
bash .claude/scripts/jira-ops.sh view $ARGUMENTS[0]
```

### Assign

```bash
bash .claude/scripts/jira-ops.sh assign $ARGUMENTS[0]
```

Assigns to current user (requires `acli` or accountId).

### Transition

```bash
bash .claude/scripts/jira-ops.sh transition $ARGUMENTS[0] "$ARGUMENTS[2]"
```

Valid statuses: `New`, `ASSIGNED`, `POST`, `ON_QA`, `Verified`, `Release Pending`, `Closed`, `MODIFIED`

Example: `/jira PROJQUAY-1234 transition POST`

### Check Target Version

```bash
bash .claude/scripts/jira-ops.sh check-version $ARGUMENTS[0]
```

Reports whether backporting is required.

### Set Target Version

```bash
bash .claude/scripts/jira-ops.sh set-version $ARGUMENTS[0] "$ARGUMENTS[2]"
```

Example: `/jira PROJQUAY-1234 set-version quay-v3.18.0`

## Notes

- All REST ops require `JIRA_API_TOKEN`. `JIRA_USER` defaults to `quay-devel@redhat.com`.
- If `acli` is installed, it is preferred.
- Instance: `https://redhat.atlassian.net`
