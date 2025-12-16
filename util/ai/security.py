"""
Security utilities for AI-powered features.

This module provides sanitization and security functions to protect against:
- XSS attacks in LLM responses
- Prompt injection attacks
- Credential exposure
- Sensitive data leakage
"""
import html
import re
from typing import Dict, Optional

# Maximum allowed response length to prevent abuse
MAX_RESPONSE_LENGTH = 50000

# Patterns that indicate sensitive environment variable names
SENSITIVE_PATTERNS = [
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "KEY",
    "CREDENTIAL",
    "CREDENTIALS",
    "AUTH",
    "APIKEY",
    "API_KEY",
    "PRIVATE",
    "CERT",
    "CERTIFICATE",
]

# Regex patterns for dangerous HTML/JS content
SCRIPT_TAG_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_TAG_PATTERN = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
IFRAME_TAG_PATTERN = re.compile(r"<iframe[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL)
OBJECT_TAG_PATTERN = re.compile(r"<object[^>]*>.*?</object>", re.IGNORECASE | re.DOTALL)
EMBED_TAG_PATTERN = re.compile(r"<embed[^>]*>", re.IGNORECASE)
EVENT_HANDLER_PATTERN = re.compile(r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", re.IGNORECASE)
JAVASCRIPT_URL_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)

# Patterns for detecting credentials in connection strings
CONNECTION_STRING_PATTERNS = [
    re.compile(r"://[^:]*:[^@]+@", re.IGNORECASE),  # user:pass@ or :pass@ in URLs
    re.compile(r"password=", re.IGNORECASE),
]


def sanitize_llm_response(response: Optional[str]) -> str:
    """
    Sanitize LLM response to remove potentially dangerous content.

    Removes:
    - Script tags and their content
    - Style tags and their content
    - Event handlers (onclick, onload, etc.)
    - javascript: URLs
    - iframe, object, embed tags
    - Excessively long content

    Preserves:
    - Valid Markdown formatting
    - Code blocks
    - Normal HTML entities

    Args:
        response: The raw LLM response.

    Returns:
        Sanitized response string.
    """
    if response is None:
        return ""

    if not response:
        return ""

    result = response

    # Remove script tags and content
    result = SCRIPT_TAG_PATTERN.sub("", result)

    # Remove style tags and content
    result = STYLE_TAG_PATTERN.sub("", result)

    # Remove iframe tags and content
    result = IFRAME_TAG_PATTERN.sub("", result)

    # Remove object tags and content
    result = OBJECT_TAG_PATTERN.sub("", result)

    # Remove embed tags
    result = EMBED_TAG_PATTERN.sub("", result)

    # Remove event handlers
    result = EVENT_HANDLER_PATTERN.sub("", result)

    # Remove javascript: URLs
    result = JAVASCRIPT_URL_PATTERN.sub("", result)

    # Truncate if too long
    if len(result) > MAX_RESPONSE_LENGTH:
        result = result[: MAX_RESPONSE_LENGTH - 3] + "..."

    return result


def filter_sensitive_env_vars(env_vars: Optional[Dict[str, str]]) -> Dict[str, str]:
    """
    Filter out environment variables that may contain sensitive data.

    Removes variables whose names match sensitive patterns or whose
    values appear to contain credentials.

    Args:
        env_vars: Dictionary of environment variable name-value pairs.

    Returns:
        Filtered dictionary with sensitive variables removed.
    """
    if env_vars is None:
        return {}

    if not env_vars:
        return {}

    result = {}

    for key, value in env_vars.items():
        # Check if key matches sensitive patterns
        if is_sensitive_key(key):
            continue

        # Check if value contains connection string credentials
        if _value_contains_credentials(value):
            continue

        result[key] = value

    return result


def _value_contains_credentials(value: str) -> bool:
    """
    Check if a value appears to contain embedded credentials.

    Args:
        value: The environment variable value.

    Returns:
        True if credentials appear to be present.
    """
    if not value:
        return False

    for pattern in CONNECTION_STRING_PATTERNS:
        if pattern.search(value):
            return True

    return False


def is_sensitive_key(key: Optional[str]) -> bool:
    """
    Check if an environment variable key name indicates sensitive data.

    Args:
        key: The environment variable name.

    Returns:
        True if the key appears to be sensitive.
    """
    if key is None or not key:
        return False

    key_upper = key.upper()

    for pattern in SENSITIVE_PATTERNS:
        if pattern in key_upper:
            return True

    return False


def escape_for_prompt(text: Optional[str]) -> str:
    """
    Escape text before including it in an LLM prompt.

    This helps prevent prompt injection attacks by treating
    user/image content as data rather than instructions.

    Args:
        text: The text to escape.

    Returns:
        Escaped text safe for prompt inclusion.
    """
    if text is None:
        return ""

    if not text:
        return ""

    result = text

    # Truncate very long input to prevent context overflow
    max_prompt_content = 30000
    if len(result) > max_prompt_content:
        result = result[:max_prompt_content] + "..."

    # Escape HTML entities to prevent interpretation issues
    result = html.escape(result)

    return result


def mask_api_key(api_key: Optional[str]) -> str:
    """
    Mask an API key for display, showing only the last 4 characters.

    Args:
        api_key: The API key to mask.

    Returns:
        Masked API key string.
    """
    if api_key is None or not api_key:
        return ""

    if len(api_key) <= 8:
        return "*" * len(api_key)

    # Show last 4 characters
    visible_chars = api_key[-4:]
    masked_length = len(api_key) - 4
    return "*" * masked_length + visible_chars


def sanitize_layer_command(command: str) -> str:
    """
    Sanitize a layer command before including in prompt.

    Args:
        command: The layer command from image history.

    Returns:
        Sanitized command string.
    """
    if not command:
        return ""

    # Remove potential embedded secrets from commands
    # This is a best-effort sanitization
    result = command

    # Redact anything that looks like a secret value assignment
    result = re.sub(
        r"(PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL)\s*=\s*\S+",
        r"\1=***REDACTED***",
        result,
        flags=re.IGNORECASE,
    )

    return result
