"""
Image history extraction for AI description generation.

This module extracts metadata from container image configs for use
in generating AI-powered descriptions.
"""
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from util.ai.providers import ImageAnalysis

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# OCI label for base image name
OCI_BASE_IMAGE_LABEL = "org.opencontainers.image.base.name"


class ImageExtractionError(Exception):
    """Raised when image analysis extraction fails."""

    pass


def parse_env_vars(env_list: Optional[List[str]]) -> Dict[str, str]:
    """
    Parse environment variables from Docker config format.

    Args:
        env_list: List of "KEY=value" strings from image config.

    Returns:
        Dictionary of environment variable key-value pairs.
    """
    if not env_list:
        return {}

    result = {}
    for entry in env_list:
        if "=" not in entry:
            # Skip malformed entries
            continue
        key, value = entry.split("=", 1)
        result[key] = value

    return result


def parse_exposed_ports(ports_dict: Optional[Dict[str, Any]]) -> List[str]:
    """
    Parse exposed ports from Docker config format.

    Args:
        ports_dict: Dictionary with port specs as keys (e.g., "8080/tcp": {}).

    Returns:
        List of port numbers as strings.
    """
    if not ports_dict:
        return []

    ports = []
    for port_spec in ports_dict.keys():
        # Port spec format: "8080/tcp" or "8080/udp" or just "8080"
        port = port_spec.split("/")[0]
        ports.append(port)

    return ports


def get_config_from_manifest(manifest, content_retriever) -> Dict[str, Any]:
    """
    Retrieve and parse the config blob from a manifest.

    Args:
        manifest: The manifest object with config reference.
        content_retriever: Object that can retrieve blob bytes.

    Returns:
        Parsed config dictionary.

    Raises:
        ImageExtractionError: If config cannot be retrieved or parsed.
    """
    config_digest = manifest.config.digest
    expected_size = manifest.config.size

    config_bytes = content_retriever.get_blob_bytes_with_digest(config_digest)
    if config_bytes is None:
        raise ImageExtractionError(f"Could not retrieve config blob with digest {config_digest}")

    actual_size = len(config_bytes)
    if actual_size != expected_size:
        raise ImageExtractionError(
            f"Config blob size mismatch: expected {expected_size}, got {actual_size}"
        )

    try:
        if isinstance(config_bytes, bytes):
            config_str = config_bytes.decode("utf-8")
        else:
            config_str = config_bytes
        return json.loads(config_str)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ImageExtractionError(f"Malformed config blob: {str(e)}")


def extract_layer_commands(history: List[Dict[str, Any]]) -> List[str]:
    """
    Extract layer commands from config history.

    Args:
        history: List of history entries from image config.

    Returns:
        List of command strings.
    """
    commands = []
    for entry in history:
        command = entry.get("created_by", "")
        if command:
            commands.append(command)
    return commands


def extract_base_image(labels: Dict[str, str]) -> Optional[str]:
    """
    Attempt to extract base image from OCI labels.

    Args:
        labels: Dictionary of image labels.

    Returns:
        Base image name if found, None otherwise.
    """
    if not labels:
        return None

    return labels.get(OCI_BASE_IMAGE_LABEL)


def extract_image_analysis(
    manifest,
    content_retriever,
    tag: str,
) -> ImageAnalysis:
    """
    Extract image analysis from a manifest.

    Args:
        manifest: The manifest object (DockerSchema2Manifest or OCI manifest).
        content_retriever: Object that can retrieve blob bytes.
        tag: The tag associated with this manifest.

    Returns:
        ImageAnalysis dataclass with extracted metadata.

    Raises:
        ImageExtractionError: If extraction fails.
    """
    # Check for manifest list (not directly supported)
    if hasattr(manifest, "is_manifest_list") and manifest.is_manifest_list:
        raise ImageExtractionError(
            "Manifest list not supported. Please select a specific platform manifest."
        )

    # Get the config blob
    try:
        config = get_config_from_manifest(manifest, content_retriever)
    except ImageExtractionError:
        raise
    except Exception as e:
        raise ImageExtractionError(f"Failed to retrieve config: {str(e)}")

    # Validate required fields
    if "history" not in config:
        raise ImageExtractionError("Config blob missing required 'history' field")

    # Extract the container config section
    container_config = config.get("config", {})

    # Extract layer commands from history
    history = config.get("history", [])
    layer_commands = extract_layer_commands(history)

    # Extract environment variables
    env_list = container_config.get("Env")
    environment_vars = parse_env_vars(env_list)

    # Extract exposed ports
    ports_dict = container_config.get("ExposedPorts")
    exposed_ports = parse_exposed_ports(ports_dict)

    # Extract labels
    labels = container_config.get("Labels") or {}

    # Extract entrypoint and cmd
    entrypoint = container_config.get("Entrypoint")
    cmd = container_config.get("Cmd")

    # Try to detect base image from labels
    base_image = extract_base_image(labels)

    # Get manifest digest
    manifest_digest = str(manifest.digest)

    return ImageAnalysis(
        layer_commands=layer_commands,
        exposed_ports=exposed_ports,
        environment_vars=environment_vars,
        labels=labels,
        entrypoint=entrypoint,
        cmd=cmd,
        base_image=base_image,
        manifest_digest=manifest_digest,
        tag=tag,
    )
