import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import redis

logger = logging.getLogger(__name__)

DEFAULT_PULL_METRICS_WORKER_COUNT = 5
DEFAULT_REDIS_CONNECTION_TIMEOUT = 5
DEFAULT_REDIS_RETRY_ATTEMPTS = 3
DEFAULT_REDIS_RETRY_DELAY = 1.0


class CannotReadPullMetricsException(Exception):
    """
    Exception raised if pull metrics cannot be read.
    """


class PullMetricsBuilder(object):
    """
    Defines a helper class for constructing PullMetrics instances.
    """

    def __init__(self, redis_config, max_workers=None):
        self._redis_config = redis_config
        self._max_workers = max_workers

    def get_event(self):
        return PullMetrics(self._redis_config, self._max_workers)


class PullMetricsBuilderModule(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        redis_config = app.config.get("PULL_METRICS_REDIS")
        if not redis_config:
            # This is the old key name.
            redis_config = {
                "host": app.config.get("PULL_METRICS_REDIS_HOSTNAME"),
            }

        # Add testing flag to redis config to disable thread pool during tests
        if app.config.get("TESTING", False):
            redis_config = redis_config.copy() if redis_config else {}
            redis_config["_testing"] = True

        max_workers = app.config.get("PULL_METRICS_WORKER_COUNT", DEFAULT_PULL_METRICS_WORKER_COUNT)
        pull_metrics = PullMetricsBuilder(redis_config, max_workers)

        app.extensions = getattr(app, "extensions", {})
        app.extensions["pullmetrics"] = pull_metrics
        app.extensions["pullmetrics_instance"] = pull_metrics

        return pull_metrics

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class PullMetrics(object):
    """
    Defines a helper class for tracking pull metrics as backed by Redis.

    Uses lazy initialization for Redis connection to handle cases where Redis
    may not be immediately available during application startup.
    """

    # Lua script for atomic tag pull tracking
    _TRACK_TAG_PULL_SCRIPT = """
    local key = KEYS[1]
    local repo_id = ARGV[1]
    local tag_name = ARGV[2]
    local manifest_digest = ARGV[3]
    local timestamp = ARGV[4]
    local pull_method = ARGV[5]

    -- Basic validation: ensure required fields are present
    if not repo_id or repo_id == '' or not tag_name or tag_name == '' or not manifest_digest or manifest_digest == '' then
        return redis.error_reply('Invalid input: missing required fields')
    end

    -- Validate timestamp is numeric
    local timestamp_num = tonumber(timestamp)
    if not timestamp_num or timestamp_num <= 0 then
        return redis.error_reply('Invalid input: timestamp must be positive number')
    end

    local exists = redis.call('EXISTS', key)

    if exists == 0 then
        redis.call('HSET', key,
            'repository_id', repo_id,
            'tag_name', tag_name,
            'manifest_digest', manifest_digest,
            'pull_count', 1,
            'last_pull_timestamp', timestamp,
            'pull_method', pull_method
        )
    else
        redis.call('HINCRBY', key, 'pull_count', 1)
        redis.call('HSET', key, 'last_pull_timestamp', timestamp)
    end

    return redis.call('HGET', key, 'pull_count')
    """

    # Lua script for atomic manifest pull tracking
    _TRACK_MANIFEST_PULL_SCRIPT = """
    local key = KEYS[1]
    local repo_id = ARGV[1]
    local manifest_digest = ARGV[2]
    local timestamp = ARGV[3]
    local pull_method = ARGV[4]

    -- Basic validation: ensure required fields are present
    if not repo_id or repo_id == '' or not manifest_digest or manifest_digest == '' then
        return redis.error_reply('Invalid input: missing required fields')
    end

    -- Validate timestamp is numeric
    local timestamp_num = tonumber(timestamp)
    if not timestamp_num or timestamp_num <= 0 then
        return redis.error_reply('Invalid input: timestamp must be positive number')
    end

    local exists = redis.call('EXISTS', key)

    if exists == 0 then
        redis.call('HSET', key,
            'repository_id', repo_id,
            'manifest_digest', manifest_digest,
            'pull_count', 1,
            'last_pull_timestamp', timestamp,
            'pull_method', pull_method,
            'tag_name', ''
        )
    else
        redis.call('HINCRBY', key, 'pull_count', 1)
        redis.call('HSET', key, 'last_pull_timestamp', timestamp)
    end

    return redis.call('HGET', key, 'pull_count')
    """

    def __init__(self, redis_config, max_workers=None):
        redis_config = (redis_config.copy() if redis_config else {}) or {}

        # Extract internal flags and connection settings (not passed to Redis)
        testing_mode = redis_config.pop("_testing", False)
        self._connection_timeout = redis_config.pop(
            "socket_connect_timeout", DEFAULT_REDIS_CONNECTION_TIMEOUT
        )
        self._socket_timeout = redis_config.pop("socket_timeout", DEFAULT_REDIS_CONNECTION_TIMEOUT)
        self._retry_attempts = redis_config.pop("retry_attempts", DEFAULT_REDIS_RETRY_ATTEMPTS)
        self._retry_delay = redis_config.pop("retry_delay", DEFAULT_REDIS_RETRY_DELAY)

        # Store only Redis connection parameters
        self._redis_config = redis_config
        self._redis = None

        # Initialize thread pool (skip in testing mode)
        worker_count = max_workers or DEFAULT_PULL_METRICS_WORKER_COUNT
        self._executor = (
            None
            if testing_mode
            else ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="pullmetrics")
        )

    def _ensure_redis_connection(self):
        """
        Ensure Redis connection is established with retry logic.

        Returns:
            redis.StrictRedis: Connected Redis client

        Raises:
            redis.RedisError: If connection fails after retries
        """
        # If we have a working connection, return it
        if self._redis is not None:
            try:
                # Quick health check - ping the connection
                self._redis.ping()
                return self._redis
            except (redis.ConnectionError, redis.TimeoutError, AttributeError):
                # Connection is broken, reset and reconnect
                logger.debug("Redis connection lost, reconnecting...")
                self._redis = None

        # Try to establish connection with retries
        last_exception = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                self._redis = redis.StrictRedis(
                    socket_connect_timeout=self._connection_timeout,
                    socket_timeout=self._socket_timeout,
                    **self._redis_config,
                )
                self._redis.ping()
                if attempt > 1:
                    logger.info(
                        "Redis connection established after %d attempt(s) for pull metrics", attempt
                    )
                return self._redis
            except (redis.ConnectionError, redis.TimeoutError) as e:
                last_exception = e
                self._redis = None
                if attempt < self._retry_attempts:
                    logger.warning(
                        "Redis connection attempt %d/%d failed for pull metrics: %s. Retrying in %.1fs...",
                        attempt,
                        self._retry_attempts,
                        str(e),
                        self._retry_delay,
                    )
                    time.sleep(self._retry_delay)
                else:
                    logger.error(
                        "Failed to connect to Redis after %d attempts for pull metrics: %s",
                        self._retry_attempts,
                        str(e),
                    )

        # All retries failed
        raise last_exception or redis.ConnectionError("Failed to connect to Redis for pull metrics")

    @staticmethod
    def _tag_pull_key(repository_id, tag_name, manifest_digest):
        """
        Generate Redis key for tag pull events.
        Pattern: pull_events:repo:{repository_id}:tag:{tag_name}:{manifest_digest}
        Matches worker pattern: pull_events:repo:*:tag:*:*

        Note: Uses repository_id for consistent key naming.
        """
        return "pull_events:repo:%s:tag:%s:%s" % (repository_id, tag_name, manifest_digest)

    @staticmethod
    def _manifest_pull_key(repository_id, manifest_digest):
        """
        Generate Redis key for manifest/digest pull events.
        Pattern: pull_events:repo:{repository_id}:digest:{manifest_digest}
        Matches worker pattern: pull_events:repo:*:digest:*

        Note: Uses repository_id for consistent key naming.
        """
        return "pull_events:repo:%s:digest:%s" % (repository_id, manifest_digest)

    def track_tag_pull_sync(self, repository_ref, tag_name, manifest_digest):
        """
        Synchronously track a tag pull event.

        Args:
            repository_ref: Repository object or repository_id
            tag_name: Name of the tag
            manifest_digest: Manifest digest
        """
        # Ensure Redis connection is available
        redis_client = self._ensure_redis_connection()

        # Get repository_id if object is passed
        repository_id = repository_ref.id if hasattr(repository_ref, "id") else repository_ref

        timestamp = int(datetime.now(timezone.utc).timestamp())

        tag_key = self._tag_pull_key(repository_id, tag_name, manifest_digest)

        try:
            pull_count = redis_client.eval(
                self._TRACK_TAG_PULL_SCRIPT,
                1,  # number of keys
                tag_key,  # KEYS[1]
                str(repository_id),  # ARGV[1]
                tag_name,  # ARGV[2]
                manifest_digest,  # ARGV[3]
                str(timestamp),  # ARGV[4]
                "tag",  # ARGV[5]
            )

            logger.debug(
                "Tracked tag pull: repo_id=%s tag=%s digest=%s count=%s",
                repository_id,
                tag_name,
                manifest_digest,
                pull_count,
            )
        except redis.RedisError as e:
            logger.error(
                "Failed to track tag pull (Redis error): repo_id=%s tag=%s error=%s",
                repository_id,
                tag_name,
                str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to track tag pull: repo_id=%s tag=%s error=%s",
                repository_id,
                tag_name,
                str(e),
                exc_info=True,
            )
            raise

    def track_tag_pull(self, repository, tag_name, manifest_digest):
        """
        Track a tag pull event.

        Note that this occurs in a thread to prevent blocking.
        """

        def conduct():
            try:
                self.track_tag_pull_sync(repository, tag_name, manifest_digest)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(
                    "Could not track tag pull metrics (connection error): %s. "
                    "Pull statistics may not be recorded until Redis is available.",
                    str(e),
                )
            except redis.RedisError as e:
                logger.error("Could not track tag pull metrics (Redis error): %s", str(e))
            except Exception as e:
                logger.exception("Unexpected error tracking tag pull metrics: %s", e)

        if self._executor:
            self._executor.submit(conduct)
        else:
            # During tests, run synchronously to avoid thread interference
            conduct()

    def track_manifest_pull_sync(self, repository_ref, manifest_digest):
        """
        Synchronously track a manifest (digest) pull event.

        Args:
            repository_ref: Repository object or repository_id
            manifest_digest: Manifest digest
        """
        # Ensure Redis connection is available
        redis_client = self._ensure_redis_connection()

        # Get repository_id if object is passed
        repository_id = repository_ref.id if hasattr(repository_ref, "id") else repository_ref

        timestamp = int(datetime.now(timezone.utc).timestamp())

        manifest_key = self._manifest_pull_key(repository_id, manifest_digest)

        try:
            pull_count = redis_client.eval(
                self._TRACK_MANIFEST_PULL_SCRIPT,
                1,  # number of keys
                manifest_key,  # KEYS[1]
                str(repository_id),  # ARGV[1]
                manifest_digest,  # ARGV[2]
                str(timestamp),  # ARGV[3]
                "digest",  # ARGV[4]
            )

            logger.debug(
                "Tracked manifest pull: repo_id=%s digest=%s count=%s",
                repository_id,
                manifest_digest,
                pull_count,
            )
        except redis.RedisError as e:
            logger.error(
                "Failed to track manifest pull (Redis error): repo_id=%s digest=%s error=%s",
                repository_id,
                manifest_digest,
                str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to track manifest pull: repo_id=%s digest=%s error=%s",
                repository_id,
                manifest_digest,
                str(e),
                exc_info=True,
            )
            raise

    def track_manifest_pull(self, repository, manifest_digest):
        """
        Track a manifest pull event.

        Note that this occurs in a thread to prevent blocking.
        """

        def conduct():
            try:
                self.track_manifest_pull_sync(repository, manifest_digest)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(
                    "Could not track manifest pull metrics (connection error): %s. "
                    "Pull statistics may not be recorded until Redis is available.",
                    str(e),
                )
            except redis.RedisError as e:
                logger.error("Could not track manifest pull metrics (Redis error): %s", str(e))
            except Exception as e:
                logger.exception("Unexpected error tracking manifest pull metrics: %s", e)

        if self._executor:
            self._executor.submit(conduct)
        else:
            # During tests, run synchronously to avoid thread interference
            conduct()

    def _get_pull_statistics(self, key):
        """
        Get pull statistics for a given Redis key.
        """
        try:
            redis_client = self._ensure_redis_connection()
            data = redis_client.hgetall(key)
            if not data:
                return None

            # Convert bytes to strings and integers
            result = {}
            for key, value in data.items():
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")

                if key in ["pull_count"]:
                    result[key] = int(value) if value else 0
                else:
                    result[key] = value

            return result
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning("Could not get pull statistics (connection error): %s", str(e))
            return None
        except redis.RedisError as e:
            logger.warning("Could not get pull statistics (Redis error): %s", str(e))
            return None

    def get_tag_pull_statistics(self, repository_id, tag_name, manifest_digest):
        """
        Get pull statistics for a specific tag+manifest combination from Redis.

        Note: This reads directly from Redis. The API endpoints read from the database
        via data.model.pull_statistics.get_tag_pull_statistics instead.

        Args:
            repository_id: Repository ID (integer)
            tag_name: Tag name
            manifest_digest: Manifest digest
        """
        tag_key = self._tag_pull_key(repository_id, tag_name, manifest_digest)
        return self._get_pull_statistics(tag_key)

    def get_manifest_pull_statistics(self, repository_id, manifest_digest):
        """
        Get pull statistics for a specific manifest from Redis.

        Args:
            repository_id: Repository ID (integer)
            manifest_digest: Manifest digest
        """
        manifest_key = self._manifest_pull_key(repository_id, manifest_digest)
        return self._get_pull_statistics(manifest_key)

    def shutdown(self):
        """
        Shutdown the thread pool executor.
        Following codebase patterns (similar to buildman/server.py server.stop(grace=5))

        Note: This method is not currently called during application shutdown,
        which means pending tasks may be lost during shutdown. This is a known
        race condition that primarily affects high-traffic deployments.

        TODO: Integrate with a centralized shutdown mechanism when available.
        See PR review comments for context.
        """
        if self._executor:
            self._executor.shutdown(wait=True)
