"""
Business logic for pull statistics operations.

This module provides functions for managing pull statistics data:
- Bulk upsert operations for tag and manifest statistics
- Helper functions for individual record operations
- Query functions for retrieving statistics
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from peewee import IntegrityError

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
    Exception raised when pull statistics operations fail.
    """

    pass


def bulk_upsert_tag_statistics(tag_updates: List[Dict]) -> int:
    """
    Upsert tag pull statistics in bulk.

    Args:
        tag_updates: List of dictionaries with tag statistics data:
            [
                {
                    'repository_id': 123,
                    'tag_name': 'latest',
                    'pull_count': 5,
                    'last_pull_timestamp': '2024-01-01T12:00:00Z',
                    'manifest_digest': 'sha256:abc...'
                }
            ]

    Returns:
        Number of rows affected

    Raises:
        PullStatisticsException: If bulk operation fails
    """
    if not tag_updates:
        return 0

    rows_affected = 0

    with db_transaction():
        for update in tag_updates:
            try:
                # Parse timestamp
                last_pull = datetime.fromisoformat(
                    update["last_pull_timestamp"].replace("Z", "+00:00")
                )

                # Try to get existing record
                try:
                    existing = TagPullStatistics.get(
                        TagPullStatistics.repository == update["repository_id"],
                        TagPullStatistics.tag_name == update["tag_name"],
                    )

                    # Update existing record
                    existing.tag_pull_count += update["pull_count"]
                    existing.last_tag_pull_date = max(existing.last_tag_pull_date, last_pull)
                    existing.current_manifest_digest = update["manifest_digest"]
                    existing.save()
                    rows_affected += 1

                except TagPullStatistics.DoesNotExist:
                    # Create new record
                    TagPullStatistics.create(
                        repository=update["repository_id"],
                        tag_name=update["tag_name"],
                        tag_pull_count=update["pull_count"],
                        last_tag_pull_date=last_pull,
                        current_manifest_digest=update["manifest_digest"],
                    )
                    rows_affected += 1

            except (ValueError, KeyError, IntegrityError) as e:
                logger.error(f"Failed to upsert tag statistics: {e}")
                raise PullStatisticsException(f"Bulk upsert failed: {e}")

    return rows_affected


def bulk_upsert_manifest_statistics(manifest_updates: List[Dict]) -> int:
    """
    Upsert manifest pull statistics in bulk.

    Args:
        manifest_updates: List of dictionaries with manifest statistics data:
            [
                {
                    'repository_id': 123,
                    'manifest_digest': 'sha256:abc...',
                    'pull_count': 5,
                    'last_pull_timestamp': '2024-01-01T12:00:00Z'
                }
            ]

    Returns:
        Number of rows affected

    Raises:
        PullStatisticsException: If bulk operation fails
    """
    if not manifest_updates:
        return 0

    rows_affected = 0

    with db_transaction():
        for update in manifest_updates:
            try:
                # Parse timestamp
                last_pull = datetime.fromisoformat(
                    update["last_pull_timestamp"].replace("Z", "+00:00")
                )

                # Try to get existing record
                try:
                    existing = ManifestPullStatistics.get(
                        ManifestPullStatistics.repository == update["repository_id"],
                        ManifestPullStatistics.manifest_digest == update["manifest_digest"],
                    )

                    # Update existing record
                    existing.manifest_pull_count += update["pull_count"]
                    existing.last_manifest_pull_date = max(
                        existing.last_manifest_pull_date, last_pull
                    )
                    existing.save()
                    rows_affected += 1

                except ManifestPullStatistics.DoesNotExist:
                    # Create new record
                    ManifestPullStatistics.create(
                        repository=update["repository_id"],
                        manifest_digest=update["manifest_digest"],
                        manifest_pull_count=update["pull_count"],
                        last_manifest_pull_date=last_pull,
                    )
                    rows_affected += 1

            except (ValueError, KeyError, IntegrityError) as e:
                logger.error(f"Failed to upsert manifest statistics: {e}")
                raise PullStatisticsException(f"Bulk upsert failed: {e}")

    return rows_affected


def get_tag_pull_statistics(repository_id: int, tag_name: str) -> Optional[Dict]:
    """
    Get pull statistics for a specific tag.

    Args:
        repository_id: Repository ID
        tag_name: Tag name

    Returns:
        Dictionary with tag statistics or None if not found
    """
    try:
        stats = TagPullStatistics.get(
            TagPullStatistics.repository == repository_id, TagPullStatistics.tag_name == tag_name
        )
        return {
            "repository_id": stats.repository.id,
            "tag_name": stats.tag_name,
            "pull_count": stats.tag_pull_count,
            "last_pull_date": stats.last_tag_pull_date,
            "current_manifest_digest": stats.current_manifest_digest,
        }
    except TagPullStatistics.DoesNotExist:
        return None


def get_manifest_pull_statistics(repository_id: int, manifest_digest: str) -> Optional[Dict]:
    """
    Get pull statistics for a specific manifest.

    Args:
        repository_id: Repository ID
        manifest_digest: Manifest digest

    Returns:
        Dictionary with manifest statistics or None if not found
    """
    try:
        stats = ManifestPullStatistics.get(
            ManifestPullStatistics.repository == repository_id,
            ManifestPullStatistics.manifest_digest == manifest_digest,
        )
        return {
            "repository_id": stats.repository.id,
            "manifest_digest": stats.manifest_digest,
            "pull_count": stats.manifest_pull_count,
            "last_pull_date": stats.last_manifest_pull_date,
        }
    except ManifestPullStatistics.DoesNotExist:
        return None
