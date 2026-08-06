import pytest

from util.config.provider.baseprovider import InvalidConfigException, import_yaml


def test_import_yaml_rejects_bootstrap_token_scope_list(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("BOOTSTRAP_TOKEN_SCOPE:\n" "  - repo:read\n" "  - repo:write\n")

    with pytest.raises(
        InvalidConfigException,
        match="BOOTSTRAP_TOKEN_SCOPE must be a space-separated string, not a YAML list",
    ):
        import_yaml({}, str(config_file))


def test_import_yaml_accepts_bootstrap_token_scope_string(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('BOOTSTRAP_TOKEN_SCOPE: "repo:read repo:write"\n')

    config = import_yaml({}, str(config_file))

    assert config["BOOTSTRAP_TOKEN_SCOPE"] == "repo:read repo:write"
