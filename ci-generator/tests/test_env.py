"""Branch and job env application."""

from conftest import PHASE0_MATRIX
from generate import (
    GENERATOR_DIR,
    apply_cell_settings,
    build_config,
    expand_cells,
    generate_all,
)
from model import Cell

QUAY_318_GREP_INVERT = (
    "@auth:OIDC|@auth:LDAP|@feature:QUOTA_NOTIFICATIONS|@webhook|"
    "saves and loads architecture filter with mirror configuration|"
    "loads existing architecture filter from saved mirror configuration"
)


def _cell(**kwargs: object) -> Cell:
    values: dict[str, object] = {
        "org": "quay",
        "repo": "quay",
        "branch": "redhat-3.18",
        "quay_version": "3.18",
        "ocp_version": "4.22",
        "cloud": "aws",
        "test": "e2e-install",
        "tier": "daily",
        "source": "nightly",
    }
    values.update(kwargs)
    return Cell(**values)  # type: ignore[arg-type]


def test_job_env_replaces_branch_env_keys() -> None:
    matrix = {
        "version": 2,
        "global_defaults": {
            "image_source": "build",
            "arch": "amd64",
            "repo": "quay/quay",
        },
        "quay": [
            {
                "branch": "redhat-3.16",
                "env": {
                    "PLAYWRIGHT_GREP_INVERT": "branch",
                    "QUAY_EXTRA_CONFIG": "shared",
                },
                "jobs": [
                    {
                        "tier": "daily",
                        "source": "nightly",
                        "clouds": ["gcp"],
                        "ocp": ["4.22"],
                        "test": "e2e-install",
                        "env": {"PLAYWRIGHT_GREP_INVERT": "job"},
                    }
                ],
            }
        ],
    }
    cells = expand_cells(matrix)
    assert len(cells) == 1
    assert cells[0].env["PLAYWRIGHT_GREP_INVERT"] == "job"
    assert cells[0].env["QUAY_EXTRA_CONFIG"] == "shared"


def test_job_as_applies_to_split_row_only() -> None:
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
                        "tier": "daily",
                        "source": "nightly",
                        "clouds": ["aws"],
                        "ocp": ["4.22"],
                        "test": "e2e-install",
                        "as": "custom-aws-name",
                    },
                    {
                        "tier": "daily",
                        "source": "nightly",
                        "clouds": ["azure"],
                        "ocp": ["4.22"],
                        "test": "e2e-install",
                    },
                ],
            }
        ],
    }
    cells = expand_cells(matrix)
    by_cloud = {cell.cloud: cell for cell in cells}
    assert by_cloud["aws"].as_name == "custom-aws-name"
    assert by_cloud["azure"].as_name is None
    assert by_cloud["azure"].test_as == "azure-blob-nightly"


def test_cell_settings_overwrite_as_and_env() -> None:
    config = {
        "tests": [
            {
                "as": "derived",
                "steps": {"env": {"KEEP": "yes", "PLAYWRIGHT_GREP_INVERT": "old"}},
            }
        ]
    }
    merged = apply_cell_settings(
        config,
        _cell(
            as_name="custom-aws-name",
            env={"PLAYWRIGHT_GREP_INVERT": "new"},
        ),
    )
    assert merged["tests"][0]["as"] == "custom-aws-name"
    assert merged["tests"][0]["steps"]["env"]["KEEP"] == "yes"
    assert merged["tests"][0]["steps"]["env"]["PLAYWRIGHT_GREP_INVERT"] == "new"


def test_periodic_names_use_cloud_storage_source() -> None:
    generated, _retired = generate_all()
    assert len(generated) == 4
    group, _filename, config = next(
        g for g in generated if g[0][0].branch == "redhat-3.18" and g[0][0].ocp_version == "4.22"
    )
    cell = group[0]
    assert (cell.quay_version, cell.cloud) == ("3.18", "aws")
    assert config["tests"][0]["as"] == "aws-s3-nightly"


def test_source_nightly_env() -> None:
    cell = _cell(source="nightly")
    config = build_config(cell, GENERATOR_DIR / "templates")
    env = config["tests"][0]["steps"]["env"]
    assert env["QUAY_OPERATOR_SOURCE"] == "fbc-operator-catalog"
    assert env["QUAY_INDEX_IMAGE_REPO"] == (
        "quay.io/redhat-user-workloads/quay-eng-tenant/stable-3-18-v4-22"
    )
    assert env["QUAY_OPERATOR_CHANNEL"] == "stable-3.18"


def test_source_stable_env() -> None:
    cell = _cell(source="stable")
    config = build_config(cell, GENERATOR_DIR / "templates")
    env = config["tests"][0]["steps"]["env"]
    assert env["QUAY_OPERATOR_SOURCE"] == "redhat-operators"
    assert env["QUAY_OPERATOR_CHANNEL"] == "stable-3.18"
    assert "QUAY_INDEX_IMAGE_REPO" not in env


def test_generated_cells_use_template_extra_config() -> None:
    generated, _retired = generate_all(matrix_path=PHASE0_MATRIX)
    assert len(generated) == 1
    _group, _filename, config = generated[0]
    env = config["tests"][0]["steps"]["env"]
    extra = env["QUAY_EXTRA_CONFIG"]
    assert env["PLAYWRIGHT_GREP_INVERT"] == QUAY_318_GREP_INVERT
    assert "FEATURE_PROGRAMMATIC_BOOTSTRAP: false" in extra
    assert "FEATURE_IMMUTABLE_TAGS: true" in extra
    assert "FEATURE_SPARSE_INDEX: true" in extra
    assert "FEATURE_QUOTA_NOTIFICATIONS: true" in extra
    assert "FEATURE_OTEL_TRACING: true" in extra
