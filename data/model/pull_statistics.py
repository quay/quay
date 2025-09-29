"""
Business logic for pull statistics operations.

This module provides functions for managing pull statistics data:
- Bulk upsert operations for tag and manifest statistics
- Helper functions for individual record operations
- Query functions for retrieving statistics
"""
import logging
from datetime import datetime
from functools import reduce
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
    Upsert tag pull statistics in bulk using optimized batch operations.

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

    try:
        with db_transaction():
            # Parse and validate all timestamps first
            parsed_updates = []
            for update in tag_updates:
                try:
                    last_pull_timestamp = update["last_pull_timestamp"]
                    if isinstance(last_pull_timestamp, datetime):
                        last_pull = last_pull_timestamp
                    elif isinstance(last_pull_timestamp, str):
                        last_pull = datetime.fromisoformat(
                            last_pull_timestamp.replace("Z", "+00:00")
                        )
                    else:
                        raise ValueError(f"Invalid timestamp format: {last_pull_timestamp}")

                    parsed_updates.append(
                        {
                            "repository_id": update["repository_id"],
                            "tag_name": update["tag_name"],
                            "pull_count": update["pull_count"],
                            "last_pull_date": last_pull,
                            "manifest_digest": update["manifest_digest"],
                        }
                    )
                except (ValueError, KeyError) as e:
                    logger.error(f"Failed to parse tag update: {e}")
                    raise PullStatisticsException(f"Invalid tag update data: {e}")

            # Build conditions for existing records lookup
            # Create a list of (repository_id, tag_name) tuples for bulk lookup
            lookup_keys = [(u["repository_id"], u["tag_name"]) for u in parsed_updates]

            # Chunk the lookup to avoid SQLite parser stack overflow with large OR queries
            CHUNK_SIZE = 50  # Reasonable limit for OR conditions
            existing_records = {}

            for i in range(0, len(lookup_keys), CHUNK_SIZE):
                chunk = lookup_keys[i : i + CHUNK_SIZE]

                if chunk:
                    conditions = []
                    for repo_id, tag_name in chunk:
                        conditions.append(
                            (TagPullStatistics.repository == repo_id)
                            & (TagPullStatistics.tag_name == tag_name)
                        )

                    # Combine all conditions with OR using bitwise operator
                    combined_condition = reduce(lambda a, b: a | b, conditions)
                    existing_query = TagPullStatistics.select().where(combined_condition)

                    # Add results to our existing_records map
                    for record in existing_query:
                        key = (record.repository.id, record.tag_name)
                        existing_records[key] = record

            # Separate updates into existing vs new records
            updates_for_existing = []
            new_records_data = []

            for update in parsed_updates:
                key = (update["repository_id"], update["tag_name"])

                if key in existing_records:
                    # Record exists - prepare for bulk update
                    existing_record = existing_records[key]
                    updates_for_existing.append(
                        {
                            "record": existing_record,
                            "new_count": existing_record.tag_pull_count + update["pull_count"],
                            "new_date": max(
                                existing_record.last_tag_pull_date, update["last_pull_date"]
                            ),
                            "new_digest": update["manifest_digest"],
                        }
                    )
                else:
                    # New record - prepare for bulk insert
                    new_records_data.append(
                        {
                            "repository": update["repository_id"],
                            "tag_name": update["tag_name"],
                            "tag_pull_count": update["pull_count"],
                            "last_tag_pull_date": update["last_pull_date"],
                            "current_manifest_digest": update["manifest_digest"],
                        }
                    )

            rows_affected = 0

            # Bulk update existing records
            for update_data in updates_for_existing:
                record = update_data["record"]
                record.tag_pull_count = update_data["new_count"]
                record.last_tag_pull_date = update_data["new_date"]
                record.current_manifest_digest = update_data["new_digest"]
                record.save()
                rows_affected += 1

            # Bulk insert new records
            if new_records_data:
                TagPullStatistics.insert_many(new_records_data).execute()
                rows_affected += len(new_records_data)

            return rows_affected

    except (IntegrityError, Exception) as e:
        logger.error(f"Failed to bulk upsert tag statistics: {e}")
        raise PullStatisticsException(f"Bulk upsert failed: {e}")


def bulk_upsert_manifest_statistics(manifest_updates: List[Dict]) -> int:
    """
    Upsert manifest pull statistics in bulk using optimized batch operations.

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

    try:
        with db_transaction():
            # Parse and validate all timestamps first
            parsed_updates = []
            for update in manifest_updates:
                try:
                    last_pull_timestamp = update["last_pull_timestamp"]
                    if isinstance(last_pull_timestamp, datetime):
                        last_pull = last_pull_timestamp
                    elif isinstance(last_pull_timestamp, str):
                        last_pull = datetime.fromisoformat(
                            last_pull_timestamp.replace("Z", "+00:00")
                        )
                    else:
                        raise ValueError(f"Invalid timestamp format: {last_pull_timestamp}")

                    parsed_updates.append(
                        {
                            "repository_id": update["repository_id"],
                            "manifest_digest": update["manifest_digest"],
                            "pull_count": update["pull_count"],
                            "last_pull_date": last_pull,
                        }
                    )
                except (ValueError, KeyError) as e:
                    logger.error(f"Failed to parse manifest update: {e}")
                    raise PullStatisticsException(f"Invalid manifest update data: {e}")

            # Build conditions for existing records lookup
            # Create a list of (repository_id, manifest_digest) tuples for bulk lookup
            lookup_keys = [(u["repository_id"], u["manifest_digest"]) for u in parsed_updates]

            # Chunk the lookup to avoid SQLite parser stack overflow with large OR queries
            CHUNK_SIZE = 50  # Reasonable limit for OR conditions
            existing_records = {}

            for i in range(0, len(lookup_keys), CHUNK_SIZE):
                chunk = lookup_keys[i : i + CHUNK_SIZE]

                if chunk:
                    conditions = []
                    for repo_id, manifest_digest in chunk:
                        conditions.append(
                            (ManifestPullStatistics.repository == repo_id)
                            & (ManifestPullStatistics.manifest_digest == manifest_digest)
                        )

                    # Combine all conditions with OR using bitwise operator
                    combined_condition = reduce(lambda a, b: a | b, conditions)
                    existing_query = ManifestPullStatistics.select().where(combined_condition)

                    # Add results to our existing_records map
                    for record in existing_query:
                        key = (record.repository.id, record.manifest_digest)
                        existing_records[key] = record

            # Separate updates into existing vs new records
            updates_for_existing = []
            new_records_data = []

            for update in parsed_updates:
                key = (update["repository_id"], update["manifest_digest"])

                if key in existing_records:
                    # Record exists - prepare for bulk update
                    existing_record = existing_records[key]
                    updates_for_existing.append(
                        {
                            "record": existing_record,
                            "new_count": existing_record.manifest_pull_count + update["pull_count"],
                            "new_date": max(
                                existing_record.last_manifest_pull_date, update["last_pull_date"]
                            ),
                        }
                    )
                else:
                    # New record - prepare for bulk insert
                    new_records_data.append(
                        {
                            "repository": update["repository_id"],
                            "manifest_digest": update["manifest_digest"],
                            "manifest_pull_count": update["pull_count"],
                            "last_manifest_pull_date": update["last_pull_date"],
                        }
                    )

            rows_affected = 0

            # Bulk update existing records
            for update_data in updates_for_existing:
                record = update_data["record"]
                record.manifest_pull_count = update_data["new_count"]
                record.last_manifest_pull_date = update_data["new_date"]
                record.save()
                rows_affected += 1

            # Bulk insert new records
            if new_records_data:
                ManifestPullStatistics.insert_many(new_records_data).execute()
                rows_affected += len(new_records_data)

            return rows_affected

    except (IntegrityError, Exception) as e:
        logger.error(f"Failed to bulk upsert manifest statistics: {e}")
        raise PullStatisticsException(f"Bulk upsert failed: {e}")


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
