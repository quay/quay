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
python3 generate.py --list       # show matrix expansion table
python3 generate.py --output DIR # write or check a specific directory
```

Standalone default output is `./out`. When this directory is named `_generator`, output is the parent directory (`ci-operator/config/quay/quay/` in openshift/release).

`--check` is the CI verification step: exit `1` if any generated file is missing, unexpected, or its parsed YAML differs. Unexpected files are only those matching a generator-owned `{org}-{repo}-{branch}__` prefix from the current matrix; `master`'s `layout: base` file (`quay-quay-master.yaml`) is checked directly, but exact ownership of neighbouring hand-written `quay-quay-master__*.yaml` files (`__claim`, `__omr-*`) is not yet enforced by prefix matching. Content comparison is parsed YAML (comments and `determinize-ci-operator` quoting are ignored).

## `matrix.yaml`

```yaml
version: 2

global_defaults:
  image_source: build  # reserved; templates do not use it yet
  arch: amd64
  repo: quay/quay

quay:
  - branch: redhat-3.18
    env:
      PLAYWRIGHT_GREP_INVERT: "@auth:OIDC|@auth:LDAP|@feature:QUOTA_NOTIFICATIONS|@webhook|..."
    jobs:
      - {tier: daily, clouds: [aws], ocp: ["4.22"], test: e2e-install}
  - branch: master
    layout: base
    env:
      QUAY_OPERATOR_CHANNEL: stable-3.17
      QUAY_OPERATOR_SOURCE: redhat-operators
    jobs:
      - {kind: presubmit, clouds: [aws], ocp: ["4.22"], test: e2e-install, always_run: false, optional: true}
```

| Field | Meaning |
| --- | --- |
| `global_defaults.repo` | GitHub `org/repo` used in `zz_generated_metadata` and filenames |
| `global_defaults.arch` | Cluster architecture |
| `global_defaults.image_source` | How images are obtained (`build` today). Not referenced by templates yet. |
| `quay[]` | One Quay release, identified by git `branch` (`redhat-X.Y`, or `master`). The Quay version `X.Y` is derived from that suffix; `master` has no Quay version. |
| `quay[].layout` | `variant` (default) writes `{org}-{repo}-{branch}__{variant}.yaml`; `base` writes `{org}-{repo}-{branch}.yaml` in place (used for `master`). |
| `quay[].env` | Env keys applied to every job on that branch. Values replace whole keys. |
| `quay[].jobs[]` | One job spec, expanded across `clouds` × `ocp` |
| `quay[].jobs[].kind` | `periodic` (default, renders `templates/`) or `presubmit` (renders `templates/presubmit/`) |
| `quay[].jobs[].tier` | Required for `periodic` (`daily` / `nightly` / `weekly`); must be unset for `presubmit` |
| `quay[].jobs[].always_run` / `.optional` / `.run_if_changed` / `.skip_if_only_changed` | Presubmit trigger fields, copied onto the test when set. `run_if_changed` and `skip_if_only_changed` are mutually exclusive; `always_run: true` cannot combine with either. Only valid when `kind: presubmit`. |
| `quay[].jobs[].env` | Optional per-job env; keys replace branch env of the same name |
| `quay[].jobs[].as` | Optional ci-operator test name. Defaults to `{storage}-{tier}` for periodic (for example `s3-daily`) or `{storage}` for presubmit (for example `s3`). Split the job into its own row when only some clouds need a different name. |

Each job is cartesian-expanded to one ci-operator file named `{org}-{repo}-{branch}__{cloud}-ocp{ocp_nodot}-{test}.yaml` (`layout: base` rows instead write `{org}-{repo}-{branch}.yaml`). Cells that share a filename (for example a periodic and a presubmit row for the same branch/cloud/OCP/test) merge into one file: their tests concatenate in matrix order, and everything but `tests` must be identical across the group or generation fails with `incompatible file-level inputs`.

## Layer order

Each cell is assembled by deep-merge, later layers win. `kind: presubmit` jobs render from `templates/presubmit/` instead of `templates/`; the three layer names underneath are the same:

1. `templates/base.yaml` (or `templates/presubmit/base.yaml`)
2. `templates/clouds/{cloud}.yaml` (or `templates/presubmit/clouds/{cloud}.yaml`)
3. `templates/tests/{test}.yaml` (or `templates/presubmit/tests/{test}.yaml`)
4. Kind settings in `generate.py`: periodic sets `cron` from the tier; presubmit copies `always_run` / `optional` / `run_if_changed` / `skip_if_only_changed` onto the test when set
5. Branch `env`, then job `env` / `as`

Mappings recurse. Lists of mappings merge by index. Scalar lists replace. Env values replace whole keys. `QUAY_EXTRA_CONFIG` lives once per kind (`templates/tests/e2e-install.yaml` and `templates/presubmit/tests/e2e-install.yaml`) and is shared by every version of that kind; unknown feature flags are treated as no-ops on older Quay releases. Each cell's own rendered config must contain exactly one test; cells sharing a filename are grouped afterward (see above).

### How often a job runs (periodic tiers)

The only difference between periodic tiers is **timing**. The ci-operator field is `cron`; the value is a Prow interval keyword, not a raw crontab. Presubmit jobs (`kind: presubmit`) don't set `tier` or `cron` at all — they run per matching trigger fields instead (see the matrix table above).

| Tier | When | Result |
| --- | --- | --- |
| `daily` | Once a day | `cron: '@daily'`. Broader matrix (several clouds × OCP versions). |
| `nightly` | Once a day | Same cron as `daily` (`'@daily'`). Use when the derived name should be `{storage}-nightly`. |
| `weekly` | Once a week | `cron: '@weekly'`. Long tail — older versions, upgrades. |

## Adding coverage

Add a Quay release by appending to `quay:`:

```yaml
  - branch: redhat-3.17
    jobs:
      - tier: daily
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
```

Add an OCP version on an existing job:

```yaml
        ocp: ["4.22", "4.23"]
```

Shared env for every job on a branch (for example a longer `PLAYWRIGHT_GREP_INVERT`). Do not copy `QUAY_EXTRA_CONFIG` here; it comes from the test template.

```yaml
  - branch: redhat-3.18
    env:
      PLAYWRIGHT_GREP_INVERT: "@auth:OIDC|@auth:LDAP|@feature:QUOTA_NOTIFICATIONS|@webhook"
    jobs:
      - {tier: daily, clouds: [gcp, azure], ocp: ["4.22"], test: e2e-install}
```

Then regenerate:

```bash
python3 generate.py
```

## Tests

```bash
uv run pytest
```
