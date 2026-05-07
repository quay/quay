---
name: retrospect
description: >
  Run the full retrospective cycle: collect session data, analyze patterns,
  identify stuck points and successes, and propose concrete improvements
  to agent_docs, skills, and workflow context.
allowed-tools:
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(python3 *)
  - Bash(date *)
  - Read
  - Write
  - Glob
  - Grep
  - Agent
  - mcp__acp__acp_list_sessions
  - mcp__acp__acp_get_session
  - mcp__acp__acp_get_session_status
  - mcp__rubric__evaluate_rubric
---

# Retrospective Engine

Run the COLLECT -> ANALYZE -> PROPOSE -> OUTPUT cycle for continuous workflow improvement.

## Phase 1: COLLECT

### Step 1: Enumerate Sessions

List all sessions from the last 24 hours, including completed ones:

```
mcp__acp__acp_list_sessions(include_completed=true, limit=100)
```

Record each session's name, displayName, phase, and createdAt.

### Step 2: Retrieve Session Details and Messages

For each session, get the full spec (including `initialPrompt`) and conditions:

```
mcp__acp__acp_get_session(session_name="<name>")
```

Then get messages. Try `acp_get_session_status` first. If messages come back
empty, fall back to the extract script:

```bash
python3 .ambient/workflows/retrospective/scripts/extract-session-messages.py <PROJECT> <SESSION_NAME> 30
```

The script handles both AG-UI streaming deltas (active sessions) and
MESSAGES_SNAPSHOT fallback (completed sessions). It outputs JSON with a
`messages` array.

For each session extract:
- What it was trying to accomplish (initialPrompt + displayName)
- Whether it succeeded or got stuck
- Key messages showing conversation flow
- Error messages, retries, or user corrections
- Which skills/commands were invoked
- Duration (startTime to lastActivityTime)

Skip sessions that are still actively Running.

### Step 3: Check Git Activity

```bash
git log --since="24 hours ago" --oneline --all
```

Cross-reference commits with session autoBranches.

### Step 4: Review Existing Workflow State

Read the current workflow files to understand what guidance already exists:

- `AGENTS.md` and `CLAUDE.md`
- `agent_docs/` documentation
- `.claude/skills/` definitions

## Phase 2: ANALYZE

### Step 5: Classify Session Outcomes

| Category | Signal |
|----------|--------|
| **Smooth** | Completed with minimal back-and-forth, no corrections |
| **Recovered** | Hit obstacle but self-corrected or user corrected once |
| **Stuck** | Multiple retries, user frustration, or abandoned |
| **Failed** | Session in Failed phase or explicit failure |

### Step 6: Root Cause Analysis (Stuck/Failed)

- **Missing documentation** — agent didn't know how
- **Missing skill** — manual steps that should be automated
- **Wrong approach** — suboptimal path taken
- **Tool limitation** — needed unavailable capability
- **External blocker** — CI, API, auth issues
- **Platform bug** — Ambient platform issue

### Step 7: Identify Successes and Patterns

- Sessions that went well — patterns worth codifying
- Cross-session recurring themes
- Convention violations appearing repeatedly

## Phase 3: PROPOSE

### Step 8: Generate Improvement Proposals

For each finding, generate a concrete proposal:

- **Documentation gaps**: target file path, section, actual content, evidence
- **Skill improvements**: target SKILL.md, change, rationale, evidence
- **New skills**: name, description, what it automates, outline
- **Workflow changes**: target file, change, impact

### Step 9: Prioritize

- **P1**: High frequency + high impact + low effort
- **P2**: High frequency OR high impact
- **P3**: Low frequency + low impact

## Phase 4: OUTPUT

### Step 10: Write Daily Digest

Write to `/workspace/artifacts/retrospective-<DATE>.md`:

```markdown
# Ambient Retrospective — <DATE>

## Executive Summary
<!-- 3-5 bullets -->

## Session Inventory
| Session | Status | Duration | Outcome | Notes |
|---------|--------|----------|---------|-------|

## Findings
### Stuck Points
### Successes
### Patterns

## Improvement Proposals
### P1 — Do First
### P2 — Do Soon
### P3 — Backlog

## Metrics
- Sessions reviewed: N
- Stuck points identified: N
- Proposals generated: N
```

### Step 11: Evaluate

Run rubric evaluation against `.ambient/workflows/retrospective/rubric.md`.
