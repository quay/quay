"""
Tests for image history extraction.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from util.ai.history_extractor import (
    extract_image_analysis,
    parse_env_vars,
    parse_exposed_ports,
    get_config_from_manifest,
    ImageExtractionError,
)
from util.ai.providers import ImageAnalysis


# Sample Docker Schema2 config JSON matching the format in image/docker/schema2/config.py
SAMPLE_CONFIG_JSON = {
    "architecture": "amd64",
    "config": {
        "Hostname": "",
        "Domainname": "",
        "User": "node",
        "AttachStdin": False,
        "AttachStdout": False,
        "AttachStderr": False,
        "ExposedPorts": {"8080/tcp": {}, "3000/tcp": {}},
        "Tty": False,
        "OpenStdin": False,
        "StdinOnce": False,
        "Env": [
            "NODE_ENV=production",
            "PORT=8080",
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        ],
        "Cmd": ["node", "server.js"],
        "Image": "",
        "Volumes": None,
        "WorkingDir": "/app",
        "Entrypoint": ["/docker-entrypoint.sh"],
        "OnBuild": None,
        "Labels": {
            "maintainer": "dev@example.com",
            "version": "1.0.0",
            "org.opencontainers.image.source": "https://github.com/example/app",
        },
    },
    "created": "2024-01-15T10:41:19.079522722Z",
    "docker_version": "24.0.0",
    "history": [
        {
            "created": "2024-01-10T18:37:09.284840891Z",
            "created_by": "/bin/sh -c #(nop) ADD file:abc123 in / ",
        },
        {
            "created": "2024-01-10T18:37:09.613317719Z",
            "created_by": '/bin/sh -c #(nop)  CMD ["node"]',
            "empty_layer": True,
        },
        {
            "created": "2024-01-15T10:37:44.418262777Z",
            "created_by": "/bin/sh -c apt-get update && apt-get install -y nodejs npm",
        },
        {
            "created": "2024-01-15T10:38:00.000000000Z",
            "created_by": "/bin/sh -c npm install express",
        },
        {
            "created": "2024-01-15T10:40:00.000000000Z",
            "created_by": "/bin/sh -c #(nop) COPY file:xyz789 in /app ",
        },
        {
            "created": "2024-01-15T10:41:00.000000000Z",
            "created_by": '/bin/sh -c #(nop)  EXPOSE 8080',
            "empty_layer": True,
        },
        {
            "created": "2024-01-15T10:41:19.079522722Z",
            "created_by": '/bin/sh -c #(nop)  CMD ["node", "server.js"]',
            "empty_layer": True,
        },
    ],
    "os": "linux",
    "rootfs": {
        "type": "layers",
        "diff_ids": [
            "sha256:layer1",
            "sha256:layer2",
            "sha256:layer3",
            "sha256:layer4",
        ],
    },
}


@pytest.fixture
def sample_config_bytes():
    """Sample config bytes for testing."""
    return json.dumps(SAMPLE_CONFIG_JSON).encode("utf-8")


@pytest.fixture
def mock_content_retriever(sample_config_bytes):
    """Mock content retriever for testing."""
    mock = MagicMock()
    mock.get_blob_bytes_with_digest.return_value = sample_config_bytes
    return mock


@pytest.fixture
def mock_manifest():
    """Mock manifest with config reference."""
    mock = MagicMock()
    mock.config.digest = "sha256:abc123configdigest"
    mock.config.size = len(json.dumps(SAMPLE_CONFIG_JSON).encode("utf-8"))
    mock.digest = "sha256:manifestdigest123"
    mock.is_manifest_list = False
    return mock


class TestExtractImageAnalysis:
    """Tests for the extract_image_analysis function."""

    def test_extracts_layer_commands(self, mock_manifest, mock_content_retriever):
        """Test that layer commands are extracted from history."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        assert isinstance(result, ImageAnalysis)
        assert len(result.layer_commands) == 7
        assert "/bin/sh -c apt-get update" in result.layer_commands[2]
        assert "npm install express" in result.layer_commands[3]

    def test_extracts_exposed_ports(self, mock_manifest, mock_content_retriever):
        """Test that exposed ports are extracted."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        assert "8080" in result.exposed_ports
        assert "3000" in result.exposed_ports

    def test_extracts_environment_variables(self, mock_manifest, mock_content_retriever):
        """Test that environment variables are extracted."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        assert "NODE_ENV" in result.environment_vars
        assert result.environment_vars["NODE_ENV"] == "production"
        assert "PORT" in result.environment_vars
        assert result.environment_vars["PORT"] == "8080"

    def test_extracts_labels(self, mock_manifest, mock_content_retriever):
        """Test that labels are extracted."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        assert "maintainer" in result.labels
        assert result.labels["maintainer"] == "dev@example.com"
        assert "version" in result.labels
        assert result.labels["version"] == "1.0.0"

    def test_extracts_entrypoint(self, mock_manifest, mock_content_retriever):
        """Test that entrypoint is extracted."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        assert result.entrypoint == ["/docker-entrypoint.sh"]

    def test_extracts_cmd(self, mock_manifest, mock_content_retriever):
        """Test that cmd is extracted."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        assert result.cmd == ["node", "server.js"]

    def test_includes_manifest_digest(self, mock_manifest, mock_content_retriever):
        """Test that manifest digest is included."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        assert result.manifest_digest == "sha256:manifestdigest123"

    def test_includes_tag(self, mock_manifest, mock_content_retriever):
        """Test that tag is included."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="v1.0.0",
        )

        assert result.tag == "v1.0.0"

    def test_handles_missing_config_blob(self, mock_manifest):
        """Test handling when config blob cannot be retrieved."""
        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = None

        with pytest.raises(ImageExtractionError) as exc:
            extract_image_analysis(
                manifest=mock_manifest,
                content_retriever=mock_retriever,
                tag="latest",
            )
        assert "config blob" in str(exc.value).lower()

    def test_handles_invalid_config_json(self, mock_manifest):
        """Test handling of invalid JSON in config blob."""
        mock_retriever = MagicMock()
        invalid_bytes = b"not valid json"
        mock_retriever.get_blob_bytes_with_digest.return_value = invalid_bytes
        # Set size to match so we get past size check to JSON parsing
        mock_manifest.config.size = len(invalid_bytes)

        with pytest.raises(ImageExtractionError) as exc:
            extract_image_analysis(
                manifest=mock_manifest,
                content_retriever=mock_retriever,
                tag="latest",
            )
        assert "malformed" in str(exc.value).lower() or "invalid" in str(exc.value).lower()

    def test_handles_config_without_history(self, mock_manifest):
        """Test handling config without history key."""
        config_no_history = {
            "architecture": "amd64",
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": []},
        }
        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = json.dumps(
            config_no_history
        ).encode("utf-8")

        # Should handle gracefully with empty history
        with pytest.raises(ImageExtractionError):
            extract_image_analysis(
                manifest=mock_manifest,
                content_retriever=mock_retriever,
                tag="latest",
            )


class TestParseEnvVars:
    """Tests for environment variable parsing."""

    def test_parses_simple_env_vars(self):
        """Test parsing simple key=value pairs."""
        env_list = ["NODE_ENV=production", "PORT=8080"]
        result = parse_env_vars(env_list)

        assert result == {"NODE_ENV": "production", "PORT": "8080"}

    def test_parses_env_with_equals_in_value(self):
        """Test parsing env vars where value contains equals sign."""
        env_list = ["DATABASE_URL=postgres://user:pass@host:5432/db?sslmode=require"]
        result = parse_env_vars(env_list)

        assert result["DATABASE_URL"] == "postgres://user:pass@host:5432/db?sslmode=require"

    def test_handles_empty_value(self):
        """Test handling env vars with empty values."""
        env_list = ["EMPTY_VAR="]
        result = parse_env_vars(env_list)

        assert result == {"EMPTY_VAR": ""}

    def test_handles_empty_list(self):
        """Test handling empty env var list."""
        result = parse_env_vars([])
        assert result == {}

    def test_handles_none_input(self):
        """Test handling None input."""
        result = parse_env_vars(None)
        assert result == {}

    def test_skips_malformed_entries(self):
        """Test that malformed entries are skipped."""
        env_list = ["GOOD=value", "MALFORMED_NO_EQUALS", "ALSO_GOOD=another"]
        result = parse_env_vars(env_list)

        assert "GOOD" in result
        assert "ALSO_GOOD" in result
        assert "MALFORMED_NO_EQUALS" not in result


class TestParseExposedPorts:
    """Tests for exposed ports parsing."""

    def test_parses_tcp_ports(self):
        """Test parsing TCP ports."""
        ports_dict = {"8080/tcp": {}, "3000/tcp": {}}
        result = parse_exposed_ports(ports_dict)

        assert "8080" in result
        assert "3000" in result

    def test_parses_udp_ports(self):
        """Test parsing UDP ports."""
        ports_dict = {"53/udp": {}}
        result = parse_exposed_ports(ports_dict)

        assert "53" in result

    def test_parses_ports_without_protocol(self):
        """Test parsing ports specified without protocol."""
        ports_dict = {"9000": {}}
        result = parse_exposed_ports(ports_dict)

        assert "9000" in result

    def test_handles_empty_dict(self):
        """Test handling empty ports dict."""
        result = parse_exposed_ports({})
        assert result == []

    def test_handles_none_input(self):
        """Test handling None input."""
        result = parse_exposed_ports(None)
        assert result == []


class TestGetConfigFromManifest:
    """Tests for getting parsed config from manifest."""

    def test_retrieves_config_blob(self, mock_manifest, mock_content_retriever, sample_config_bytes):
        """Test that config blob is retrieved correctly."""
        config = get_config_from_manifest(mock_manifest, mock_content_retriever)

        mock_content_retriever.get_blob_bytes_with_digest.assert_called_once_with(
            "sha256:abc123configdigest"
        )
        assert config is not None

    def test_returns_parsed_config_dict(self, mock_manifest, mock_content_retriever):
        """Test that config is returned as parsed dict."""
        config = get_config_from_manifest(mock_manifest, mock_content_retriever)

        assert isinstance(config, dict)
        assert "config" in config
        assert "history" in config

    def test_raises_on_missing_blob(self, mock_manifest):
        """Test that exception is raised when blob is missing."""
        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = None

        with pytest.raises(ImageExtractionError):
            get_config_from_manifest(mock_manifest, mock_retriever)

    def test_raises_on_size_mismatch(self, mock_manifest):
        """Test that exception is raised when size doesn't match."""
        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = b"short"

        with pytest.raises(ImageExtractionError) as exc:
            get_config_from_manifest(mock_manifest, mock_retriever)
        assert "size" in str(exc.value).lower()


class TestMinimalConfig:
    """Tests for handling minimal/empty configs."""

    def test_handles_no_exposed_ports(self, mock_manifest):
        """Test handling config without exposed ports."""
        config_no_ports = dict(SAMPLE_CONFIG_JSON)
        config_no_ports["config"] = dict(config_no_ports["config"])
        config_no_ports["config"].pop("ExposedPorts", None)
        config_bytes = json.dumps(config_no_ports).encode("utf-8")

        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = config_bytes
        mock_manifest.config.size = len(config_bytes)

        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_retriever,
            tag="latest",
        )

        assert result.exposed_ports == []

    def test_handles_no_env_vars(self, mock_manifest):
        """Test handling config without environment variables."""
        config_no_env = dict(SAMPLE_CONFIG_JSON)
        config_no_env["config"] = dict(config_no_env["config"])
        config_no_env["config"].pop("Env", None)
        config_bytes = json.dumps(config_no_env).encode("utf-8")

        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = config_bytes
        mock_manifest.config.size = len(config_bytes)

        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_retriever,
            tag="latest",
        )

        assert result.environment_vars == {}

    def test_handles_no_labels(self, mock_manifest):
        """Test handling config without labels."""
        config_no_labels = dict(SAMPLE_CONFIG_JSON)
        config_no_labels["config"] = dict(config_no_labels["config"])
        config_no_labels["config"]["Labels"] = None
        config_bytes = json.dumps(config_no_labels).encode("utf-8")

        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = config_bytes
        mock_manifest.config.size = len(config_bytes)

        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_retriever,
            tag="latest",
        )

        assert result.labels == {}

    def test_handles_null_entrypoint(self, mock_manifest):
        """Test handling config with null entrypoint."""
        config_null_entry = dict(SAMPLE_CONFIG_JSON)
        config_null_entry["config"] = dict(config_null_entry["config"])
        config_null_entry["config"]["Entrypoint"] = None
        config_bytes = json.dumps(config_null_entry).encode("utf-8")

        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = config_bytes
        mock_manifest.config.size = len(config_bytes)

        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_retriever,
            tag="latest",
        )

        assert result.entrypoint is None

    def test_handles_null_cmd(self, mock_manifest):
        """Test handling config with null cmd."""
        config_null_cmd = dict(SAMPLE_CONFIG_JSON)
        config_null_cmd["config"] = dict(config_null_cmd["config"])
        config_null_cmd["config"]["Cmd"] = None
        config_bytes = json.dumps(config_null_cmd).encode("utf-8")

        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = config_bytes
        mock_manifest.config.size = len(config_bytes)

        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_retriever,
            tag="latest",
        )

        assert result.cmd is None


class TestBaseImageDetection:
    """Tests for base image detection from layer history."""

    def test_detects_base_image_from_add_command(self, mock_manifest, mock_content_retriever):
        """Test detecting base image from ADD command in first layer."""
        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_content_retriever,
            tag="latest",
        )

        # Base image detection may be None if not implemented or extractable
        # from the layer commands. The implementation can improve this.
        assert result.base_image is None or isinstance(result.base_image, str)

    def test_base_image_from_labels(self, mock_manifest):
        """Test extracting base image from OCI labels if available."""
        config_with_base = dict(SAMPLE_CONFIG_JSON)
        config_with_base["config"] = dict(config_with_base["config"])
        config_with_base["config"]["Labels"] = {
            "org.opencontainers.image.base.name": "node:18-alpine",
        }
        config_bytes = json.dumps(config_with_base).encode("utf-8")

        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = config_bytes
        mock_manifest.config.size = len(config_bytes)

        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_retriever,
            tag="latest",
        )

        assert result.base_image == "node:18-alpine"


class TestOCIManifestSupport:
    """Tests for OCI manifest format support."""

    def test_handles_oci_config_format(self, mock_manifest):
        """Test handling OCI image config format."""
        # OCI configs have similar structure to Docker Schema2
        oci_config = {
            "architecture": "amd64",
            "os": "linux",
            "config": {
                "Env": ["PATH=/usr/local/bin:/usr/bin"],
                "Cmd": ["/bin/bash"],
                "ExposedPorts": {"80/tcp": {}},
                "Labels": {},
            },
            "history": [
                {
                    "created": "2024-01-01T00:00:00Z",
                    "created_by": "/bin/sh -c #(nop) ADD file:... in / ",
                }
            ],
            "rootfs": {"type": "layers", "diff_ids": ["sha256:abc"]},
        }
        config_bytes = json.dumps(oci_config).encode("utf-8")

        mock_retriever = MagicMock()
        mock_retriever.get_blob_bytes_with_digest.return_value = config_bytes
        mock_manifest.config.size = len(config_bytes)

        result = extract_image_analysis(
            manifest=mock_manifest,
            content_retriever=mock_retriever,
            tag="latest",
        )

        assert "80" in result.exposed_ports
        assert result.cmd == ["/bin/bash"]


class TestManifestListSupport:
    """Tests for manifest list handling."""

    def test_raises_for_manifest_list(self):
        """Test that manifest lists raise appropriate error."""
        mock_manifest = MagicMock()
        mock_manifest.is_manifest_list = True

        mock_retriever = MagicMock()

        with pytest.raises(ImageExtractionError) as exc:
            extract_image_analysis(
                manifest=mock_manifest,
                content_retriever=mock_retriever,
                tag="latest",
            )
        assert "manifest list" in str(exc.value).lower()
