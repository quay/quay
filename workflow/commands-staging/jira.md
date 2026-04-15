---
allowed-tools: Bash(bash:*), Bash(curl:*), Bash(jq:*), Bash(cat:*), Bash(which:*), Read, Grep, AskUserQuestion
argument-hint: PROJQUAY-XXXX [action]
description: Check or update JIRA ticket status and fields
---

# JIRA Ticket Operations

Manage JIRA ticket `$ARGUMENTS`.

Parse `$ARGUMENTS` to extract:
- **ISSUE_KEY**: The JIRA ticket key (e.g. `PROJQUAY-1234`)
- **ACTION**: Optional action (e.g. `assign`, `transition POST`, `set-version quay-v3.18.0`)

If no action is specified, default to `view`.

## Available Operations

### View Ticket

```bash
bash workflow/scripts/jira-ops.sh view <ISSUE_KEY>
```

Shows: key, summary, status, assignee, type, priority, target version, labels, and description.

### Assign Ticket

```bash
bash workflow/scripts/jira-ops.sh assign <ISSUE_KEY>
```

Assigns the ticket to the current user (requires `acli`).

### Transition Ticket

```bash
bash workflow/scripts/jira-ops.sh transition <ISSUE_KEY> "<STATUS>"
```

Valid transitions: `New`, `ASSIGNED`, `POST`, `ON_QA`, `Verified`, `Release Pending`, `Closed`, `MODIFIED`

### Check Target Version

```bash
bash workflow/scripts/jira-ops.sh check-version <ISSUE_KEY>
```

Reports whether backporting is required based on the Target Version field.

### Set Target Version

```bash
bash workflow/scripts/jira-ops.sh set-version <ISSUE_KEY> "<VERSION>"
```

Example: `bash workflow/scripts/jira-ops.sh set-version PROJQUAY-1234 "quay-v3.18.0"`

## Notes

- All REST operations require `JIRA_API_TOKEN`. `JIRA_USER` defaults to `quay-devel@redhat.com`.
- If `acli` is installed, it is preferred and uses its own credentials.
- JIRA instance: `https://redhat.atlassian.net`
