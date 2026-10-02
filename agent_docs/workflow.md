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

- **Target Version** (customfield_10855) holds exactly one version: `.0`
  means master (e.g. `quay-v3.19.0`), `quay-vX.Y.z` means `redhat-X.Y`
- The list of releases to backport to is **fixVersions**, mapped like Target
  Version above (`quay-vX.Y.z` → `redhat-X.Y`; drop `.0` — master already has
  the change), skipping the sync check's master-synced branch even if named.
- For a PROJQUAY-titled PR, fire the cascade with `/jira backport <branch>`,
  one branch per comment; for a NO-ISSUE or QUAYIO-titled PR, use
  `/cherrypick <branch>`, also one branch per comment. To skip over an
  intermediate branch, `/jira backport` a comma-separated list naming every
  branch from the current PR down to the target — this also clones the
  skipped branch's ticket, which a human then sets to Won't Do. `/cherrypick`
  has no such form: skip a branch by firing `/cherrypick <target>` alone on
  the last merged PR. See `agent_docs/backports.md` for the cascade order

### Release Branch Model

Branch facts go stale every release. Verify before backporting instead of
trusting the snapshot below.

- The newest `redhat-*` branch is kept in sync with `master` — do **not**
  cherry-pick to it. Identify and confirm it:
  ```
  git fetch upstream --prune
  git branch -r --list 'upstream/redhat-*' | sed 's|.*upstream/||' | sort -V | tail -1
  git rev-list --left-right --count upstream/<branch>...upstream/master  # "0  0" == synced
  ```
  As of 2026-09-20 that branch is `redhat-3.19`. `redhat-3.18` is a normal
  release branch and **does** take cherry-picks.
- For which older branches are still maintained, check recent activity
  rather than a hardcoded range:
  ```
  git log --oneline --since='3 months ago' upstream/<branch> ^upstream/master
  ```
  Read the tier off the subjects: a `feat` subject means regular backports;
  fixes/CVE/dependency/changelog only means critical/security fixes only; no
  commits means dormant. The lifecycle API is the authoritative tier check,
  not this heuristic:
  ```
  curl -s 'https://access.redhat.com/product-life-cycles/api/v1/products?name=Red%20Hat%20Quay' | jq -c '.data[].versions[] | {name, type}'
  ```
  As of 2026-09-25: `redhat-3.17`/`redhat-3.18` (Full Support) take regular
  backports; `redhat-3.15`/`redhat-3.16` (Maintenance Support) take only
  critical/important security fixes and urgent or selected high-priority bug
  fixes; `redhat-3.9`, `redhat-3.10`, `redhat-3.12`, `redhat-3.13`,
  `redhat-3.14` receive critical/security fixes only; `redhat-3.11` is
  dormant.
- When backporting, target the branches fixVersions names: map
  `quay-vX.Y.z` → `redhat-X.Y`, drop `.0` (master has it already), then skip
  the master-synced branch identified above.
- CodeRabbit auto-review is intentionally scoped to `master` only — it is
  not enabled for `redhat-*` branches. Backport/cherry-pick PRs carry code
  already reviewed on `master`, so re-running review on the release branch
  was evaluated and rejected as unnecessary noise (see PR #6894). Do not
  re-propose adding `base_branches` for `redhat-*` in `.coderabbit.yaml`
  without first revisiting this decision explicitly.

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
| **openshift-ci-robot** | JIRA lifecycle plugin | Validates ticket refs, transitions status (ASSIGNED→POST→MODIFIED), supports `/cherrypick` and `/jira backport` for backports |
| **coderabbitai[bot]** | AI code review | Runs 7 pre-merge checks with `chill` profile. Flags are generally valid — fix or reply with rationale |
| **codecov[bot]** | Coverage reporting | Reports coverage diffs. Project baseline ~72% |
| **github-actions[bot]** | CI results | Playwright reports, Surge preview links |

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
| Playwright | `cd web && pnpm run test:e2e` |
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

## Modifying sentinel.yaml Routing

`.github/workflows/sentinel.yaml` maps changed file paths to CI workflow
triggers. Every filter change is a potential coverage gap: an exclusion that
diverts a path away from an existing filter also silently removes whatever CI
jobs that filter triggered.

**Checklist — required when adding or changing a filter:**

1. **Map new filters to CI workflows.**
   For each new `change filter` added to the `detect-changes` job, explicitly
   list which CI workflows will run when that filter matches. Confirm the list
   covers type checking, unit tests, and any security scans that must apply to
   the new path.

2. **Verify excluded paths still receive equivalent coverage.**
   For each exclusion rule added to an existing filter (a line starting with
   `!`), identify every CI job the original filter would have triggered for
   files in the excluded path. Then confirm those jobs are still triggered
   through a separate route. The minimum required coverage for any Python or
   Go path is:
   - **Type checking** (mypy / go vet / golangci-lint)
   - **Unit tests**
   - **Security / lint scans** (where applicable)

3. **Add a coverage route before merging if one is missing.**
   If step 2 reveals that the excluded path has no equivalent route for any
   required check, add the route in the same PR before merging. Do not defer
   coverage gaps to follow-up issues.

4. **Document coverage routing in the PR description.**
   Include a brief table or list in the PR body enumerating:
   - Each filter added or modified
   - Each CI workflow the filter routes to (or routes away from)
   - For exclusions: the alternative route that preserves coverage

**Background:** PR #7110 added `ci-generator/` and excluded it from the
`python` filter without routing generator-only changes through `ci-python.yaml`
(mypy). The type annotation gap was only discovered post-merge. PR #7131
closed the gap by adding a `types-only` input to `ci-python.yaml` and routing
generator-only changes through it via a combined condition in `sentinel.yaml`.

## Backport Process

After a PR merges to master, if it needs to land on a release branch (a
PROJQUAY/QUAYIO ticket with fixVersions naming one, or a NO-ISSUE PR whose
change a release branch carries):

1. Run the sync check from Release Branch Model to confirm the target
   branch isn't the master-synced branch — do not cherry-pick to it
2. Post `/jira backport <branch>` as a comment on the merged PR for a
   PROJQUAY-titled PR, or `/cherrypick <branch>` for a NO-ISSUE or
   QUAYIO-titled PR — one branch per comment; to skip an intermediate
   branch, `/jira backport` a comma-separated list naming every branch from
   the current PR down to the target instead — this also clones the skipped
   branch's ticket, which a human then sets to Won't Do. `/cherrypick` has no
   such form: skip a branch by firing `/cherrypick <target>` alone on the
   last merged PR
3. `openshift-ci-robot` (via the cherrypick plugin) creates a new PR against the release branch
4. The JIRA lifecycle plugin clones on a successful `/cherrypick` apply only;
   `/jira backport` clones first, before any apply is attempted
5. Monitor the backport PR for CI results

For predecessor surveys, the cascade order, bot failures and manual ports, follow `agent_docs/backports.md`.
