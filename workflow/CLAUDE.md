# Quay Development Workflow

Full-lifecycle development workflow for Project Quay: from JIRA ticket to merged PR.

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

When given a JIRA ticket key (e.g., `PROJQUAY-1234`):

1. **Fetch ticket details:**
   ```bash
   bash scripts/jira-ops.sh view PROJQUAY-1234
   ```

2. **Assign the ticket to yourself** (if not already assigned):
   ```bash
   bash scripts/jira-ops.sh assign PROJQUAY-1234
   ```

3. **Check Target Version:**
   ```bash
   bash scripts/jira-ops.sh check-version PROJQUAY-1234
   ```
   - If "Target Version" is set (e.g., `quay-v3.18.0` or `z-stream`), note that backporting will be required after merge.
   - Save this context for the `/backport` phase.

4. **Transition ticket to "In Progress":**
   ```bash
   bash scripts/jira-ops.sh transition PROJQUAY-1234 "In Progress"
   ```

### 1.2 Branch Setup

Create a feature branch from `master`:

```bash
git checkout master && git pull origin master
git checkout -b PROJQUAY-1234-short-description
```

Branch naming: `PROJQUAY-<number>-<kebab-case-description>`

### 1.3 Context Loading

Read the relevant AGENTS.md documentation based on what the ticket involves:

| If the ticket involves... | Read... |
|---------------------------|---------|
| API endpoints, auth | `agent_docs/api.md` |
| Database models, migrations | `agent_docs/database.md` |
| Testing | `agent_docs/testing.md` |
| Architecture overview | `agent_docs/architecture.md` |
| Global readonly superuser | `agent_docs/global_readonly_superuser.md` |
| Local dev setup | `agent_docs/development.md` |
| React frontend | `web/AGENTS.md` |

---

## Phase 2: Code (`/code`)

### 2.1 Implementation

Follow the conventions from `AGENTS.md`:

**Python Backend:**
- Flask-based REST API in `endpoints/api/` (v1) and `endpoints/v2/` (OCI registry)
- SQLAlchemy models in `data/model/`
- Alembic migrations in `data/migrations/versions/`
- Background workers in `workers/`

**React Frontend:**
- React 18, TypeScript, PatternFly 5 in `web/src/`
- Use `useSuspenseQuery` for data fetching (not `useQuery` with loading states)
- Follow the Component -> Hook -> Resource -> Axios -> API data flow
- No Recoil for new code (use React Query + Context API)

**Universal Rules:**
1. Always run relevant tests before committing
2. Rely on pre-commit hooks for formatting
3. Never commit credentials or API keys
4. Follow existing import ordering patterns
5. Use exception types from `endpoints/exception.py`
6. For Alembic migrations: **always** run `alembic revision -m "description"` to scaffold -- never hand-craft revision IDs

### 2.2 Pre-Commit Quality Checks

The project uses `pre-commit` with hooks defined in `.pre-commit-config.yaml`. Ensure hooks are installed:

```bash
make install-pre-commit-hook
# or: pre-commit install
```

Pre-commit runs automatically on `git commit`. To run manually before committing:

```bash
# Run on staged files
bash scripts/format-and-lint.sh

# Run on all files
bash scripts/format-and-lint.sh --all-files

# Run a specific hook
bash scripts/format-and-lint.sh --hook black
```

The pre-commit config includes:
- **gitleaks** -- secret detection
- **Black** (line-length=100, target-version=py39) -- Python formatting
- **isort** (profile=black) -- import sorting
- **config-files-check** -- validates config file changes
- **no-new-cypress-tests** -- blocks new Cypress tests (use Playwright)
- **requirements-build-sync** -- checks requirements-build.txt is updated
- **ESLint** -- for `web/` JavaScript/TypeScript files
- **trailing-whitespace** and **end-of-file-fixer**

Fix any issues before proceeding. Some hooks (Black, isort, ESLint) auto-fix files -- re-stage and commit.

### 2.3 Testing

Run tests based on what changed:

```bash
# Python unit tests (single file)
TEST=true PYTHONPATH="." pytest path/to/test.py -v

# All unit tests
make unit-test

# Registry protocol tests
make registry-test

# Type checking
make types-test

# Frontend tests
cd web && npm test

# Playwright E2E (new tests)
cd web && npm run test:e2e
```

**Important:** New Cypress tests are blocked by pre-commit hook. Use Playwright for new E2E tests.

### 2.4 Commit

Commit messages must follow the project convention:

```
<subsystem>: <what changed> (PROJQUAY-####)

<why this change was made>
```

Example:
```
endpoints: add pagination to tag listing API (PROJQUAY-1234)

Large repositories with thousands of tags caused timeouts on the
tag listing endpoint. Added cursor-based pagination with a default
page size of 100.
```

---

## Phase 3: Pull Request (`/pr`)

### 3.1 Validate PR Title

The PR title **must** match this regex (enforced by CI):

```
^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
```

Valid examples:
- `PROJQUAY-1234: fix(api): add pagination to tag listing`
- `PROJQUAY-1234: feat(web): add mirror config page`
- `NO-ISSUE: chore: update dependencies`
- `[redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination`

Validate before creating:
```bash
bash scripts/validate-pr-title.sh "PROJQUAY-1234: fix(api): add pagination to tag listing"
```

### 3.2 PR Description

Use the template at `templates/pr-description.md`. Fill in all sections:

```bash
cat templates/pr-description.md
```

The description must include:
- **Summary** -- bullet points of what changed
- **Root Cause** (for bugs) or **Rationale** (for features)
- **Changes** -- technical details of what was modified
- **Test Plan** -- checkboxes for manual and automated verification
- **JIRA** -- link to the ticket

### 3.3 Create the PR

```bash
gh pr create \
  --title "PROJQUAY-1234: type(scope): description" \
  --body "$(cat /tmp/pr-body.md)" \
  --base master
```

### 3.4 Post-PR JIRA Bot Interaction

After PR creation, the **openshift-ci-robot** (JIRA Lifecycle Plugin) will:
- Validate the JIRA reference in the PR title
- Check that the ticket targets the correct version
- Transition the ticket status from IN PROGRESS to POST
- Apply labels like `jira/valid-reference`

If the bot reports issues:
- `/jira refresh` -- force re-check of JIRA reference
- Fix the PR title if the format is wrong
- Update the JIRA ticket's "Target Version" if needed

---

## Phase 4: Poll & Act (`/poll`)

This is the core feedback loop. Run the poll script to check PR status:

```bash
bash scripts/poll-pr.sh <PR_NUMBER>
```

The script checks:
1. **GitHub Actions status** -- all CI workflow runs
2. **CodeRabbit review** -- AI review comments and pre-merge checks
3. **Codecov** -- coverage report
4. **Human reviews** -- approval status

### 4.1 Acting on CI Failures

When CI fails, diagnose and fix:

| CI Job | What It Checks | Common Fixes |
|--------|---------------|--------------|
| Format (Black) | Python formatting | Run `pre-commit run black --all-files` |
| Format (Flake8) | Linting | Fix reported issues; run `flake8` locally |
| Pre-commit | All pre-commit hooks | Run `pre-commit run --all-files` |
| Unit tests | Python unit tests | Run failing test locally, fix code |
| Types (mypy) | Type checking | Fix type annotations |
| Registry tests | OCI/Docker protocol | Run `make registry-test` locally |
| Cypress/Playwright | Frontend E2E | Run `cd web && npm run test:e2e` |
| PR Lint | Title format | Fix PR title to match required regex |

### 4.2 Acting on CodeRabbit Feedback

CodeRabbit runs with profile `chill` and performs these pre-merge checks:

| Check | What It Validates |
|-------|-------------------|
| Title check | PR title starts with PROJQUAY-XXXX or NO-ISSUE |
| Description check | Description is relevant to changes |
| Docstring Coverage | >= 80% docstring coverage on changed functions |
| Migration Safety at Scale | No unsafe operations on large tables (Manifest, ManifestBlob, Tag, ImageStorage = 100M+ rows) |
| Migration Downgrade Exists | Every Alembic migration has a real `downgrade()` |
| N+1 Query Prevention | No new loop-based query patterns in `data/model/`, `endpoints/`, `workers/` |
| Read Path Performance | No latency regressions on v2 registry read path (98% of traffic) |

**Path-specific review instructions CodeRabbit follows:**
- `data/migrations/versions/` -- extreme care for production safety, checks for table locks, NOT NULL without defaults, missing CONCURRENTLY
- `data/model/` -- query performance, N+1, missing indexes, full table scans
- `endpoints/` -- pagination, timeouts, caching, input validation, security
- `workers/` -- resource safety, rate limiting, error handling, streaming

When CodeRabbit flags an issue:
1. Read the specific comment
2. Determine if it's actionable (CodeRabbit is in `chill` mode, so flags are generally valid)
3. Fix the code if the suggestion is correct
4. If you disagree, leave a reply explaining why
5. Push fixes and re-poll

### 4.3 Acting on Codecov

Codecov reports coverage at ~72% for the project. Aim to maintain or improve coverage:
- Don't reduce project coverage
- Add tests for new code paths
- The coverage flag is `unit`

### 4.4 Poll Loop

After fixing issues, push and re-poll:

```bash
git add -A && git commit -m "fix: address review feedback (PROJQUAY-1234)"
git push
bash scripts/poll-pr.sh <PR_NUMBER>
```

Repeat until:
- All CI checks pass (green)
- CodeRabbit pre-merge checks pass
- Coverage is maintained
- Human review is approved

---

## Phase 5: CI Quick Check (`/ci`)

For a quick status check without the full poll:

```bash
bash scripts/check-ci.sh <PR_NUMBER>
```

This shows a summary table of all workflow runs and their status.

---

## Phase 6: Backport (`/backport`)

After a PR is merged to `master`, check if backporting is needed:

1. **Check Target Version** on the JIRA ticket:
   ```bash
   bash scripts/jira-ops.sh check-version PROJQUAY-1234
   ```

2. **If backporting is required**, comment on the merged PR:
   ```bash
   gh pr comment <PR_NUMBER> --body "/cherrypick redhat-3.12"
   ```

3. The `openshift-cherrypick-robot` will create a new PR against the release branch.

4. The JIRA lifecycle plugin will clone the parent ticket for the target release.

5. Review and merge the cherry-pick PR.

---

## Phase 7: JIRA Updates (`/jira`)

Check or update a JIRA ticket:

```bash
# View ticket
bash scripts/jira-ops.sh view PROJQUAY-1234

# Assign to self
bash scripts/jira-ops.sh assign PROJQUAY-1234

# Check/set target version
bash scripts/jira-ops.sh check-version PROJQUAY-1234
bash scripts/jira-ops.sh set-version PROJQUAY-1234 "quay-v3.18.0"

# Transition status
bash scripts/jira-ops.sh transition PROJQUAY-1234 "In Progress"
bash scripts/jira-ops.sh transition PROJQUAY-1234 "Code Review"
```

---

## Hook Recommendations

These Claude Code hooks can be configured in `.claude/settings.json` to automate quality enforcement. See `claude-settings-recommended.json` for the full config.

### Pre-commit Hook (ensures hooks are installed before commit)

Git's pre-commit hooks run automatically on `git commit` if installed. This Claude hook ensures they stay installed:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c '...if git commit detected, ensure pre-commit install...'",
            "timeout": 15,
            "_comment": "pre-commit runs automatically on commit; this just ensures hooks are installed"
          }
        ]
      }
    ]
  }
}
```

The project's `.pre-commit-config.yaml` handles all formatting and linting automatically on commit. If a hook fails, the commit is blocked -- fix the issues (some hooks auto-fix), re-stage, and commit again.

### PR Title Validation Hook

Validates PR title format before `gh pr create` to avoid CI failures on the Pull Request Lint workflow.

### Embargo Check Hook (from upstream)

The existing embargo check hook from the Quay repo (`.claude/scripts/check-embargo.sh`) blocks processing of embargoed JIRA tickets.

---

## Project Context

### Critical Tables (100M+ rows in production)

| Table | Row Count | Impact |
|-------|-----------|--------|
| Manifest | 100M+ | CRITICAL |
| ManifestBlob | 100M+ | CRITICAL |
| Tag | 100M+ | CRITICAL |
| ImageStorage | 100M+ | CRITICAL |
| User | Millions | HIGH |
| Repository | Millions | HIGH |

**Traffic pattern:** 98% reads (image pulls), 2% writes (pushes)

### Formatting & Linting (via pre-commit)

All formatting and linting is managed by `pre-commit` (`.pre-commit-config.yaml`). Install once:

```bash
make install-pre-commit-hook  # or: pre-commit install
```

Hooks run automatically on every `git commit`. To run manually: `pre-commit run --all-files`

**Configured hooks:**
1. `gitleaks` -- secret detection
2. `black` -- Python formatting
3. `isort` -- import sorting
4. `config-files-check` -- validates config file changes
5. `no-new-cypress-tests` -- blocks new Cypress tests (use Playwright)
6. `requirements-build-sync` -- checks requirements-build.txt is updated
7. `eslint` -- JavaScript/TypeScript linting for `web/`
8. `trailing-whitespace` -- removes trailing whitespace
9. `end-of-file-fixer` -- ensures files end with newline

### CI Workflows (key ones)

| Workflow | Trigger | What It Does |
|----------|---------|--------------|
| CI | push/PR | Format, pre-commit, unit tests, types, e2e, registry, Cypress, MySQL, PostgreSQL |
| Pull Request Lint | PR open/edit | Validates PR title regex |
| PR Auto-Labeler | PR | Applies area labels |
| Web CI | PR | Frontend tests |
| Playwright E2E | PR | Browser E2E tests |
| OCI Distribution Spec | push/PR | OCI conformance tests |
| CodeQL | scheduled | Security scanning |

### Bot Ecosystem

| Bot | What It Does |
|-----|--------------|
| **openshift-ci-robot** | JIRA lifecycle: validates ticket refs, transitions status, supports `/cherrypick` |
| **coderabbitai[bot]** | AI code review with 7 custom pre-merge checks |
| **codecov[bot]** | Coverage reports and diffs |
| **github-actions[bot]** | Cypress results, Playwright reports, Surge previews |

---

## Improvement Suggestions

Areas where the Quay project could benefit from additional automation:

1. **Auto-assign JIRA on branch push** -- Hook that assigns the JIRA ticket when a branch with `PROJQUAY-XXXX` in the name is pushed.

2. **Pre-push migration chain check** -- Hook that verifies Alembic migration `down_revision` matches the current head before pushing, preventing multiple-head conflicts.

3. **Automatic coverage gate** -- Hook that blocks commits if new Python files have < 80% test coverage.

4. **Stale PR reminder** -- Scheduled workflow that comments on PRs older than 7 days without activity.

5. **Auto-backport on merge** -- When a merged PR's JIRA ticket has "Target Version" set, automatically trigger `/cherrypick` for the corresponding release branch.

6. **Local pre-push hook** -- Run `make types-test` before pushing to catch mypy errors early rather than waiting for CI.
