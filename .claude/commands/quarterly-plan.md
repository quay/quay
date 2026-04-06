---
allowed-tools: Bash(acli:*), Bash(python3:*), Bash(cat:*), Bash(which:*), Bash(sips:*), Read, Write, Glob, Grep, AskUserQuestion
argument-hint: <quarter> <must-have-issues> e.g., "2026-Q3 QUAYIO-1234,QUAYIO-5678"
description: Plan the next quarter by tagging JIRA issues with the quarterly label
---

# Quarterly Planning

Tag JIRA issues with the next quarter's label based on priority triage. Automatically tags Blockers and Criticals, presents Majors for review.

## Arguments

Input: `$ARGUMENTS`

**Format:** `<quarter> [must-have-issues]` or `add <quarter> <issue-keys>`

- `<quarter>` (required): The quarter being planned, e.g., `2026-Q3`
- `[must-have-issues]` (optional): Comma-separated issue keys to always include, e.g., `QUAYIO-1234,QUAYIO-5678`

**Modes:**
- **Plan mode** (default): Full quarterly planning with priority triage
- **Add mode**: Quickly add issues to an existing quarter plan

**Examples:**
```
/quarterly-plan 2026-Q3
/quarterly-plan 2026-Q3 QUAYIO-1234,QUAYIO-5678
/quarterly-plan add 2026-Q3 QUAYIO-1900,QUAYIO-1905
```

---

## Phase 0: Prerequisites

### Step 1: Check acli Installation

```bash
which acli
```

If acli is NOT installed, display setup instructions (same as `/jira-ticket`) and stop.

### Step 2: Check Authentication

```bash
acli jira auth status
```

If not authenticated, attempt login using token from `~/.config/acli/token.txt`, `~/.acli-token`, or `$JIRA_API_TOKEN`. Read email from `~/.config/acli/jira_config.yaml`.

### Step 3: Store User Email

```bash
cat ~/.config/acli/jira_config.yaml
```

Extract the `email` field for use throughout the skill.

---

## Phase 1: Parse Arguments and Determine Scope

### Step 1: Parse Quarter

Parse `$ARGUMENTS` to extract:
- **Target quarter**: The quarter being planned (e.g., `2026-Q3`)
- **Must-have issues**: Optional comma-separated issue keys

Derive the **previous quarter** automatically:
- Q2 -> previous is Q1 (same year)
- Q3 -> previous is Q2 (same year)
- Q4 -> previous is Q3 (same year)
- Q1 -> previous is Q4 (previous year)

### Step 2: Derive Label Names

Labels follow the format `quay-{YYYY}-Q{N}` (capital Q):
- **Current quarter label**: e.g., `quay-2026-Q2`
- **Target quarter label**: e.g., `quay-2026-Q3`

### Step 3: Determine Project

Ask the user which project to plan for:

> Which project?
> 1. **QUAYIO** (default)
> 2. **PROJQUAY**

Default to **QUAYIO** if the user confirms or doesn't specify.

---

## Phase 2: Gather Data

Run all three queries in parallel:

### Query 1: Current Quarter Carryover

Find all non-closed issues with the current quarter label, filtered to Blocker/Critical/Major:

```bash
acli jira workitem search \
  --jql 'project = {PROJECT} AND labels = "{CURRENT_Q_LABEL}" AND status != Closed AND priority in (Blocker, Critical, Major) ORDER BY priority ASC, updated DESC' \
  --fields "key,priority,status,issuetype,assignee,summary,labels" \
  --paginate --csv
```

### Query 2: Already Tagged for Target Quarter

Find issues already labeled with the target quarter:

```bash
acli jira workitem search \
  --jql 'project = {PROJECT} AND labels = "{TARGET_Q_LABEL}" ORDER BY priority ASC, updated DESC' \
  --fields "key,priority,status,issuetype,assignee,summary,labels" \
  --paginate --csv
```

### Query 3: All Blockers/Criticals in Project

Find ALL non-closed Blockers and Criticals in the project, excluding those already tagged with the current quarter label (these are net-new):

```bash
acli jira workitem search \
  --jql 'project = {PROJECT} AND status != Closed AND priority in (Blocker, Critical) AND (labels is EMPTY OR labels not in ("{CURRENT_Q_LABEL}")) ORDER BY priority ASC, updated DESC' \
  --fields "key,priority,status,issuetype,assignee,summary,labels" \
  --paginate --csv
```

### Query 4: Must-Have Issues (if provided)

If must-have issue keys were provided, fetch their details:

```bash
acli jira workitem search \
  --jql 'key in ({MUST_HAVE_KEYS})' \
  --fields "key,priority,status,issuetype,assignee,summary,labels" \
  --csv
```

---

## Phase 3: Present Summary

### Step 1: Display Current State

Present a summary organized by category:

```
============================================================
QUARTERLY PLANNING: {TARGET_Q_LABEL}
Project: {PROJECT}
Previous Quarter: {CURRENT_Q_LABEL}
============================================================

ALREADY TAGGED {TARGET_Q_LABEL}: {count} issues
[table of issues]

MUST-HAVES (user specified): {count} issues
[table with priority, status, assignee, summary]
Note which ones already have the target quarter label.

------------------------------------------------------------
CURRENT QUARTER CARRYOVER ({CURRENT_Q_LABEL}, non-closed):
------------------------------------------------------------

BLOCKERS: {count} issues
[table with key, status, assignee, summary]

CRITICALS: {count} issues
[table with key, status, assignee, summary]

MAJORS: {count} issues (for review)
[table with key, status, assignee, summary]

------------------------------------------------------------
NEW BLOCKERS/CRITICALS (not in {CURRENT_Q_LABEL}):
------------------------------------------------------------

BLOCKERS: {count} issues
[table with key, status, assignee, summary]

CRITICALS: {count} issues
[table with key, status, assignee, summary]
============================================================
```

### Step 2: State the Auto-Tag Plan

Tell the user:

> **Auto-tag plan:**
> - All Blockers (current quarter carryover + new): {count} issues
> - All Criticals (current quarter carryover + new): {count} issues
> - Must-have issues: {count} issues
> - Already tagged: {count} issues (no action needed)
>
> **For your review:**
> - Majors from current quarter: {count} issues
> - New Blockers/Criticals (not in current quarter): {count} issues
>
> Proceed with auto-tagging Blockers, Criticals, and must-haves?

Wait for user confirmation before proceeding.

---

## Phase 4: Apply Labels (Auto-Tag)

### Step 1: Add Target Quarter Label

**IMPORTANT:** The `acli jira workitem edit --labels` flag **appends** labels (does not replace). Use this to add the target quarter label without losing existing labels.

**IMPORTANT:** Always use Python for batch operations. Bash `for` loops with shell variables do not reliably split issue keys. Use a Python script with `subprocess` instead.

```python
import subprocess

issues = ["KEY-1", "KEY-2", ...]  # All auto-tag issues

for key in issues:
    result = subprocess.run(
        ["acli", "jira", "workitem", "edit", "--key", key, "--labels", "{TARGET_Q_LABEL}", "--yes"],
        capture_output=True, text=True
    )
    if "successfully" in result.stdout:
        print(f"{key}: OK")
    else:
        print(f"{key}: FAILED - {result.stdout.strip()}")
```

### Step 2: Skip Already-Tagged Issues

Before tagging, check if the issue already has the target quarter label. If it does, skip it to avoid unnecessary API calls. Use the data from Query 2 (Phase 2) for this check.

### Step 3: Report Auto-Tag Results

Display results:

```
Auto-tagged {count} issues with {TARGET_Q_LABEL}:
  Blockers: {count}
  Criticals: {count}
  Must-haves: {count}
  Skipped (already tagged): {count}
  Failed: {count}
```

---

## Phase 5: Review Majors and New Issues

### Step 1: Present Majors for Review

Display the full list of Majors from the current quarter carryover, plus any new Blockers/Criticals not in the current quarter that the user should review.

Ask the user:

> Which of these should be tagged with {TARGET_Q_LABEL}?
> - Type "all" to tag everything listed
> - Type "all except KEY-1, KEY-2" to exclude specific issues
> - Type "KEY-1, KEY-2, KEY-3" to include only specific issues
> - Type "none" to skip

### Step 2: Apply User Selections

Use the same Python-based approach from Phase 4 to add the target quarter label to user-approved issues.

### Step 3: Final Summary

Display the final state:

```
============================================================
QUARTERLY PLANNING COMPLETE: {TARGET_Q_LABEL}
============================================================

Total issues tagged with {TARGET_Q_LABEL}: {count}
  Blockers:   {count}
  Criticals:  {count}
  Majors:     {count}
  Must-haves: {count}
  Previously tagged: {count}

View in JIRA:
  https://redhat.atlassian.net/issues/?jql=project%20%3D%20{PROJECT}%20AND%20labels%20%3D%20%22{TARGET_Q_LABEL}%22
============================================================
```

---

## Add Mode: Incrementally Add Issues to an Existing Quarter

If `$ARGUMENTS` starts with `add`, enter Add mode instead of the full planning flow.

### Step 1: Parse Arguments

Extract the target quarter and issue keys from `$ARGUMENTS`:
- `add 2026-Q3 QUAYIO-1900,QUAYIO-1905`
- Target quarter: `2026-Q3` -> label: `quay-2026-Q3`
- Issue keys: `QUAYIO-1900`, `QUAYIO-1905`

If no issue keys are provided, ask the user for them.

### Step 2: Fetch Issue Details

Query all specified issues to show current state:

```bash
acli jira workitem search \
  --jql 'key in ({ISSUE_KEYS})' \
  --fields "key,priority,status,issuetype,assignee,summary,labels" \
  --csv
```

### Step 3: Show and Confirm

Display the issues and their current labels. Flag any that already have the target quarter label.

```
Adding to {TARGET_Q_LABEL}:

| Key | Priority | Status | Assignee | Summary | Already Tagged? |
|-----|----------|--------|----------|---------|-----------------|
| ... | ...      | ...    | ...      | ...     | Yes/No          |

Proceed? (yes / cancel)
```

### Step 4: Apply Labels

Use the same Python-based approach from Phase 4. Skip issues that already have the label.

### Step 5: Confirm

```
Added {TARGET_Q_LABEL} to {count} issues:
  {list of keys}
Skipped (already tagged): {count}
```

---

## Important Notes

### Label Format

Labels always follow the pattern `quay-{YYYY}-Q{N}` with a **capital Q**:
- `quay-2026-Q1`
- `quay-2026-Q2`
- `quay-2026-Q3`
- `quay-2026-Q4`

If the user provides lowercase (e.g., `2026-q3`), normalize to uppercase (`quay-2026-Q3`).

### acli Label Behavior

- `--labels "value"` **appends** a label to existing labels (does not replace)
- `--remove-labels "value"` removes a label
- When passing multiple labels to set at once, use **comma-separated without spaces**: `--labels "label1,label2"`
- **Never** use comma-with-spaces format (`"label1, label2"`) as this creates labels with embedded quote characters

### Bash Loop Pitfall

**Never** use shell variable expansion in bash `for` loops for issue keys:

```bash
# WRONG - keys get concatenated into one string
ISSUES="KEY-1 KEY-2 KEY-3"
for key in $ISSUES; do ...
```

**Always** use Python with `subprocess` for batch operations:

```python
# CORRECT
issues = ["KEY-1", "KEY-2", "KEY-3"]
for key in issues:
    subprocess.run(["acli", "jira", "workitem", "edit", "--key", key, ...])
```

### Deduplication

Before tagging, deduplicate the issue list. An issue may appear in multiple queries (e.g., a Blocker from the current quarter carryover that is also a must-have). Only tag each issue once.

### Customer Data

Never include customer names, company names, or identifying information in any output or generated files.

---

## Example Usage

### Plan Q3 with must-haves:
```
/quarterly-plan 2026-Q3 QUAYIO-1800,QUAYIO-1805
```

### Plan Q3 with no must-haves:
```
/quarterly-plan 2026-Q3
```

### Plan Q1 of next year:
```
/quarterly-plan 2027-Q1 QUAYIO-2000
```

### Add issues to an existing quarter:
```
/quarterly-plan add 2026-Q3 QUAYIO-1900,QUAYIO-1905
```
