"""
Tests for LLM provider implementations.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from util.ai.providers import (
    AnthropicProvider,
    CustomProvider,
    DeepSeekProvider,
    GoogleProvider,
    ImageAnalysis,
    LLMProviderInterface,
    OpenAIProvider,
    ProviderAPIError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderFactory,
    ProviderRateLimitError,
    ProviderTimeoutError,
)


@pytest.fixture
def sample_image_analysis():
    """Sample image analysis for testing."""
    return ImageAnalysis(
        layer_commands=[
            "/bin/sh -c #(nop) ADD file:abc123 in /",
            "/bin/sh -c apt-get update && apt-get install -y nodejs",
            "/bin/sh -c npm install express",
            "/bin/sh -c #(nop) EXPOSE 8080",
            '/bin/sh -c #(nop) CMD ["node", "server.js"]',
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


class TestProviderFactory:
    """Tests for the provider factory."""

    def test_create_anthropic_provider(self):
        """Test creating an Anthropic provider."""
        provider = ProviderFactory.create(
            provider="anthropic",
            api_key="sk-ant-test",
            model="claude-3-haiku-20240307",
        )
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-3-haiku-20240307"

    def test_create_openai_provider(self):
        """Test creating an OpenAI provider."""
        provider = ProviderFactory.create(
            provider="openai",
            api_key="sk-test",
            model="gpt-4-turbo-preview",
        )
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4-turbo-preview"

    def test_create_google_provider(self):
        """Test creating a Google provider."""
        provider = ProviderFactory.create(
            provider="google",
            api_key="google-api-key",
            model="gemini-2.0-flash-lite",
        )
        assert isinstance(provider, GoogleProvider)
        assert provider.model == "gemini-2.0-flash-lite"

    def test_create_deepseek_provider(self):
        """Test creating a DeepSeek provider."""
        provider = ProviderFactory.create(
            provider="deepseek",
            api_key="deepseek-key",
            model="deepseek-chat",
        )
        assert isinstance(provider, DeepSeekProvider)
        assert provider.model == "deepseek-chat"

    def test_create_custom_provider(self):
        """Test creating a custom provider."""
        provider = ProviderFactory.create(
            provider="custom",
            api_key="custom-key",
            model="llama3",
            endpoint="http://localhost:11434/v1",
        )
        assert isinstance(provider, CustomProvider)
        assert provider.endpoint == "http://localhost:11434/v1"

    def test_invalid_provider_raises_exception(self):
        """Test that invalid provider name raises exception."""
        with pytest.raises(ProviderConfigError) as exc:
            ProviderFactory.create(
                provider="invalid-provider",
                api_key="key",
                model="model",
            )
        assert "Unknown provider" in str(exc.value)

    def test_missing_api_key_raises_exception(self):
        """Test that missing API key raises exception."""
        with pytest.raises(ProviderConfigError) as exc:
            ProviderFactory.create(
                provider="anthropic",
                api_key=None,
                model="claude-3-haiku",
            )
        assert "API key is required" in str(exc.value)

    def test_empty_api_key_raises_exception(self):
        """Test that empty API key raises exception."""
        with pytest.raises(ProviderConfigError) as exc:
            ProviderFactory.create(
                provider="openai",
                api_key="",
                model="gpt-4",
            )
        assert "API key is required" in str(exc.value)

    def test_custom_provider_requires_endpoint(self):
        """Test that custom provider requires endpoint."""
        with pytest.raises(ProviderConfigError) as exc:
            ProviderFactory.create(
                provider="custom",
                api_key="key",
                model="model",
                endpoint=None,
            )
        assert "endpoint is required" in str(exc.value).lower()


class TestAnthropicProvider:
    """Tests for the Anthropic provider."""

    @patch("util.ai.providers.requests.post")
    def test_generate_description_success(self, mock_post, sample_image_analysis):
        """Test successful description generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "This is a Node.js web server image."}]
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(
            api_key="sk-ant-test",
            model="claude-3-haiku-20240307",
        )

        result = provider.generate_description(sample_image_analysis)

        assert result == "This is a Node.js web server image."
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "anthropic" in call_args[0][0]
        assert "Authorization" in call_args[1]["headers"]

    @patch("util.ai.providers.requests.post")
    def test_handles_rate_limit_error(self, mock_post, sample_image_analysis):
        """Test handling rate limit errors."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        mock_post.return_value = mock_response

        provider = AnthropicProvider(
            api_key="sk-ant-test",
            model="claude-3-haiku-20240307",
        )

        with pytest.raises(ProviderRateLimitError):
            provider.generate_description(sample_image_analysis)

    @patch("util.ai.providers.requests.post")
    def test_handles_auth_error(self, mock_post, sample_image_analysis):
        """Test handling authentication errors."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_post.return_value = mock_response

        provider = AnthropicProvider(
            api_key="invalid-key",
            model="claude-3-haiku-20240307",
        )

        with pytest.raises(ProviderAuthError):
            provider.generate_description(sample_image_analysis)

    @patch("util.ai.providers.requests.post")
    def test_handles_timeout(self, mock_post, sample_image_analysis):
        """Test handling timeout errors."""
        import requests

        mock_post.side_effect = requests.Timeout("Connection timed out")

        provider = AnthropicProvider(
            api_key="sk-ant-test",
            model="claude-3-haiku-20240307",
        )

        with pytest.raises(ProviderTimeoutError):
            provider.generate_description(sample_image_analysis)


class TestOpenAIProvider:
    """Tests for the OpenAI provider."""

    @patch("util.ai.providers.requests.post")
    def test_generate_description_success(self, mock_post, sample_image_analysis):
        """Test successful description generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is a Node.js Express server."}}]
        }
        mock_post.return_value = mock_response

        provider = OpenAIProvider(
            api_key="sk-test",
            model="gpt-4-turbo-preview",
        )

        result = provider.generate_description(sample_image_analysis)

        assert result == "This is a Node.js Express server."
        mock_post.assert_called_once()

    @patch("util.ai.providers.requests.post")
    def test_handles_rate_limit_error(self, mock_post, sample_image_analysis):
        """Test handling rate limit errors."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        mock_post.return_value = mock_response

        provider = OpenAIProvider(
            api_key="sk-test",
            model="gpt-4",
        )

        with pytest.raises(ProviderRateLimitError):
            provider.generate_description(sample_image_analysis)


class TestGoogleProvider:
    """Tests for the Google provider."""

    @patch("util.ai.providers.requests.post")
    def test_generate_description_success(self, mock_post, sample_image_analysis):
        """Test successful description generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "This image runs a Node.js server."}]}}]
        }
        mock_post.return_value = mock_response

        provider = GoogleProvider(
            api_key="google-key",
            model="gemini-2.0-flash-lite",
        )

        result = provider.generate_description(sample_image_analysis)

        assert result == "This image runs a Node.js server."
        mock_post.assert_called_once()


class TestCustomProvider:
    """Tests for the custom (OpenAI-compatible) provider."""

    @patch("util.ai.providers.requests.post")
    def test_uses_openai_compatible_api(self, mock_post, sample_image_analysis):
        """Test that custom provider uses OpenAI-compatible API format."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Local LLM response."}}]
        }
        mock_post.return_value = mock_response

        provider = CustomProvider(
            api_key="local-key",
            model="llama3",
            endpoint="http://localhost:11434/v1",
        )

        result = provider.generate_description(sample_image_analysis)

        assert result == "Local LLM response."
        # Verify it called the custom endpoint
        call_args = mock_post.call_args
        assert "localhost:11434" in call_args[0][0]


class TestProviderConfiguration:
    """Tests for provider configuration options."""

    def test_provider_respects_max_tokens(self):
        """Test that max_tokens config is used."""
        provider = ProviderFactory.create(
            provider="anthropic",
            api_key="sk-test",
            model="claude-3-haiku",
            max_tokens=100,
        )
        assert provider.max_tokens == 100

    def test_provider_respects_temperature(self):
        """Test that temperature config is used."""
        provider = ProviderFactory.create(
            provider="openai",
            api_key="sk-test",
            model="gpt-4",
            temperature=0.5,
        )
        assert provider.temperature == 0.5

    def test_provider_uses_configured_model(self):
        """Test that the configured model is used."""
        provider = ProviderFactory.create(
            provider="anthropic",
            api_key="sk-test",
            model="claude-3-opus-20240229",
        )
        assert provider.model == "claude-3-opus-20240229"

    def test_provider_default_max_tokens(self):
        """Test default max_tokens value."""
        provider = ProviderFactory.create(
            provider="openai",
            api_key="sk-test",
            model="gpt-4",
        )
        assert provider.max_tokens == 500  # Default

    def test_provider_default_temperature(self):
        """Test default temperature value."""
        provider = ProviderFactory.create(
            provider="anthropic",
            api_key="sk-test",
            model="claude-3-haiku",
        )
        assert provider.temperature == 0.7  # Default


class TestConnectivityVerification:
    """Tests for credential connectivity verification."""

    @patch("util.ai.providers.requests.post")
    def test_verify_connectivity_success(self, mock_post):
        """Test successful connectivity verification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"type": "text", "text": "Hello"}]}
        mock_post.return_value = mock_response

        provider = AnthropicProvider(
            api_key="sk-ant-valid",
            model="claude-3-haiku-20240307",
        )

        success, error = provider.verify_connectivity()

        assert success is True
        assert error is None

    @patch("util.ai.providers.requests.post")
    def test_verify_connectivity_invalid_key(self, mock_post):
        """Test connectivity verification with invalid key."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_post.return_value = mock_response

        provider = AnthropicProvider(
            api_key="invalid-key",
            model="claude-3-haiku-20240307",
        )

        success, error = provider.verify_connectivity()

        assert success is False
        assert "Invalid" in error or "authentication" in error.lower()

    @patch("util.ai.providers.requests.post")
    def test_verify_connectivity_unreachable_endpoint(self, mock_post):
        """Test connectivity verification with unreachable endpoint."""
        import requests

        mock_post.side_effect = requests.ConnectionError("Connection refused")

        provider = CustomProvider(
            api_key="key",
            model="model",
            endpoint="http://unreachable:11434/v1",
        )

        success, error = provider.verify_connectivity()

        assert success is False
        assert "connect" in error.lower() or "unreachable" in error.lower()

    @patch("util.ai.providers.requests.post")
    def test_verify_connectivity_timeout(self, mock_post):
        """Test connectivity verification with timeout."""
        import requests

        mock_post.side_effect = requests.Timeout("Connection timed out")

        provider = OpenAIProvider(
            api_key="sk-test",
            model="gpt-4",
        )

        success, error = provider.verify_connectivity()

        assert success is False
        assert "timeout" in error.lower() or "timed out" in error.lower()
