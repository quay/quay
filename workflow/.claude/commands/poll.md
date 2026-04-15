---
allowed-tools: Bash(bash:*), Bash(git:*), Bash(gh:*), Bash(curl:*), Bash(jq:*), Bash(make:*), Bash(pytest:*), Bash(pre-commit:*), Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
argument-hint: PR_NUMBER
description: Poll a PR for CI results and CodeRabbit feedback, then act on issues
---

# Poll PR and Act on Feedback

Poll PR #$ARGUMENTS for GitHub Actions CI, CodeRabbit review, and human reviews. Fix any issues found.

## Step 1: Run Poll Script

```bash
bash workflow/scripts/poll-pr.sh $ARGUMENTS
```

The script checks: GitHub Actions CI, CodeRabbit review, Codecov, and human reviews.

## Step 2: Act on CI Failures

| CI Job | Common Fix |
|--------|------------|
| Format / Pre-commit | `pre-commit run --all-files` |
| Unit tests | Run failing test locally, fix code |
| Types (mypy) | Fix type annotations |
| Registry tests | `make registry-test` locally |
| Cypress/Playwright | `cd web && npm run test:e2e` |
| PR Lint | Fix PR title to match required regex |

## Step 3: Act on CodeRabbit Feedback

CodeRabbit runs with profile `chill` and performs 7 pre-merge checks (see `.coderabbit.yaml`):

| Check | What It Validates |
|-------|-------------------|
| Title check | PR title starts with PROJQUAY-XXXX or NO-ISSUE |
| Description check | Description is relevant to changes |
| Docstring Coverage | >= 80% docstring coverage on changed functions |
| Migration Safety at Scale | No unsafe operations on large tables |
| Migration Downgrade Exists | Every Alembic migration has a real `downgrade()` |
| N+1 Query Prevention | No new loop-based query patterns |
| Read Path Performance | No latency regressions on v2 registry read path |

When CodeRabbit flags an issue:
1. Read the specific comment
2. Determine if it's actionable (in `chill` mode, flags are generally valid)
3. Fix the code or reply explaining why you disagree
4. Push fixes and re-poll

## Step 4: Push Fixes and Re-poll

After fixing issues:

```bash
git add -A && git commit -m "fix: address review feedback (PROJQUAY-XXXX)"
git push
bash workflow/scripts/poll-pr.sh $ARGUMENTS
```

Repeat until all CI checks pass, CodeRabbit checks pass, coverage is maintained, and human review is approved.
