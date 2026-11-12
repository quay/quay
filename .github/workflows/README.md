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

## Prow after CI

`prow-after-ci.yaml` runs when `CI` succeeds on a pull request to an enrolled base (`master`). It never checks out PR code. For the PR's current HEAD it:

1. Comments `/pipeline remaining` once, so the openshift-ci pipeline controller dispatches second-stage Prow jobs and completes `ci/pipeline-gate`.
2. Publishes the `ci/quay-deps-prow` check: success when the PR changes none of `requirements.txt`, `requirements-build.txt`, `constraints.txt`, `pyproject.toml`; otherwise it waits for `ci/prow/gcp-gcs` and mirrors its result, failing after 5 hours without one. The check does not follow a later `/retest`: once `ci/prow/gcp-gcs` passes, re-run the `Prow After CI` workflow to update it.

Logic and tests live in `.github/scripts/prow-after-ci.py` and `test_prow_after_ci.py`.

## GitHub UI

Each reusable workflow appears as a single collapsible job. Click through to see individual sub-job results.

## Re-running failed jobs

Use **"Re-run failed jobs"** (not "Re-run all jobs") to avoid re-running already-passed workflows.
