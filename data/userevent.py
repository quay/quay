import json
import threading
import logging

import redis

logger = logging.getLogger(__name__)


class CannotReadUserEventsException(Exception):
    """
    Exception raised if user events cannot be read.
    """


class UserEventBuilder(object):
    """
    Defines a helper class for constructing UserEvent and UserEventListener instances.
    """

    def __init__(self, redis_config):
        self._redis_config = redis_config

    def get_event(self, username):
        return UserEvent(self._redis_config, username)

    def get_listener(self, username, events):
        return UserEventListener(self._redis_config, username, events)


class UserEventsBuilderModule(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        redis_config = app.config.get("USER_EVENTS_REDIS")
        if not redis_config:
            # This is the old key name.
            redis_config = {
                "host": app.config.get("USER_EVENTS_REDIS_HOSTNAME"),
            }

        user_events = UserEventBuilder(redis_config)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["userevents"] = user_events
        return user_events

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class UserEvent(object):
    """
    Defines a helper class for publishing to realtime user events as backed by Redis.
    """

    def __init__(self, redis_config, username):
        self._redis = redis.StrictRedis(socket_connect_timeout=2, socket_timeout=2, **redis_config)
        self._username = username

    @staticmethod
    def _user_event_key(username, event_id):
        return "user/%s/events/%s" % (username, event_id)

    def publish_event_data_sync(self, event_id, data_obj):
        return self._redis.publish(
            self._user_event_key(self._username, event_id), json.dumps(data_obj)
        )

    def publish_event_data(self, event_id, data_obj):
        """
        Publishes the serialized form of the data object for the given event.

        Note that this occurs in a thread to prevent blocking.
        """

        def conduct():
            try:
                self.publish_event_data_sync(event_id, data_obj)
                logger.debug("Published user event %s: %s", event_id, data_obj)
            except redis.RedisError:
                logger.exception("Could not publish user event")

        thread = threading.Thread(target=conduct)
        thread.start()


class UserEventListener(object):
    """
    Defines a helper class for subscribing to realtime user events as backed by Redis.
    """

    def __init__(self, redis_config, username, events=None):
        events = events or set([])
        channels = [self._user_event_key(username, e) for e in events]

        args = dict(redis_config)
        args.update({"socket_connect_timeout": 5, "single_connection_client": True})

        try:
            self._redis = redis.StrictRedis(**args)
            self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
            self._pubsub.subscribe(channels)
        except redis.RedisError as re:
            logger.exception("Could not reach user events redis: %s", re)
            raise CannotReadUserEventsException

    @staticmethod
    def _user_event_key(username, event_id):
        return "user/%s/events/%s" % (username, event_id)

    def event_stream(self):
        """
        Starts listening for events on the channel(s), yielding for each event found.

        Will yield a "pulse" event (a custom event we've decided) as a heartbeat every few seconds.
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
                event_id = channel.split("/")[3]  # user/{username}/{events}/{id}
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

        Should be called once the connection has terminated.
        """
        if self._pubsub is not None:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        if self._redis is not None:
            self._redis.close()

        self._pubsub = None
        self._redis = None
