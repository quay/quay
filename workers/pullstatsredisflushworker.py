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
from data.model.pull_statistics import (
    PullStatisticsException,
    bulk_upsert_manifest_statistics,
    bulk_upsert_tag_statistics,
)
from digest.digest_tools import Digest, InvalidDigestException
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
            redis_config = app.config.get("PULL_METRICS_REDIS", {})
            redis_host = redis_config.get("host", "localhost")
            redis_port = redis_config.get("port", 6379)
            redis_db = redis_config.get("db", 1)
            redis_password = redis_config.get("password")
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

        except redis.ConnectionError:
            logger.warning("RedisFlushWorker: Redis connection failed (will retry)")
            self.redis_client = None
        except redis.RedisError as re:
            logger.error(f"RedisFlushWorker: Redis initialization error: {re}")
            self.redis_client = None
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
            (
                tag_updates,
                manifest_updates,
                cleanable_keys,
                database_dependent_keys,
            ) = self._process_redis_events(pull_event_keys)

            # Always clean up empty/invalid keys first
            if cleanable_keys:
                self._cleanup_redis_keys(cleanable_keys)
                logger.debug(
                    f"RedisFlushWorker: Cleaned up {len(cleanable_keys)} empty/invalid keys"
                )

            # Perform bulk database operations
            success = self._flush_to_database(tag_updates, manifest_updates)

            if success:
                # Clean up Redis keys after successful database writes
                self._cleanup_redis_keys(database_dependent_keys)

                elapsed_time = time.time() - start_time
                total_processed = len(cleanable_keys) + len(database_dependent_keys)
                logger.info(
                    f"RedisFlushWorker: Successfully processed {total_processed} keys "
                    f"({len(tag_updates)} tag updates, {len(manifest_updates)} manifest updates) "
                    f"in {elapsed_time:.2f}s"
                )
            else:
                logger.warning(
                    f"RedisFlushWorker: Database flush failed, keeping {len(database_dependent_keys)} keys for retry"
                )

        except redis.RedisError as re:
            logger.error(f"RedisFlushWorker: Redis error during pull metrics flush: {re}")
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
            keys_set: Set[str] = set()
            cursor = 0

            while len(keys_set) < limit:
                if self.redis_client is None:
                    break
                cursor, batch_keys = self.redis_client.scan(
                    cursor=cursor, match=pattern, count=REDIS_SCAN_COUNT
                )

                if batch_keys:
                    # Add keys to set to automatically deduplicate
                    keys_set.update(batch_keys)

                # Break if we've scanned through all keys
                if cursor == 0:
                    break

            # Convert set back to list and limit results
            keys_list = list(keys_set)
            return keys_list[:limit]  # Ensure we don't exceed the limit

        except redis.RedisError as re:
            logger.error(f"RedisFlushWorker: Redis error during key scan: {re}")
            return []
        except Exception as e:
            logger.error(f"RedisFlushWorker: Error scanning Redis keys: {e}")
            return []

    def _process_redis_events(
        self, keys: List[str]
    ) -> Tuple[List[Dict], List[Dict], Set[str], Set[str]]:
        """
        Process Redis events and aggregate data for database updates.

        Args:
            keys: List of Redis keys to process

        Returns:
            Tuple of (tag_updates, manifest_updates, cleanable_keys, database_dependent_keys)
        """
        tag_updates = []
        manifest_updates = []
        cleanable_keys = set()  # Keys that can always be cleaned up (empty/invalid)
        database_dependent_keys = (
            set()
        )  # Keys that should only be cleaned up after successful DB write

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
                    cleanable_keys.add(key)  # Empty key, can always be cleaned up
                    continue

                # Validate data before processing
                if not self._validate_redis_key_data(key, metrics_data):
                    cleanable_keys.add(key)  # Invalid key, can be cleaned up
                    continue

                # Extract data from Redis hash
                repository_id = int(metrics_data.get("repository_id", 0))
                tag_name = metrics_data.get("tag_name", "")
                manifest_digest = metrics_data.get("manifest_digest", "")
                pull_count = int(metrics_data.get("pull_count", 0))
                last_pull_timestamp = int(metrics_data.get("last_pull_timestamp", 0))
                pull_method = metrics_data.get("pull_method", "")

                if pull_count <= 0:
                    cleanable_keys.add(key)  # No pulls, can always be cleaned up
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
                        "last_pull_timestamp": pull_timestamp,
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
                            "last_pull_timestamp": pull_timestamp,
                        }
                    )

                # Mark this key for cleanup only after successful database write
                # ToDo: add exception handling after database write implementation
                database_dependent_keys.add(key)

            except redis.RedisError as re:
                logger.error(f"RedisFlushWorker: Redis error processing key {key}: {re}")
                continue
            except Exception as e:
                logger.error(f"RedisFlushWorker: Error processing key {key}: {e}")
                continue

        return tag_updates, manifest_updates, cleanable_keys, database_dependent_keys

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
            has_updates = bool(tag_updates or manifest_updates)

            # Process tag updates
            if tag_updates:
                tag_count = bulk_upsert_tag_statistics(tag_updates)
                logger.info(
                    f"RedisFlushWorker: Successfully updated {tag_count}/{len(tag_updates)} tag statistics"
                )

            # Process manifest updates
            if manifest_updates:
                manifest_count = bulk_upsert_manifest_statistics(manifest_updates)
                logger.info(
                    f"RedisFlushWorker: Successfully updated {manifest_count}/{len(manifest_updates)} manifest statistics"
                )

            # Consider it successful if:
            # 1. We processed some records, OR
            # 2. There were no updates to process (empty batch)
            return (tag_count > 0 or manifest_count > 0) or not has_updates

        except PullStatisticsException as e:
            logger.error(f"RedisFlushWorker: Pull statistics error during database flush: {e}")
            return False
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
            failed_deletions = []

            for i in range(0, len(key_list), batch_size):
                batch = key_list[i : i + batch_size]
                if self.redis_client is not None:
                    try:
                        deleted_count = self.redis_client.delete(*batch)
                        if deleted_count != len(batch):
                            # Some keys may have been deleted by another process or expired
                            logger.debug(
                                f"RedisFlushWorker: Expected to delete {len(batch)} keys, actually deleted {deleted_count}"
                            )
                        else:
                            logger.debug(
                                f"RedisFlushWorker: Successfully deleted {deleted_count} Redis keys"
                            )
                    except Exception as batch_e:
                        logger.warning(
                            f"RedisFlushWorker: Failed to delete batch of keys: {batch_e}"
                        )
                        failed_deletions.extend(batch)

            if failed_deletions:
                logger.warning(
                    f"RedisFlushWorker: Failed to delete {len(failed_deletions)} Redis keys - they may be retried later"
                )

        except redis.RedisError as re:
            logger.error(f"RedisFlushWorker: Redis error during key cleanup: {re}")
        except Exception as e:
            logger.error(f"RedisFlushWorker: Error cleaning up Redis keys: {e}")

    def _validate_redis_key_data(self, key: str, metrics_data: Dict) -> bool:
        """
        Validate Redis key data for consistency and completeness.

        Args:
            key: Redis key being processed
            metrics_data: Data retrieved from Redis

        Returns:
            True if data is valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = [
                "repository_id",
                "manifest_digest",
                "pull_count",
                "last_pull_timestamp",
            ]
            for field in required_fields:
                if field not in metrics_data:
                    logger.debug(f"RedisFlushWorker: Key {key} missing required field: {field}")
                    return False

            # Validate data types and ranges
            repository_id = int(metrics_data.get("repository_id", 0))
            pull_count = int(metrics_data.get("pull_count", 0))
            last_pull_timestamp = int(metrics_data.get("last_pull_timestamp", 0))

            if repository_id <= 0:
                logger.debug(
                    f"RedisFlushWorker: Key {key} has invalid repository_id: {repository_id}"
                )
                return False

            if pull_count < 0:  # 0 is valid for cleanup
                logger.debug(f"RedisFlushWorker: Key {key} has invalid pull_count: {pull_count}")
                return False

            if last_pull_timestamp < 0:
                logger.debug(
                    f"RedisFlushWorker: Key {key} has invalid timestamp: {last_pull_timestamp}"
                )
                return False

            manifest_digest = metrics_data.get("manifest_digest", "")
            if not manifest_digest:
                logger.debug(f"RedisFlushWorker: Key {key} missing manifest_digest")
                return False

            try:
                Digest.parse_digest(manifest_digest)
            except InvalidDigestException:
                logger.debug(
                    f"RedisFlushWorker: Key {key} has invalid manifest_digest: {manifest_digest}"
                )
                return False

            return True

        except (ValueError, TypeError) as e:
            logger.debug(f"RedisFlushWorker: Key {key} has invalid data format: {e}")
            return False


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
