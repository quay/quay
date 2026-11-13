import pytest

from util.config.provider.baseprovider import InvalidConfigException, import_yaml


@pytest.mark.parametrize(
    "value",
    ["- repo:read\n  - repo:write", "42", "true", "null"],
)
def test_import_yaml_rejects_non_string_bootstrap_token_scope(tmp_path, value):
    config_file = tmp_path / "config.yaml"
    if value.startswith("-"):
        config_file.write_text(f"BOOTSTRAP_TOKEN_SCOPE:\n  {value}\n")
    else:
        config_file.write_text(f"BOOTSTRAP_TOKEN_SCOPE: {value}\n")

    config = {"EXISTING_CONFIG": "preserved"}

    with pytest.raises(
        InvalidConfigException,
        match="BOOTSTRAP_TOKEN_SCOPE must be a space-separated string",
    ):
        import_yaml(config, str(config_file))

    assert config == {"EXISTING_CONFIG": "preserved"}


def test_import_yaml_accepts_bootstrap_token_scope_string(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('BOOTSTRAP_TOKEN_SCOPE: "repo:read repo:write"\n')

    config = import_yaml({}, str(config_file))

    assert config["BOOTSTRAP_TOKEN_SCOPE"] == "repo:read repo:write"
