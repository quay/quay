import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import redis

logger = logging.getLogger(__name__)

DEFAULT_PULL_METRICS_WORKER_COUNT = 5


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
    """

    def __init__(self, redis_config, max_workers=None):
        self._redis = redis.StrictRedis(socket_connect_timeout=2, socket_timeout=2, **redis_config)
        worker_count = max_workers or DEFAULT_PULL_METRICS_WORKER_COUNT
        # Skip thread pool creation during tests to avoid interference
        if not redis_config.get("_testing", False):
            self._executor = ThreadPoolExecutor(
                max_workers=worker_count, thread_name_prefix="pullmetrics"
            )
        else:
            self._executor = None

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

        # Get repository_id if object is passed
        repository_id = repository_ref.id if hasattr(repository_ref, "id") else repository_ref

        timestamp = int(datetime.now(timezone.utc).timestamp())

        tag_key = self._tag_pull_key(repository_id, tag_name, manifest_digest)
        manifest_key = self._manifest_pull_key(repository_id, manifest_digest)

        # Use Redis pipeline for atomic operations
        pipe = self._redis.pipeline()

        # Tag pull event - the worker will create both tag and manifest stats from this
        pipe.hset(tag_key, "repository_id", repository_id)
        pipe.hset(tag_key, "tag_name", tag_name)
        pipe.hset(tag_key, "manifest_digest", manifest_digest)
        pipe.hincrby(tag_key, "pull_count", 1)
        pipe.hset(tag_key, "last_pull_timestamp", timestamp)
        pipe.hset(tag_key, "pull_method", "tag")

        pipe.execute()

        logger.debug(
            "Tracked tag pull: repo_id=%s tag=%s digest=%s",
            repository_id,
            tag_name,
            manifest_digest,
        )

    def track_tag_pull(self, repository, tag_name, manifest_digest):
        """
        Track a tag pull event.

        Note that this occurs in a thread to prevent blocking.
        """

        def conduct():
            try:
                self.track_tag_pull_sync(repository, tag_name, manifest_digest)
            except redis.RedisError:
                logger.exception("Could not track tag pull metrics")

        if self._executor:
            self._executor.submit(conduct)
        else:
            # During tests, run synchronously to avoid thread interference
            conduct()

    def track_manifest_pull_sync(self, repository_ref, manifest_digest):
        """
        Synchronously track a manifest pull event (direct digest pull).

        Args:
            repository_ref: Repository object or repository_id
            manifest_digest: Manifest digest
        """

        # Get repository_id if object is passed
        repository_id = repository_ref.id if hasattr(repository_ref, "id") else repository_ref

        timestamp = int(datetime.now(timezone.utc).timestamp())

        manifest_key = self._manifest_pull_key(repository_id, manifest_digest)

        pipe = self._redis.pipeline()
        pipe.hset(manifest_key, "repository_id", repository_id)
        pipe.hset(manifest_key, "manifest_digest", manifest_digest)
        pipe.hincrby(manifest_key, "pull_count", 1)
        pipe.hset(manifest_key, "last_pull_timestamp", timestamp)
        pipe.hset(manifest_key, "pull_method", "digest")
        pipe.execute()

        logger.debug("Tracked manifest pull: repo_id=%s digest=%s", repository_id, manifest_digest)

    def track_manifest_pull(self, repository, manifest_digest):
        """
        Track a manifest pull event.

        Note that this occurs in a thread to prevent blocking.
        """

        def conduct():
            try:
                self.track_manifest_pull_sync(repository, manifest_digest)
            except redis.RedisError:
                logger.exception("Could not track manifest pull metrics")

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
            data = self._redis.hgetall(key)
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
        except redis.RedisError as e:
            logger.exception("Could not get pull statistics: %s", e)
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
