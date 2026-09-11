#!/usr/bin/env python3
"""
==============================================================================
🛑 STOP! PLEASE DO NOT HARDCODE CI CONFIGURATIONS IN THIS PYTHON SCRIPT 🛑
==============================================================================

This script is the Quay CI config generator. It handles the merging logic and
cartesian expansion of the CI matrix. Do NOT modify this code to update
test steps, cluster profiles, or to add new OpenShift/Quay versions.

WHERE TO MAKE YOUR CHANGES:
---------------------------
1. Matrix Expansion (Add/remove Quay releases, OCP versions, clouds, tiers):
   👉 Edit `matrix.yaml`

2. Job Definitions (Change steps, images, cluster profiles, base structure):
   👉 Edit the Jinja templates in `templates/`
      - Base config: `templates/base.yaml`
      - Cloud specifics: `templates/clouds/{cloud}.yaml`
      - Test specifics: `templates/tests/{test}.yaml`

3. Edge Cases (Patch a specific job without affecting the rest of the matrix):
   👉 Add or edit a YAML file in the `overrides/` directory.

HOW IT MERGES:
--------------
Each cell is deep-merged in this strict order (later layers overwrite earlier):
  1. templates/base.yaml
  2. templates/clouds/<cloud>.yaml
  3. templates/tests/<test>.yaml
  4. Tier mapping (presubmit / daily / nightly / weekly)
  5. overrides/ (broadest match -> most specific match)

USAGE AFTER MAKING CHANGES:
---------------------------
$ python3 generate.py              # Regenerate all CI configs
$ python3 generate.py --dry-run    # Preview without writing
$ python3 generate.py --check      # CI gate: verify configs are up to date
==============================================================================
"""

from __future__ import annotations

import argparse
import copy
import itertools
import sys
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError
from model import Cell, Override, YamlMap

GENERATOR_DIR = Path(__file__).resolve().parent
TIERS = ("presubmit", "daily", "nightly", "weekly")
TIER_INTERVALS = {
    "daily": "@daily",
    "nightly": "@daily",
    "weekly": "@weekly",
}
MATCH_FIELDS = {
    "quay": "quay_version",
    "ocp": "ocp_version",
    "cloud": "cloud",
    "test": "test",
    "tier": "tier",
    "branch": "branch",
    "arch": "arch",
}


def default_output_dir(generator_dir: Path = GENERATOR_DIR) -> Path:
    if generator_dir.name == "_generator":
        return generator_dir.parent
    return generator_dir / "out"


def load_yaml(path: Path) -> Any:
    with path.open() as fh:
        return yaml.safe_load(fh)


def jinja_env(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_template(env: Environment, name: str, context: dict[str, str]) -> YamlMap:
    try:
        rendered = env.get_template(name).render(**context)
    except TemplateError as exc:
        raise ValueError(f"failed to render template {name}: {exc}") from exc
    loaded = yaml.safe_load(rendered)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"template {name} must render to a YAML mapping")
    return loaded


def _is_list_of_maps(value: list[Any]) -> bool:
    return bool(value) and all(isinstance(item, dict) for item in value)


def deep_merge(base: Any, overlay: Any) -> Any:
    """Deep-merge overlay onto base. Later values win.

    Mappings recurse. Lists of mappings merge by index. Other lists replace.
    """
    if overlay is None:
        return copy.deepcopy(base)
    if base is None:
        return copy.deepcopy(overlay)
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged: YamlMap = copy.deepcopy(base)
        for key, value in overlay.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    if isinstance(base, list) and isinstance(overlay, list) and _is_list_of_maps(base) and _is_list_of_maps(overlay):
        merged_list: list[Any] = copy.deepcopy(base)
        for index, item in enumerate(overlay):
            if index < len(merged_list):
                merged_list[index] = deep_merge(merged_list[index], item)
            else:
                merged_list.append(copy.deepcopy(item))
        return merged_list
    return copy.deepcopy(overlay)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _parse_github_repo(value: str) -> tuple[str, str]:
    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"repo must be org/repo, got {value!r}")
    return parts[0], parts[1]


def _quay_releases(matrix: YamlMap) -> list[YamlMap]:
    quay = matrix.get("quay")
    if not isinstance(quay, list) or not quay:
        raise ValueError("quay must be a non-empty list of mappings")
    releases: list[YamlMap] = []
    for index, item in enumerate(quay):
        if not isinstance(item, dict):
            raise ValueError(f"quay[{index}] must be a mapping")
        releases.append(item)
    return releases


def _quay_version_from_branch(branch: str) -> str:
    prefix = "redhat-"
    if not branch.startswith(prefix):
        raise ValueError(f"quay branch {branch!r} must look like 'redhat-X.Y' so the Quay version can be derived")
    version = branch[len(prefix) :].strip()
    if not version:
        raise ValueError(f"quay branch {branch!r} is missing a version suffix")
    return version


def expand_cells(matrix: YamlMap) -> list[Cell]:
    defaults = matrix.get("global_defaults") or {}
    if not isinstance(defaults, dict):
        raise ValueError("global_defaults must be a mapping")

    org, repo = _parse_github_repo(str(defaults.get("repo") or "quay/quay"))
    arch = str(defaults.get("arch") or "amd64")
    image_source = str(defaults.get("image_source") or "build")

    cells: list[Cell] = []
    for release_index, release in enumerate(_quay_releases(matrix)):
        branch = str(release.get("branch") or "").strip()
        if not branch:
            raise ValueError(f"quay[{release_index}] is missing branch")
        quay_version = _quay_version_from_branch(branch)
        jobs = release.get("jobs") or []
        if not isinstance(jobs, list):
            raise ValueError(f"quay[{release_index}].jobs must be a list")
        for job_index, job in enumerate(jobs):
            if not isinstance(job, dict):
                raise ValueError(f"quay[{release_index}].jobs[{job_index}] must be a mapping")
            tier = str(job.get("tier") or "")
            test = str(job.get("test") or "")
            ocps = _as_str_list(job.get("ocp"))
            clouds = _as_str_list(job.get("clouds"))
            if not tier or not test or not ocps or not clouds:
                raise ValueError(f"quay[{release_index}].jobs[{job_index}] is missing tier, test, ocp, or clouds")
            if tier not in TIERS:
                raise ValueError(f"unsupported tier {tier!r}")
            for ocp, cloud in itertools.product(ocps, clouds):
                cells.append(
                    Cell(
                        org=org,
                        repo=repo,
                        branch=branch,
                        quay_version=quay_version,
                        ocp_version=ocp,
                        cloud=cloud,
                        test=test,
                        tier=tier,
                        arch=arch,
                        image_source=image_source,
                    )
                )
    return cells


def apply_tier_mapping(config: YamlMap, cell: Cell) -> YamlMap:
    config = copy.deepcopy(config)
    tests = config.get("tests")
    if not isinstance(tests, list) or not tests or not isinstance(tests[0], dict):
        raise ValueError("generated config is missing tests[0]")
    test = tests[0]
    steps = test.setdefault("steps", {})
    if not isinstance(steps, dict):
        raise ValueError("tests[0].steps must be a mapping")
    if cell.tier == "presubmit":
        test["always_run"] = True
        steps.pop("cluster_profile", None)
        steps["cluster_claim"] = {
            "architecture": cell.arch,
            "cloud": cell.cloud,
            "owner": "openshift-ci",
            "product": "ocp",
            "timeout": "1h0m0s",
            "version": cell.ocp_version,
        }
        test.pop("cron", None)
    elif cell.tier in TIER_INTERVALS:
        test["cron"] = TIER_INTERVALS[cell.tier]
    else:
        raise ValueError(f"unsupported tier {cell.tier!r}")
    return config


def load_overrides(overrides_dir: Path) -> list[Override]:
    if not overrides_dir.is_dir():
        return []
    loaded: list[Override] = []
    for path in sorted(overrides_dir.glob("*.yaml")):
        data = load_yaml(path)
        if data is None:
            continue
        if not isinstance(data, dict):
            raise ValueError(f"{path} must be a YAML mapping")
        match = match = data.get("match", {})
        if not isinstance(match, dict):
            raise ValueError(f"{path} match: must be a mapping")
        patch = {key: value for key, value in data.items() if key != "match"}
        loaded.append(Override(path=path, match=match, patch=patch))
    loaded.sort(key=lambda item: (item.specificity, item.path.name))
    return loaded


def override_matches(match: YamlMap, cell: Cell) -> bool:
    context = cell.context()
    for key, expected in match.items():
        if key not in MATCH_FIELDS:
            raise ValueError(f"unknown override match key {key!r}")
        actual = context[MATCH_FIELDS[key]]
        if str(actual) != str(expected):
            return False
    return True


def apply_overrides(config: YamlMap, cell: Cell, overrides: list[Override]) -> YamlMap:
    merged = copy.deepcopy(config)
    for override in overrides:
        if override_matches(override.match, cell):
            merged = deep_merge(merged, override.patch)
    return merged


def build_config(cell: Cell, templates_dir: Path, overrides: list[Override]) -> YamlMap:
    env = jinja_env(templates_dir)
    context = cell.context()
    layers = [
        render_template(env, "base.yaml", context),
        render_template(env, f"clouds/{cell.cloud}.yaml", context),
        render_template(env, f"tests/{cell.test}.yaml", context),
    ]
    config: YamlMap = {}
    for layer in layers:
        config = deep_merge(config, layer)
    config = apply_tier_mapping(config, cell)
    return apply_overrides(config, cell, overrides)


class GeneratorDumper(yaml.SafeDumper):
    pass


def _looks_like_number(value: str) -> bool:
    stripped = value.replace(".", "", 1)
    return stripped.isdigit()


def _represent_str(dumper: yaml.Dumper, data: str) -> yaml.Node:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    needs_quotes = (
        data == ""
        or data.lower() in {"true", "false", "null", "yes", "no", "on", "off"}
        or _looks_like_number(data)
        or data[0] in "@*&!%|#>,[?'\"{}:"
        or ": " in data
        or data.startswith(" ")
        or data.endswith(" ")
    )
    if needs_quotes:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


GeneratorDumper.add_representer(str, _represent_str)


def dump_config(config: YamlMap) -> str:
    dumped = yaml.dump(
        config,
        Dumper=GeneratorDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
        indent=2,
    )
    if not dumped.endswith("\n"):
        dumped += "\n"
    return dumped


def generate_all(
    generator_dir: Path = GENERATOR_DIR,
    matrix_path: Path | None = None,
    templates_dir: Path | None = None,
    overrides_dir: Path | None = None,
) -> list[tuple[Cell, str, YamlMap]]:
    matrix_path = matrix_path or generator_dir / "matrix.yaml"
    templates_dir = templates_dir or generator_dir / "templates"
    overrides_dir = overrides_dir or generator_dir / "overrides"
    matrix = load_yaml(matrix_path)
    if not isinstance(matrix, dict):
        raise ValueError("matrix.yaml must be a YAML mapping")
    overrides = load_overrides(overrides_dir)
    results: list[tuple[Cell, str, YamlMap]] = []
    seen_filenames: set[str] = set()
    for cell in expand_cells(matrix):
        config = build_config(cell, templates_dir, overrides)
        if cell.filename in seen_filenames:
            raise ValueError(f"duplicate generated filename {cell.filename}")
        seen_filenames.add(cell.filename)
        results.append((cell, cell.filename, config))
    return results


def _print_list(results: list[tuple[Cell, str, YamlMap]]) -> None:
    headers = ("QUAY", "OCP", "CLOUD", "TEST", "TIER", "FILE", "AS")
    rows: list[tuple[str, ...]] = [headers]
    for cell, filename, config in results:
        test_as = config["tests"][0].get("as", cell.test_as)
        rows.append((cell.quay_version, cell.ocp_version, cell.cloud, cell.test, cell.tier, filename, str(test_as)))
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    for row in rows:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def _write_configs(results: list[tuple[Cell, str, YamlMap]], output_dir: Path, dry_run: bool) -> None:
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    for _cell, filename, config in results:
        text = dump_config(config)
        path = output_dir / filename
        if dry_run:
            print(f"=== {path} ===")
            print(text, end="" if text.endswith("\n") else "\n")
            continue
        path.write_text(text)
        print(f"wrote {path}")


def _check_configs(results: list[tuple[Cell, str, YamlMap]], output_dir: Path) -> int:
    failures = 0
    expected = {filename for _cell, filename, _config in results}
    for _cell, filename, config in results:
        path = output_dir / filename
        if not path.exists():
            print(f"missing {path}", file=sys.stderr)
            failures += 1
            continue
        if path.read_text() != dump_config(config):
            print(f"stale {path}", file=sys.stderr)
            failures += 1
    if output_dir.is_dir():
        for path in sorted(output_dir.glob("*.yaml")):
            if path.name not in expected:
                print(f"unexpected {path}", file=sys.stderr)
                failures += 1
    if failures:
        print(f"{failures} config(s) out of date", file=sys.stderr)
        return 1
    print(f"{len(results)} config(s) up to date")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Quay ci-operator configs from matrix.yaml")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="preview YAML without writing")
    mode.add_argument("--check", action="store_true", help="verify generated configs are up to date")
    mode.add_argument("--list", action="store_true", help="show matrix expansion table")
    parser.add_argument("--output", type=Path, help="directory to write (or check) config files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output.resolve() if args.output else default_output_dir()
    results = generate_all()
    if args.list:
        _print_list(results)
        return 0
    if args.check:
        return _check_configs(results, output_dir)
    _write_configs(results, output_dir, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
