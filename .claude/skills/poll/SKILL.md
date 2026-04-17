---
name: poll
description: >
  Stateful PR poller: tracks GitHub Actions CI, CodeRabbit, Codecov, and human
  reviews across polls. Loops with adaptive backoff internally. Run via the Bash
  tool with run_in_background: true so the platform notifies the agent on exit.
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

The script manages its own state in `.claude/poll-state/pr-$ARGUMENTS.json` and loops
internally with adaptive backoff (120-600s). It shows a full report on the first run,
then delta-only on subsequent polls so only new events surface.

## CRITICAL: always use run_in_background: true

Run the script via the Bash tool with `run_in_background: true`. **Never use `&`** to
background it in the shell — that detaches the process and makes the exit code invisible.

With `run_in_background: true`, the platform tracks the process and sends a
`<task-notification>` when it exits. Read the output file from the notification to
see the full report and exit code, then act on it.

```bash
# Bash tool call — set run_in_background: true
bash .claude/scripts/poll-pr.sh $ARGUMENTS --team-reviewer downstream-team
```

The script sleeps and polls on its own. Do not interrupt it. When it exits, you will
be notified automatically.

## Exit codes — what to do when notified

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All checks pass | Ready to merge |
| 1 | CI failures | Fix code, push, re-run (background again) |
| 2 | Checks pending | Should not exit 2 unless --max-polls hit; re-run |
| 3 | Inline review comments | Address comments, push, re-run (background again) |
| 4 | Awaiting human review | Reviewers notified; CronCreate to re-poll later |

## Exit 4 — schedule a re-poll cron

When the script exits 4, it has already posted a comment and requested reviewers.
Use CronCreate to check back automatically:

```
CronCreate: every 2 hours, /poll $ARGUMENTS
```

Delete the cron (CronDelete) once the PR is approved or merged.

## Exit 1 — CI failures

| CI Job | Fix |
|--------|-----|
| Format / Pre-commit | `pre-commit run --all-files` |
| Unit tests | Run failing test locally, fix code |
| Types (mypy) | Fix type annotations |
| Registry tests | `make registry-test` locally |
| Cypress/Playwright | `cd web && npm run test:e2e` |
| PR Lint | Fix PR title regex |

After fixing: push, then re-run the script via Bash with `run_in_background: true`.

## Exit 3 — inline review comments

Run `--once --full` to see comments with reply/resolve commands:

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS --once --full
```

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

Steps:
1. Read all inline comments (reply command + resolve command shown per thread)
2. Fix the code or reply with rationale, then resolve the thread via GraphQL
3. Push and re-run the script via Bash with `run_in_background: true`

## Push and re-run

```bash
git add -A && git commit -m "type(scope): address feedback"
git push fork <branch>
# then re-run poll via Bash tool with run_in_background: true
```

Repeat until exit 0.
