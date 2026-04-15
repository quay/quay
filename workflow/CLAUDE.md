# Quay Development Workflow

Full-lifecycle development workflow for Project Quay: from JIRA ticket to merged PR.

## Session Setup

On first use, install the recommended Claude Code hooks:

```bash
cp workflow/claude-settings-recommended.json .claude/settings.json
```

This activates: embargo check, pre-commit install guard, and PR title validation.
If `.claude/settings.json` already exists, merge the `"hooks"` key instead of overwriting.

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/start <PROJQUAY-XXXX>` | Begin work on a JIRA ticket |
| `/code` | Implement changes following Quay conventions |
| `/pr` | Create a PR with correct format and JIRA reference |
| `/poll <PR#>` | Poll PR for CodeRabbit + GitHub Actions, then act on feedback |
| `/ci <PR#>` | Quick CI status check |
| `/backport <PR#> <branch>` | Trigger cherry-pick for backporting |
| `/jira <PROJQUAY-XXXX>` | Check/update JIRA ticket status |

---

## Phase 1: Start (`/start`)

### 1.1 JIRA Ticket Setup

```bash
bash scripts/jira-ops.sh view PROJQUAY-1234
bash scripts/jira-ops.sh assign PROJQUAY-1234
bash scripts/jira-ops.sh check-version PROJQUAY-1234
bash scripts/jira-ops.sh transition PROJQUAY-1234 "ASSIGNED"
```

- If "Target Version" is set, note that backporting will be required after merge.
- Valid transitions: `New`, `ASSIGNED`, `POST`, `ON_QA`, `Verified`, `Release Pending`, `Closed`, `MODIFIED`

**Note:** Write operations (assign, transition, set-version) require `JIRA_USER` (email) and `JIRA_API_TOKEN` env vars. Read operations work without auth.

### 1.2 Branch Setup

```bash
git checkout master && git pull origin master
git checkout -b PROJQUAY-1234-short-description
```

Branch naming: `PROJQUAY-<number>-<kebab-case-description>`

### 1.3 Context Loading

Read the relevant documentation for the ticket's area. See the **"Documentation by Task"** table in `@AGENTS.md` for the full mapping (api.md, database.md, testing.md, etc.).

---

## Phase 2: Code (`/code`)

### 2.1 Implementation

Follow `@AGENTS.md` conventions and read the relevant `agent_docs/` file for the area you're working in. For React frontend work, see `web/AGENTS.md`.

### 2.2 Quality Checks

Pre-commit hooks handle formatting and linting automatically on `git commit`. To run manually:

```bash
bash scripts/format-and-lint.sh            # staged files
bash scripts/format-and-lint.sh --all-files # all files
```

See `@AGENTS.md` for test commands (`make unit-test`, `make registry-test`, `make types-test`, etc.).

### 2.3 Commit

```
<subsystem>: <what changed> (PROJQUAY-####)

<why this change was made>
```

See `.github/CONTRIBUTING.md` for full commit message conventions.

---

## Phase 3: Pull Request (`/pr`)

### 3.1 PR Title Format

The PR title **must** match this regex (enforced by CI):

```
^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
```

Examples:
- `PROJQUAY-1234: fix(api): add pagination to tag listing`
- `NO-ISSUE: chore: update dependencies`
- `[redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination`

Validate before creating:
```bash
bash scripts/validate-pr-title.sh "PROJQUAY-1234: fix(api): add pagination to tag listing"
```

### 3.2 PR Description

Use the template at `templates/pr-description.md`. Fill in: Summary, Root Cause/Rationale, Changes, Test Plan, JIRA link, and Backport status.

### 3.3 Create the PR

```bash
gh pr create \
  --title "PROJQUAY-1234: type(scope): description" \
  --body "$(cat /tmp/pr-body.md)" \
  --base master
```

### 3.4 Post-PR Bot Interactions

After PR creation, **openshift-ci-robot** (JIRA Lifecycle Plugin) will:
- Validate the JIRA reference in the PR title
- Check that the ticket targets the correct version
- Transition the ticket status from ASSIGNED to POST
- Apply labels like `jira/valid-reference`

If the bot reports issues: `/jira refresh`, fix the PR title, or update the JIRA ticket's "Target Version".

---

## Phase 4: Poll & Act (`/poll`)

The core feedback loop. Run the poll script to check PR status:

```bash
bash scripts/poll-pr.sh <PR_NUMBER>
```

The script checks: GitHub Actions CI, CodeRabbit review, Codecov, and human reviews.

### 4.1 Acting on CI Failures

| CI Job | Common Fix |
|--------|------------|
| Format / Pre-commit | `pre-commit run --all-files` |
| Unit tests | Run failing test locally, fix code |
| Types (mypy) | Fix type annotations |
| Registry tests | `make registry-test` locally |
| Cypress/Playwright | `cd web && npm run test:e2e` |
| PR Lint | Fix PR title to match required regex |

### 4.2 Acting on CodeRabbit Feedback

CodeRabbit runs with profile `chill` and performs 7 pre-merge checks (see `.coderabbit.yaml` for full config):

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

### 4.3 Poll Loop

After fixing issues, push and re-poll:

```bash
git add -A && git commit -m "fix: address review feedback (PROJQUAY-1234)"
git push
bash scripts/poll-pr.sh <PR_NUMBER>
```

Repeat until all CI checks pass, CodeRabbit checks pass, coverage is maintained, and human review is approved.

---

## Phase 5: CI Quick Check (`/ci`)

```bash
bash scripts/check-ci.sh <PR_NUMBER>
```

---

## Phase 6: Backport (`/backport`)

After a PR is merged to `master`, check if backporting is needed:

```bash
bash scripts/jira-ops.sh check-version PROJQUAY-1234
```

If Target Version is set, trigger the cherry-pick bot:

```bash
gh pr comment <PR_NUMBER> --body "/cherrypick redhat-3.12"
```

The `openshift-cherrypick-robot` creates a new PR against the release branch. The JIRA lifecycle plugin clones the parent ticket for the target release.

---

## Phase 7: JIRA Updates (`/jira`)

```bash
bash scripts/jira-ops.sh view PROJQUAY-1234
bash scripts/jira-ops.sh assign PROJQUAY-1234
bash scripts/jira-ops.sh check-version PROJQUAY-1234
bash scripts/jira-ops.sh set-version PROJQUAY-1234 "quay-v3.18.0"
bash scripts/jira-ops.sh transition PROJQUAY-1234 "ASSIGNED"
bash scripts/jira-ops.sh transition PROJQUAY-1234 "POST"
```

---

## Bot Ecosystem

| Bot | Role in PR Lifecycle |
|-----|----------------------|
| **openshift-ci-robot** | JIRA lifecycle: validates ticket refs, transitions status, supports `/cherrypick` |
| **coderabbitai[bot]** | AI code review with 7 custom pre-merge checks |
| **codecov[bot]** | Coverage reports and diffs (~72% project baseline) |
| **github-actions[bot]** | Cypress results, Playwright reports, Surge previews |

---

## Improvement Suggestions

1. **Auto-assign JIRA on branch push** -- assign ticket when branch with `PROJQUAY-XXXX` is pushed
2. **Pre-push migration chain check** -- verify Alembic `down_revision` matches head before push
3. **Auto-backport on merge** -- trigger `/cherrypick` automatically when Target Version is set
4. **Local pre-push hook** -- run `make types-test` before push to catch mypy errors early
