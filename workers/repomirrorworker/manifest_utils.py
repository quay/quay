"""Utilities for parsing and filtering manifest lists during repository mirroring."""

import json
import logging
from typing import Optional

from image.docker.schema2 import DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE

logger = logging.getLogger(__name__)

MANIFEST_LIST_MEDIA_TYPES = {
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    OCI_IMAGE_INDEX_CONTENT_TYPE,
}


def is_manifest_list(manifest_bytes: str) -> bool:
    """Check if manifest JSON represents a manifest list/index."""
    try:
        parsed = json.loads(manifest_bytes)
        media_type = parsed.get("mediaType", "")
        if media_type in MANIFEST_LIST_MEDIA_TYPES:
            return True
        # OCI index may not have mediaType but has manifests array
        if "manifests" in parsed and isinstance(parsed["manifests"], list):
            return True
        return False
    except (json.JSONDecodeError, TypeError):
        return False


def get_manifest_media_type(manifest_bytes: str) -> Optional[str]:
    """Extract media type from manifest JSON."""
    try:
        return json.loads(manifest_bytes).get("mediaType")
    except (json.JSONDecodeError, TypeError):
        return None


def filter_manifests_by_architecture(manifest_bytes: str, architectures: list[str]) -> list[dict]:
    """
    Filter manifest list entries to only include specified architectures.

    Returns list of manifest entries with digest, size, and platform info.
    """
    try:
        parsed = json.loads(manifest_bytes)
    except json.JSONDecodeError:
        return []

    filtered = []
    for manifest in parsed.get("manifests", []):
        platform = manifest.get("platform", {})
        arch = platform.get("architecture", "")
        if arch in architectures:
            filtered.append(manifest)
            logger.debug("Including manifest %s for arch %s", manifest.get("digest"), arch)
    return filtered


def get_available_architectures(manifest_bytes: str) -> list[str]:
    """Get all architectures present in a manifest list."""
    try:
        parsed = json.loads(manifest_bytes)
    except json.JSONDecodeError:
        return []

    return [
        m.get("platform", {}).get("architecture")
        for m in parsed.get("manifests", [])
        if m.get("platform", {}).get("architecture")
    ]
