import pytest
from jsonschema import ValidationError, validate

from auth.scopes import validate_scope_string
from config import DefaultConfig
from util.config.schema import CONFIG_SCHEMA, INTERNAL_ONLY_PROPERTIES


def test_ensure_schema_defines_all_fields():
    for key in (key for key in vars(DefaultConfig) if key.isupper()):
        has_key = key in CONFIG_SCHEMA["properties"] or key in INTERNAL_ONLY_PROPERTIES
        assert has_key, "Property `%s` is missing from config schema" % key


def test_bootstrap_token_expiration_must_be_positive():
    schema = CONFIG_SCHEMA["properties"]["BOOTSTRAP_TOKEN_EXPIRATION"]

    validate(1, schema)

    for value in [0, -1]:
        with pytest.raises(ValidationError):
            validate(value, schema)


def test_bootstrap_token_owner_required_when_programmatic_bootstrap_enabled():
    schema = {
        "type": "object",
        "allOf": CONFIG_SCHEMA["allOf"],
        "properties": {
            "FEATURE_PROGRAMMATIC_BOOTSTRAP": CONFIG_SCHEMA["properties"][
                "FEATURE_PROGRAMMATIC_BOOTSTRAP"
            ],
            "BOOTSTRAP_TOKEN_OWNER": CONFIG_SCHEMA["properties"]["BOOTSTRAP_TOKEN_OWNER"],
        },
    }

    validate({"FEATURE_PROGRAMMATIC_BOOTSTRAP": False, "BOOTSTRAP_TOKEN_OWNER": None}, schema)
    validate({"FEATURE_PROGRAMMATIC_BOOTSTRAP": True, "BOOTSTRAP_TOKEN_OWNER": "admin"}, schema)

    for config in [
        {"FEATURE_PROGRAMMATIC_BOOTSTRAP": True},
        {"FEATURE_PROGRAMMATIC_BOOTSTRAP": True, "BOOTSTRAP_TOKEN_OWNER": None},
        {"FEATURE_PROGRAMMATIC_BOOTSTRAP": True, "BOOTSTRAP_TOKEN_OWNER": ""},
    ]:
        with pytest.raises(ValidationError):
            validate(config, schema)


@pytest.mark.parametrize(
    "value",
    [
        "/var/lib/quay/quay-machine-token.json",
        "/tmp/token.json",
    ],
)
def test_bootstrap_token_path_accepts_absolute_paths(value):
    schema = CONFIG_SCHEMA["properties"]["BOOTSTRAP_TOKEN_PATH"]

    validate(value, schema)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "../../../etc/shadow",
        "var/lib/quay/token.json",
        "/tmp/token\x00.json",
    ],
)
def test_bootstrap_token_path_rejects_unsafe_paths(value):
    schema = CONFIG_SCHEMA["properties"]["BOOTSTRAP_TOKEN_PATH"]

    with pytest.raises(ValidationError):
        validate(value, schema)


def test_default_bootstrap_token_scope_uses_valid_oauth_scopes():
    schema = CONFIG_SCHEMA["properties"]["BOOTSTRAP_TOKEN_SCOPE"]

    validate(DefaultConfig.BOOTSTRAP_TOKEN_SCOPE, schema)
    assert validate_scope_string(DefaultConfig.BOOTSTRAP_TOKEN_SCOPE)

    for value in ["", "a" * 1025]:
        with pytest.raises(ValidationError):
            validate(value, schema)


def test_programmatic_token_k8s_defaults_validate():
    validate(
        DefaultConfig.PROGRAMMATIC_TOKEN_K8S_SECRET,
        CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_SECRET"],
    )
    validate(
        DefaultConfig.PROGRAMMATIC_TOKEN_K8S_KEY,
        CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_KEY"],
    )
    validate(
        DefaultConfig.PROGRAMMATIC_TOKEN_K8S_NAMESPACE,
        CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_NAMESPACE"],
    )


@pytest.mark.parametrize(
    "value",
    [None, "/var/lib/quay/bootstrap-token/token.json", "/tmp/token.json"],
)
def test_programmatic_token_path_accepts_null_and_absolute_paths(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_PATH"]

    validate(value, schema)


@pytest.mark.parametrize(
    "value", ["", "../token.json", "var/lib/quay/token.json", "/tmp/token\x00.json"]
)
def test_programmatic_token_path_rejects_unsafe_paths(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_PATH"]

    with pytest.raises(ValidationError):
        validate(value, schema)


@pytest.mark.parametrize(
    "value",
    [None, "bootstrap-token", "q", "q1-token", "registry.example-bootstrap-token"],
)
def test_programmatic_token_k8s_secret_accepts_valid_dns_subdomains(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_SECRET"]

    validate(value, schema)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "Bootstrap",
        "bootstrap_token",
        "-bootstrap",
        "bootstrap-",
        "bootstrap..token",
        "a" * 64,
        "a" * 254,
    ],
)
def test_programmatic_token_k8s_secret_rejects_invalid_dns_subdomains(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_SECRET"]

    with pytest.raises(ValidationError):
        validate(value, schema)


@pytest.mark.parametrize("value", ["token.json", "custom-token_json.1", "TOKEN.JSON"])
def test_programmatic_token_k8s_key_accepts_valid_secret_data_keys(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_KEY"]

    validate(value, schema)


@pytest.mark.parametrize("value", ["", "token/json", "../token.json", "token json"])
def test_programmatic_token_k8s_key_rejects_invalid_secret_data_keys(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_KEY"]

    with pytest.raises(ValidationError):
        validate(value, schema)


@pytest.mark.parametrize("value", [None, "quay-enterprise", "q", "q1-token"])
def test_programmatic_token_k8s_namespace_accepts_valid_dns_labels(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_NAMESPACE"]

    validate(value, schema)


@pytest.mark.parametrize(
    "value",
    ["", "Quay", "quay_enterprise", "-quay", "quay-", "a" * 64],
)
def test_programmatic_token_k8s_namespace_rejects_invalid_dns_labels(value):
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_K8S_NAMESPACE"]

    with pytest.raises(ValidationError):
        validate(value, schema)
