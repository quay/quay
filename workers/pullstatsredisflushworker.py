"""
Redis Pull Metrics Flush Worker

Background worker that periodically flushes pull metrics from Redis to the database.
Processes Redis keys matching patterns:
- pull_events:repo:*:tag:*:*
- pull_events:repo:*:digest:*

Converts Redis pull events into persistent TagPullStatistics and ManifestPullStatistics records.
"""

import logging.config
import time
from datetime import datetime
from typing import Dict, List, Set, Tuple

import redis

import features
from app import app
from util.locking import GlobalLock
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

# Configuration constants
POLL_PERIOD = app.config.get("REDIS_FLUSH_INTERVAL_SECONDS", 300)  # 5 minutes
BATCH_SIZE = app.config.get("REDIS_FLUSH_WORKER_BATCH_SIZE", 1000)
REDIS_SCAN_COUNT = app.config.get("REDIS_FLUSH_WORKER_SCAN_COUNT", 100)


class RedisFlushWorker(Worker):
    """
    Worker that flushes pull metrics from Redis to database tables.

    This worker:
    1. Scans Redis for pull_events:* keys
    2. Processes pull events and aggregates data
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
            # Get Redis configuration
            redis_host = app.config.get("PULL_METRICS_REDIS_HOST", "localhost")
            redis_port = app.config.get("PULL_METRICS_REDIS_PORT", 6379)
            redis_db = app.config.get("PULL_METRICS_REDIS_DB", 0)
            redis_password = app.config.get("PULL_METRICS_REDIS_PASSWORD")
            redis_connection_timeout = app.config.get("REDIS_CONNECTION_TIMEOUT", 5)

            # Create Redis client
            self.redis_client = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=redis_connection_timeout,
                socket_timeout=redis_connection_timeout,
            )

            # Test connection
            self.redis_client.ping()
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
            tag_updates, manifest_updates, processed_keys = self._process_redis_events(
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
            keys: List[str] = []
            cursor = 0

            while len(keys) < limit:
                if self.redis_client is None:
                    break
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

    def _process_redis_events(self, keys: List[str]) -> Tuple[List[Dict], List[Dict], Set[str]]:
        """
        Process Redis events and aggregate data for database updates.

        Args:
            keys: List of Redis keys to process

        Returns:
            Tuple of (tag_updates, manifest_updates, processed_keys)
        """
        tag_updates = []
        manifest_updates = []
        processed_keys = set()

        for key in keys:
            try:
                # Basic validation - ensure it's a pull_events key
                if not key.startswith("pull_events:"):
                    continue

                # Get the data from Redis
                if self.redis_client is None:
                    continue
                metrics_data = self.redis_client.hgetall(key)
                if not metrics_data:
                    processed_keys.add(key)  # Empty key, mark for cleanup
                    continue

                # Extract data from Redis hash
                repository_id = int(metrics_data.get("repository_id", 0))
                tag_name = metrics_data.get("tag_name", "")
                manifest_digest = metrics_data.get("manifest_digest", "")
                pull_count = int(metrics_data.get("pull_count", 0))
                last_pull_timestamp = int(metrics_data.get("last_pull_timestamp", 0))
                pull_method = metrics_data.get("pull_method", "")

                if pull_count <= 0:
                    processed_keys.add(key)  # No pulls, mark for cleanup
                    continue

                # Convert timestamp
                pull_timestamp = (
                    datetime.fromtimestamp(last_pull_timestamp) if last_pull_timestamp > 0 else None
                )

                # Always update manifest stats (both tag and digest pulls)
                manifest_updates.append(
                    {
                        "repository_id": repository_id,
                        "manifest_digest": manifest_digest,
                        "pull_count": pull_count,
                        "last_pull": pull_timestamp,
                    }
                )

                # Additionally update tag stats for tag pulls
                if pull_method == "tag" and tag_name:
                    tag_updates.append(
                        {
                            "repository_id": repository_id,
                            "tag_name": tag_name,
                            "manifest_digest": manifest_digest,
                            "pull_count": pull_count,
                            "last_pull": pull_timestamp,
                        }
                    )

                processed_keys.add(key)

            except Exception as e:
                logger.error(f"RedisFlushWorker: Error processing key {key}: {e}")
                continue

        return tag_updates, manifest_updates, processed_keys

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

            # TODO: Implement database operations when schema is ready
            # Process tag updates
            if tag_updates:
                # tag_count = bulk_upsert_tag_statistics(tag_updates)
                tag_count = len(tag_updates)  # Mock for now
                logger.info(
                    f"RedisFlushWorker: Would update {tag_count}/{len(tag_updates)} tag statistics"
                )

            # Process manifest updates
            if manifest_updates:
                # manifest_count = bulk_upsert_manifest_statistics(manifest_updates)
                manifest_count = len(manifest_updates)  # Mock for now
                logger.info(
                    f"RedisFlushWorker: Would update {manifest_count}/{len(manifest_updates)} manifest statistics"
                )

            # Consider it successful if we processed some records
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
                if self.redis_client is not None:
                    deleted_count = self.redis_client.delete(*batch)
                    logger.debug(
                        f"RedisFlushWorker: Deleted {deleted_count}/{len(batch)} Redis keys"
                    )

        except Exception as e:
            logger.error(f"RedisFlushWorker: Error cleaning up Redis keys: {e}")


def create_gunicorn_worker():
    """Create the Gunicorn worker instance."""
    worker = GunicornWorker(__name__, app, RedisFlushWorker(), features.IMAGE_PULL_STATS)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    # Check if Redis pull metrics feature is enabled
    if not features.IMAGE_PULL_STATS:
        logger.debug("Redis pull metrics disabled; skipping redisflushworker")
        while True:
            time.sleep(100000)

    # Check if Redis is configured
    if not app.config.get("PULL_METRICS_REDIS"):
        logger.debug("PULL_METRICS_REDIS not configured; skipping redis flush worker")
        while True:
            time.sleep(100000)

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = RedisFlushWorker()
    worker.start()
