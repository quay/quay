"""Branch and job env application."""

from generate import apply_cell_settings, expand_cells, generate_all
from model import Cell


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
                        "clouds": ["aws"],
                        "ocp": ["4.22"],
                        "test": "e2e-install",
                        "as": "aws-s3-3-18-nightly-4-22",
                    },
                    {
                        "tier": "daily",
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
    assert by_cloud["aws"].as_name == "aws-s3-3-18-nightly-4-22"
    assert by_cloud["azure"].as_name is None
    assert by_cloud["azure"].test_as == "azure-blob-3-18-daily-4-22"


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
            as_name="aws-s3-3-18-nightly-4-22",
            env={"PLAYWRIGHT_GREP_INVERT": "new"},
        ),
    )
    assert merged["tests"][0]["as"] == "aws-s3-3-18-nightly-4-22"
    assert merged["tests"][0]["steps"]["env"]["KEEP"] == "yes"
    assert merged["tests"][0]["steps"]["env"]["PLAYWRIGHT_GREP_INVERT"] == "new"


def test_phase0_names_are_version_specific() -> None:
    by_key = {
        (cell.quay_version, cell.cloud): config["tests"][0]["as"]
        for cell, _filename, config in generate_all()
    }
    assert by_key[("3.18", "aws")] == "aws-s3-3-18-nightly-4-22"
    assert by_key[("3.18", "gcp")] == "gcp-gcs-3-18-nightly-4-22"
    assert by_key[("3.18", "azure")] == "azure-blob-3-18-daily-4-22"
    assert by_key[("3.17", "gcp")] == "gcp-gcs-3-17-daily-4-22"
    assert by_key[("3.17", "azure")] == "azure-blob-3-17-daily-4-22"
    assert by_key[("3.16", "gcp")] == "gcp-gcs-3-16-daily-4-22"
    assert by_key[("3.16", "azure")] == "azure-blob-3-16-daily-4-22"


def test_older_branches_replace_extra_config_without_otel() -> None:
    by_key = {(cell.quay_version, cell.cloud): config for cell, _filename, config in generate_all()}
    aws = by_key[("3.18", "aws")]["tests"][0]["steps"]["env"]
    assert "FEATURE_OTEL_TRACING: true" in aws["QUAY_EXTRA_CONFIG"]
    gcp_317 = by_key[("3.17", "gcp")]["tests"][0]["steps"]["env"]
    assert "FEATURE_OTEL_TRACING" not in gcp_317["QUAY_EXTRA_CONFIG"]
    assert gcp_317["PLAYWRIGHT_GREP_INVERT"] == "@auth:OIDC|@auth:LDAP"
    azure_316 = by_key[("3.16", "azure")]["tests"][0]["steps"]["env"]
    assert "FEATURE_OTEL_TRACING" not in azure_316["QUAY_EXTRA_CONFIG"]
    assert "FEATURE_IMMUTABLE_TAGS" not in azure_316["QUAY_EXTRA_CONFIG"]
