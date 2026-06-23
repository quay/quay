# CI Workflows

All CI runs through a single **sentinel** gate. Branch protection requires only the `all-green` check.

## How it works

`sentinel.yaml` is the orchestrator. It:
1. Runs `dorny/paths-filter` to detect which file categories changed
2. Calls reusable workflows conditionally (or unconditionally for lint)
3. Aggregates all results with `re-actors/alls-green`

If every expected job passes (or is legitimately skipped), `all-green` passes. If any expected job fails, `all-green` fails.

## File structure

| File | Role | Dependency tiers |
|------|------|-----------------|
| `sentinel.yaml` | Orchestrator + gate (the only required check) | — |
| `ci-lint.yaml` | PR title check, pre-commit | Always runs, no tiers |
| `ci-python.yaml` | Types, Unit, SQLite, PostgreSQL, Registry, OCI Spec | No tiers (all parallel) |
| `ci-go.yaml` | Build → Lint → Test + Schema Drift → E2E Mirror | 4 tiers |
| `ci-web.yaml` | Build Plugin, Vitest, e2e-test-check, Playwright E2E | No tiers |

## Tier gating

**Go:** Build → Lint → Test + Schema Drift → E2E Mirror. Each tier gates the next.

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
