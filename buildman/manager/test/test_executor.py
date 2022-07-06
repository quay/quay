from buildman.manager.executor import KubernetesPodmanExecutor
from unittest.mock import mock_open, patch
from _init import OVERRIDE_CONFIG_DIRECTORY


def test_podman_executor_adding_cacerts():
    cert = "-----BEGIN CERTIFICATE-----certificate-----END CERTIFICATE-----"
    additional_cert = "-----BEGIN CERTIFICATE-----additionalcertificate-----END CERTIFICATE-----"
    executor_config = {"CA_CERT": cert, "EXTRA_CA_CERTS": ["extra_ca_cert_additional.crt"]}
    with patch("builtins.open", mock_open(read_data=additional_cert)) as mock_file:
        executor = KubernetesPodmanExecutor(
            executor_config=executor_config,
            registry_hostname="test.hostname",
            manager_hostname="build.test.hostname",
        )
        spec = executor._build_job_containers("token", "builduid")
        cert_env = [entry for entry in spec["env"] if entry["name"] == "CA_CERT"]
        assert cert_env[0]["value"] == cert + "\n" + additional_cert
        mock_file.assert_called_with(
            OVERRIDE_CONFIG_DIRECTORY + "extra_ca_cert_additional.crt", "r"
        )
