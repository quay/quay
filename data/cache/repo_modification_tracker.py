import logging

logger = logging.getLogger(__name__)

KEY_PREFIX = "quay:repo_content_tracker:"


class RepoModificationTracker:
    """
    Tracks repository modifications and permission revocations using Redis server time.

    Keys:
        quay:repo_content_tracker:repo_modified:{namespace}:{repo} -> Redis timestamp (seconds.microseconds)
        quay:repo_content_tracker:permission_revoked:{user_id}:{namespace}:{repo} -> Redis timestamp

    Using Redis TIME command ensures all timestamps come from a single source,
    avoiding clock skew problems across distributed application servers.
    """

    def __init__(self, redis_client):
        """
        Initialize the tracker.

        Args:
            redis_client: Redis client instance (e.g. from the model cache), or None
        """
        self.redis = redis_client

    def _get_redis_time(self):
        """
        Get current time from Redis server.

        Returns:
            float: Timestamp in seconds with microsecond precision,
                   or None if Redis is unavailable
        """
        if not self.redis:
            return None

        try:
            # Redis TIME returns [seconds, microseconds]
            seconds, microseconds = self.redis.time()
            return float(seconds) + (float(microseconds) / 1_000_000)
        except Exception as e:
            logger.warning("Failed to get Redis server time: %s", e)
            return None

    def mark_repo_modified(self, namespace, repo_name):
        """
        Mark a repository as modified at current Redis server time.

        Should be called when tags are created, updated, or deleted.

        Args:
            namespace: Repository namespace
            repo_name: Repository name

        Returns:
            float: Timestamp when modification was recorded, or None on error
        """
        if not self.redis:
            return None

        try:
            redis_time = self._get_redis_time()
            if redis_time is None:
                return None

            key = f"{KEY_PREFIX}repo_modified:{namespace}:{repo_name}"
            self.redis.set(key, redis_time, ex=300)  # 5 minute TTL
            return redis_time
        except Exception as e:
            logger.warning("Failed to mark repo modified: %s", e)
            return None

    def mark_permission_revoked(self, user_id, namespace, repo_name):
        """
        Mark a permission as revoked at current Redis server time.

        Should be called when user's repository permission is removed.

        Args:
            user_id: User whose permission was revoked
            namespace: Repository namespace
            repo_name: Repository name

        Returns:
            float: Timestamp when revocation was recorded, or None on error
        """
        if not self.redis:
            return None

        try:
            redis_time = self._get_redis_time()
            if redis_time is None:
                return None

            key = f"{KEY_PREFIX}permission_revoked:{user_id}:{namespace}:{repo_name}"
            self.redis.set(key, redis_time, ex=300)  # 5 minute TTL
            return redis_time
        except Exception as e:
            logger.warning("Failed to mark permission revoked: %s", e)
            return None

    def mark_permissions_revoked_batch(self, user_ids, namespace, repo_name):
        """
        Mark permissions as revoked for multiple users using a Redis pipeline.

        Args:
            user_ids: Iterable of user IDs whose permissions were revoked
            namespace: Repository namespace
            repo_name: Repository name

        Returns:
            float: Timestamp when revocations were recorded, or None on error
        """
        if not self.redis:
            return None

        try:
            redis_time = self._get_redis_time()
            if redis_time is None:
                return None

            pipe = self.redis.pipeline()
            for user_id in user_ids:
                key = f"{KEY_PREFIX}permission_revoked:{user_id}:{namespace}:{repo_name}"
                pipe.set(key, redis_time, ex=300)
            pipe.execute()
            return redis_time
        except Exception as e:
            logger.warning("Failed to batch mark permissions revoked: %s", e)
            return None

    def should_block_read_access(self, user_id, namespace, repo_name):
        """
        Check if read access should be blocked due to repo modification after revocation.

        Logic:
        1. If no revocation recorded → allow (user still has permission or never had it)
        2. If no modification time → allow (assume repo is old, unchanged content)
        3. If repo modified after revocation → block (new content user shouldn't see)
        4. If repo modified before revocation → allow (old content they could have seen)

        NOTE: If Redis is unavailable (self.redis is None), this returns False (allow).
        However, callers SHOULD check tracker.redis before calling this method.
        If Redis is unavailable, callers should fall back to primary DB instead of
        using read replicas.

        Args:
            user_id: User to check
            namespace: Repository namespace
            repo_name: Repository name

        Returns:
            bool: True if access should be blocked, False if allowed

        Important: Returns False if Redis unavailable - caller should check
                   tracker.redis and use primary DB fallback in that case.
        """
        if not self.redis:
            # No Redis, can't track - return allow but caller should use primary DB
            return False

        try:
            # Get revocation time
            revoke_key = f"{KEY_PREFIX}permission_revoked:{user_id}:{namespace}:{repo_name}"
            revoke_time_str = self.redis.get(revoke_key)

            if revoke_time_str is None:
                # No revocation recorded, allow access
                return False

            revoke_time = float(revoke_time_str)

            # Get modification time
            mod_key = f"{KEY_PREFIX}repo_modified:{namespace}:{repo_name}"
            mod_time_str = self.redis.get(mod_key)

            if mod_time_str is None:
                # No modification tracking - assume old content, allow
                return False

            mod_time = float(mod_time_str)

            # Compare times
            if mod_time > revoke_time:
                # Repo was modified AFTER permission revocation - block access
                logger.debug(
                    "BLOCKING access: repo %s/%s modified after revocation. "
                    "user=%s, revoked_at=%s, modified_at=%s",
                    namespace,
                    repo_name,
                    user_id,
                    revoke_time,
                    mod_time,
                )
                return True
            else:
                # Repo was modified BEFORE revocation - allow access to old content
                return False

        except Exception as e:
            # On error, fail open (allow) to avoid breaking legitimate requests
            logger.warning(
                "Error checking repo modification for user=%s, repo=%s/%s: %s - allowing access",
                user_id,
                namespace,
                repo_name,
                e,
            )
            return False
