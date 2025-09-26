"""
Model for managing pull statistics data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from peewee import DoesNotExist, IntegrityError

from data.database import (
    ManifestPullStatistics,
    Repository,
    TagPullStatistics,
    db_transaction,
)
from data.model import DataModelException

logger = logging.getLogger(__name__)


class PullStatisticsException(DataModelException):
    """
    Exception raised for pull statistics-related errors.
    """

    pass


def get_tag_pull_statistics(repository_id: int, tag_name: str) -> Optional[TagPullStatistics]:
    """
    Get pull statistics for a specific tag in a repository.

    Args:
        repository_id: The repository ID
        tag_name: The tag name

    Returns:
        TagPullStatistics object or None if not found
    """
    try:
        return TagPullStatistics.get(
            TagPullStatistics.repository == repository_id, TagPullStatistics.tag_name == tag_name
        )
    except DoesNotExist:
        return None


def get_manifest_pull_statistics(
    repository_id: int, manifest_digest: str
) -> Optional[ManifestPullStatistics]:
    """
    Get pull statistics for a specific manifest in a repository.

    Args:
        repository_id: The repository ID
        manifest_digest: The manifest digest

    Returns:
        ManifestPullStatistics object or None if not found
    """
    try:
        return ManifestPullStatistics.get(
            ManifestPullStatistics.repository == repository_id,
            ManifestPullStatistics.manifest_digest == manifest_digest,
        )
    except DoesNotExist:
        return None


def upsert_tag_pull_statistics(
    repository_id: int,
    tag_name: str,
    pull_count_increment: int,
    manifest_digest: Optional[str] = None,
    pull_timestamp: Optional[datetime] = None,
) -> TagPullStatistics:
    """
    Insert or update pull statistics for a tag.

    Args:
        repository_id: The repository ID
        tag_name: The tag name
        pull_count_increment: Number of pulls to add to the count
        manifest_digest: The current manifest digest for this tag
        pull_timestamp: The timestamp of the pull (defaults to now)

    Returns:
        The updated/created TagPullStatistics object
    """
    if pull_timestamp is None:
        pull_timestamp = datetime.utcnow()

    try:
        with db_transaction():
            # Try to get existing record
            existing = get_tag_pull_statistics(repository_id, tag_name)

            if existing:
                # Update existing record
                existing.tag_pull_count += pull_count_increment
                existing.last_tag_pull_date = pull_timestamp
                if manifest_digest:
                    existing.current_manifest_digest = manifest_digest
                existing.save()
                return existing
            else:
                # Create new record
                return TagPullStatistics.create(
                    repository=repository_id,
                    tag_name=tag_name,
                    tag_pull_count=pull_count_increment,
                    last_tag_pull_date=pull_timestamp,
                    current_manifest_digest=manifest_digest,
                )
    except IntegrityError as e:
        logger.warning(f"Integrity error upserting tag pull statistics: {e}")
        # Handle race condition - retry once
        existing = get_tag_pull_statistics(repository_id, tag_name)
        if existing:
            with db_transaction():
                existing.tag_pull_count += pull_count_increment
                existing.last_tag_pull_date = pull_timestamp
                if manifest_digest:
                    existing.current_manifest_digest = manifest_digest
                existing.save()
                return existing
        raise PullStatisticsException(f"Failed to upsert tag pull statistics: {e}")


def upsert_manifest_pull_statistics(
    repository_id: int,
    manifest_digest: str,
    pull_count_increment: int,
    pull_timestamp: Optional[datetime] = None,
) -> ManifestPullStatistics:
    """
    Insert or update pull statistics for a manifest.

    Args:
        repository_id: The repository ID
        manifest_digest: The manifest digest
        pull_count_increment: Number of pulls to add to the count
        pull_timestamp: The timestamp of the pull (defaults to now)

    Returns:
        The updated/created ManifestPullStatistics object
    """
    if pull_timestamp is None:
        pull_timestamp = datetime.utcnow()

    try:
        with db_transaction():
            # Try to get existing record
            existing = get_manifest_pull_statistics(repository_id, manifest_digest)

            if existing:
                # Update existing record
                existing.manifest_pull_count += pull_count_increment
                existing.last_manifest_pull_date = pull_timestamp
                existing.save()
                return existing
            else:
                # Create new record
                return ManifestPullStatistics.create(
                    repository=repository_id,
                    manifest_digest=manifest_digest,
                    manifest_pull_count=pull_count_increment,
                    last_manifest_pull_date=pull_timestamp,
                )
    except IntegrityError as e:
        logger.warning(f"Integrity error upserting manifest pull statistics: {e}")
        # Handle race condition - retry once
        existing = get_manifest_pull_statistics(repository_id, manifest_digest)
        if existing:
            with db_transaction():
                existing.manifest_pull_count += pull_count_increment
                existing.last_manifest_pull_date = pull_timestamp
                existing.save()
                return existing
        raise PullStatisticsException(f"Failed to upsert manifest pull statistics: {e}")


def bulk_upsert_tag_statistics(tag_updates: List[Dict]) -> int:
    """
    Efficiently bulk upsert tag pull statistics.

    Args:
        tag_updates: List of dicts with keys: repository_id, tag_name, pull_count_increment,
                    manifest_digest, pull_timestamp

    Returns:
        Number of records processed
    """
    if not tag_updates:
        return 0

    processed_count = 0

    with db_transaction():
        for update in tag_updates:
            try:
                upsert_tag_pull_statistics(
                    repository_id=update["repository_id"],
                    tag_name=update["tag_name"],
                    pull_count_increment=update["pull_count_increment"],
                    manifest_digest=update.get("manifest_digest"),
                    pull_timestamp=update.get("pull_timestamp"),
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process tag update {update}: {e}")
                # Continue processing other updates
                continue

    return processed_count


def bulk_upsert_manifest_statistics(manifest_updates: List[Dict]) -> int:
    """
    Efficiently bulk upsert manifest pull statistics.

    Args:
        manifest_updates: List of dicts with keys: repository_id, manifest_digest,
                         pull_count_increment, pull_timestamp

    Returns:
        Number of records processed
    """
    if not manifest_updates:
        return 0

    processed_count = 0

    with db_transaction():
        for update in manifest_updates:
            try:
                upsert_manifest_pull_statistics(
                    repository_id=update["repository_id"],
                    manifest_digest=update["manifest_digest"],
                    pull_count_increment=update["pull_count_increment"],
                    pull_timestamp=update.get("pull_timestamp"),
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process manifest update {update}: {e}")
                # Continue processing other updates
                continue

    return processed_count


def get_repository_tag_statistics(repository_id: int, limit: int = 100) -> List[TagPullStatistics]:
    """
    Get pull statistics for all tags in a repository, ordered by pull count descending.

    Args:
        repository_id: The repository ID
        limit: Maximum number of records to return

    Returns:
        List of TagPullStatistics objects
    """
    return list(
        TagPullStatistics.select()
        .where(TagPullStatistics.repository == repository_id)
        .order_by(TagPullStatistics.tag_pull_count.desc())
        .limit(limit)
    )


def get_repository_manifest_statistics(
    repository_id: int, limit: int = 100
) -> List[ManifestPullStatistics]:
    """
    Get pull statistics for all manifests in a repository, ordered by pull count descending.

    Args:
        repository_id: The repository ID
        limit: Maximum number of records to return

    Returns:
        List of ManifestPullStatistics objects
    """
    return list(
        ManifestPullStatistics.select()
        .where(ManifestPullStatistics.repository == repository_id)
        .order_by(ManifestPullStatistics.manifest_pull_count.desc())
        .limit(limit)
    )
