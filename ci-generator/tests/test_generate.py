"""Generator expansion, rendering, golden Phase 0 config, and CLI modes."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from generate import (
    GENERATED_HEADER,
    GENERATOR_DIR,
    apply_cell_settings,
    apply_kind_settings,
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
MASTER_NAME = "quay-quay-master.yaml"
MASTER_FIXTURE = Path(__file__).parent / "fixtures" / MASTER_NAME
MIXED_DIR = Path(__file__).parent / "fixtures" / "mixed"


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
        (
            cell.quay_version,
            cell.branch,
            cell.cloud,
            cell.ocp_version,
            cell.test,
            cell.tier,
            cell.kind,
        )
        for cell in cells
    } == {
        ("3.18", "redhat-3.18", "aws", "4.22", "e2e-install", "daily", "periodic"),
        (None, "master", "aws", "4.22", "e2e-install", None, "presubmit"),
    }
    cell = next(c for c in cells if c.branch == "redhat-3.18")
    assert cell.filename == PHASE0_NAME
    assert cell.arch == "amd64"
    assert cell.as_name is None
    assert cell.test_as == "s3-daily"
    assert cell.env["PLAYWRIGHT_GREP_INVERT"] == (
        "@auth:OIDC|@auth:LDAP|@feature:QUOTA_NOTIFICATIONS|@webhook|"
        "saves and loads architecture filter with mirror configuration|"
        "loads existing architecture filter from saved mirror configuration"
    )

    master_cell = next(c for c in cells if c.branch == "master")
    assert master_cell.filename == MASTER_NAME
    assert master_cell.test_as == "s3"
    assert master_cell.always_run is False
    assert master_cell.optional is True
    assert master_cell.quay_version is None
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


def test_kind_settings_periodic_uses_interval_keywords() -> None:
    weekly = apply_kind_settings(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="weekly", as_name=None),
    )
    assert weekly["tests"][0]["cron"] == "@weekly"

    daily = apply_kind_settings(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="daily"),
    )
    assert daily["tests"][0]["cron"] == "@daily"

    nightly = apply_kind_settings(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe"}}]},
        _phase0_cell(tier="nightly", as_name=None),
    )
    assert nightly["tests"][0]["cron"] == "@daily"


def test_kind_settings_presubmit_copies_trigger_fields_when_set() -> None:
    presubmit = apply_kind_settings(
        {"tests": [{"steps": {"cluster_profile": "aws-quay-qe", "workflow": "ipi-aws"}}]},
        _phase0_cell(
            test="api-test",
            kind="presubmit",
            tier=None,
            as_name=None,
            always_run=False,
            optional=True,
        ),
    )
    test = presubmit["tests"][0]
    assert "cron" not in test
    assert test["always_run"] is False
    assert test["optional"] is True
    assert "run_if_changed" not in test
    assert "skip_if_only_changed" not in test
    assert test["steps"]["cluster_profile"] == "aws-quay-qe"


def test_kind_settings_presubmit_leaves_unset_trigger_fields_absent() -> None:
    presubmit = apply_kind_settings(
        {"tests": [{"steps": {}}]},
        _phase0_cell(test="api-test", kind="presubmit", tier=None, as_name=None),
    )
    test = presubmit["tests"][0]
    for field_name in ("always_run", "optional", "run_if_changed", "skip_if_only_changed"):
        assert field_name not in test


def test_golden_phase0_bytes() -> None:
    results = generate_all()
    by_name = {filename: config for _cell, filename, config in results}
    assert PHASE0_NAME in by_name
    dumped = dump_config(by_name[PHASE0_NAME])
    assert dumped == FIXTURE.read_text()
    assert dumped.startswith(GENERATED_HEADER)


def test_golden_master_bytes() -> None:
    results = generate_all()
    by_name = {filename: config for _cell, filename, config in results}
    assert MASTER_NAME in by_name
    config = by_name[MASTER_NAME]
    dumped = dump_config(config)
    assert dumped == MASTER_FIXTURE.read_text()
    assert dumped.startswith(GENERATED_HEADER)

    test = config["tests"][0]
    assert "cron" not in test
    assert test["as"] == "s3"
    assert test["optional"] is True
    assert test["always_run"] is False
    assert config["promotion"] == {
        "to": [{"namespace": "quay", "tag": "latest", "tag_by_commit": True}]
    }
    assert "variant" not in config["zz_generated_metadata"]
    assert test["steps"]["dependencies"] == {"QUAY_CI_IMAGE": "pipeline:quay-server"}


def test_mixed_golden_groups_periodic_and_presubmit_into_one_file() -> None:
    results = generate_all(
        matrix_path=MIXED_DIR / "matrix.yaml", templates_dir=MIXED_DIR / "templates"
    )
    assert len(results) == 1
    _cell, filename, config = results[0]
    assert filename == PHASE0_NAME
    tests = config["tests"]
    assert [t["as"] for t in tests] == ["s3-daily", "s3"]
    assert tests[0]["cron"] == "@daily"
    assert "cron" not in tests[1]
    dumped = dump_config(config)
    assert dumped == (MIXED_DIR / "expected.yaml").read_text()


def test_mixed_release_with_real_templates_rejects_incompatible_file_level(tmp_path: Path) -> None:
    matrix = {
        "version": 2,
        "global_defaults": {"image_source": "build", "arch": "amd64", "repo": "quay/quay"},
        "quay": [
            {
                "branch": "redhat-3.18",
                "jobs": [
                    {"tier": "daily", "clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"},
                    {
                        "kind": "presubmit",
                        "clouds": ["aws"],
                        "ocp": ["4.22"],
                        "test": "e2e-install",
                    },
                ],
            }
        ],
    }
    matrix_path = tmp_path / "matrix.yaml"
    matrix_path.write_text(yaml.dump(matrix))
    with pytest.raises(ValueError, match="incompatible file-level inputs"):
        generate_all(matrix_path=matrix_path, templates_dir=GENERATOR_DIR / "templates")


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


def test_check_ignores_unrelated_branch_neighbors(tmp_path: Path) -> None:
    # quay-quay-master.yaml is now the generated/managed master file (layout:
    # base). Exact managed_files ownership (so hand-written neighbours like
    # quay-quay-master__claim.yaml / __omr-*.yaml stay ignored despite sharing
    # the master owned_prefix) is requirement 5, done in bead B.
    assert main(["--output", str(tmp_path)]) == 0
    (tmp_path / "quay-quay-redhat-3.17__aws-ocp422-e2e-install.yaml").write_text("foo: bar\n")
    assert main(["--check", "--output", str(tmp_path)]) == 0


def test_generate_all_rejects_duplicate_as_in_one_file(tmp_path: Path) -> None:
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
      - tier: daily
        clouds: [aws]
        ocp: ["4.22"]
        test: e2e-install
""")
    with pytest.raises(ValueError, match="duplicate as"):
        generate_all(matrix_path=matrix_path, templates_dir=GENERATOR_DIR / "templates")


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


def test_dump_quotes_yaml_special_strings() -> None:
    dumped = dump_config(
        {
            "cron": "@daily",
            "flag": "true",
            "count": "4.22",
            "plain": "s3-daily",
        }
    )
    assert "cron: '@daily'" in dumped
    assert 'flag: "true"' in dumped
    assert 'count: "4.22"' in dumped
    assert "plain: s3-daily" in dumped
    assert yaml.safe_load(dumped) == {
        "cron": "@daily",
        "flag": "true",
        "count": "4.22",
        "plain": "s3-daily",
    }


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


def _matrix_with_job(
    job: dict[str, Any], release_overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    release: dict[str, Any] = {"branch": "redhat-3.18", "jobs": [job]}
    if release_overrides:
        release.update(release_overrides)
    return {
        "version": 2,
        "global_defaults": {"image_source": "build", "arch": "amd64", "repo": "quay/quay"},
        "quay": [release],
    }


def test_kind_must_be_periodic_or_presubmit() -> None:
    matrix = _matrix_with_job(
        {
            "kind": "bogus",
            "tier": "daily",
            "clouds": ["aws"],
            "ocp": ["4.22"],
            "test": "e2e-install",
        }
    )
    with pytest.raises(ValueError, match="kind must be"):
        expand_cells(matrix)


def test_tier_presubmit_is_retired_in_favor_of_kind() -> None:
    matrix = _matrix_with_job(
        {"tier": "presubmit", "clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"}
    )
    with pytest.raises(ValueError, match="kind: presubmit"):
        expand_cells(matrix)


def test_periodic_requires_tier_in_known_set() -> None:
    matrix = _matrix_with_job({"clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"})
    with pytest.raises(ValueError, match="requires tier"):
        expand_cells(matrix)

    matrix = _matrix_with_job(
        {"tier": "hourly", "clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"}
    )
    with pytest.raises(ValueError, match="requires tier"):
        expand_cells(matrix)


def test_presubmit_rejects_tier() -> None:
    matrix = _matrix_with_job(
        {
            "kind": "presubmit",
            "tier": "daily",
            "clouds": ["aws"],
            "ocp": ["4.22"],
            "test": "e2e-install",
        }
    )
    with pytest.raises(ValueError, match="must not set tier"):
        expand_cells(matrix)


def test_periodic_rejects_trigger_fields() -> None:
    matrix = _matrix_with_job(
        {
            "tier": "daily",
            "clouds": ["aws"],
            "ocp": ["4.22"],
            "test": "e2e-install",
            "always_run": True,
        }
    )
    with pytest.raises(ValueError, match="only valid for kind: presubmit"):
        expand_cells(matrix)


def test_presubmit_rejects_run_if_changed_with_skip_if_only_changed() -> None:
    matrix = _matrix_with_job(
        {
            "kind": "presubmit",
            "clouds": ["aws"],
            "ocp": ["4.22"],
            "test": "e2e-install",
            "run_if_changed": "^docs/",
            "skip_if_only_changed": "^docs/",
        }
    )
    with pytest.raises(ValueError, match="mutually exclusive"):
        expand_cells(matrix)


def test_presubmit_rejects_always_run_true_with_filter() -> None:
    matrix = _matrix_with_job(
        {
            "kind": "presubmit",
            "clouds": ["aws"],
            "ocp": ["4.22"],
            "test": "e2e-install",
            "always_run": True,
            "run_if_changed": "^docs/",
        }
    )
    with pytest.raises(ValueError, match="cannot be combined"):
        expand_cells(matrix)


def test_layout_must_be_variant_or_base() -> None:
    matrix = _matrix_with_job(
        {"tier": "daily", "clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"},
        release_overrides={"layout": "bogus"},
    )
    with pytest.raises(ValueError, match="layout must be"):
        expand_cells(matrix)


def test_malformed_branch_still_raises() -> None:
    matrix = _matrix_with_job(
        {"tier": "daily", "clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"},
        release_overrides={"branch": "redhat-x"},
    )
    with pytest.raises(ValueError, match="must look like"):
        expand_cells(matrix)


def test_master_branch_version_is_none() -> None:
    matrix = _matrix_with_job(
        {"kind": "presubmit", "clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"},
        release_overrides={"branch": "master", "layout": "base"},
    )
    cells = expand_cells(matrix)
    assert len(cells) == 1
    assert cells[0].quay_version is None


def test_master_context_has_no_quay_version_key() -> None:
    master_cell = next(
        c
        for c in expand_cells(
            _matrix_with_job(
                {"kind": "presubmit", "clouds": ["aws"], "ocp": ["4.22"], "test": "e2e-install"},
                release_overrides={"branch": "master", "layout": "base"},
            )
        )
    )
    context = master_cell.context()
    for key in ("quay_version", "quay_version_dashed", "operator_channel", "index_image_repo"):
        assert key not in context
