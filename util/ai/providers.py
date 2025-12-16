"""
LLM provider implementations for AI-powered features.

This module provides a unified interface for interacting with various LLM providers
including Anthropic, OpenAI, Google, DeepSeek, and custom OpenAI-compatible endpoints.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from util.ai.prompt import build_prompt

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MAX_TOKENS = 500
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 30  # seconds


class ProviderConfigError(Exception):
    """Raised when provider configuration is invalid."""

    pass


class ProviderAPIError(Exception):
    """Raised when the provider API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ProviderRateLimitError(ProviderAPIError):
    """Raised when the provider rate limit is exceeded."""

    pass


class ProviderAuthError(ProviderAPIError):
    """Raised when authentication fails."""

    pass


class ProviderTimeoutError(ProviderAPIError):
    """Raised when the request times out."""

    pass


@dataclass
class ImageAnalysis:
    """
    Container for extracted image metadata.

    This is used as input to generate descriptions.
    """

    layer_commands: List[str]
    exposed_ports: List[str]
    environment_vars: Dict[str, str]
    labels: Dict[str, str]
    entrypoint: Optional[List[str]]
    cmd: Optional[List[str]]
    base_image: Optional[str]
    manifest_digest: str
    tag: str


class LLMProviderInterface(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_description(self, image_analysis: ImageAnalysis) -> str:
        """
        Generate a description from image analysis.

        Args:
            image_analysis: Extracted metadata from the container image.

        Returns:
            Generated markdown description.

        Raises:
            ProviderAPIError: If the API request fails.
            ProviderRateLimitError: If rate limited.
            ProviderAuthError: If authentication fails.
            ProviderTimeoutError: If the request times out.
        """
        pass

    @abstractmethod
    def verify_connectivity(self) -> Tuple[bool, Optional[str]]:
        """
        Verify that credentials are valid and the provider is reachable.

        Returns:
            Tuple of (success, error_message). error_message is None on success.
        """
        pass


class AnthropicProvider(LLMProviderInterface):
    """Provider for Anthropic Claude API."""

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _make_request(self, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Make a request to the Anthropic API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.Timeout:
            raise ProviderTimeoutError("Request timed out")
        except requests.ConnectionError as e:
            raise ProviderAPIError(f"Connection error: {str(e)}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except Exception:
            error_message = response.text or "Unknown error"

        if response.status_code == 401 or response.status_code == 403:
            raise ProviderAuthError(error_message, response.status_code)
        elif response.status_code == 429:
            raise ProviderRateLimitError(error_message, response.status_code)
        else:
            raise ProviderAPIError(error_message, response.status_code)

    def generate_description(self, image_analysis: ImageAnalysis) -> str:
        """Generate description using Anthropic Claude."""
        prompt = build_prompt(image_analysis)
        response = self._make_request(prompt)

        # Extract text from response
        content = response.get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", "")
        return ""

    def verify_connectivity(self) -> Tuple[bool, Optional[str]]:
        """Verify Anthropic API connectivity."""
        try:
            self._make_request("Say 'Hello' in one word.", timeout=10)
            return True, None
        except ProviderAuthError as e:
            return False, f"Invalid API key or authentication failed: {str(e)}"
        except ProviderRateLimitError:
            # Rate limited but credentials are valid
            return True, None
        except ProviderTimeoutError:
            return False, "Connection timed out"
        except ProviderAPIError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


class OpenAIProvider(LLMProviderInterface):
    """Provider for OpenAI API."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _make_request(self, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Make a request to the OpenAI API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.Timeout:
            raise ProviderTimeoutError("Request timed out")
        except requests.ConnectionError as e:
            raise ProviderAPIError(f"Connection error: {str(e)}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except Exception:
            error_message = response.text or "Unknown error"

        if response.status_code == 401 or response.status_code == 403:
            raise ProviderAuthError(error_message, response.status_code)
        elif response.status_code == 429:
            raise ProviderRateLimitError(error_message, response.status_code)
        else:
            raise ProviderAPIError(error_message, response.status_code)

    def generate_description(self, image_analysis: ImageAnalysis) -> str:
        """Generate description using OpenAI."""
        prompt = build_prompt(image_analysis)
        response = self._make_request(prompt)

        # Extract text from response
        choices = response.get("choices", [])
        if choices and len(choices) > 0:
            return choices[0].get("message", {}).get("content", "")
        return ""

    def verify_connectivity(self) -> Tuple[bool, Optional[str]]:
        """Verify OpenAI API connectivity."""
        try:
            self._make_request("Say 'Hello' in one word.", timeout=10)
            return True, None
        except ProviderAuthError as e:
            return False, f"Invalid API key or authentication failed: {str(e)}"
        except ProviderRateLimitError:
            return True, None
        except ProviderTimeoutError:
            return False, "Connection timed out"
        except ProviderAPIError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


class GoogleProvider(LLMProviderInterface):
    """Provider for Google Gemini API."""

    API_URL_TEMPLATE = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _make_request(self, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Make a request to the Google Gemini API."""
        url = self.API_URL_TEMPLATE.format(model=self.model)

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                params={"key": self.api_key},
                timeout=timeout,
            )
        except requests.Timeout:
            raise ProviderTimeoutError("Request timed out")
        except requests.ConnectionError as e:
            raise ProviderAPIError(f"Connection error: {str(e)}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except Exception:
            error_message = response.text or "Unknown error"

        if response.status_code == 401 or response.status_code == 403:
            raise ProviderAuthError(error_message, response.status_code)
        elif response.status_code == 429:
            raise ProviderRateLimitError(error_message, response.status_code)
        else:
            raise ProviderAPIError(error_message, response.status_code)

    def generate_description(self, image_analysis: ImageAnalysis) -> str:
        """Generate description using Google Gemini."""
        prompt = build_prompt(image_analysis)
        response = self._make_request(prompt)

        # Extract text from response
        candidates = response.get("candidates", [])
        if candidates and len(candidates) > 0:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts and len(parts) > 0:
                return parts[0].get("text", "")
        return ""

    def verify_connectivity(self) -> Tuple[bool, Optional[str]]:
        """Verify Google Gemini API connectivity."""
        try:
            self._make_request("Say 'Hello' in one word.", timeout=10)
            return True, None
        except ProviderAuthError as e:
            return False, f"Invalid API key or authentication failed: {str(e)}"
        except ProviderRateLimitError:
            return True, None
        except ProviderTimeoutError:
            return False, "Connection timed out"
        except ProviderAPIError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


class DeepSeekProvider(LLMProviderInterface):
    """Provider for DeepSeek API (OpenAI-compatible)."""

    API_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _make_request(self, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Make a request to the DeepSeek API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.Timeout:
            raise ProviderTimeoutError("Request timed out")
        except requests.ConnectionError as e:
            raise ProviderAPIError(f"Connection error: {str(e)}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except Exception:
            error_message = response.text or "Unknown error"

        if response.status_code == 401 or response.status_code == 403:
            raise ProviderAuthError(error_message, response.status_code)
        elif response.status_code == 429:
            raise ProviderRateLimitError(error_message, response.status_code)
        else:
            raise ProviderAPIError(error_message, response.status_code)

    def generate_description(self, image_analysis: ImageAnalysis) -> str:
        """Generate description using DeepSeek."""
        prompt = build_prompt(image_analysis)
        response = self._make_request(prompt)

        # Extract text from response (OpenAI-compatible format)
        choices = response.get("choices", [])
        if choices and len(choices) > 0:
            return choices[0].get("message", {}).get("content", "")
        return ""

    def verify_connectivity(self) -> Tuple[bool, Optional[str]]:
        """Verify DeepSeek API connectivity."""
        try:
            self._make_request("Say 'Hello' in one word.", timeout=10)
            return True, None
        except ProviderAuthError as e:
            return False, f"Invalid API key or authentication failed: {str(e)}"
        except ProviderRateLimitError:
            return True, None
        except ProviderTimeoutError:
            return False, "Connection timed out"
        except ProviderAPIError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


class CustomProvider(LLMProviderInterface):
    """Provider for custom OpenAI-compatible endpoints (e.g., Ollama, vLLM)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        endpoint: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _get_api_url(self) -> str:
        """Get the full API URL for chat completions."""
        return f"{self.endpoint}/chat/completions"

    def _make_request(self, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Make a request to the custom endpoint."""
        headers = {
            "Content-Type": "application/json",
        }

        # Only add Authorization header if api_key is provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = requests.post(
                self._get_api_url(),
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.Timeout:
            raise ProviderTimeoutError("Request timed out")
        except requests.ConnectionError as e:
            raise ProviderAPIError(f"Connection error: {str(e)}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except Exception:
            error_message = response.text or "Unknown error"

        if response.status_code == 401 or response.status_code == 403:
            raise ProviderAuthError(error_message, response.status_code)
        elif response.status_code == 429:
            raise ProviderRateLimitError(error_message, response.status_code)
        else:
            raise ProviderAPIError(error_message, response.status_code)

    def generate_description(self, image_analysis: ImageAnalysis) -> str:
        """Generate description using custom endpoint."""
        prompt = build_prompt(image_analysis)
        response = self._make_request(prompt)

        # Extract text from response (OpenAI-compatible format)
        choices = response.get("choices", [])
        if choices and len(choices) > 0:
            return choices[0].get("message", {}).get("content", "")
        return ""

    def verify_connectivity(self) -> Tuple[bool, Optional[str]]:
        """Verify custom endpoint connectivity."""
        try:
            self._make_request("Say 'Hello' in one word.", timeout=10)
            return True, None
        except ProviderAuthError as e:
            return False, f"Invalid API key or authentication failed: {str(e)}"
        except ProviderRateLimitError:
            return True, None
        except ProviderTimeoutError:
            return False, "Connection timed out"
        except ProviderAPIError as e:
            return False, f"Connection error or unreachable: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


class ProviderFactory:
    """Factory for creating LLM providers."""

    PROVIDER_MAP = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "google": GoogleProvider,
        "deepseek": DeepSeekProvider,
        "custom": CustomProvider,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        model: str,
        endpoint: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> LLMProviderInterface:
        """
        Create an LLM provider instance.

        Args:
            provider: Provider name (anthropic, openai, google, deepseek, custom)
            api_key: API key for the provider
            model: Model name to use
            endpoint: Custom endpoint URL (required for 'custom' provider)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            LLM provider instance

        Raises:
            ProviderConfigError: If configuration is invalid
        """
        provider_lower = provider.lower() if provider else ""

        if provider_lower not in cls.PROVIDER_MAP:
            raise ProviderConfigError(
                f"Unknown provider: {provider}. "
                f"Supported providers: {', '.join(cls.PROVIDER_MAP.keys())}"
            )

        # Validate API key (custom provider may not need one for local deployments)
        if not api_key and provider_lower != "custom":
            raise ProviderConfigError("API key is required")

        if provider_lower == "custom" and not endpoint:
            raise ProviderConfigError("Endpoint is required for custom provider")

        provider_class = cls.PROVIDER_MAP[provider_lower]

        if provider_lower == "custom":
            return provider_class(
                api_key=api_key or "",
                model=model,
                endpoint=endpoint,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        return provider_class(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @classmethod
    def create_from_org_settings(cls, org_settings) -> LLMProviderInterface:
        """
        Create a provider from organization AI settings.

        Args:
            org_settings: OrganizationAISettings model instance

        Returns:
            LLM provider instance
        """
        api_key = org_settings.api_key_encrypted
        if hasattr(api_key, "decrypt"):
            api_key = api_key.decrypt()

        return cls.create(
            provider=org_settings.provider,
            api_key=api_key,
            model=org_settings.model,
            endpoint=org_settings.endpoint,
        )

    @classmethod
    def create_managed(cls) -> LLMProviderInterface:
        """
        Create a provider from Quay's internal managed configuration.

        This is used in managed mode (quay.io) where Quay provides the LLM backend.

        Returns:
            LLM provider instance

        Raises:
            ProviderConfigError: If managed provider is not configured
        """
        from app import app

        managed_config = app.config.get("AI_MANAGED_PROVIDER", {})

        if not managed_config:
            raise ProviderConfigError(
                "Managed AI provider is not configured. "
                "Please set AI_MANAGED_PROVIDER in config."
            )

        provider = managed_config.get("PROVIDER")
        api_key = managed_config.get("API_KEY")
        model = managed_config.get("MODEL")
        endpoint = managed_config.get("ENDPOINT")
        max_tokens = managed_config.get("MAX_TOKENS", DEFAULT_MAX_TOKENS)
        temperature = managed_config.get("TEMPERATURE", DEFAULT_TEMPERATURE)

        if not provider:
            raise ProviderConfigError("AI_MANAGED_PROVIDER.PROVIDER is required")

        return cls.create(
            provider=provider,
            api_key=api_key,
            model=model,
            endpoint=endpoint,
            max_tokens=max_tokens,
            temperature=temperature,
        )
