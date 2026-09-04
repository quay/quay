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


def test_oauth_application_maximum_token_count_is_optional_positive_integer():
    schema = CONFIG_SCHEMA["properties"]["OAUTH_APPLICATION_MAXIMUM_TOKEN_COUNT"]

    validate(None, schema)
    validate(1, schema)

    for value in [0, -1, "1"]:
        with pytest.raises(ValidationError):
            validate(value, schema)


def _bootstrap_config_schema():
    property_names = [
        "FEATURE_PROGRAMMATIC_BOOTSTRAP",
        "FEATURE_KUBERNETES_SA_BOOTSTRAP",
        "KUBERNETES_SA_BOOTSTRAP_CONFIG",
        "BOOTSTRAP_TOKEN_OWNER",
    ]
    return {
        "type": "object",
        "allOf": CONFIG_SCHEMA["allOf"],
        "properties": {name: CONFIG_SCHEMA["properties"][name] for name in property_names},
    }


def _valid_kubernetes_sa_bootstrap_config():
    return {
        "REQUIRED_AUDIENCE": "quay-bootstrap",
        "ISSUERS": [{"ISSUER": "https://kubernetes.default.svc"}],
        "AUTHORIZED_SUBJECTS": [
            {
                "ISSUER": "https://kubernetes.default.svc",
                "SUBJECT": "system:serviceaccount:quay-operator:controller-manager",
                "SCOPES": "org:admin repo:create repo:read repo:write",
            }
        ],
        "JWKS_CACHE_TTL_SECONDS": 3600,
        "BOOTSTRAP_TOKEN_MAX_TTL": 86400,
    }


def test_bootstrap_token_owner_required_when_bootstrap_enabled():
    schema = _bootstrap_config_schema()

    validate(
        {
            "FEATURE_PROGRAMMATIC_BOOTSTRAP": False,
            "FEATURE_KUBERNETES_SA_BOOTSTRAP": False,
            "BOOTSTRAP_TOKEN_OWNER": None,
        },
        schema,
    )
    validate(
        {"FEATURE_PROGRAMMATIC_BOOTSTRAP": True, "BOOTSTRAP_TOKEN_OWNER": "admin"},
        schema,
    )
    validate(
        {
            "FEATURE_KUBERNETES_SA_BOOTSTRAP": True,
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": _valid_kubernetes_sa_bootstrap_config(),
            "BOOTSTRAP_TOKEN_OWNER": "admin",
        },
        schema,
    )

    for config in [
        {"FEATURE_PROGRAMMATIC_BOOTSTRAP": True},
        {"FEATURE_PROGRAMMATIC_BOOTSTRAP": True, "BOOTSTRAP_TOKEN_OWNER": None},
        {"FEATURE_PROGRAMMATIC_BOOTSTRAP": True, "BOOTSTRAP_TOKEN_OWNER": ""},
        {
            "FEATURE_KUBERNETES_SA_BOOTSTRAP": True,
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": _valid_kubernetes_sa_bootstrap_config(),
        },
    ]:
        with pytest.raises(ValidationError):
            validate(config, schema)


def test_kubernetes_sa_bootstrap_config_required_only_when_enabled():
    schema = _bootstrap_config_schema()

    validate({"FEATURE_KUBERNETES_SA_BOOTSTRAP": False}, schema)
    validate(
        {
            "FEATURE_KUBERNETES_SA_BOOTSTRAP": True,
            "BOOTSTRAP_TOKEN_OWNER": "admin",
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": _valid_kubernetes_sa_bootstrap_config(),
        },
        schema,
    )

    for config in [
        {
            "FEATURE_KUBERNETES_SA_BOOTSTRAP": True,
            "BOOTSTRAP_TOKEN_OWNER": "admin",
        },
        {
            "FEATURE_KUBERNETES_SA_BOOTSTRAP": True,
            "BOOTSTRAP_TOKEN_OWNER": "admin",
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": None,
        },
    ]:
        with pytest.raises(ValidationError):
            validate(config, schema)


def test_kubernetes_sa_bootstrap_config_accepts_supported_issuer_forms():
    schema = CONFIG_SCHEMA["properties"]["KUBERNETES_SA_BOOTSTRAP_CONFIG"]
    config = _valid_kubernetes_sa_bootstrap_config()
    config["ISSUERS"].append(
        {
            "ISSUER": "https://cluster.example.com",
            "DISCOVERY_ENDPOINT": "https://api.cluster.example.com:6443",
            "CA_CERT_PATH": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
            "BEARER_TOKEN_PATH": "/var/run/secrets/kubernetes.io/serviceaccount/token",
        }
    )

    validate(config, schema)


@pytest.mark.parametrize(
    "subject",
    [
        "system:serviceaccount:default:builder",
        "system:serviceaccount:quay-operator:controller-manager",
        # Single-character namespace/name segments and the 63-character
        # DNS-1123 label boundary are both valid.
        "system:serviceaccount:a:b",
        "system:serviceaccount:" + ("a" * 63) + ":" + ("b" * 63),
    ],
)
def test_kubernetes_sa_bootstrap_config_accepts_valid_subject_names(subject):
    schema = CONFIG_SCHEMA["properties"]["KUBERNETES_SA_BOOTSTRAP_CONFIG"]
    config = _valid_kubernetes_sa_bootstrap_config()
    config["AUTHORIZED_SUBJECTS"] = [
        {
            "ISSUER": "https://kubernetes.default.svc",
            "SUBJECT": subject,
            "SCOPES": "repo:read",
        }
    ]

    validate(config, schema)


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"ISSUERS": [], "AUTHORIZED_SUBJECTS": []},
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "ISSUERS": [{"ISSUER": "http://insecure.example.com"}],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "ISSUERS": [{"ISSUER": "https://cluster.example.com?unexpected=query"}],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "ISSUERS": [{"ISSUER": "https://cluster.example.com:notaport"}],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "ISSUERS": [
                {
                    "ISSUER": "https://cluster.example.com",
                    "DISCOVERY_ENDPOINT": "https://api.cluster.example.com:notaport",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "ISSUERS": [
                {
                    "ISSUER": "https://cluster.example.com",
                    "BEARER_TOKEN_PATH": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "ISSUERS": [
                {
                    "ISSUER": "https://cluster.example.com",
                    "DISCOVERY_ENDPONT": "https://api.cluster.example.com:6443",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "AUTHORIZED_SUBJECTS": [
                {
                    "ISSUER": "https://kubernetes.default.svc",
                    "SUBJECT": "default:builder",
                    "SCOPES": "repo:read",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "AUTHORIZED_SUBJECTS": [
                {
                    "ISSUER": "https://kubernetes.default.svc",
                    "SUBJECT": "system:serviceaccount:default:builder",
                    "SCOPES": "repo:unknown",
                }
            ],
        },
        {**_valid_kubernetes_sa_bootstrap_config(), "JWKS_CACHE_TTL_SECONDS": 0},
        {**_valid_kubernetes_sa_bootstrap_config(), "BOOTSTRAP_TOKEN_MAX_TTL": 0},
        {**_valid_kubernetes_sa_bootstrap_config(), "UNKNOWN_SETTING": True},
        # SUBJECT must be a valid Kubernetes namespace:ServiceAccount pair,
        # not just any non-colon, non-whitespace text.
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "AUTHORIZED_SUBJECTS": [
                {
                    "ISSUER": "https://kubernetes.default.svc",
                    "SUBJECT": "system:serviceaccount:default:Build_Robot",
                    "SCOPES": "repo:read",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "AUTHORIZED_SUBJECTS": [
                {
                    "ISSUER": "https://kubernetes.default.svc",
                    "SUBJECT": "system:serviceaccount:-default:builder",
                    "SCOPES": "repo:read",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "AUTHORIZED_SUBJECTS": [
                {
                    "ISSUER": "https://kubernetes.default.svc",
                    "SUBJECT": "system:serviceaccount:default:builder-",
                    "SCOPES": "repo:read",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "AUTHORIZED_SUBJECTS": [
                {
                    "ISSUER": "https://kubernetes.default.svc",
                    "SUBJECT": "system:serviceaccount:" + ("a" * 64) + ":builder",
                    "SCOPES": "repo:read",
                }
            ],
        },
        {
            **_valid_kubernetes_sa_bootstrap_config(),
            "AUTHORIZED_SUBJECTS": [
                {
                    "ISSUER": "https://kubernetes.default.svc",
                    "SUBJECT": "system:serviceaccount:default:" + ("a" * 64),
                    "SCOPES": "repo:read",
                }
            ],
        },
    ],
)
def test_kubernetes_sa_bootstrap_config_rejects_invalid_values(config):
    schema = CONFIG_SCHEMA["properties"]["KUBERNETES_SA_BOOTSTRAP_CONFIG"]

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


class TestGunicornTimeoutSchema:
    @pytest.mark.parametrize("field", ["GUNICORN_REGISTRY_TIMEOUT", "GUNICORN_WEB_TIMEOUT"])
    def test_accepts_valid_timeout(self, field):
        schema = CONFIG_SCHEMA["properties"][field]
        for value in [30, 60, 300]:
            validate(value, schema)

    @pytest.mark.parametrize("field", ["GUNICORN_REGISTRY_TIMEOUT", "GUNICORN_WEB_TIMEOUT"])
    def test_rejects_timeout_below_minimum(self, field):
        schema = CONFIG_SCHEMA["properties"][field]
        for value in [0, 1, 29]:
            with pytest.raises(ValidationError):
                validate(value, schema)

    @pytest.mark.parametrize("field", ["GUNICORN_REGISTRY_TIMEOUT", "GUNICORN_WEB_TIMEOUT"])
    def test_rejects_timeout_above_maximum(self, field):
        schema = CONFIG_SCHEMA["properties"][field]
        for value in [301, 600, 1800, 3600, 7200]:
            with pytest.raises(ValidationError):
                validate(value, schema)

    @pytest.mark.parametrize("field", ["GUNICORN_REGISTRY_TIMEOUT", "GUNICORN_WEB_TIMEOUT"])
    def test_rejects_non_integer_timeout(self, field):
        schema = CONFIG_SCHEMA["properties"][field]
        for value in ["300", 30.5]:
            with pytest.raises(ValidationError):
                validate(value, schema)

    def test_default_registry_timeout(self):
        assert DefaultConfig.GUNICORN_REGISTRY_TIMEOUT == 30

    def test_default_web_timeout(self):
        assert DefaultConfig.GUNICORN_WEB_TIMEOUT == 30
