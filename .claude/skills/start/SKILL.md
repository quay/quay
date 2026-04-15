---
name: start
description: >
  Begin work on a JIRA ticket. Assigns the ticket, creates a feature branch,
  checks if backporting is needed, and loads the relevant agent_docs/ for the
  ticket's area. Use at the start of any PROJQUAY or QUAYIO ticketed work.
argument-hint: PROJQUAY-XXXX
disable-model-invocation: true
allowed-tools:
  - Bash(bash .claude/scripts/jira-ops.sh *)
  - Bash(git checkout *)
  - Bash(git pull *)
  - Read
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
---

# Start Work on JIRA Ticket

Begin work on JIRA ticket `$ARGUMENTS`.

## Step 1: View and Assign

```bash
bash .claude/scripts/jira-ops.sh view $ARGUMENTS
```

Review the ticket summary, status, and description. Then assign and transition:

```bash
bash .claude/scripts/jira-ops.sh assign $ARGUMENTS
bash .claude/scripts/jira-ops.sh transition $ARGUMENTS "ASSIGNED"
```

## Step 2: Check Backport Requirement

```bash
bash .claude/scripts/jira-ops.sh check-version $ARGUMENTS
```

If Target Version is set, note that **backporting will be required** after merge.

## Step 3: Create Branch

```bash
git checkout master && git pull origin master
git checkout -b $ARGUMENTS-short-description
```

Branch naming: `PROJQUAY-<number>-<kebab-case-description>`. Derive the description from the ticket summary. Ask the user if it's ambiguous.

## Step 4: Load Context

Based on the ticket's area, read the relevant docs:

| Area | Doc |
|------|-----|
| API endpoints, auth | `agent_docs/api.md` |
| Database, migrations | `agent_docs/database.md` |
| Testing | `agent_docs/testing.md` |
| Architecture | `agent_docs/architecture.md` |
| Global readonly superuser | `agent_docs/global_readonly_superuser.md` |
| Local dev setup | `agent_docs/development.md` |
| React frontend | `web/AGENTS.md` |

## Step 5: Report

Summarize:
- Ticket: key, summary, status, assignee
- Backport: required or not
- Branch: name created
- Docs loaded
- Next step: `/code`
