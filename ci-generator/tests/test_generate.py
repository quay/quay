"""Generator expansion, rendering, golden Phase 0 config, and CLI modes."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from generate import (
    GENERATED_HEADER,
    GENERATOR_DIR,
    apply_cell_settings,
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


def _phase0_cell(**kwargs: Any) -> Cell:
    values: dict[str, Any] = {
        "org": "quay",
        "repo": "quay",
        "branch": "redhat-3.18",
        "quay_version": "3.18",
        "ocp_version": "4.22",
        "cloud": "aws",
        "test": "e2e-install",
        "tier": "daily",
    }
    values.update(kwargs)
    return Cell(**values)


def test_expand_matrix_cells() -> None:
    matrix = yaml.safe_load((GENERATOR_DIR / "matrix.yaml").read_text())
    cells = expand_cells(matrix)
    assert {
        (cell.quay_version, cell.branch, cell.cloud, cell.ocp_version, cell.test, cell.tier)
        for cell in cells
    } == {
        ("3.18", "redhat-3.18", "aws", "4.22", "e2e-install", "daily"),
    }
    cell = cells[0]
    assert cell.filename == PHASE0_NAME
    assert cell.arch == "amd64"
    assert cell.as_name is None
    assert cell.test_as == "s3-daily"
    assert cell.env["PLAYWRIGHT_GREP_INVERT"] == (
        "@auth:OIDC|@auth:LDAP|@feature:QUOTA_NOTIFICATIONS|@webhook|"
        "saves and loads architecture filter with mirror configuration|"
        "loads existing architecture filter from saved mirror configuration"
    )
    assert "QUAY_EXTRA_CONFIG" not in cell.env


def test_adding_ocp_version_expands_cells() -> None:
    matrix = {
        "version": 2,
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
    assert rendered["prowgen"]["enable_secrets_store_csi_driver"] is True


def test_e2e_install_template_inverts_only_auth() -> None:
    env = jinja_env(GENERATOR_DIR / "templates")
    rendered = render_template(env, "tests/e2e-install.yaml", _phase0_cell().context())
    assert rendered["tests"][0]["steps"]["env"]["PLAYWRIGHT_GREP_INVERT"] == (
        "@auth:OIDC|@auth:LDAP"
    )


def test_tier_uses_interval_keywords() -> None:
    weekly = apply_tier_mapping(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="weekly", as_name=None),
    )
    assert weekly["tests"][0]["cron"] == "@weekly"

    daily = apply_tier_mapping(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="daily"),
    )
    assert daily["tests"][0]["cron"] == "@daily"

    nightly = apply_tier_mapping(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="nightly", as_name=None),
    )
    assert nightly["tests"][0]["cron"] == "@daily"

    presubmit = apply_tier_mapping(
        {
            "tests": [
                {
                    "steps": {
                        "cluster_profile": "aws-quay-qe",
                        "workflow": "ipi-aws",
                        "post": [{"ref": "quay-deprovision"}],
                    }
                }
            ]
        },
        _phase0_cell(test="api-test", tier="presubmit", as_name=None),
    )
    test = presubmit["tests"][0]
    assert "cron" not in test
    assert test["always_run"] is True
    assert "cluster_profile" not in test["steps"]
    assert "post" not in test["steps"]
    assert test["steps"]["workflow"] == "generic-claim"
    assert "cluster_claim" not in test["steps"]
    assert test["cluster_claim"]["version"] == "4.22"
    assert test["cluster_claim"]["cloud"] == "aws"


def test_golden_phase0_bytes() -> None:
    results = generate_all()
    by_name = {filename: config for _cell, filename, config in results}
    assert PHASE0_NAME in by_name
    dumped = dump_config(by_name[PHASE0_NAME])
    assert dumped == FIXTURE.read_text()
    assert dumped.startswith(GENERATED_HEADER)


def test_list_shows_phase0_row(capsys: object) -> None:
    assert main(["--list"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "3.18" in out
    assert "3.17" not in out
    assert "3.16" not in out
    assert "4.22" in out
    assert "e2e-install" in out
    assert PHASE0_NAME in out
    assert "s3-daily" in out


def test_check_clean_after_generate(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    assert (tmp_path / PHASE0_NAME).exists()
    assert main(["--check", "--output", str(tmp_path)]) == 0


def test_check_fails_when_stale(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    (tmp_path / PHASE0_NAME).write_text("foo: bar\n")
    assert main(["--check", "--output", str(tmp_path)]) == 1


def test_check_ignores_header_and_quoting_drift(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    path = tmp_path / PHASE0_NAME
    parsed = yaml.safe_load(path.read_text())
    path.write_text("# extra comment\n" + yaml.dump(parsed, sort_keys=False))
    assert yaml.safe_load(path.read_text()) == parsed
    assert main(["--check", "--output", str(tmp_path)]) == 0


def test_check_fails_when_missing(tmp_path: Path) -> None:
    assert main(["--check", "--output", str(tmp_path)]) == 1


def test_check_fails_when_unexpected_owned_file(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    (tmp_path / "quay-quay-redhat-3.18__orphan.yaml").write_text("foo: bar\n")
    assert main(["--check", "--output", str(tmp_path)]) == 1


def test_check_ignores_unmanaged_yaml(tmp_path: Path) -> None:
    assert main(["--output", str(tmp_path)]) == 0
    (tmp_path / "quay-quay-master.yaml").write_text("foo: bar\n")
    (tmp_path / "quay-quay-master__claim.yaml").write_text("foo: bar\n")
    assert main(["--check", "--output", str(tmp_path)]) == 0


def test_generate_all_rejects_duplicate_filenames(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.yaml"
    matrix_path.write_text("""
version: 2
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
    assert "s3-daily" in out
    assert "DO NOT EDIT THIS FILE" in out


def test_dump_round_trip() -> None:
    for _cell, _name, config in generate_all():
        dumped = dump_config(config)
        assert dumped.startswith(GENERATED_HEADER)
        assert yaml.safe_load(dumped) == config


def test_default_output_dir(tmp_path: Path) -> None:
    standalone = tmp_path / "ci-generator"
    standalone.mkdir()
    assert default_output_dir(standalone) == standalone / "out"
    nested = tmp_path / "_generator"
    nested.mkdir()
    assert default_output_dir(nested) == tmp_path


def test_apply_cell_settings_requires_one_test() -> None:
    cell = _phase0_cell()
    with pytest.raises(ValueError, match="exactly one test"):
        apply_cell_settings({"tests": []}, cell)
    with pytest.raises(ValueError, match="exactly one test"):
        apply_cell_settings({"tests": [{}, {}]}, cell)
