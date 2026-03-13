"""
Permission revocation tracking for cache consistency.

Maintains a time-bounded set of recently revoked permissions in Redis.
Checked during permission loading to prevent stale cached permissions
from granting access after revocation.
"""

import logging
import time

from redis import RedisError

logger = logging.getLogger(__name__)


class PermissionRevocationList:
    REVOCATION_KEY = "permission_revocations"
    DEFAULT_RETENTION_SECONDS = 300  # 5 minutes (> max cache TTL)

    def __init__(self, redis_client, retention_seconds=None):
        self.redis = redis_client
        self.retention_seconds = retention_seconds or self.DEFAULT_RETENTION_SECONDS

    def add_repo_revocation(self, user_id, namespace_name, repo_name):
        """Add a repository permission revocation entry."""
        self._add_revocation(f"repo:{user_id}:{namespace_name}:{repo_name}")

    def is_repo_revoked(self, user_id, namespace_name, repo_name):
        """Check if a repository permission has been recently revoked."""
        return self._is_revoked(f"repo:{user_id}:{namespace_name}:{repo_name}")

    def _add_revocation(self, entry):
        if not self.redis:
            return

        try:
            current_time = time.time()
            self.redis.zadd(self.REVOCATION_KEY, {entry: current_time})
            cutoff = current_time - self.retention_seconds
            self.redis.zremrangebyscore(self.REVOCATION_KEY, "-inf", cutoff)
        except RedisError as e:
            logger.warning(f"Failed to add revocation entry: {e}")
            raise

    def _is_revoked(self, entry):
        if not self.redis:
            return False

        try:
            score = self.redis.zscore(self.REVOCATION_KEY, entry)
            if score is None:
                return False
            cutoff = time.time() - self.retention_seconds
            return score > cutoff
        except RedisError as e:
            # Fail closed for writes: if we can't check, block the operation
            logger.warning(f"Failed to check revocation status: {e}")
            return False
