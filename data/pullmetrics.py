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
    Defines a helper class for constructing PullMetrics and PullMetricsListener instances.
    """

    def __init__(self, redis_config):
        self._redis_config = redis_config

    def get_metrics(self):
        return PullMetrics(self._redis_config)

    def get_listener(self, events=None):
        return PullMetricsListener(self._redis_config, events)


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
            # Fallback to user events redis if pull metrics redis is not configured
            redis_config = app.config.get("USER_EVENTS_REDIS")
            if not redis_config:
                # This is the old key name.
                redis_config = {
                    "host": app.config.get("USER_EVENTS_REDIS_HOSTNAME"),
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
    Defines a helper class for publishing pull metrics to Redis.
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
        data = {
            "repository": repository,
            "tag_name": tag_name,
            "manifest_digest": manifest_digest,
            "timestamp": timestamp,
        }

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
        return True

    def track_tag_pull(self, repository, tag_name, manifest_digest):
        """
        Asynchronously track a tag pull event.
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
        data = {
            "repository": repository,
            "manifest_digest": manifest_digest,
            "timestamp": timestamp,
        }

        # Increment manifest counter
        manifest_key = self._manifest_pull_key(repository, manifest_digest)

        pipe = self._redis.pipeline()
        pipe.hincrby(manifest_key, "pull_count", 1)
        pipe.hset(manifest_key, "last_pull_date", timestamp)
        pipe.execute()

        logger.debug("Tracked manifest pull: %s -> %s", repository, manifest_digest)
        return True

    def track_manifest_pull(self, repository, manifest_digest):
        """
        Asynchronously track a manifest pull event.
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


class PullMetricsListener(object):
    """
    Defines a helper class for subscribing to pull metrics events as backed by Redis.
    """

    def __init__(self, redis_config, events=None):
        events = events or set([])
        channels = [f"pull_metrics/{e}" for e in events]

        args = dict(redis_config)
        args.update({"socket_connect_timeout": 5, "single_connection_client": True})

        try:
            self._redis = redis.StrictRedis(**args)
            self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
            self._pubsub.subscribe(channels)
        except redis.RedisError as re:
            logger.exception("Could not reach pull metrics redis: %s", re)
            raise CannotReadPullMetricsException

    def event_stream(self):
        """
        Starts listening for events on the channel(s), yielding for each event found.
        """
        while True:
            pubsub = self._pubsub
            if pubsub is None:
                return

            try:
                item = pubsub.get_message(ignore_subscribe_messages=True, timeout=5)
            except redis.RedisError:
                item = None

            if item is None:
                yield "pulse", {}
            else:
                channel = item["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()

                event_id = channel.split("/")[-1]  # Get the last part of the channel
                data = None

                try:
                    data = json.loads(item["data"] or "{}")
                except ValueError:
                    continue

                if data:
                    yield event_id, data

    def stop(self):
        """
        Unsubscribes from the channel(s).
        """
        if self._pubsub is not None:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        if self._redis is not None:
            self._redis.close()

        self._pubsub = None
        self._redis = None
