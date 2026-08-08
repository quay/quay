# CI Workflows

All CI runs through a single **sentinel** gate. Branch protection requires only the `all-green` check.

## How it works

`sentinel.yaml` is the orchestrator. It:
1. Runs `dorny/paths-filter` to detect which file categories changed
2. Calls reusable workflows conditionally
3. Aggregates all results with `re-actors/alls-green`

If every expected job passes (or is legitimately skipped), `all-green` passes. If any expected job fails, `all-green` fails.

## File structure

| File | Role |
|------|------|
| `sentinel.yaml` | Orchestrator + gate (the only required check) |
| `ci-python.yaml` | Format, Pre-commit, Unit, SQLite, PostgreSQL, Types, E2E, Registry |
| `ci-go.yaml` | Go Lint, Build, Test, Schema Drift, OCI Conformance, E2E Mirror |
| `ci-web.yaml` | Build Plugin, Vitest, e2e-test-check, Playwright E2E |

## Adding a new always-run job

1. Add the job to the appropriate `ci-*.yaml` file
2. No other changes needed — the sentinel already aggregates the reusable workflow result

## Adding a new path-conditional job

1. Create `ci-foo.yaml` with `on: workflow_call:`
2. In `sentinel.yaml`, add a filter group to `detect-changes`:
   ```yaml
   foo:
     - 'path/to/files/**'
   ```
3. Add the output to `detect-changes.outputs`:
   ```yaml
   foo: ${{ steps.filter.outputs.foo }}
   ```
4. Add the conditional call:
   ```yaml
   foo-ci:
     needs: detect-changes
     if: ${{ needs.detect-changes.outputs.foo == 'true' }}
     uses: ./.github/workflows/ci-foo.yaml
     secrets: inherit
   ```
5. Add `foo-ci` to the sentinel's `needs` list
6. Add to the sentinel's `allowed-skips`:
   ```yaml
   ${{ needs.foo-ci.result == 'skipped' && 'foo-ci,' || '' }}
   ```

## Adding a PR-only job

1. Add `is-pr` input to the reusable workflow if it doesn't have one
2. Use `if: ${{ inputs.is-pr }}` on the job

## GitHub UI

Each reusable workflow appears as a single collapsible job. Click through to see individual sub-job results.

## Re-running failed jobs

Use **"Re-run failed jobs"** (not "Re-run all jobs") to avoid re-running already-passed workflows.

---

## PR Labeling

Three workflows automate PR labels for component tracking, review status, and backport provenance.

### Workflow overview

| File | Trigger | Purpose |
|------|---------|---------|
| `pr-labeler.yaml` | `pull_request_target`, `pull_request_review` | Area labels, community detection, PR data capture |
| `pr-status-labeler.yaml` | `workflow_run` (after PR Auto-Labeler) | Review/merge status labels |
| `label-backported-pr.yml` | PR merged to `redhat-*` | Back-label the original PR |

### Data flow

```text
PR opened/updated ──► pr-labeler.yaml ──► saves PR number artifact
review submitted  ──┘                          │
                        workflow_run trigger ◄──┘
                               │
                               ▼
                      pr-status-labeler.yaml ──► applies status labels
```

`pr-labeler.yaml` fires on both `pull_request_target` (opened, synchronize, reopened) and `pull_request_review` (submitted, dismissed) events. It captures the PR number as a build artifact, then `pr-status-labeler.yaml` consumes it via `workflow_run` completion to apply status labels downstream.

### `pr-labeler.yaml` — PR Auto-Labeler

Three jobs:

- **label-components** — Runs `actions/labeler` with `.github/labeler.yml` to apply `area/*` labels based on changed file paths. Uses `sync-labels: true` so labels are removed when files no longer match.
- **label-community** — Checks if the PR author is a `quay` org public member or listed in `OWNERS`. If neither, adds `community-contribution`. Skips known bots (`openshift-ci[bot]`, `openshift-merge-robot`, `openshift-cherrypick-robot`).
- **capture-pr-data** — Saves the PR number as a build artifact for downstream `workflow_run` consumers.

### `pr-status-labeler.yaml` — PR Event Handler

Triggers on `workflow_run` completion of "PR Auto-Labeler". Single job applying status labels:

| Condition | Label added | Label removed |
|-----------|-------------|---------------|
| `reviewDecision == APPROVED` | `approved` | — |
| `reviewDecision != APPROVED` | — | `approved` |
| `mergeable` non-null AND (`mergeable` is false OR `mergeStateStatus` is DIRTY) | `needs-rebase` | — |
| Otherwise (mergeable and clean) | — | `needs-rebase` |
| Base branch is `redhat-3.x` | `backport/redhat-3.x` | — |
| Base branch changed away from `redhat-3.x` | — | stale `backport/*` |

### `label-backported-pr.yml` — Label Original PR on Backport Merge

Triggers when a PR merges to a `redhat-*` branch. Parses `cherry-pick of #NNNN` from the merged PR body, then adds a `backported/${targetBranch}` label (e.g. `backported/redhat-3.18`) to the original PR. Creates the label with green color if it doesn't exist. Note: these `backported/` labels track completed cherry-picks on the original PR, distinct from the `backport/` labels that `pr-status-labeler.yaml` applies to PRs targeting a release branch.

### `.github/labeler.yml` — area label mappings

| Label | Paths |
|-------|-------|
| `area/api` | `endpoints/api/**` |
| `area/registry` | `endpoints/v1/**`, `endpoints/v2/**` |
| `area/web-ui` | `web/**` |
| `area/config-tool` | `config-tool/**` |
| `area/workers` | `workers/**` |
| `area/build-system` | `buildman/**` |
| `area/storage` | `storage/**` |
| `area/auth` | `auth/**` |
| `area/database` | `data/**` |
| `area/deployment` | `deploy/**` |
| `area/ci` | `.github/workflows/**` |
| `area/docs` | `docs/**`, `**/*.md` |
| `area/tests` | `test/**`, `integration_tests/**` |

To add a new area label, append an entry to `.github/labeler.yml` following the existing pattern.
