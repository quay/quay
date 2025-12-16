"""
Tests for prompt template construction.
"""
import pytest

from util.ai.prompt import (
    build_prompt,
    sanitize_env_vars,
    format_layer_commands,
    format_ports,
    format_env_vars,
    truncate_command,
    MAX_LAYER_COMMANDS,
    MAX_COMMAND_LENGTH,
    MAX_PROMPT_LENGTH,
)
from util.ai.providers import ImageAnalysis


@pytest.fixture
def sample_image_analysis():
    """Sample image analysis for testing."""
    return ImageAnalysis(
        layer_commands=[
            "/bin/sh -c #(nop) ADD file:abc123 in /",
            "/bin/sh -c apt-get update && apt-get install -y nodejs",
            "/bin/sh -c npm install express",
            "/bin/sh -c #(nop) EXPOSE 8080",
            "/bin/sh -c #(nop) CMD [\"node\", \"server.js\"]",
        ],
        exposed_ports=["8080"],
        environment_vars={"NODE_ENV": "production", "PORT": "8080"},
        labels={"maintainer": "dev@example.com"},
        entrypoint=None,
        cmd=["node", "server.js"],
        base_image="node:18-alpine",
        manifest_digest="sha256:abc123",
        tag="latest",
    )


class TestBuildPrompt:
    """Tests for the build_prompt function."""

    def test_prompt_includes_layer_commands(self, sample_image_analysis):
        """Test that layer commands are included in prompt."""
        prompt = build_prompt(sample_image_analysis)

        assert "apt-get update" in prompt
        assert "npm install express" in prompt
        assert "EXPOSE 8080" in prompt

    def test_prompt_includes_exposed_ports(self, sample_image_analysis):
        """Test that exposed ports are included in prompt."""
        prompt = build_prompt(sample_image_analysis)

        assert "8080" in prompt

    def test_prompt_includes_environment_variables(self, sample_image_analysis):
        """Test that environment variables are included in prompt."""
        prompt = build_prompt(sample_image_analysis)

        assert "NODE_ENV" in prompt
        assert "production" in prompt

    def test_prompt_includes_labels(self, sample_image_analysis):
        """Test that labels are included in prompt."""
        prompt = build_prompt(sample_image_analysis)

        assert "maintainer" in prompt
        assert "dev@example.com" in prompt

    def test_prompt_handles_empty_history(self):
        """Test prompt generation with empty layer history."""
        analysis = ImageAnalysis(
            layer_commands=[],
            exposed_ports=[],
            environment_vars={},
            labels={},
            entrypoint=None,
            cmd=None,
            base_image=None,
            manifest_digest="sha256:abc",
            tag="latest",
        )

        prompt = build_prompt(analysis)

        assert "No layer history available" in prompt

    def test_prompt_handles_none_values(self):
        """Test prompt generation with None values."""
        analysis = ImageAnalysis(
            layer_commands=None,
            exposed_ports=None,
            environment_vars=None,
            labels=None,
            entrypoint=None,
            cmd=None,
            base_image=None,
            manifest_digest="sha256:abc",
            tag="latest",
        )

        # Should not raise
        prompt = build_prompt(analysis)
        assert prompt is not None

    def test_prompt_truncates_very_long_history(self):
        """Test that very long layer history is truncated."""
        long_commands = [f"RUN command_{i}" for i in range(100)]

        analysis = ImageAnalysis(
            layer_commands=long_commands,
            exposed_ports=[],
            environment_vars={},
            labels={},
            entrypoint=None,
            cmd=None,
            base_image=None,
            manifest_digest="sha256:abc",
            tag="latest",
        )

        prompt = build_prompt(analysis)

        # Should include truncation message
        assert "more layers" in prompt
        # Should have limited commands
        assert prompt.count("RUN command_") <= MAX_LAYER_COMMANDS

    def test_prompt_max_length_respected(self):
        """Test that prompt doesn't exceed max length."""
        # Create a very long analysis
        very_long_command = "x" * 10000
        analysis = ImageAnalysis(
            layer_commands=[very_long_command] * 100,
            exposed_ports=["8080"] * 100,
            environment_vars={f"VAR_{i}": "value" * 100 for i in range(50)},
            labels={f"LABEL_{i}": "value" * 100 for i in range(50)},
            entrypoint=["long_entrypoint"] * 50,
            cmd=["long_cmd"] * 50,
            base_image="very/long/base/image/name" * 10,
            manifest_digest="sha256:abc",
            tag="latest",
        )

        prompt = build_prompt(analysis)

        assert len(prompt) <= MAX_PROMPT_LENGTH


class TestSanitizeEnvVars:
    """Tests for environment variable sanitization."""

    def test_password_env_vars_filtered(self):
        """Test that PASSWORD variables are filtered."""
        env_vars = {
            "DATABASE_PASSWORD": "secret123",
            "MY_PASSWORD": "hidden",
            "APP_NAME": "myapp",
        }

        result = sanitize_env_vars(env_vars)

        assert "DATABASE_PASSWORD" not in result
        assert "MY_PASSWORD" not in result
        assert "APP_NAME" in result

    def test_secret_env_vars_filtered(self):
        """Test that SECRET variables are filtered."""
        env_vars = {
            "AWS_SECRET_ACCESS_KEY": "secret",
            "MY_SECRET": "hidden",
            "PUBLIC_VAR": "visible",
        }

        result = sanitize_env_vars(env_vars)

        assert "AWS_SECRET_ACCESS_KEY" not in result
        assert "MY_SECRET" not in result
        assert "PUBLIC_VAR" in result

    def test_token_env_vars_filtered(self):
        """Test that TOKEN variables are filtered."""
        env_vars = {
            "GITHUB_TOKEN": "ghp_xxx",
            "AUTH_TOKEN": "abc123",
            "APP_VERSION": "1.0.0",
        }

        result = sanitize_env_vars(env_vars)

        assert "GITHUB_TOKEN" not in result
        assert "AUTH_TOKEN" not in result
        assert "APP_VERSION" in result

    def test_key_env_vars_filtered(self):
        """Test that API_KEY variables are filtered."""
        env_vars = {
            "OPENAI_API_KEY": "sk-xxx",
            "SERVICE_API_KEY": "key123",
            "DEBUG": "true",
        }

        result = sanitize_env_vars(env_vars)

        assert "OPENAI_API_KEY" not in result
        assert "SERVICE_API_KEY" not in result
        assert "DEBUG" in result

    def test_case_insensitive_filtering(self):
        """Test that filtering is case insensitive."""
        env_vars = {
            "password": "secret",
            "Password": "hidden",
            "PASSWORD": "also_hidden",
            "Normal_Var": "visible",
        }

        result = sanitize_env_vars(env_vars)

        assert len(result) == 1
        assert "Normal_Var" in result

    def test_empty_env_vars(self):
        """Test handling of empty env vars."""
        assert sanitize_env_vars({}) == {}
        assert sanitize_env_vars(None) == {}


class TestFormatLayerCommands:
    """Tests for layer command formatting."""

    def test_formats_commands_with_numbers(self):
        """Test that commands are numbered."""
        commands = ["RUN apt-get update", "RUN npm install"]

        result = format_layer_commands(commands)

        assert "1. RUN apt-get update" in result
        assert "2. RUN npm install" in result

    def test_truncates_individual_commands(self):
        """Test that long commands are truncated."""
        long_command = "RUN " + "x" * 1000

        result = format_layer_commands([long_command])

        assert len(result.split("\n")[0]) < MAX_COMMAND_LENGTH + 10
        assert "..." in result

    def test_limits_number_of_commands(self):
        """Test that number of commands is limited."""
        commands = [f"RUN command_{i}" for i in range(100)]

        result = format_layer_commands(commands)

        # Count numbered commands
        numbered_count = sum(1 for line in result.split("\n") if line.startswith(tuple("0123456789")))
        assert numbered_count <= MAX_LAYER_COMMANDS

    def test_empty_commands(self):
        """Test handling of empty commands list."""
        result = format_layer_commands([])
        assert "No layer history available" in result


class TestFormatPorts:
    """Tests for port formatting."""

    def test_formats_single_port(self):
        """Test formatting single port."""
        result = format_ports(["8080"])
        assert result == "8080"

    def test_formats_multiple_ports(self):
        """Test formatting multiple ports."""
        result = format_ports(["8080", "443", "22"])
        assert "8080" in result
        assert "443" in result
        assert "22" in result

    def test_empty_ports(self):
        """Test handling of empty ports list."""
        result = format_ports([])
        assert result == "None"


class TestTruncateCommand:
    """Tests for command truncation."""

    def test_short_command_unchanged(self):
        """Test that short commands are not modified."""
        cmd = "RUN apt-get update"
        result = truncate_command(cmd)
        assert result == cmd

    def test_long_command_truncated(self):
        """Test that long commands are truncated with ellipsis."""
        cmd = "x" * 1000
        result = truncate_command(cmd)

        assert len(result) <= MAX_COMMAND_LENGTH
        assert result.endswith("...")
