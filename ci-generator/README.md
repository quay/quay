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

`--check` is the CI verification step: exit `1` if any generated file is missing, unexpected, or its parsed YAML differs. Unexpected files are only those matching a generator-owned `{org}-{repo}-{branch}__` prefix from the current matrix, so hand-written `quay-quay-master*.yaml` files in the same directory are ignored. Content comparison is parsed YAML (comments and `determinize-ci-operator` quoting are ignored).

## `matrix.yaml`

```yaml
version: 2

global_defaults:
  image_source: build  # reserved; templates do not use it yet
  arch: amd64
  repo: quay/quay

quay:
  - branch: redhat-3.18
    jobs:
      - tier: daily
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
        as: aws-s3-3-18-nightly-4-22
      - tier: weekly
        clouds: [gcp]
        ocp: ["4.22"]
        test: e2e-install
        as: gcp-gcs-3-18-nightly-4-22
      - {tier: daily, clouds: [azure], ocp: ["4.22"], test: e2e-install}
  - branch: redhat-3.17
    env:
      PLAYWRIGHT_GREP_INVERT: "@auth:OIDC|@auth:LDAP"
      QUAY_EXTRA_CONFIG: |
        # shared by every 3.17 job; replaces the template value whole
    jobs:
      - {tier: daily, clouds: [gcp, azure], ocp: ["4.22"], test: e2e-install}
```

| Field | Meaning |
| --- | --- |
| `global_defaults.repo` | GitHub `org/repo` used in `zz_generated_metadata` and filenames |
| `global_defaults.arch` | Cluster architecture (also used for presubmit `cluster_claim`) |
| `global_defaults.image_source` | How images are obtained (`build` today). Not referenced by templates yet. |
| `quay[]` | One Quay release, identified by git `branch` (`redhat-X.Y`). The Quay version `X.Y` is derived from that suffix. |
| `quay[].env` | Env keys applied to every job on that branch. Values replace whole keys. |
| `quay[].jobs[]` | One job spec, expanded across `clouds` × `ocp` |
| `quay[].jobs[].env` | Optional per-job env; keys replace branch env of the same name |
| `quay[].jobs[].as` | Optional ci-operator test name. Use this to keep a live/legacy name. Split the job into its own row when only some clouds need it. |

Each job is cartesian-expanded to one ci-operator file named:

`{org}-{repo}-{branch}__{cloud}-ocp{ocp_nodot}-{test}.yaml`

The derived test name is `{cloud}-{storage}-{quay}-{tier}-{ocp}` unless `as` is set.

## Layer order

Each cell is assembled by deep-merge, later layers win:

1. `templates/base.yaml`
2. `templates/clouds/{cloud}.yaml`
3. `templates/tests/{test}.yaml`
4. Tier mapping in `generate.py` (`presubmit` / `daily` / `nightly` / `weekly`)
5. Branch `env`, then job `env` / `as`

Mappings recurse. Lists of mappings merge by index. Scalar lists replace. Env values replace whole keys, so an older `QUAY_EXTRA_CONFIG` cannot inherit a newer flag by accident. Generated configs must contain exactly one test.

### How often a job runs (tiers)

The only difference between tiers is **timing** and **how a cluster is obtained**. The ci-operator field is still `cron`; the value is a Prow interval keyword, not a raw crontab.

| Tier | When | Result |
| --- | --- | --- |
| `presubmit` | On every PR, before merge | Test-level `cluster_claim` + `always_run: true`, `workflow: generic-claim`, no `cluster_profile` / `post`. Fast gate; keep the matrix small. |
| `daily` | Once a day | `cluster_profile` + `cron: '@daily'`. Broader matrix (several clouds × OCP versions). |
| `nightly` | Once a day | Same cron as `daily` (`'@daily'`). Alias so a cell can stay daily-scheduled while a legacy `as:` still contains `nightly`. |
| `weekly` | Once a week | `cluster_profile` + `cron: '@weekly'`. Long tail — older versions, upgrades. |

Job-level `as:` is how live names such as `aws-s3-3-18-nightly-4-22` are preserved on a `daily` or `weekly` cell.

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

Shared env for every job on a branch:

```yaml
  - branch: redhat-3.16
    env:
      PLAYWRIGHT_GREP_INVERT: "@auth:OIDC|@auth:LDAP"
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
