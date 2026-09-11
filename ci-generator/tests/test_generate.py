"""Generator expansion, rendering, golden Phase 0 config, and CLI modes."""

from pathlib import Path

import pytest
import yaml
from generate import (
    GENERATOR_DIR,
    apply_tier_mapping,
    default_output_dir,
    dump_config,
    expand_cells,
    generate_all,
    jinja_env,
    main,
    render_template,
)
from model import Cell

PHASE0_NAME = "quay-quay-redhat-3.18__aws-ocp422-e2e-install.yaml"
FIXTURE = Path(__file__).parent / "fixtures" / PHASE0_NAME


def _phase0_cell(**kwargs: str) -> Cell:
    values = {
        "org": "quay",
        "repo": "quay",
        "branch": "redhat-3.18",
        "quay_version": "3.18",
        "ocp_version": "4.22",
        "cloud": "aws",
        "test": "e2e-install",
        "tier": "weekly",
    }
    values.update(kwargs)
    return Cell(**values)


def test_expand_matrix_cells() -> None:
    matrix = yaml.safe_load((GENERATOR_DIR / "matrix.yaml").read_text())
    cells = expand_cells(matrix)
    assert {(cell.quay_version, cell.branch, cell.cloud, cell.ocp_version, cell.test, cell.tier) for cell in cells} == {
        ("3.18", "redhat-3.18", "aws", "4.22", "e2e-install", "daily"),
        ("3.18", "redhat-3.18", "gcp", "4.22", "e2e-install", "daily"),
        ("3.18", "redhat-3.18", "azure", "4.22", "e2e-install", "daily"),
        ("3.17", "redhat-3.17", "gcp", "4.22", "e2e-install", "daily"),
        ("3.17", "redhat-3.17", "azure", "4.22", "e2e-install", "daily"),
        ("3.16", "redhat-3.16", "gcp", "4.22", "e2e-install", "daily"),
        ("3.16", "redhat-3.16", "azure", "4.22", "e2e-install", "daily"),
    }
    by_key = {(cell.quay_version, cell.cloud): cell for cell in cells}
    assert by_key[("3.18", "aws")].filename == PHASE0_NAME
    assert by_key[("3.18", "aws")].arch == "amd64"
    assert by_key[("3.17", "gcp")].filename == "quay-quay-redhat-3.17__gcp-ocp422-e2e-install.yaml"
    assert by_key[("3.16", "gcp")].filename == "quay-quay-redhat-3.16__gcp-ocp422-e2e-install.yaml"


def test_adding_ocp_version_expands_cells() -> None:
    matrix = {
        "version": 1,
        "global_defaults": {
            "image_source": "build",
            "arch": "amd64",
            "repo": "quay/quay",
        },
        "quay": [
            {
                "branch": "redhat-3.18",
                "jobs": [
                    {
                        "tier": "weekly",
                        "clouds": ["aws"],
                        "ocp": ["4.22", "4.23"],
                        "test": "e2e-install",
                    }
                ],
            }
        ],
    }
    cells = expand_cells(matrix)
    assert [cell.ocp_version for cell in cells] == ["4.22", "4.23"]
    assert cells[1].filename == "quay-quay-redhat-3.18__aws-ocp423-e2e-install.yaml"


def test_jinja_renders_ocp_version() -> None:
    env = jinja_env(GENERATOR_DIR / "templates")
    rendered = render_template(env, "base.yaml", _phase0_cell().context())
    assert rendered["releases"]["latest"]["candidate"]["architecture"] == "amd64"
    assert rendered["releases"]["latest"]["candidate"]["version"] == "4.22"
    assert rendered["zz_generated_metadata"]["variant"] == "aws-ocp422-e2e-install"


def test_tier_uses_interval_keywords() -> None:
    weekly = apply_tier_mapping({"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]}, _phase0_cell())
    assert weekly["tests"][0]["cron"] == "@weekly"

    daily = apply_tier_mapping(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="daily"),
    )
    assert daily["tests"][0]["cron"] == "@daily"

    nightly = apply_tier_mapping(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="nightly"),
    )
    assert nightly["tests"][0]["cron"] == "@daily"

    presubmit = apply_tier_mapping(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(test="api-test", tier="presubmit"),
    )
    assert "cron" not in presubmit["tests"][0]
    assert presubmit["tests"][0]["always_run"] is True
    assert "cluster_profile" not in presubmit["tests"][0]["steps"]
    assert presubmit["tests"][0]["steps"]["cluster_claim"]["version"] == "4.22"


def test_golden_phase0_parsed_yaml() -> None:
    results = generate_all()
    by_name = {filename: config for _cell, filename, config in results}
    assert PHASE0_NAME in by_name
    expected = yaml.safe_load(FIXTURE.read_text())
    assert by_name[PHASE0_NAME] == expected


def test_list_shows_phase0_row(capsys: object) -> None:
    assert main(["--list"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "3.18" in out
    assert "3.17" in out
    assert "3.16" in out
    assert "4.22" in out
    assert "e2e-install" in out
    assert PHASE0_NAME in out
    assert "aws-s3-3-18-nightly-4-22" in out


def test_check_clean_after_generate(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    assert (tmp_path / PHASE0_NAME).exists()
    assert main(["--check", "--output", str(tmp_path)]) == 0


def test_check_fails_when_stale(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    (tmp_path / PHASE0_NAME).write_text("foo: bar\n")
    assert main(["--check", "--output", str(tmp_path)]) == 1


def test_check_fails_on_serialized_text_mismatch(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    path = tmp_path / PHASE0_NAME
    path.write_text(path.read_text() + "# leftover\n")
    assert main(["--check", "--output", str(tmp_path)]) == 1


def test_check_fails_when_missing(tmp_path: Path) -> None:
    assert main(["--check", "--output", str(tmp_path)]) == 1


def test_check_fails_when_unexpected(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    (tmp_path / "orphan.yaml").write_text("foo: bar\n")
    assert main(["--check", "--output", str(tmp_path)]) == 1


def test_generate_all_rejects_duplicate_filenames(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.yaml"
    matrix_path.write_text("""
version: 1
global_defaults:
  image_source: build
  arch: amd64
  repo: quay/quay
quay:
  - branch: redhat-3.18
    jobs:
      - tier: daily
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
      - tier: weekly
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
""")
    with pytest.raises(ValueError, match="duplicate generated filename"):
        generate_all(matrix_path=matrix_path)


def test_dry_run_does_not_write(tmp_path: Path, capsys: object) -> None:
    assert main(["--dry-run", "--output", str(tmp_path)]) == 0
    assert not (tmp_path / PHASE0_NAME).exists()
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert PHASE0_NAME in out
    assert "aws-s3-3-18-nightly-4-22" in out


def test_dump_round_trip() -> None:
    for _cell, _name, config in generate_all():
        assert yaml.safe_load(dump_config(config)) == config


def test_default_output_dir(tmp_path: Path) -> None:
    standalone = tmp_path / "ci-generator"
    standalone.mkdir()
    assert default_output_dir(standalone) == standalone / "out"
    nested = tmp_path / "_generator"
    nested.mkdir()
    assert default_output_dir(nested) == tmp_path
