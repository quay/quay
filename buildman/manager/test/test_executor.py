import json
from unittest.mock import mock_open, patch

import pytest

from _init import OVERRIDE_CONFIG_DIRECTORY
from buildman.manager.executor import BuilderExecutor, KubernetesPodmanExecutor


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


@pytest.mark.parametrize(
    "executor_config,expected_quay_builder_unit_contents",
    [
        (
            {
                "CONTAINER_RUNTIME": "docker",
            },
            """[Unit]
Wants=docker.service network-online.target
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
TimeoutStartSec=10800
TimeoutStopSec=2000

ExecStartPre=/usr/bin/docker login -u quay_username -p quay_password quay.io
ExecStart=/usr/bin/docker run --user 0 --rm --net=host --privileged --env-file /root/overrides.list -v /var/run/docker.sock:/var/run/docker.sock -v /etc/pki/ca-trust-source/anchors:/certs --name quay-builder quay.io/example/quay-builder:worker_tag
ExecStopPost=/bin/sh -xc "/bin/sleep 120; /usr/bin/systemctl --no-block poweroff"

[Install]
WantedBy=multi-user.target""",
        ),
        (
            {
                "CONTAINER_RUNTIME": "podman",
            },
            """[Unit]
Wants=podman.service network-online.target
After=podman.service network-online.target
Requires=podman.service

[Service]
Type=oneshot
TimeoutStartSec=10800
TimeoutStopSec=2000

ExecStartPre=/usr/bin/podman login -u quay_username -p quay_password quay.io
ExecStart=/usr/bin/podman run --user 0 --rm --privileged --env-file /root/overrides.list -v /var/run/podman/podman.sock:/var/run/podman/podman.sock -v /etc/pki/ca-trust-source/anchors:/certs -e CONTAINER_RUNTIME=podman -e DOCKER_HOST=unix:/var/run/podman/podman.sock --name quay-builder quay.io/example/quay-builder:worker_tag
ExecStopPost=/bin/sh -xc "/bin/sleep 120; /usr/bin/systemctl --no-block poweroff"

[Install]
WantedBy=multi-user.target""",
        ),
        (
            {
                "CONTAINER_RUNTIME": "podman",
                "MAX_LIFETIME_S": 7200,
                "DEBUG": True,
            },
            """[Unit]
Wants=podman.service network-online.target
After=podman.service network-online.target
Requires=podman.service

[Service]
Type=oneshot
TimeoutStartSec=7200
TimeoutStopSec=2000

ExecStartPre=/usr/bin/podman login -u quay_username -p quay_password quay.io
ExecStart=/usr/bin/podman run --user 0 --rm --privileged --env-file /root/overrides.list -v /var/run/podman/podman.sock:/var/run/podman/podman.sock -v /etc/pki/ca-trust-source/anchors:/certs -e CONTAINER_RUNTIME=podman -e DOCKER_HOST=unix:/var/run/podman/podman.sock --name quay-builder quay.io/example/quay-builder:worker_tag

[Install]
WantedBy=multi-user.target""",
        ),
    ],
)
def test_builder_cloud_config(executor_config, expected_quay_builder_unit_contents):
    executor_config = {
        "CA_CERT": b"ca_cert",
        "QUAY_PASSWORD": "quay_password",
        "QUAY_USERNAME": "quay_username",
        "WORKER_IMAGE": "quay.io/example/quay-builder",
        "WORKER_TAG": "worker_tag",
    } | executor_config
    executor = BuilderExecutor(executor_config, "registry_hostname", "manager_hostname")
    generated_cloud_config_json = executor.generate_cloud_config(
        "token", "build_uuid", "manager_hostname"
    )
    generated_cloud_config = json.loads(generated_cloud_config_json)
    quay_builder_unit = generated_cloud_config["systemd"]["units"][0]
    assert quay_builder_unit["name"] == "quay-builder.service"
    assert quay_builder_unit["enabled"]
    assert quay_builder_unit["contents"] == expected_quay_builder_unit_contents
