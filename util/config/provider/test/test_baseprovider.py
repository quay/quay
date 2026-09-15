import yaml

from util.config.provider.baseprovider import import_yaml


def _write_yaml(tmp_path, data):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump(data))
    return str(config_file)


def test_import_yaml_materializes_kubernetes_sa_bootstrap_defaults(tmp_path):
    config_file = _write_yaml(
        tmp_path,
        {
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": {
                "ISSUERS": [{"ISSUER": "https://kubernetes.default.svc"}],
                "AUTHORIZED_SUBJECTS": [
                    {
                        "ISSUER": "https://kubernetes.default.svc",
                        "SUBJECT": "system:serviceaccount:quay-operator:controller-manager",
                        "SCOPES": "org:admin",
                    }
                ],
            }
        },
    )

    config_obj = import_yaml({}, config_file)

    bootstrap_config = config_obj["KUBERNETES_SA_BOOTSTRAP_CONFIG"]
    assert bootstrap_config["REQUIRED_AUDIENCE"] == "quay-bootstrap"
    assert bootstrap_config["JWKS_CACHE_TTL_SECONDS"] == 3600
    assert bootstrap_config["BOOTSTRAP_TOKEN_MAX_TTL"] == 86400


def test_import_yaml_preserves_explicit_kubernetes_sa_bootstrap_overrides(tmp_path):
    config_file = _write_yaml(
        tmp_path,
        {
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": {
                "REQUIRED_AUDIENCE": "custom-audience",
                "ISSUERS": [{"ISSUER": "https://kubernetes.default.svc"}],
                "AUTHORIZED_SUBJECTS": [
                    {
                        "ISSUER": "https://kubernetes.default.svc",
                        "SUBJECT": "system:serviceaccount:quay-operator:controller-manager",
                        "SCOPES": "org:admin",
                    }
                ],
                "JWKS_CACHE_TTL_SECONDS": 60,
                "BOOTSTRAP_TOKEN_MAX_TTL": 120,
            }
        },
    )

    config_obj = import_yaml({}, config_file)

    bootstrap_config = config_obj["KUBERNETES_SA_BOOTSTRAP_CONFIG"]
    assert bootstrap_config["REQUIRED_AUDIENCE"] == "custom-audience"
    assert bootstrap_config["JWKS_CACHE_TTL_SECONDS"] == 60
    assert bootstrap_config["BOOTSTRAP_TOKEN_MAX_TTL"] == 120


def test_import_yaml_without_kubernetes_sa_bootstrap_config_is_noop(tmp_path):
    config_file = _write_yaml(tmp_path, {"SOME_OTHER_KEY": "value"})

    config_obj = import_yaml({}, config_file)

    assert "KUBERNETES_SA_BOOTSTRAP_CONFIG" not in config_obj
