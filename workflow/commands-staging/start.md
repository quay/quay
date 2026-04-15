---
allowed-tools: Bash(bash:*), Bash(git:*), Bash(curl:*), Bash(jq:*), Bash(cat:*), Bash(which:*), Read, Write, Glob, Grep, Agent, AskUserQuestion
argument-hint: PROJQUAY-XXXX
description: Begin work on a JIRA ticket — assign, create branch, load context
---

# Start Work on JIRA Ticket

Begin work on JIRA ticket `$ARGUMENTS`. This sets up the JIRA ticket, creates a branch, and loads relevant documentation.

## Step 1: JIRA Ticket Setup

Run these commands to view and assign the ticket:

```bash
bash workflow/scripts/jira-ops.sh view $ARGUMENTS
bash workflow/scripts/jira-ops.sh assign $ARGUMENTS
bash workflow/scripts/jira-ops.sh check-version $ARGUMENTS
bash workflow/scripts/jira-ops.sh transition $ARGUMENTS "ASSIGNED"
```

- If "Target Version" is set, note that **backporting will be required** after merge.
- Valid transitions: `New`, `ASSIGNED`, `POST`, `ON_QA`, `Verified`, `Release Pending`, `Closed`, `MODIFIED`

## Step 2: Branch Setup

```bash
git checkout master && git pull origin master
git checkout -b $ARGUMENTS-short-description
```

Branch naming convention: `PROJQUAY-<number>-<kebab-case-description>`

Ask the user for a short description if one isn't obvious from the ticket summary.

## Step 3: Context Loading

Based on the ticket's area, read the relevant documentation from `agent_docs/`:

| If working on... | Read... |
|------------------|---------|
| API endpoints, authentication | `agent_docs/api.md` |
| Database models, migrations | `agent_docs/database.md` |
| Testing patterns, fixtures | `agent_docs/testing.md` |
| Architecture, key files | `agent_docs/architecture.md` |
| Global readonly superuser feature | `agent_docs/global_readonly_superuser.md` |
| Local development setup | `agent_docs/development.md` |
| React frontend | `web/AGENTS.md` |

Read the ticket description to determine which docs are relevant, then load them.

## Step 4: Summary

Report to the user:
- Ticket summary, status, and assignee
- Whether backporting is required (Target Version)
- Branch name created
- Which documentation was loaded
- Suggested next step: run `/code` to start implementation
