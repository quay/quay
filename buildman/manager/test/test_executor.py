import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from _init import OVERRIDE_CONFIG_DIRECTORY
from buildman.manager.executor import (
    BuilderExecutor,
    ExecutorException,
    KubernetesPodmanExecutor,
    PopenExecutor,
)


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


class TestPopenExecutor:
    def _make_executor(self, config=None):
        base = {
            "CONTAINER_RUNTIME": "docker",
            "INSECURE": True,
            "BUILDER_BINARY_LOCATION": "/usr/local/bin/quay-builder",
        }
        if config:
            base.update(config)
        return PopenExecutor(base, "localhost:8080", "localhost:8080")

    def test_constructor_stores_args(self):
        executor = self._make_executor()
        assert executor.registry_hostname == "localhost:8080"
        assert executor.manager_hostname == "localhost:8080"
        assert executor._jobs == {}

    def test_grpc_addr_insecure(self):
        executor = self._make_executor({"INSECURE": True})
        assert executor._get_grpc_server_addr() == "localhost:50051"

    def test_grpc_addr_secure(self):
        executor = self._make_executor({"INSECURE": False})
        assert executor._get_grpc_server_addr() == "localhost:55443"

    def test_grpc_addr_secure_strips_existing_port(self):
        executor = PopenExecutor(
            {"INSECURE": False}, "registry.example.com", "build.example.com:443"
        )
        assert executor._get_grpc_server_addr() == "build.example.com:55443"

    def test_running_builders_count_empty(self):
        executor = self._make_executor()
        assert executor.running_builders_count == 0

    def test_running_builders_count_with_running_process(self):
        executor = self._make_executor()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_logpipe = MagicMock()
        executor._jobs["test-id"] = (mock_proc, mock_logpipe)
        assert executor.running_builders_count == 1

    def test_running_builders_count_with_finished_process(self):
        executor = self._make_executor()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_logpipe = MagicMock()
        executor._jobs["test-id"] = (mock_proc, mock_logpipe)
        assert executor.running_builders_count == 0

    def test_running_builders_count_mixed(self):
        executor = self._make_executor()
        running = MagicMock()
        running.poll.return_value = None
        finished = MagicMock()
        finished.poll.return_value = 0
        executor._jobs["running"] = (running, MagicMock())
        executor._jobs["finished"] = (finished, MagicMock())
        assert executor.running_builders_count == 1

    @patch("buildman.manager.executor.subprocess.Popen")
    @patch("buildman.manager.executor.LogPipe")
    def test_start_builder_spawns_process(self, mock_logpipe_cls, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        executor = self._make_executor()
        with patch.dict("os.environ", {"DOCKER_HOST": "unix:///var/run/docker.sock"}):
            with patch("os.path.exists", return_value=True):
                builder_id = executor.start_builder("test-token", "build-uuid-123")

        assert builder_id is not None
        assert builder_id in executor._jobs
        assert executor._jobs[builder_id][0] is mock_proc

        call_args = mock_popen.call_args
        env = call_args[1]["env"]
        assert env["TOKEN"] == "test-token"
        assert env["BUILD_UUID"] == "build-uuid-123"
        assert env["SERVER"] == "localhost:50051"
        assert env["CONTAINER_RUNTIME"] == "docker"
        assert env["INSECURE"] == "true"

    @patch("buildman.manager.executor.subprocess.Popen")
    @patch("buildman.manager.executor.LogPipe")
    def test_start_builder_popen_failure_raises(self, mock_logpipe_cls, mock_popen):
        mock_popen.side_effect = OSError("binary not found")
        executor = self._make_executor()

        with patch.dict("os.environ", {"DOCKER_HOST": "unix:///var/run/docker.sock"}):
            with patch("os.path.exists", return_value=True):
                with pytest.raises(ExecutorException, match="Failed to spawn"):
                    executor.start_builder("token", "uuid")

        mock_logpipe_cls.return_value.close.assert_called_once()

    @patch("buildman.manager.executor.subprocess.Popen")
    @patch("buildman.manager.executor.LogPipe")
    def test_start_builder_passes_debug_env(self, mock_logpipe_cls, mock_popen):
        mock_popen.return_value = MagicMock()
        executor = self._make_executor({"DEBUG": True})

        with patch.dict("os.environ", {"DOCKER_HOST": "unix:///var/run/docker.sock"}):
            with patch("os.path.exists", return_value=True):
                executor.start_builder("token", "uuid")

        env = mock_popen.call_args[1]["env"]
        assert env["DEBUG"] == "true"

    @patch("buildman.manager.executor.subprocess.Popen")
    @patch("buildman.manager.executor.LogPipe")
    def test_start_builder_passes_proxy_env(self, mock_logpipe_cls, mock_popen):
        mock_popen.return_value = MagicMock()
        executor = self._make_executor()

        env_vars = {
            "DOCKER_HOST": "unix:///var/run/docker.sock",
            "HTTP_PROXY": "http://proxy:8080",
            "HTTPS_PROXY": "http://proxy:8443",
            "NO_PROXY": "localhost",
        }
        with patch.dict("os.environ", env_vars):
            with patch("os.path.exists", return_value=True):
                executor.start_builder("token", "uuid")

        env = mock_popen.call_args[1]["env"]
        assert env["HTTP_PROXY"] == "http://proxy:8080"
        assert env["HTTPS_PROXY"] == "http://proxy:8443"
        assert env["NO_PROXY"] == "localhost"

    @patch("buildman.manager.executor.subprocess.Popen")
    @patch("buildman.manager.executor.LogPipe")
    def test_start_builder_docker_socket_fallback(self, mock_logpipe_cls, mock_popen):
        mock_popen.return_value = MagicMock()
        executor = self._make_executor()

        def exists_side_effect(path):
            return path == "/opt/docker.sock"

        with patch.dict("os.environ", {"DOCKER_HOST": "unix:///var/run/docker.sock"}):
            with patch("os.path.exists", side_effect=exists_side_effect):
                with patch("os.path.realpath", return_value="/run/docker.sock"):
                    with patch("os.path.isdir", return_value=True):
                        with patch("os.listdir", return_value=[]):
                            executor.start_builder("token", "uuid")

        env = mock_popen.call_args[1]["env"]
        assert env["DOCKER_HOST"] == "unix:///opt/docker.sock"

    def test_stop_builder_unknown_id_raises(self):
        executor = self._make_executor()
        with pytest.raises(ExecutorException, match="not being tracked"):
            executor.stop_builder("nonexistent-id")

    def test_stop_builder_kills_running_process(self):
        executor = self._make_executor()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_logpipe = MagicMock()
        executor._jobs["test-id"] = (mock_proc, mock_logpipe)

        executor.stop_builder("test-id")

        mock_proc.kill.assert_called_once()
        mock_logpipe.close.assert_called_once()
        assert "test-id" not in executor._jobs

    def test_stop_builder_skips_kill_for_finished_process(self):
        executor = self._make_executor()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_logpipe = MagicMock()
        executor._jobs["test-id"] = (mock_proc, mock_logpipe)

        executor.stop_builder("test-id")

        mock_proc.kill.assert_not_called()
        mock_logpipe.close.assert_called_once()
        assert "test-id" not in executor._jobs

    def test_stop_builder_cleanup_on_kill_failure(self):
        executor = self._make_executor()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.kill.side_effect = OSError("process already dead")
        mock_logpipe = MagicMock()
        executor._jobs["test-id"] = (mock_proc, mock_logpipe)

        with pytest.raises(OSError):
            executor.stop_builder("test-id")

        mock_logpipe.close.assert_called_once()
        assert "test-id" not in executor._jobs
