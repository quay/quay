---
name: pilot-update
description: >
  Post a biweekly Agentic SDLC pilot update comment to PROJQUAY-11352.
  Traverses the Jira issue hierarchy, scans 15 quay/* repos for
  pilot-relevant PRs, drafts a structured 5-section update, and posts
  after user review. Accepts an optional lookback window in days
  (default 14).
argument-hint: "[days]"
allowed-tools:
  - Bash(gh search prs *)
  - Bash(gh pr view *)
  - Bash(gh pr list *)
  - Bash(gh api *)
  - Bash(git log *)
  - Bash(date *)
  - Bash(bash .claude/scripts/jira-ops.sh *)
  - Bash(curl *)
  - mcp__mcp-atlassian__jira_get_issue
  - mcp__mcp-atlassian__jira_search
  - mcp__mcp-atlassian__jira_batch_get_changelogs
  - Read
  - Grep
  - Glob
  - AskUserQuestion
---

# Quay Agentic SDLC Pilot Update

Gather data from Jira and GitHub, draft a biweekly update comment, get user
input on subjective sections, and post the final comment to PROJQUAY-11352.

**Tracking issue:** PROJQUAY-11352 ("Quay Agentic Tool Pilot")
**Deadline:** June 30, 2026

> **Prerequisite:** This skill uses Jira MCP tools
> (`mcp__mcp-atlassian__jira_*`) which are configured at the Ambient
> session level, not in the repo's `.mcp.json`. It must be run inside an
> Ambient Code session with the Jira integration enabled. If running
> locally, the skill falls back to the Jira REST API via curl using
> credentials from `~/.atlassian/credentials` or environment variables.

---

## Phase 1: Gather Jira Activity (BFS traversal)

Determine the lookback window. Default is 14 days. If `$ARGUMENTS` was
provided and is a positive integer, use that value instead. Otherwise fall
back to 14.

Compute:
- `end_date` = today's date
- `start_date` = today minus lookback days

**BFS traversal starting at PROJQUAY-11352:**

Use a queue-based BFS. Start with `["PROJQUAY-11352"]`.
Before traversal, fetch and store PROJQUAY-11352's own fields using
`mcp__mcp-atlassian__jira_get_issue` with
`fields="key,summary,description,status,assignee,issuetype,created,updated"`.

For each key in the queue:
1. Search for direct children: `parent = KEY ORDER BY updated DESC`
   - Use `mcp__mcp-atlassian__jira_search` with
     `fields="key,summary,description,status,assignee,issuetype,created,updated"`
     and `limit=50`
   - Paginate with `start_at` if `total > 50` (pagination applies per
     parent-key search, not once globally)
2. Fetch each child's key, summary, description, status, assignee,
   issuetype, created, updated fields
3. Add each child's key to the queue
4. Continue until the queue is empty

The hierarchy under PROJQUAY-11352 is at least 3 levels deep
(Feature → Epic → Story/Task). The BFS must traverse all levels.

**After collecting all keys in the hierarchy (including PROJQUAY-11352
itself, with fields stored for each):**

Fetch changelogs for all discovered keys using
`mcp__mcp-atlassian__jira_batch_get_changelogs` with `fields="status"` to
get status transitions. Filter transitions to those whose timestamp falls
within the lookback window. If more than 20 keys, batch in groups of 20.

**Classify findings:**

- **Completed issues**: status transitioned to "Done", "Closed",
  "Resolved", or "MODIFIED" within the window
- **Created issues**: `created` field is within the window
- **Status transitions**: any status change within the window (excluding
  completions)
- **Blocked issues**: status is "Blocked" or summary/description contains
  "blocked" (case-insensitive)

---

## Phase 2: Gather GitHub Activity

**Repos to search:**
- `quay/quay`
- `quay/quay-operator`
- `quay/quay-bridge-operator`
- `quay/quay-bridge-operator-konflux`
- `quay/container-security-operator`
- `quay/quay-builder`
- `quay/quay-builder-qemu`
- `quay/quay-distribution`
- `quay/quay-konflux-components`
- `quay/quay-fbcs`
- `quay/registry-proxy`
- `quay/registry-proxy-tests`
- `quay/mirror-registry`
- `quay/mirror-registry-konflux`
- `quay/quay-tests`

All repos are under the `quay/` org and team-owned. No cross-team author
filtering is required.

For each repo, search for PRs using the GitHub CLI:

**Merged PRs (last N days):**
```bash
gh search prs --repo quay/<repo> --merged --merged-at ">={start_date}" --json number,title,author,closedAt,url --limit 50
```

**Open PRs (in progress):**
```bash
gh search prs --repo quay/<repo> --state open --updated ">={start_date}" --json number,title,author,createdAt,url --limit 50
```

**Filter to pilot-relevant PRs** by checking if any of these apply:
- Has label `agentic-sdlc-pilot` or `ai-pilot`
- Touches paths: `.claude/`, `CLAUDE.md`, `AGENTS.md`, `WORKFLOW.md`,
  `claude-plugin/`, skills, agents
- Title or body mentions: "SDLC", "pilot", "agentic", "skill", "claude",
  "AI", "ambient", "factory"
- PR body contains AI-generated signatures: `Co-Authored-By: Claude`,
  `Generated with Claude Code`, `Generated with Ambient`

If a repo returns a 404 or 403, skip it gracefully and note it was skipped
in the output.

Collect for each pilot-relevant PR: number, title, state, merged_at or
created_at, repo name, author.

---

## Phase 3: Draft the Update

Assemble gathered data into the 5-section template below.

### Section 1: What We Tried (auto-populated)

Populate from:
- New Jira issues created in the window (list as:
  `[KEY] Summary — issuetype`)
- PRs opened (not yet merged) — include repo and PR number
- Tools, workflows, or skills referenced in PR titles/descriptions/Jira
  summaries
- Explicitly note which tool was used where possible: **Ambient Code**,
  **Factory AI**, or **manual**
- Note the workflow type: bug fix, story implementation, triage,
  documentation, CI/CD
- Note the issue type: Bug, Story, Epic, Task

### Section 2: What Happened (auto-populated)

Populate from:
- PRs merged during the window — include repo, PR number, title, and link
- PRs opened but not yet merged — note as "in review" or "in progress"
- PRs closed without merging — note as "closed/abandoned" with reason if
  available
- Jira issues completed (status → Done/Closed/Resolved/MODIFIED) within
  the window
- Status transitions on pilot-related issues
- CI/test results if notable (failures, regressions)

Do NOT list PRs that are ordinary feature or bug work unless they were
produced using the AI-assisted workflow. The signal here is: did the
agentic pipeline produce output, and did that output land?

### Section 3: What We Learned (seeded + user input)

Seed with data where possible:
- PR review comment themes (e.g., recurring feedback patterns on
  AI-generated PRs)
- Issues that required significant rework or were rejected
- Issues that went smoothly and why (fast merge, no review comments)

After presenting the seeded bullets, use AskUserQuestion to prompt the user:

> The "What We Learned" section above is seeded from PR/Jira data.
> Please add subjective insights: What surprised you? What context was
> missing? What would you do differently? Any observations about code
> quality, review burden, or team dynamics?

### Section 4: What's Blocked (seeded + user input)

Seed with data:
- Jira issues with "Blocked" status
- Issues whose descriptions mention: blocked, waiting, dependency, access,
  permission
- PRs stuck in review for >7 days

After presenting the seeded bullets, use AskUserQuestion to prompt the user:

> The "What's Blocked" section above is seeded from Jira/GitHub data.
> Please add any additional blockers: tooling gaps, access issues, Jira
> integration problems, anything else slowing you down?

### Section 5: What We're Trying Next (seeded + user input)

Seed with data:
- Jira issues in "New", "To Do", or "Refinement" status under
  PROJQUAY-11352
- Unmerged pilot-relevant PRs (work in flight)
- Upcoming epics or stories with future start dates

After presenting the seeded bullets, use AskUserQuestion to prompt the user:

> The "What We're Trying Next" section above is seeded from upcoming Jira
> work. Please add or adjust: planned experiments, focus areas, changes in
> strategy or approach?

---

## Phase 4: Review and Confirm

Assemble the complete comment using the template:

```markdown
## Quay Agentic SDLC Pilot Update — {start_date} to {end_date}

### What We Tried
{bullet list: tools used, workflows attempted, issue types worked on, PRs opened}

### What Happened
{bullet list: PRs merged/closed, issues completed, status changes, outcomes}

### What We Learned
{bullet list: surprises, missing context, quality observations, process insights}

### What's Blocked
{bullet list: tooling gaps, access issues, integration problems, dependencies}

### What We're Trying Next
{bullet list: upcoming work, planned experiments, strategy changes}
```

Display the full formatted Markdown in the terminal. Use AskUserQuestion to
ask the user to confirm or request edits:

> Here is the full draft comment for PROJQUAY-11352. Reply with:
> - "post" to post as-is
> - Specific edits to apply
> - "cancel" to abort

Apply any requested edits and re-display until the user confirms with
"post".

**Deduplication rule:** If a PR or Jira issue is already mentioned in
"What We Tried," only carry it into "What Happened" if there is a distinct
new event to report (e.g., it merged, it was completed, it transitioned to
a new status). Do not repeat items across sections without new information.

---

## Phase 5: Post the Comment

Post the confirmed comment to PROJQUAY-11352.

**Method 1 — Jira MCP (preferred in Ambient sessions):**
If `mcp__mcp-atlassian__jira_get_issue` is available, the Jira MCP
integration is active. However, the MCP tools exposed in this skill do
not include a comment-posting tool. Proceed to Method 2.

**Method 2 — Jira REST API via curl:**
Use the same credential helpers as `.claude/scripts/jira-ops.sh`. Source
credentials from environment variables (`JIRA_EMAIL` / `JIRA_API_TOKEN`)
or from `~/.atlassian/credentials` (INI format with `email` and `token`
keys). Post the comment with:

```bash
curl -s -X POST \
  -H "Authorization: Basic $(echo -n "${JIRA_EMAIL}:${JIRA_API_TOKEN}" | base64)" \
  -H "Content-Type: application/json" \
  "https://redhat.atlassian.net/rest/api/3/issue/PROJQUAY-11352/comment" \
  -d '{"body":{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"<final_markdown>"}]}]}}'
```

If the curl call fails (non-200 response), display the full markdown for
the user to copy-paste manually and report the error.

Confirm success with: "Comment posted to PROJQUAY-11352."

---

## Error Handling

- **Repo not accessible**: skip that repo, note it was skipped in the
  output.
- **No pilot-relevant PRs found**: include "No pilot-relevant PRs found
  in this period" in "What Happened".
- **BFS finds no children under PROJQUAY-11352**: report only
  PROJQUAY-11352 itself; this is valid.
- **Jira batch changelog limit**: if >20 keys, batch in groups of 20.
- **User provides empty input for a subjective section**: use "Nothing to
  report this period." as the placeholder.
- **Comment post fails**: display markdown for manual copy-paste and
  report the error.
- **Jira MCP tools unavailable** (running outside Ambient): fall back to
  the Jira REST API via curl for both data gathering and comment posting.
  If credentials are not available, report the error and display
  instructions for manual posting.
