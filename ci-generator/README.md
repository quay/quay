# Quay CI config generator

Python generator that reads a compact `matrix.yaml` and writes [ci-operator](https://docs.ci.openshift.org/) config files for each test cell.

Templating is Jinja `{{ variable }}` placeholders only. Conditionals and loops stay in `generate.py`, not in the YAML templates.

Each generated file starts with a `# DO NOT EDIT` header pointing back at `matrix.yaml`, `templates/`, and `generate.py`.

## Setup

```bash
uv sync --extra test
```

## CLI

From this directory (in-tree: `python3 _generator/generate.py`):

```bash
python3 generate.py              # generate all configs
python3 generate.py --dry-run    # preview without writing
python3 generate.py --check      # verify configs are up to date
python3 generate.py --list       # show matrix expansion table (includes KIND and SOURCE columns)
python3 generate.py --output DIR # write or check a specific directory
```

Standalone default output is `./out`. When this directory is named `_generator`, output is the parent directory (`ci-operator/config/quay/quay/` in openshift/release).

`--check` is the CI verification step: exit `1` if any file listed in `managed_files.active` is missing or its parsed YAML differs from what the matrix generates, or if any file listed in `managed_files.retired` still exists in the output directory. Files not listed in either list are ignored entirely, including hand-written neighbours like `quay-quay-master__claim.yaml` and `quay-quay-master__omr-*.yaml`. Content comparison is parsed YAML (comments and `determinize-ci-operator` quoting are ignored).

## `matrix.yaml`

```yaml
version: 2

global_defaults:
  image_source: build  # reserved; templates do not use it yet
  arch: amd64
  repo: quay/quay

managed_files:
  active:
    - quay-quay-master.yaml
    - quay-quay-redhat-3.18__aws-ocp422-e2e-install.yaml
  retired: []

quay:
  - branch: redhat-3.18
    jobs:
      - {cron: daily, source: nightly, clouds: [aws], ocp: ["4.22"], test: e2e-install}
  - branch: master
    layout: base
    env:
      QUAY_OPERATOR_CHANNEL: stable-3.18
      QUAY_OPERATOR_SOURCE: redhat-operators
    jobs:
      - {kind: presubmit, clouds: [aws], ocp: ["4.22"], test: e2e-install, always_run: false, optional: true}
```

| Field | Meaning |
| --- | --- |
| `global_defaults.repo` | GitHub `org/repo` used in `zz_generated_metadata` and filenames |
| `global_defaults.arch` | Cluster architecture |
| `global_defaults.image_source` | How images are obtained (`build` today). Not referenced by templates yet. |
| `managed_files.active` | Required, non-empty list of every filename the matrix must generate. Generation fails loudly if this set doesn't exactly match what the matrix expands to. |
| `managed_files.retired` | Filenames the generator used to own but no longer generates. `--check` fails if any of these still exist in the output directory; run `generate.py` (without `--check`) and delete them, then drop them from this list. Defaults to `[]`. |
| `quay[]` | One Quay release, identified by git `branch` (`redhat-X.Y`, or `master`). The Quay version `X.Y` is derived from that suffix; `master` has no Quay version. |
| `quay[].layout` | `variant` (default) writes `{org}-{repo}-{branch}__{variant}.yaml`; `base` writes `{org}-{repo}-{branch}.yaml` in place (used for `master`). |
| `quay[].env` | Env keys applied to every job on that branch. Values replace whole keys. |
| `quay[].jobs[]` | One job spec, expanded across `clouds` × `ocp` |
| `quay[].jobs[].kind` | `periodic` (default, renders `templates/`) or `presubmit` (renders `templates/presubmit/`) |
| `quay[].jobs[].cron` | Required for `periodic`; must be unset for `presubmit`. Either an alias (`daily` / `nightly` / `weekly`) or a raw 5-field cron expression, passed through verbatim |
| `quay[].jobs[].source` | Required for periodic: `nightly` (`fbc-operator-catalog` + `QUAY_INDEX_IMAGE_REPO`) or `stable` (`redhat-operators`, no index image); must be unset for presubmit |
| `quay[].jobs[].always_run` / `.optional` / `.run_if_changed` / `.skip_if_only_changed` | Presubmit trigger fields, copied onto the test when set. `run_if_changed` and `skip_if_only_changed` are mutually exclusive; `always_run: true` cannot combine with either. Only valid when `kind: presubmit`. |
| `quay[].jobs[].env` | Optional per-job env; keys replace branch env of the same name |
| `quay[].jobs[].as` | Optional ci-operator test name. Defaults to `{cloud}-{storage}-{source}` for `periodic` (for example `aws-s3-nightly`) and `{cloud}-{storage}` for `presubmit` (for example `aws-s3`) -- cron changes only timing, never the name. Split the job into its own row when only some clouds need a different name. |

Each job is cartesian-expanded to one ci-operator file named `{org}-{repo}-{branch}__{cloud}-ocp{ocp_nodot}-{test}.yaml` (`layout: base` rows instead write `{org}-{repo}-{branch}.yaml`). Cells that share a filename (for example a periodic and a presubmit row for the same branch/cloud/OCP/test) merge into one file: their tests concatenate in matrix order, and everything but `tests` must be identical across the group or generation fails with `incompatible file-level inputs`. Two rows in one file that derive or set the same `as` collide: the generator fails with `duplicate as`. Periodic derives `{cloud}-{storage}-{source}` and presubmit derives `{cloud}-{storage}`, so a periodic/presubmit pair does not collide on its own. Two rows of the same kind can still collide; set an explicit `as` on one row to resolve it, and the name must not encode the kind.

## Layer order

Each cell is assembled by deep-merge, later layers win. `kind: presubmit` jobs render from `templates/presubmit/` for base and clouds; the test layer instead builds on top of the shared periodic one:

1. `templates/base.yaml` (or `templates/presubmit/base.yaml`)
2. `templates/sources/{source}.yaml` (periodic only; presubmit renders no source layer)
3. `templates/clouds/{cloud}.yaml`, or the optional override `templates/presubmit/clouds/{cloud}.yaml` when present; presubmit falls back to the shared file otherwise
4. `templates/tests/{test}.yaml`
5. `templates/presubmit/tests/{test}.yaml`, when present, merged on top of layer 4 (presubmit only); if it does not exist, presubmit uses layer 4 unchanged
6. Kind settings in `generate.py`: periodic sets `cron` from the resolved `cron` field (alias or raw expression); presubmit copies `always_run` / `optional` / `run_if_changed` / `skip_if_only_changed` onto the test when set
7. Branch `env`, then job `env` / `as`

Mappings recurse. Lists of mappings merge by index. Scalar lists replace. Env values replace whole keys. `QUAY_EXTRA_CONFIG` lives once, in `templates/tests/e2e-install.yaml`, and is shared by every branch and kind; unknown feature flags are treated as no-ops on older Quay releases. `templates/presubmit/tests/e2e-install.yaml` layers only the presubmit-specific delta (image-test dependencies/env and the extra `quay-deploy-custom-image` step) on top of it. Each cell's own rendered config must contain exactly one test; cells sharing a filename are grouped afterward (see above).

### How often a job runs (periodic cron)

The `cron` field controls **timing** only. Its value is either a short alias or a raw 5-field cron expression, and the resolved value is passed through verbatim to the ci-operator `cron` field. Presubmit jobs (`kind: presubmit`) don't set `cron` at all — they run per matching trigger fields instead (see the matrix table above).

| Alias | When | Result |
| --- | --- | --- |
| `daily` | Once a day | `cron: '@daily'`. Broader matrix (several clouds × OCP versions). |
| `nightly` | Once a day | Same cron as `daily` (`'@daily'`). |
| `weekly` | Once a week | `cron: '@weekly'`. Long tail — older versions, upgrades. |

A `cron` value that isn't one of those aliases must be a raw 5-field cron expression (for example `17 3 * * 1`); it is used verbatim.

The old `tier` field was removed outright, with no aliasing or deprecation window — `matrix.yaml` was its only consumer. A job that still sets `tier:` fails generation; migrate it to `cron:`.

## Adding coverage

Every new filename the matrix generates (a new release, job, or OCP version that changes `variant`) must be added to `managed_files.active`, or generation fails with `active but not generated` / `generated but not active`.

Add a Quay release by appending to `quay:`:

```yaml
  - branch: redhat-3.17
    jobs:
      - cron: daily
        source: nightly
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
```

Add an OCP version on an existing job:

```yaml
        ocp: ["4.22", "4.23"]
```

Both add a new generated filename for `layout: variant` releases; add it to `managed_files.active` in the same change. `layout: base` rows (for example `master`) share one file per branch: an extra cloud on an existing job needs a distinct `as` instead of a new filename, but an extra OCP version does not work the same way — `ocp` is a file-level input for base rows, so it needs its own variant/file.

Add a `stable` source alongside a `nightly` one on the same branch/cloud/OCP/test: `source` isn't part of the filename, so both jobs land in one shared file with distinct `as` names:

```yaml
  - branch: redhat-3.18
    jobs:
      - cron: daily
        source: nightly
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
      - cron: daily
        source: stable
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
```

This generates `aws-s3-nightly` and `aws-s3-stable` in the same `quay-quay-redhat-3.18__aws-ocp422-e2e-install.yaml`.

Branch `env` overrides the test template's default for every job on that branch (for example a shorter `PLAYWRIGHT_GREP_INVERT` on an older release that lacks a feature the default filter excludes). Do not copy `QUAY_EXTRA_CONFIG` here; it comes from the test template.

```yaml
  - branch: redhat-3.16
    env:
      PLAYWRIGHT_GREP_INVERT: "@auth:OIDC|@auth:LDAP"
    jobs:
      - {cron: daily, source: nightly, clouds: [gcp, azure], ocp: ["4.22"], test: e2e-install}
```

The presubmit test template adds the two image-unsafe test titles to `PLAYWRIGHT_GREP_INVERT`; the shared regex lives in `templates/tests/_e2e-install.defaults.j2`.

Then regenerate:

```bash
python3 generate.py
```

## Syncing to openshift/release

Merging a `ci-generator/matrix.yaml` change to `master` triggers the `Sync openshift CI configs` workflow (`.github/workflows/sync-ci-configs.yaml`). It regenerates the configs and copies the files listed in `managed_files` into `openshift/release`, deleting any previously-copied file that is no longer generated (for example one moved to `managed_files.retired`) from the release tree. It then regenerates Prow jobs and determinizes the ci-operator config (`make jobs` and `make ci-operator-config`), and opens or updates a PR on `openshift/release` from the fork configured in the `RELEASE_SYNC_FORK` repository variable. Nothing opens if the regenerated config and jobs are byte-identical to what is already in the release repo.

The workflow comments the release PR link on the merged Quay PR; that comment is the primary way to find it. If the comment is missing, search https://github.com/openshift/release/pulls?q=is%3Apr+is%3Aopen+sync-quay-ci-config or look for a branch named `sync-quay-ci-config-quay-<quay PR number>`.

After your matrix change merges:

1. Follow the linked `openshift/release` PR.
2. Comment `/pj-rehearse <job names>` (or the bare `/pj-rehearse` form the release repo supports) on the jobs the change touches. Read the changed job names from the PR's own diff under `ci-operator/jobs/quay/quay/` — `python3 generate.py --list` prints the matrix's short `AS` names, not the full Prow job names, so it is not a substitute.
3. Wait for the rehearsal jobs to report on the PR, then comment `/pj-rehearse ack` (or open with `/pj-rehearse auto-ack` up front) to satisfy the `rehearsals-ack` label.
4. Get `/lgtm` from a reviewer other than the change's author and `/approve` from an approver listed in the OWNERS file for `ci-operator/config/quay/quay` and `ci-operator/jobs/quay/quay` in `openshift/release`. Tide's merge query for this repo requires all three labels — `lgtm`, `approved`, `rehearsals-ack` — before it merges.

If a rehearsal fails, fix it in `quay/quay`'s `matrix.yaml` and merge that fix — only a `matrix.yaml` change retriggers the sync automatically (see below); a template-only fix needs the manual `workflow_dispatch` path too. Because the fix lands as a new Quay PR, the workflow pushes a new branch (`sync-quay-ci-config-quay-<new PR number>`) and opens a second `openshift/release` PR rather than updating the first — close the stale PR, or rerun the workflow manually with `quay_pr_number` set to the original PR to update the same release PR in place. Never hand-edit the generated config in the release PR.

A change to `ci-generator/templates/` or `generate.py` alone does not trigger the sync — only `ci-generator/matrix.yaml` is in the workflow's push paths filter. Run it by hand from the Actions tab (`Sync openshift CI configs` -> `Run workflow`), optionally passing the Quay PR number; it runs against whichever ref you pick.

Verify locally before merging. Bare `python3 generate.py --check` always fails in this checkout because `ci-generator/out/` is gitignored and nothing generated is committed to compare against, so use the round-trip form instead:

```bash
OUT=$(mktemp -d)
python3 generate.py --output "$OUT"
python3 generate.py --check --output "$OUT"
```

For a `templates/` or `generate.py` change, the stronger check is generating from the pre-change and post-change trees into two temp directories and diffing them (`diff -r`).

## Tests

```bash
uv run pytest
```

Golden output and other fixed expectations use `tests/fixtures/matrix-phase0.yaml`, not the checked-in `matrix.yaml`. You can add releases, clouds, and OCP versions to `matrix.yaml` without updating those tests; `test_production_matrix_expands_without_error` only checks that the production matrix expands with unique filenames.
