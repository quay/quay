"""
Redis Pull Metrics Flush Worker

Background worker that periodically flushes pull metrics from Redis to the database.
Processes Redis keys matching patterns:
- pull_events:repo:*:tag:*:*
- pull_events:repo:*:digest:*

Converts Redis pull events into persistent TagPullStatistics and ManifestPullStatistics records.
"""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import redis

from app import app
from data.model.pull_statistics import (
    bulk_upsert_manifest_statistics,
    bulk_upsert_tag_statistics,
)
from util.pullmetrics import create_redis_client_from_config
from workers.worker import Worker

logger = logging.getLogger(__name__)

# Configuration constants
POLL_PERIOD = app.config.get("REDIS_FLUSH_WORKER_POLL_PERIOD", 300)  # 5 minutes
BATCH_SIZE = app.config.get("REDIS_FLUSH_WORKER_BATCH_SIZE", 1000)
REDIS_SCAN_COUNT = app.config.get("REDIS_FLUSH_WORKER_SCAN_COUNT", 100)


class RedisFlushWorker(Worker):
    """
    Worker that flushes pull metrics from Redis to database tables.

    This worker:
    1. Scans Redis for pull_events:* keys
    2. Aggregates pull counts and timestamps by repository/tag/manifest
    3. Performs bulk upserts to TagPullStatistics and ManifestPullStatistics tables
    4. Cleans up Redis keys after successful database writes
    """

    def __init__(self):
        super(RedisFlushWorker, self).__init__()
        self.redis_client = None
        self._initialize_redis_client()
        self.add_operation(self._flush_pull_metrics, POLL_PERIOD)

    def _initialize_redis_client(self):
        """Initialize Redis client for pull metrics."""
        try:
            redis_config = app.config.get("PULL_METRICS_REDIS")
            if not redis_config:
                logger.error("PULL_METRICS_REDIS configuration not found")
                return

            self.redis_client = create_redis_client_from_config(redis_config)
            logger.info("RedisFlushWorker: Initialized Redis client for pull metrics")

        except Exception as e:
            logger.error(f"RedisFlushWorker: Failed to initialize Redis client: {e}")
            self.redis_client = None

    def _flush_pull_metrics(self):
        """Main method to flush pull metrics from Redis to database."""
        if not self.redis_client:
            logger.warning("RedisFlushWorker: Redis client not initialized, skipping flush")
            return

        try:
            logger.debug("RedisFlushWorker: Starting pull metrics flush")
            start_time = time.time()

            # Scan for pull event keys
            pull_event_keys = self._scan_redis_keys("pull_events:*", BATCH_SIZE)

            if not pull_event_keys:
                logger.debug("RedisFlushWorker: No pull event keys found")
                return

            logger.info(f"RedisFlushWorker: Processing {len(pull_event_keys)} Redis keys")

            # Process keys and aggregate data
            tag_updates, manifest_updates, processed_keys = self._aggregate_pull_events(
                pull_event_keys
            )

            # Perform bulk database operations
            success = self._flush_to_database(tag_updates, manifest_updates)

            if success:
                # Clean up Redis keys after successful database writes
                self._cleanup_redis_keys(processed_keys)

                elapsed_time = time.time() - start_time
                logger.info(
                    f"RedisFlushWorker: Successfully processed {len(processed_keys)} keys "
                    f"({len(tag_updates)} tag updates, {len(manifest_updates)} manifest updates) "
                    f"in {elapsed_time:.2f}s"
                )
            else:
                logger.warning(
                    "RedisFlushWorker: Database flush failed, keeping Redis keys for retry"
                )

        except Exception as e:
            logger.error(f"RedisFlushWorker: Error during pull metrics flush: {e}")

    def _scan_redis_keys(self, pattern: str, limit: int) -> List[str]:
        """
        Scan Redis for keys matching the pattern.

        Args:
            pattern: Redis key pattern to match
            limit: Maximum number of keys to return

        Returns:
            List of matching Redis keys
        """
        try:
            keys = []
            cursor = 0

            while len(keys) < limit:
                cursor, batch_keys = self.redis_client.scan(
                    cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                )

                if batch_keys:
                    keys.extend(batch_keys)

                # Break if we've scanned through all keys
                if cursor == 0:
                    break

            return keys[:limit]  # Ensure we don't exceed the limit

        except Exception as e:
            logger.error(f"RedisFlushWorker: Error scanning Redis keys: {e}")
            return []

    def _aggregate_pull_events(self, keys: List[str]) -> Tuple[List[Dict], List[Dict], Set[str]]:
        """
        Aggregate pull events from Redis keys into database update structures.

        Args:
            keys: List of Redis keys to process

        Returns:
            Tuple of (tag_updates, manifest_updates, processed_keys)
        """
        tag_updates = defaultdict(
            lambda: {
                "pull_count_increment": 0,
                "last_pull_timestamp": None,
                "manifest_digest": None,
            }
        )
        manifest_updates = defaultdict(
            lambda: {"pull_count_increment": 0, "last_pull_timestamp": None}
        )
        processed_keys = set()

        for key in keys:
            try:
                # Parse the key to determine type and extract information
                key_info = self._parse_redis_key(key)
                if not key_info:
                    continue

                # Get the data from Redis
                metrics_data = self.redis_client.hgetall(key)
                if not metrics_data:
                    processed_keys.add(key)  # Empty key, mark for cleanup
                    continue

                pull_count = int(metrics_data.get("pull_count", 0))
                last_pull_timestamp = int(metrics_data.get("last_pull_timestamp", 0))
                pull_timestamp = (
                    datetime.fromtimestamp(last_pull_timestamp) if last_pull_timestamp > 0 else None
                )

                if key_info["type"] == "tag":
                    # Tag pull - update both tag and manifest statistics
                    tag_key = (key_info["repository_id"], key_info["tag_name"])
                    manifest_key = (key_info["repository_id"], key_info["manifest_digest"])

                    # Aggregate tag updates
                    tag_update = tag_updates[tag_key]
                    tag_update["pull_count_increment"] += pull_count
                    tag_update["manifest_digest"] = key_info["manifest_digest"]
                    if pull_timestamp and (
                        not tag_update["last_pull_timestamp"]
                        or pull_timestamp > tag_update["last_pull_timestamp"]
                    ):
                        tag_update["last_pull_timestamp"] = pull_timestamp

                    # Aggregate manifest updates
                    manifest_update = manifest_updates[manifest_key]
                    manifest_update["pull_count_increment"] += pull_count
                    if pull_timestamp and (
                        not manifest_update["last_pull_timestamp"]
                        or pull_timestamp > manifest_update["last_pull_timestamp"]
                    ):
                        manifest_update["last_pull_timestamp"] = pull_timestamp

                elif key_info["type"] == "digest":
                    # Digest pull - update only manifest statistics
                    manifest_key = (key_info["repository_id"], key_info["manifest_digest"])

                    manifest_update = manifest_updates[manifest_key]
                    manifest_update["pull_count_increment"] += pull_count
                    if pull_timestamp and (
                        not manifest_update["last_pull_timestamp"]
                        or pull_timestamp > manifest_update["last_pull_timestamp"]
                    ):
                        manifest_update["last_pull_timestamp"] = pull_timestamp

                processed_keys.add(key)

            except Exception as e:
                logger.error(f"RedisFlushWorker: Error processing key {key}: {e}")
                continue

        # Convert aggregated data to list format expected by bulk operations
        tag_updates_list = []
        for (repository_id, tag_name), update_data in tag_updates.items():
            tag_updates_list.append(
                {
                    "repository_id": repository_id,
                    "tag_name": tag_name,
                    "pull_count_increment": update_data["pull_count_increment"],
                    "manifest_digest": update_data["manifest_digest"],
                    "pull_timestamp": update_data["last_pull_timestamp"],
                }
            )

        manifest_updates_list = []
        for (repository_id, manifest_digest), update_data in manifest_updates.items():
            manifest_updates_list.append(
                {
                    "repository_id": repository_id,
                    "manifest_digest": manifest_digest,
                    "pull_count_increment": update_data["pull_count_increment"],
                    "pull_timestamp": update_data["last_pull_timestamp"],
                }
            )

        return tag_updates_list, manifest_updates_list, processed_keys

    def _parse_redis_key(self, key: str) -> Optional[Dict[str, str]]:
        """
        Parse a Redis key to extract pull event information.

        Expected formats:
        - pull_events:repo:{repository_id}:tag:{tag_name}:{manifest_digest}
        - pull_events:repo:{repository_id}:digest:{manifest_digest}

        Note: manifest_digest contains ':' (e.g., sha256:abc123), so we need to handle this properly.

        Args:
            key: Redis key to parse

        Returns:
            Dictionary with parsed key information or None if invalid
        """
        try:
            parts = key.split(":")

            if len(parts) < 5 or parts[0] != "pull_events" or parts[1] != "repo":
                return None

            repository_id = parts[2]
            pull_type = parts[3]

            if pull_type == "tag" and len(parts) >= 6:
                # Format: pull_events:repo:{repo_id}:tag:{tag_name}:{manifest_digest}
                # manifest_digest is everything after the 5th ':'
                tag_name = parts[4]
                manifest_digest = ":".join(parts[5:])  # Rejoin the digest parts
                return {
                    "type": "tag",
                    "repository_id": repository_id,
                    "tag_name": tag_name,
                    "manifest_digest": manifest_digest,
                }
            elif pull_type == "digest" and len(parts) >= 5:
                # Format: pull_events:repo:{repo_id}:digest:{manifest_digest}
                # manifest_digest is everything after the 4th ':'
                manifest_digest = ":".join(parts[4:])  # Rejoin the digest parts
                return {
                    "type": "digest",
                    "repository_id": repository_id,
                    "manifest_digest": manifest_digest,
                }

            return None

        except Exception as e:
            logger.warning(f"RedisFlushWorker: Error parsing key {key}: {e}")
            return None

    def _flush_to_database(self, tag_updates: List[Dict], manifest_updates: List[Dict]) -> bool:
        """
        Flush aggregated updates to the database.

        Args:
            tag_updates: List of tag update dictionaries
            manifest_updates: List of manifest update dictionaries

        Returns:
            True if successful, False otherwise
        """
        try:
            tag_count = 0
            manifest_count = 0

            # Process tag updates
            if tag_updates:
                tag_count = bulk_upsert_tag_statistics(tag_updates)
                logger.info(
                    f"RedisFlushWorker: Updated {tag_count}/{len(tag_updates)} tag statistics"
                )

            # Process manifest updates
            if manifest_updates:
                manifest_count = bulk_upsert_manifest_statistics(manifest_updates)
                logger.info(
                    f"RedisFlushWorker: Updated {manifest_count}/{len(manifest_updates)} manifest statistics"
                )

            # Consider it successful if we processed some records
            # (bulk operations may have partial failures but continue processing)
            return tag_count > 0 or manifest_count > 0 or (not tag_updates and not manifest_updates)

        except Exception as e:
            logger.error(f"RedisFlushWorker: Error flushing to database: {e}")
            return False

    def _cleanup_redis_keys(self, keys: Set[str]):
        """
        Clean up Redis keys after successful database write.

        Args:
            keys: Set of Redis keys to delete
        """
        if not keys:
            return

        try:
            # Delete keys in batches to avoid blocking Redis
            key_list = list(keys)
            batch_size = 100

            for i in range(0, len(key_list), batch_size):
                batch = key_list[i : i + batch_size]
                deleted_count = self.redis_client.delete(*batch)
                logger.debug(f"RedisFlushWorker: Deleted {deleted_count}/{len(batch)} Redis keys")

        except Exception as e:
            logger.error(f"RedisFlushWorker: Error cleaning up Redis keys: {e}")
