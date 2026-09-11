# Quay CI config generator

Python generator that reads a compact `matrix.yaml` and writes [ci-operator](https://docs.ci.openshift.org/) config files for each test cell.

Templating is Jinja `{{ variable }}` placeholders only. Conditionals and loops stay in `generate.py`, not in the YAML templates.

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

Standalone default output is `./out`. When this directory is named `_generator`, output is the parent directory (`ci-operator/config/quay/quay/`).

`--check` is the CI verification step: exit `1` if any generated file is missing, unexpected, or its serialized text differs.

## `matrix.yaml`

```yaml
version: 1

global_defaults:
  image_source: build
  arch: amd64
  repo: quay/quay

quay:
  - branch: redhat-3.18
    jobs:
      - tier: daily
        clouds: [aws, gcp, azure]
        ocp: ["4.22"]
        test: e2e-install
  - branch: redhat-3.17
    jobs:
      - tier: daily
        clouds: [gcp, azure]
        ocp: ["4.22"]
        test: e2e-install
  - branch: redhat-3.16
    jobs:
      - tier: daily
        clouds: [gcp, azure]
        ocp: ["4.22"]
        test: e2e-install
```

| Field | Meaning |
| --- | --- |
| `global_defaults.repo` | GitHub `org/repo` used in `zz_generated_metadata` and filenames |
| `global_defaults.arch` | Cluster architecture (also used for presubmit `cluster_claim`) |
| `global_defaults.image_source` | How images are obtained (`build` today) |
| `quay[]` | One Quay release, identified by git `branch` (`redhat-X.Y`). The Quay version `X.Y` is derived from that suffix. |
| `quay[].jobs[]` | One job spec, expanded across `clouds` × `ocp` |

Each job is cartesian-expanded to one ci-operator file named:

`{org}-{repo}-{branch}__{cloud}-ocp{ocp_nodot}-{test}.yaml`

## Layer order

Each cell is assembled by deep-merge, later layers win:

1. `templates/base.yaml`
2. `templates/clouds/{cloud}.yaml`
3. `templates/tests/{test}.yaml`
4. Tier mapping in `generate.py` (`presubmit` / `daily` / `nightly` / `weekly`)
5. Matching files in `overrides/` (broad → specific)

Mappings recurse. Lists of mappings merge by index. Scalar lists replace.

### How often a job runs (tiers)

The only difference between tiers is **timing** and **how many combinations** you run. The ci-operator field is still `cron`; the value is a Prow interval keyword, not a raw crontab.

| Tier | When | Result |
| --- | --- | --- |
| `presubmit` | On every PR, before merge | `cluster_claim` + `always_run: true` (drops `cluster_profile`). Fast gate; keep the matrix small. |
| `daily` | Once a day | `cluster_profile` + `cron: "@daily"`. Broader matrix (several clouds × OCP versions). |
| `nightly` | Once a day | Same as `daily` (`cron: "@daily"`). Kept as an alias. |
| `weekly` | Once a week | `cluster_profile` + `cron: "@weekly"`. Long tail — older versions, upgrades. |

Overrides can still change `as` or other fields after that.

### Override matching

Each override file has a `match:` block. Remaining keys are the patch. The generator sorts by specificity (fewer match keys first) so last-write-wins on deep merge. Known match keys: `quay`, `ocp`, `cloud`, `test`, `tier`, `branch`, `arch`.

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

Then regenerate:

```bash
python3 generate.py
```

## Tests

```bash
uv run pytest
```
