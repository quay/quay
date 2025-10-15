import json
import logging
import threading
from datetime import datetime

import redis

logger = logging.getLogger(__name__)


class CannotReadPullMetricsException(Exception):
    """
    Exception raised if pull metrics cannot be read.
    """


class PullMetricsBuilder(object):
    """
    Defines a helper class for constructing PullMetrics instances.
    """

    def __init__(self, redis_config):
        self._redis_config = redis_config

    def get_event(self):
        return PullMetrics(self._redis_config)


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

        pull_metrics = PullMetricsBuilder(redis_config)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["pullmetrics"] = pull_metrics
        return pull_metrics

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class PullMetrics(object):
    """
    Defines a helper class for tracking pull metrics as backed by Redis.
    """

    def __init__(self, redis_config):
        self._redis = redis.StrictRedis(socket_connect_timeout=2, socket_timeout=2, **redis_config)

    @staticmethod
    def _tag_pull_key(repository, tag_name):
        return "pull_metrics/tag/%s/%s" % (repository, tag_name)

    @staticmethod
    def _manifest_pull_key(repository, manifest_digest):
        return "pull_metrics/manifest/%s/%s" % (repository, manifest_digest)

    def track_tag_pull_sync(self, repository, tag_name, manifest_digest):
        """
        Synchronously track a tag pull event.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Increment counters in Redis
        tag_key = self._tag_pull_key(repository, tag_name)
        manifest_key = self._manifest_pull_key(repository, manifest_digest)

        # Use Redis pipeline for atomic operations
        pipe = self._redis.pipeline()
        pipe.hincrby(tag_key, "pull_count", 1)
        pipe.hset(tag_key, "last_pull_date", timestamp)
        pipe.hset(tag_key, "current_manifest_digest", manifest_digest)
        pipe.hincrby(manifest_key, "pull_count", 1)
        pipe.hset(manifest_key, "last_pull_date", timestamp)
        pipe.execute()

        logger.debug("Tracked tag pull: %s/%s -> %s", repository, tag_name, manifest_digest)

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

        thread = threading.Thread(target=conduct)
        thread.start()

    def track_manifest_pull_sync(self, repository, manifest_digest):
        """
        Synchronously track a manifest pull event.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Increment manifest counter
        manifest_key = self._manifest_pull_key(repository, manifest_digest)

        pipe = self._redis.pipeline()
        pipe.hincrby(manifest_key, "pull_count", 1)
        pipe.hset(manifest_key, "last_pull_date", timestamp)
        pipe.execute()

        logger.debug("Tracked manifest pull: %s -> %s", repository, manifest_digest)

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

        thread = threading.Thread(target=conduct)
        thread.start()

    def get_tag_pull_statistics(self, repository, tag_name):
        """
        Get pull statistics for a specific tag.
        """
        tag_key = self._tag_pull_key(repository, tag_name)

        try:
            data = self._redis.hgetall(tag_key)
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
            logger.exception("Could not get tag pull statistics: %s", e)
            return None

    def get_manifest_pull_statistics(self, repository, manifest_digest):
        """
        Get pull statistics for a specific manifest.
        """
        manifest_key = self._manifest_pull_key(repository, manifest_digest)

        try:
            data = self._redis.hgetall(manifest_key)
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
            logger.exception("Could not get manifest pull statistics: %s", e)
            return None
