---
name: poll
description: >
  Stateful PR poller: tracks GitHub Actions CI, CodeRabbit, Codecov, and human
  reviews across polls. Loops with adaptive backoff by default; use --once for
  a single status snapshot. Exits with a specific code so the agent knows
  exactly what action to take next.
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
---

# Poll PR and Act on Feedback

Poll PR #$ARGUMENTS for CI, CodeRabbit, and human review status, then fix what's broken.

The script manages its own state in `.claude/poll-state/pr-$ARGUMENTS.json` and loops
with adaptive backoff. It shows a full report on the first run, then delta-only on
subsequent polls so only new events surface.

## Exit codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All checks pass | Ready to merge |
| 1 | CI failures | Fix code, push, re-run |
| 2 | Checks pending | Script is still looping; wait |
| 3 | CodeRabbit inline comments | Address comments, push, re-run |
| 4 | Awaiting human review | Reviewers notified; schedule a re-poll cron |

## Step 1: Start polling

Specify reviewers to notify when CI is clean and the PR is ready:

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS --reviewer jbpratt
```

For a team (once the team exists):

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS --team-reviewer downstream-team
```

The script loops with adaptive backoff (120-600s) while CI is pending, then exits when action is needed:
- **Exit 0**: Everything passes — done.
- **Exit 1**: CI failures — needs a fix.
- **Exit 3**: Inline review comments — needs your attention.
- **Exit 4**: Awaiting human review — reviewers notified.

For a single snapshot without looping (e.g. to check status mid-fix):

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS --once
```

For a complete report instead of delta-only output:

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS --once --full
```

## Step 1b: If exit 4 — schedule a re-poll cron

When the script exits 4 (awaiting review), it has already posted a comment and requested reviewers. Use CronCreate to check back automatically:

```
CronCreate: every 2 hours, run: bash .claude/scripts/poll-pr.sh $ARGUMENTS --reviewer jbpratt
```

Delete the cron (CronDelete) once the PR is merged or approved.

## Step 2: Act on CI Failures (exit code 1)

| CI Job | Fix |
|--------|-----|
| Format / Pre-commit | `pre-commit run --all-files` |
| Unit tests | Run failing test locally, fix code |
| Types (mypy) | Fix type annotations |
| Registry tests | `make registry-test` locally |
| Cypress/Playwright | `cd web && npm run test:e2e` |
| PR Lint | Fix PR title regex |

## Step 3: Act on CodeRabbit Feedback (exit code 3)

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
1. Run `--once --full` to see all inline comments
2. Assess each: in `chill` mode, flags are generally valid
3. Fix the code or reply with rationale
4. Push and restart polling

## Step 4: Push and re-poll

```bash
git add -A && git commit -m "type(scope): address feedback (PROJQUAY-XXXX)"
git push
bash .claude/scripts/poll-pr.sh $ARGUMENTS
```

State is preserved across runs -- the next poll will show only what changed since the last run.

Repeat until exit 0.
