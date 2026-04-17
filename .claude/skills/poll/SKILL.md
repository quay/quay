---
name: poll
description: >
  Stateful PR poller: tracks GitHub Actions CI, CodeRabbit, Codecov, and human
  reviews across polls. Always run with --once so the agent drives the loop and
  can act on each exit code immediately. Use CronCreate for async re-polling
  while CI is pending.
argument-hint: PR_NUMBER
disable-model-invocation: false
allowed-tools:
  - Bash(bash .claude/scripts/poll-pr.sh *)
  - Bash(bash .claude/scripts/format-and-lint.sh *)
  - Bash(git *)
  - Bash(gh *)
  - Bash(make *)
  - Bash(pytest *)
  - Bash(pre-commit *)
  - Bash(npm *)
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - CronCreate
  - CronDelete
  - CronList
---

# Poll PR and Act on Feedback

Poll PR #$ARGUMENTS for CI, CodeRabbit, and human review status, then fix what's broken.

**Always run with `--once`** — this lets the agent see the exit code immediately and
act on it. Never run without `--once` or in the background (`&`); the internal loop
blocks the agent and swallows exit codes.

The script manages its own state in `.claude/poll-state/pr-$ARGUMENTS.json`.
It shows a full report on the first run, then delta-only on subsequent polls.

## Exit codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All checks pass | Ready to merge |
| 1 | CI failures | Fix code, push, re-run |
| 2 | Checks pending | CronCreate to re-poll; exit this session |
| 3 | Inline review comments | Address comments, push, re-run |
| 4 | Awaiting human review | Reviewers notified; CronCreate to re-poll |

## Step 1: First poll

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS --once --team-reviewer downstream-team
```

Read the exit code and act on it per the table above. For a complete report:

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS --once --full
```

## Step 2: Exit 2 — CI still pending

Read the suggested sleep interval from the state file:

```bash
jq .next_sleep_seconds .claude/poll-state/pr-$ARGUMENTS.json
```

Create a cron to re-run the skill automatically after that interval:

```
CronCreate: in <next_sleep_seconds> seconds, /poll $ARGUMENTS
```

Then exit. The cron fires a new session which continues from the saved state.
Delete the cron (CronDelete) if you need to cancel.

## Step 3: Exit 4 — awaiting human review

The script has already posted a comment and requested reviewers.
Create a cron to check back periodically:

```
CronCreate: every 2 hours, /poll $ARGUMENTS
```

Delete the cron (CronDelete) once the PR is approved or merged.

## Step 4: Exit 1 — CI failures

| CI Job | Fix |
|--------|-----|
| Format / Pre-commit | `pre-commit run --all-files` |
| Unit tests | Run failing test locally, fix code |
| Types (mypy) | Fix type annotations |
| Registry tests | `make registry-test` locally |
| Cypress/Playwright | `cd web && npm run test:e2e` |
| PR Lint | Fix PR title regex |

## Step 5: Exit 3 — inline review comments

CodeRabbit (`chill` profile) runs 7 pre-merge checks:

| Check | Validates |
|-------|-----------|
| Title check | PR title starts with PROJQUAY-XXXX or NO-ISSUE |
| Description check | Description is relevant |
| Docstring Coverage | >= 80% on changed functions |
| Migration Safety at Scale | No unsafe ops on large tables |
| Migration Downgrade Exists | Real `downgrade()` in every migration |
| N+1 Query Prevention | No loop-based query patterns |
| Read Path Performance | No latency regressions on v2 read path |

When flagged:
1. Run `--once --full` to see all inline comments with reply/resolve commands
2. Assess each: in `chill` mode, flags are generally valid
3. Fix the code or reply with rationale, then resolve the thread
4. Push and re-run `--once`

## Step 6: Push and re-poll

```bash
git add -A && git commit -m "type(scope): address feedback"
git push fork <branch>
bash .claude/scripts/poll-pr.sh $ARGUMENTS --once
```

State is preserved across runs — the next poll shows only what changed.

Repeat until exit 0.
