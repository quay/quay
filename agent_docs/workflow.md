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
^(?:\[(?:redhat|mirror-registry)-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
```

Examples:
- `PROJQUAY-1234: fix(api): add pagination to tag listing`
- `NO-ISSUE: chore: update dependencies`
- `[redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination`
- `[mirror-registry-3.0] PROJQUAY-1234: fix(omr): backport upgrade health check`

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

### Handling openshift-ci-robot Validation Errors

When `openshift-ci-robot` posts a validation comment on a PR you created, act
within the same review session — do not leave it for the human assignee unless
the error type requires human involvement (see below). Parse the comment to
determine the error type, then follow the procedure for that type.

**Recognizing error types**

| Phrase in bot comment | Error type |
|-----------------------|------------|
| "invalid Jira target version" / "target version" | Wrong Target Version |
| "missing release notes" / "release note" | Missing release notes |
| "parent.*MODIFIED" / "parent.*not VERIFIED" / "parent.*not CLOSED" | Dependent-ticket-state error |

**Wrong Target Version**

The ticket's `customfield_10855` (Target Version) is set to the wrong value.
Correct it with a JIRA REST PATCH, then trigger re-validation:

```bash
# Determine expected value from the PR's target branch:
#   master PR           → quay-v<next-minor>.0   (e.g. quay-v5.1.0)
#   redhat-X.Y branch   → quay-vX.Y.<z>          (e.g. quay-v5.0.3)
# The bot comment usually names the expected value explicitly.
TICKET="PROJQUAY-12345"       # from bot comment or PR title
CORRECT_VERSION="quay-v5.1.0" # from bot comment

curl --silent --fail-with-body \
  -X PUT "${JIRA_BASE_URL}/rest/api/2/issue/${TICKET}" \
  -u "${JIRA_USER}:${JIRA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"fields\":{\"customfield_10855\":{\"name\":\"${CORRECT_VERSION}\"}}}"

# Re-validate:
gh pr comment <PR_NUMBER> --body "/jira refresh"
```

If the PUT fails (non-2xx), fall through to the escalation step below.

**Missing release notes**

The ticket is missing release-note content required by the lifecycle plugin.
Set both the release-note type and body fields on the ticket:

```bash
curl --silent --fail-with-body \
  -X PUT "${JIRA_BASE_URL}/rest/api/2/issue/${TICKET}" \
  -u "${JIRA_USER}:${JIRA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "customfield_10073": {"value": "Bug Fix"},
      "customfield_10075": "Brief description of the fix for release notes."
    }
  }'

gh pr comment <PR_NUMBER> --body "/jira refresh"
```

Verify the exact custom-field IDs in the Jira instance before relying on the
values above — they can vary between Jira projects. Use
`GET /rest/api/2/issue/{key}` and inspect the `fields` object to confirm.

**Dependent-ticket-state errors**

When the error states that a parent or blocking ticket is not yet in VERIFIED
or CLOSED state, the agent cannot unilaterally transition it — that requires
QE sign-off. Post a PR comment that names the exact ticket and expected state
so the human assignee can act without inspecting the bot comment:

```bash
gh pr comment <PR_NUMBER> --body "$(cat <<'EOF'
@<assignee> openshift-ci-robot flagged a dependent-ticket-state error:
parent ticket PROJQUAY-XXXXX must be in VERIFIED or CLOSED state before this
PR can be validated. Please work with the QE team to transition it, then
comment \`/jira refresh\` here.
EOF
)"
```

**Jira API failure or missing token**

If any `curl` call above fails, or if `JIRA_API_TOKEN` is absent, post a PR
comment that names the exact field and expected value so a human can fix it
without re-reading the bot comment:

```bash
gh pr comment <PR_NUMBER> --body "$(cat <<'EOF'
openshift-ci-robot posted a Jira validation error that I could not fix
automatically (Jira API unavailable or token absent).

Manual fix required on PROJQUAY-XXXXX:
- Field: Target Version (customfield_10855)
- Expected value: quay-v5.1.0

After updating, comment \`/jira refresh\` on this PR.
EOF
)"
```

Adjust the field name, customfield ID, and expected value to match the actual
bot error. Tag the PR assignee if one is set.

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
