"""Branch and job env application."""

from generate import apply_cell_settings, expand_cells, generate_all
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
                        "as": "custom-aws-name",
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
    assert by_cloud["aws"].as_name == "custom-aws-name"
    assert by_cloud["azure"].as_name is None
    assert by_cloud["azure"].test_as == "blob-daily"


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


def test_phase0_names_use_storage_and_tier() -> None:
    generated = list(generate_all())
    assert len(generated) == 1
    cell, _filename, config = generated[0]
    assert (cell.quay_version, cell.cloud) == ("3.18", "aws")
    assert config["tests"][0]["as"] == "s3-daily"


def test_generated_cells_use_template_extra_config() -> None:
    generated = list(generate_all())
    assert len(generated) == 1
    _cell, _filename, config = generated[0]
    env = config["tests"][0]["steps"]["env"]
    extra = env["QUAY_EXTRA_CONFIG"]
    assert env["PLAYWRIGHT_GREP_INVERT"] == QUAY_318_GREP_INVERT
    assert "FEATURE_PROGRAMMATIC_BOOTSTRAP: false" in extra
    assert "FEATURE_IMMUTABLE_TAGS: true" in extra
    assert "FEATURE_SPARSE_INDEX: true" in extra
    assert "FEATURE_QUOTA_NOTIFICATIONS: true" in extra
    assert "FEATURE_OTEL_TRACING: true" in extra
