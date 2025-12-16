"""
Prompt templates for AI-powered features.

This module provides prompt construction for LLM-based description generation.
"""
import re
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from util.ai.providers import ImageAnalysis

# Maximum number of layer commands to include in prompt
MAX_LAYER_COMMANDS = 50

# Maximum length of individual layer command
MAX_COMMAND_LENGTH = 500

# Maximum total prompt length (chars)
MAX_PROMPT_LENGTH = 8000

# Sensitive environment variable patterns to filter
SENSITIVE_PATTERNS = [
    r".*PASSWORD.*",
    r".*SECRET.*",
    r".*TOKEN.*",
    r".*API_KEY.*",
    r".*CREDENTIAL.*",
    r".*PRIVATE_KEY.*",
    r".*ACCESS_KEY.*",
]

DESCRIPTION_PROMPT_TEMPLATE = """Analyze this container image build history and generate a concise Markdown description.

## Layer History (Dockerfile commands):
{layer_commands}

## Image Configuration:
- Exposed Ports: {ports}
- Environment Variables: {env_vars}
- Entrypoint: {entrypoint}
- CMD: {cmd}
- Labels: {labels}
- Base Image: {base_image}

## Instructions:
Write a 1-2 paragraph summary describing:
1. What this image does / its purpose
2. Key software and versions it contains
3. How to use it (exposed ports, important environment variables)

Keep the response under 500 words. Use Markdown formatting.
Do not include any code blocks or shell commands in the response.
Focus on being informative and helpful for users discovering this image."""


def sanitize_env_vars(env_vars: Dict[str, str]) -> Dict[str, str]:
    """
    Remove sensitive environment variables from the dict.

    Filters out any variable whose name matches common secret patterns.
    """
    if not env_vars:
        return {}

    filtered = {}
    for key, value in env_vars.items():
        is_sensitive = False
        for pattern in SENSITIVE_PATTERNS:
            if re.match(pattern, key, re.IGNORECASE):
                is_sensitive = True
                break

        if not is_sensitive:
            filtered[key] = value

    return filtered


def truncate_command(command: str, max_length: int = MAX_COMMAND_LENGTH) -> str:
    """Truncate a command to max length."""
    if len(command) <= max_length:
        return command
    return command[: max_length - 3] + "..."


def format_layer_commands(commands: List[str]) -> str:
    """Format layer commands for the prompt."""
    if not commands:
        return "No layer history available"

    # Take only the first MAX_LAYER_COMMANDS
    limited = commands[:MAX_LAYER_COMMANDS]

    # Truncate individual commands
    formatted = []
    for i, cmd in enumerate(limited, 1):
        truncated = truncate_command(cmd)
        formatted.append(f"{i}. {truncated}")

    if len(commands) > MAX_LAYER_COMMANDS:
        formatted.append(f"... and {len(commands) - MAX_LAYER_COMMANDS} more layers")

    return "\n".join(formatted)


def format_ports(ports: List[str]) -> str:
    """Format exposed ports for the prompt."""
    if not ports:
        return "None"
    return ", ".join(ports)


def format_env_vars(env_vars: Dict[str, str]) -> str:
    """Format environment variables for the prompt."""
    # Filter sensitive vars first
    safe_vars = sanitize_env_vars(env_vars)

    if not safe_vars:
        return "None"

    # Format as key=value pairs
    formatted = []
    for key, value in safe_vars.items():
        # Truncate long values
        if len(value) > 100:
            value = value[:97] + "..."
        formatted.append(f"{key}={value}")

    return ", ".join(formatted)


def format_labels(labels: Dict[str, str]) -> str:
    """Format labels for the prompt."""
    if not labels:
        return "None"

    formatted = []
    for key, value in labels.items():
        # Truncate long values
        if len(value) > 100:
            value = value[:97] + "..."
        formatted.append(f"{key}: {value}")

    return ", ".join(formatted)


def format_command_list(cmd: List[str]) -> str:
    """Format entrypoint or cmd for the prompt."""
    if not cmd:
        return "None"
    return " ".join(cmd)


def build_prompt(image_analysis: "ImageAnalysis") -> str:
    """
    Build a prompt for description generation from image analysis.

    Args:
        image_analysis: Extracted metadata from the container image.

    Returns:
        Formatted prompt string for the LLM.
    """
    prompt = DESCRIPTION_PROMPT_TEMPLATE.format(
        layer_commands=format_layer_commands(image_analysis.layer_commands),
        ports=format_ports(image_analysis.exposed_ports),
        env_vars=format_env_vars(image_analysis.environment_vars),
        entrypoint=format_command_list(image_analysis.entrypoint),
        cmd=format_command_list(image_analysis.cmd),
        labels=format_labels(image_analysis.labels),
        base_image=image_analysis.base_image or "Unknown",
    )

    # Ensure prompt doesn't exceed max length
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH]

    return prompt
