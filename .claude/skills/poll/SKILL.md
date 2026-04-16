---
name: poll
description: >
  Poll a PR for GitHub Actions CI results, CodeRabbit review feedback, Codecov
  coverage, and human reviews. Identifies failures and acts on them: fixes code,
  responds to review comments, pushes, and re-polls until everything passes.
argument-hint: PR_NUMBER
disable-model-invocation: true
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

Poll PR #$ARGUMENTS for CI, CodeRabbit, and human review status. Fix issues found.

## Step 1: Poll

```bash
bash .claude/scripts/poll-pr.sh $ARGUMENTS
```

## Step 2: Act on CI Failures

| CI Job | Fix |
|--------|-----|
| Format / Pre-commit | `pre-commit run --all-files` |
| Unit tests | Run failing test locally, fix code |
| Types (mypy) | Fix type annotations |
| Registry tests | `make registry-test` locally |
| Cypress/Playwright | `cd web && npm run test:e2e` |
| PR Lint | Fix PR title regex |

## Step 3: Act on CodeRabbit Feedback

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
1. Read the specific comment
2. Assess if actionable (in `chill` mode, flags are generally valid)
3. Fix or reply with rationale
4. Push and re-poll

## Step 4: Push and Re-poll

```bash
git add -A && git commit -m "<subsystem>: <what changed> (PROJQUAY-XXXX)"
git push
bash .claude/scripts/poll-pr.sh $ARGUMENTS
```

Repeat until all CI passes, CodeRabbit passes, coverage holds, and human review approves.
