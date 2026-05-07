# Development Workflow

End-to-end process for PROJQUAY/QUAYIO ticketed work: JIRA ticket to merged PR.

## Lifecycle Phases

```
  /start          /code           /pr            /poll           /backport
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌───────────┐
│  JIRA   │──>│  Code   │──>│  Pull   │──>│  Review  │──>│ Backport  │
│  Setup  │   │  & Test │   │ Request │   │  & Fix   │   │ (if needed│
└─────────┘   └─────────┘   └─────────┘   └──────────┘   └───────────┘
 ASSIGNED       ASSIGNED        POST          POST         POST/ON_QA
```

## JIRA Process

### Ticket Lifecycle

| JIRA Status | When | Triggered By |
|-------------|------|--------------|
| New | Ticket created | Reporter |
| ASSIGNED | Work begins | `/start` or manual |
| POST | PR created | openshift-ci-robot on PR creation |
| MODIFIED | PR merged | openshift-ci-robot on merge |
| ON_QA | In QA pipeline | QE team |
| Verified | QA passed | QE team |
| Closed | Released | Release manager |

### Target Version & Backporting

- **Target Version** (customfield_10855) indicates the release this fix targets
- If set, backporting is **required** after merge to master
- Map version to branch: `quay-v3.12.0` → `redhat-3.12`
- Use `/backport <PR#> <branch>` after merge

### Release Branch Model

- `redhat-3.18` is synced with `master` — do **not** cherry-pick to it
- Actively maintained branches: `redhat-3.15` through `redhat-3.17`
- Older branches (`redhat-3.12` through `redhat-3.14`) receive critical/security fixes only
- When backporting, skip `redhat-3.18` and target only the branches older than master

### Auth

- All JIRA REST operations require `JIRA_API_TOKEN`
- `JIRA_USER` defaults to `quay-devel@redhat.com`
- If `acli` is installed, it is preferred and uses its own credentials
- Instance: `https://redhat.atlassian.net`

## PR Conventions

### Title Format (CI-enforced)

```
^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
```

Examples:
- `PROJQUAY-1234: fix(api): add pagination to tag listing`
- `NO-ISSUE: chore: update dependencies`
- `[redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination`

### Commit Message Format

```
<subsystem>: <what changed> (PROJQUAY-####)

<why this change was made>
```

### Branch Naming

```
<type>/projquay-<number>-<kebab-case-description>
```

Where `<type>` matches the PR type: `fix`, `feat`, `test`, `refactor`, `docs`, `chore`.

## Bot Ecosystem

Four bots interact with PRs. Understanding their roles helps respond correctly.

| Bot | Role | Common Actions |
|-----|------|----------------|
| **openshift-ci-robot** | JIRA lifecycle plugin | Validates ticket refs, transitions status (ASSIGNED→POST→MODIFIED), supports `/cherrypick` for backports |
| **coderabbitai[bot]** | AI code review | Runs 7 pre-merge checks with `chill` profile. Flags are generally valid — fix or reply with rationale |
| **codecov[bot]** | Coverage reporting | Reports coverage diffs. Project baseline ~72% |
| **github-actions[bot]** | CI results | Cypress/Playwright reports, Surge preview links |

### CodeRabbit Pre-merge Checks

| Check | What It Validates |
|-------|-------------------|
| Title check | PR title starts with PROJQUAY-XXXX or NO-ISSUE |
| Description check | Description is relevant to changes |
| Docstring Coverage | >= 80% on changed functions |
| Migration Safety at Scale | No unsafe operations on large tables |
| Migration Downgrade Exists | Every Alembic migration has a real `downgrade()` |
| N+1 Query Prevention | No new loop-based query patterns |
| Read Path Performance | No latency regressions on v2 registry read path |

### CI Jobs & Common Fixes

| CI Job | Common Fix |
|--------|------------|
| Format / Pre-commit | `pre-commit run --all-files` |
| Unit tests | Run failing test locally, fix code |
| Types (mypy) | Fix type annotations |
| Registry tests | `make registry-test` locally |
| Cypress/Playwright | `cd web && pnpm run test:e2e` |
| PR Lint | Fix PR title to match regex |

## Session Setup

All hooks are consolidated in `.claude/settings.json` — no manual setup required.

### Hooks by Event

| Event | Hook | Script/Command |
|-------|------|----------------|
| **SessionStart** | Bootstrap + state restore | `session-setup.sh` — acli, pre-commit, gh auth, restores previous session state |
| **UserPromptSubmit** | Embargo check | `check-embargo.sh` — blocks embargoed JIRA tickets |
| **UserPromptSubmit** | JIRA ticket detection | `detect-jira-ticket.sh` — detects PROJQUAY/QUAYIO refs, suggests `/jira` or `/start` |
| **PreToolUse** (Bash) | Embargo check | `check-embargo.sh` — blocks JIRA commands on embargoed tickets |
| **PreToolUse** (git commit) | Pre-commit guard | Ensures `pre-commit install` runs before commit |
| **PreToolUse** (git commit) | Commit message hint | Warns if message doesn't match `<subsystem>: <what> (PROJQUAY-####)` |
| **PreToolUse** (gh pr create) | PR title validation | Blocks if title doesn't match CI-enforced regex |
| **PostToolUse** (gh pr create) | Poll reminder | Suggests `/poll <PR#>` after PR creation |
| **PostToolUse** (git push) | Target Version check | `check-target-version.sh` — warns if JIRA ticket missing Target Version |
| **PreCompact** | State save | `save-session-state.sh` — saves branch/ticket/PR to survive compaction |
| **Stop** | Next-step reminder | `workflow-next-step.sh` — suggests `/pr`, `/poll`, or `/backport` based on state |

## GitHub CLI Notes

- `gh pr edit` may fail with `read:org` scope errors on restricted tokens
- Fallback: use `gh api repos/{owner}/{repo}/pulls/{number} -X PATCH -f title="..." -f body="..."`
- Always verify `gh auth status` at session start

## Backport Process

After a PR merges to master, if the JIRA ticket has a Target Version:

1. Post `/cherrypick <branch>` as a comment on the merged PR
2. `openshift-ci-robot` (via the cherrypick plugin) creates a new PR against the release branch
3. The JIRA lifecycle plugin clones the parent ticket for the target release
4. Monitor the backport PR for CI results
