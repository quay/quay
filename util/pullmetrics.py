"""
Utility module for recording pull events to Redis (write-only).

This module provides functionality to capture pull events for images during docker pulls.
Events are stored temporarily in Redis and processed by RedisFlushWorker into persistent database storage.

Architecture:
- Docker Pull → Redis (this module) - Fast, non-blocking writes
- Redis → Database (RedisFlushWorker) - Background aggregation
- Database → UI (pull_statistics model) - Consistent reads
"""
import json
import logging
import time
from typing import Any, Dict, Optional

from redis import StrictRedis

logger = logging.getLogger(__name__)


class PullMetricsTracker:
    """
    Records pull metrics to Redis for background processing (write-only).

    Architecture:
    - WRITE: Pull Events → Redis (fast, non-blocking)
    - PROCESS: Redis → Worker → Database (background aggregation)
    - READ: UI ← Database (persistent, consistent)

    Redis keys:
    - pull_events:repo:{repository_id}:tag:{tag_name}:{manifest_digest}
    - pull_events:repo:{repository_id}:digest:{manifest_digest}
    """

    def __init__(self, redis_client):
        """Initialize with a Redis client."""
        self.redis_client = redis_client

    def _get_tag_pull_key(self, repository_id: str, tag_name: str, manifest_digest: str) -> str:
        """Generate Redis key for tag-based pulls."""
        return f"pull_events:repo:{repository_id}:tag:{tag_name}:{manifest_digest}"

    def _get_digest_pull_key(self, repository_id: str, manifest_digest: str) -> str:
        """Generate Redis key for digest-based pulls."""
        return f"pull_events:repo:{repository_id}:digest:{manifest_digest}"

    def record_tag_pull(self, repository_id: str, tag_name: str, manifest_digest: str) -> None:
        """
        Record a pull event for a tag.

        Args:
            repository_id: The repository ID
            tag_name: The tag name that was pulled
            manifest_digest: The manifest digest
        """
        try:
            key = self._get_tag_pull_key(repository_id, tag_name, manifest_digest)
            current_time = int(time.time())

            # Use Redis HSET to store/update the pull metrics
            self.redis_client.hmset(
                key,
                {
                    "repository_id": repository_id,
                    "tag_name": tag_name,
                    "manifest_digest": manifest_digest,
                    "last_pull_timestamp": current_time,
                    "pull_method": "tag",
                },
            )

            # Increment pull count
            self.redis_client.hincrby(key, "pull_count", 1)

            # Set expiration to 30 days (2592000 seconds) to prevent Redis bloat
            self.redis_client.expire(key, 2592000)

            logger.debug(
                "Recorded tag pull for repo=%s, tag=%s, digest=%s",
                repository_id,
                tag_name,
                manifest_digest,
            )

        except Exception as e:
            logger.warning(
                "Failed to record tag pull metrics for repo=%s, tag=%s: %s",
                repository_id,
                tag_name,
                str(e),
            )

    def record_digest_pull(self, repository_id: str, manifest_digest: str) -> None:
        """
        Record a pull event for a manifest digest.

        Args:
            repository_id: The repository ID
            manifest_digest: The manifest digest that was pulled
        """
        try:
            key = self._get_digest_pull_key(repository_id, manifest_digest)
            current_time = int(time.time())

            # Use Redis HSET to store/update the pull metrics
            self.redis_client.hmset(
                key,
                {
                    "repository_id": repository_id,
                    "manifest_digest": manifest_digest,
                    "last_pull_timestamp": current_time,
                    "pull_method": "digest",
                },
            )

            # Increment pull count
            self.redis_client.hincrby(key, "pull_count", 1)

            # Set expiration to 30 days (2592000 seconds) to prevent Redis bloat
            self.redis_client.expire(key, 2592000)

            logger.debug(
                "Recorded digest pull for repo=%s, digest=%s", repository_id, manifest_digest
            )

        except Exception as e:
            logger.warning(
                "Failed to record digest pull metrics for repo=%s, digest=%s: %s",
                repository_id,
                manifest_digest,
                str(e),
            )

    # Note: Redis read methods removed - pull metrics are now served exclusively from database
    # Redis is used only for fast, non-blocking writes during pull operations
    # The RedisFlushWorker processes Redis data into persistent database storage


def get_pull_metrics_tracker(redis_client) -> PullMetricsTracker:
    """
    Factory function to create a PullMetricsTracker instance.

    Args:
        redis_client: Redis client instance

    Returns:
        PullMetricsTracker instance
    """
    return PullMetricsTracker(redis_client)


def create_redis_client_from_config(redis_config):
    """
    Create a Redis client from configuration.

    Args:
        redis_config: Dictionary with Redis configuration (host, port, password, etc.)

    Returns:
        Redis client instance
    """
    if not redis_config:
        return None

    return StrictRedis(
        host=redis_config.get("host", "localhost"),
        port=redis_config.get("port", 6379),
        password=redis_config.get("password"),
        db=redis_config.get("db", 0),
        socket_connect_timeout=1,
        socket_timeout=2,
        health_check_interval=2,
        decode_responses=True,  # This will automatically decode bytes to strings
    )
