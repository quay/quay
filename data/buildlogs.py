import redis
import json
import time

from contextlib import closing

from util.dynamic import import_class
from datetime import timedelta


ONE_DAY = timedelta(days=1)
SEVEN_DAYS = timedelta(days=7)


class BuildStatusRetrievalError(Exception):
    pass


class RedisBuildLogs(object):
    ERROR = "error"
    COMMAND = "command"
    PHASE = "phase"

    def __init__(self, redis_config):
        self._redis_client = None
        self._redis_config = redis_config

    @property
    def _redis(self):
        if self._redis_client is not None:
            return self._redis_client

        args = dict(self._redis_config)
        args.update(
            {"socket_connect_timeout": 1, "socket_timeout": 2, "single_connection_client": True}
        )

        self._redis_client = redis.StrictRedis(**args)
        return self._redis_client

    @staticmethod
    def _logs_key(build_id):
        return "builds/%s/logs" % build_id

    def append_log_entry(self, build_id, log_obj):
        """
        Appends the serialized form of log_obj to the end of the log entry list and returns the new
        length of the list.
        """
        pipeline = self._redis.pipeline(transaction=False)
        pipeline.expire(self._logs_key(build_id), SEVEN_DAYS)
        pipeline.rpush(self._logs_key(build_id), json.dumps(log_obj))
        result = pipeline.execute()
        return result[1]

    def append_log_message(self, build_id, log_message, log_type=None, log_data=None):
        """
        Wraps the message in an envelope and push it to the end of the log entry list and returns
        the index at which it was inserted.
        """
        log_obj = {"message": log_message}

        if log_type:
            log_obj["type"] = log_type

        if log_data:
            log_obj["data"] = log_data

        return self.append_log_entry(build_id, log_obj) - 1

    def get_log_entries(self, build_id, start_index):
        """
        Returns a tuple of the current length of the list and an iterable of the requested log
        entries.
        """
        try:
            llen = self._redis.llen(self._logs_key(build_id))
            log_entries = self._redis.lrange(self._logs_key(build_id), start_index, -1)
            return (llen, (json.loads(entry) for entry in log_entries))
        except redis.RedisError as re:
            raise BuildStatusRetrievalError("Cannot retrieve build logs: %s" % re)

    def expire_status(self, build_id):
        """
        Sets the status entry to expire in 1 day.
        """
        self._redis.expire(self._status_key(build_id), ONE_DAY)

    def expire_log_entries(self, build_id):
        """
        Sets the log entry to expire in 1 day.
        """
        self._redis.expire(self._logs_key(build_id), ONE_DAY)

    def delete_log_entries(self, build_id):
        """
        Delete the log entry.
        """
        self._redis.delete(self._logs_key(build_id))

    @staticmethod
    def _status_key(build_id):
        return "builds/%s/status" % build_id

    def set_status(self, build_id, status_obj):
        """
        Sets the status key for this build to json serialized form of the supplied obj.
        """
        self._redis.set(self._status_key(build_id), json.dumps(status_obj), ex=SEVEN_DAYS)

    def get_status(self, build_id):
        """
        Loads the status information for the specified build id.
        """
        try:
            fetched = self._redis.get(self._status_key(build_id))
        except redis.RedisError as re:
            raise BuildStatusRetrievalError("Cannot retrieve build status: %s" % re)

        return json.loads(fetched) if fetched else None

    @staticmethod
    def _health_key():
        return "_health"

    def check_health(self):
        try:
            args = dict(self._redis_config)
            args.update(
                {"socket_connect_timeout": 1, "socket_timeout": 1, "single_connection_client": True}
            )

            with closing(redis.StrictRedis(**args)) as connection:
                if not connection.ping():
                    return (False, "Could not ping redis")

                # Ensure we can write and read a key.
                connection.set(self._health_key(), time.time())
                connection.get(self._health_key())
                return (True, None)
        except redis.RedisError as re:
            return (False, "Could not connect to redis: %s" % str(re))


class BuildLogs(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        buildlogs_config = app.config.get("BUILDLOGS_REDIS")
        if not buildlogs_config:
            # This is the old key name.
            buildlogs_config = {"host": app.config.get("BUILDLOGS_REDIS_HOSTNAME")}

        buildlogs_options = app.config.get("BUILDLOGS_OPTIONS", [])
        buildlogs_import = app.config.get("BUILDLOGS_MODULE_AND_CLASS", None)

        if buildlogs_import is None:
            klass = RedisBuildLogs
        else:
            klass = import_class(buildlogs_import[0], buildlogs_import[1])

        buildlogs = klass(buildlogs_config, *buildlogs_options)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["buildlogs"] = buildlogs
        return buildlogs

    def __getattr__(self, name):
        return getattr(self.state, name, None)
