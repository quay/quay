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

DEFAULT_MAX_MANIFEST_LIST_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_MAX_MANIFEST_ENTRIES = 1000


def _check_manifest_size(manifest_bytes, max_size: int) -> bool:
    """Return True if manifest_bytes is within the allowed size limit."""
    if manifest_bytes is None:
        return False
    size = (
        len(manifest_bytes.encode("utf-8"))
        if isinstance(manifest_bytes, str)
        else len(manifest_bytes)
    )
    if size > max_size:
        logger.error(
            "Manifest list exceeds maximum size: %d bytes (limit: %d bytes)",
            size,
            max_size,
        )
        return False
    return True


def is_manifest_list(
    manifest_bytes: str,
    max_size: int = DEFAULT_MAX_MANIFEST_LIST_SIZE,
) -> bool:
    """Check if manifest JSON represents a manifest list/index."""
    if not _check_manifest_size(manifest_bytes, max_size):
        return False

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


def filter_manifests_by_architecture(
    manifest_bytes: str,
    architectures: list[str],
    max_size: int = DEFAULT_MAX_MANIFEST_LIST_SIZE,
    max_entries: int = DEFAULT_MAX_MANIFEST_ENTRIES,
) -> list[dict]:
    """
    Filter manifest list entries to only include specified architectures.

    Returns list of manifest entries with digest, size, and platform info.
    Validates manifest size before parsing and caps entry count to prevent DoS.
    """
    if not _check_manifest_size(manifest_bytes, max_size):
        return []

    try:
        parsed = json.loads(manifest_bytes)
    except json.JSONDecodeError:
        return []

    manifests = parsed.get("manifests", [])
    if len(manifests) > max_entries:
        logger.warning(
            "Manifest list has %d entries, exceeds limit of %d. Truncating.",
            len(manifests),
            max_entries,
        )
        manifests = manifests[:max_entries]

    filtered = []
    for manifest in manifests:
        platform = manifest.get("platform", {})
        arch = platform.get("architecture", "")
        if arch in architectures:
            filtered.append(manifest)
            logger.debug("Including manifest %s for arch %s", manifest.get("digest"), arch)
    return filtered


def get_available_architectures(
    manifest_bytes: str,
    max_size: int = DEFAULT_MAX_MANIFEST_LIST_SIZE,
    max_entries: int = DEFAULT_MAX_MANIFEST_ENTRIES,
) -> list[str]:
    """Get all architectures present in a manifest list."""
    if not _check_manifest_size(manifest_bytes, max_size):
        return []

    try:
        parsed = json.loads(manifest_bytes)
    except json.JSONDecodeError:
        return []

    manifests = parsed.get("manifests", [])
    if len(manifests) > max_entries:
        logger.warning(
            "Manifest list has %d entries, exceeds limit of %d. Truncating.",
            len(manifests),
            max_entries,
        )
        manifests = manifests[:max_entries]

    return [
        m.get("platform", {}).get("architecture")
        for m in manifests
        if m.get("platform", {}).get("architecture")
    ]
