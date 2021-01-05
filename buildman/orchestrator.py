from abc import ABCMeta, abstractmethod
from collections import namedtuple
from contextlib import ContextDecorator

import datetime
import json
import logging
import re
import time

from enum import IntEnum, unique

import redis

from util import slash_join
from util.expiresdict import ExpiresDict


logger = logging.getLogger(__name__)

ONE_DAY = 60 * 60 * 24
ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION = 5
DEFAULT_LOCK_EXPIRATION = 10000

REDIS_EXPIRING_SUFFIX = "/expiring"
REDIS_EXPIRED_SUFFIX = "/expired"
REDIS_DEFAULT_PUBSUB_KEY = "orchestrator_events"
REDIS_EVENT_KIND_MESSAGE = "message"
REDIS_EVENT_KIND_PMESSAGE = "pmessage"
REDIS_NONEXPIRING_KEY = -1

# This constant defines the Redis configuration flags used to watch [K]eyspace and e[x]pired
# events on keys. For more info, see https://redis.io/topics/notifications#configuration
REDIS_KEYSPACE_EXPIRED_EVENT_CONFIG_VALUE = "Kx"
REDIS_KEYSPACE_EVENT_CONFIG_KEY = "notify-keyspace-events"
REDIS_KEYSPACE_KEY_PATTERN = "__keyspace@%s__:%s"
REDIS_EXPIRED_KEYSPACE_PATTERN = slash_join(REDIS_KEYSPACE_KEY_PATTERN, REDIS_EXPIRING_SUFFIX)
REDIS_EXPIRED_KEYSPACE_REGEX = re.compile(REDIS_EXPIRED_KEYSPACE_PATTERN % (r"(\S+)", r"(\S+)"))


def orchestrator_from_config(manager_config, canceller_only=False):
    """
    :param manager_config: the configuration for the orchestrator
    :type manager_config: dict
    :rtype: :class: Orchestrator
    """
    # Sanity check that legacy prefixes are no longer being used.
    for key in list(manager_config["ORCHESTRATOR"].keys()):
        words = key.split("_")
        if len(words) > 1 and words[-1].lower() == "prefix":
            raise AssertionError("legacy prefix used, use ORCHESTRATOR_PREFIX instead")

    def _dict_key_prefix(d):
        """
        :param d: the dict that has keys prefixed with underscore
        :type d: {str: any}
        :rtype: str
        """
        return list(d.keys())[0].split("_", 1)[0].lower()

    orchestrator_name = _dict_key_prefix(manager_config["ORCHESTRATOR"])

    def format_key(key):
        return key.lower().split("_", 1)[1]

    orchestrator_kwargs = {
        format_key(key): value for (key, value) in manager_config["ORCHESTRATOR"].items()
    }

    if manager_config.get("ORCHESTRATOR_PREFIX") is not None:
        orchestrator_kwargs["orchestrator_prefix"] = manager_config["ORCHESTRATOR_PREFIX"]

    orchestrator_kwargs["canceller_only"] = canceller_only

    logger.debug(
        "attempting to create orchestrator %s with kwargs %s",
        orchestrator_name,
        orchestrator_kwargs,
    )
    return orchestrator_by_name(orchestrator_name, **orchestrator_kwargs)


def orchestrator_by_name(name, **kwargs):
    _ORCHESTRATORS = {
        "mem": MemoryOrchestrator,
        "redis": RedisOrchestrator,
    }
    return _ORCHESTRATORS.get(name, MemoryOrchestrator)(**kwargs)


class OrchestratorError(Exception):
    pass


# TODO: replace with ConnectionError when this codebase is Python 3.
class OrchestratorConnectionError(OrchestratorError):
    pass


@unique
class KeyEvent(IntEnum):
    CREATE = 1
    SET = 2
    DELETE = 3
    EXPIRE = 4


class KeyChange(namedtuple("KeyChange", ["event", "key", "value"])):
    pass


class Orchestrator(metaclass=ABCMeta):
    """
    Orchestrator is the interface that is used to synchronize the build states across build
    managers.

    This interface assumes that storage is being done by a key-value store
    that supports watching for events on keys.

    Missing keys should return KeyError; otherwise, errors should raise an
    OrchestratorError.

    :param key_prefix: the prefix of keys being watched
    :type key_prefix: str
    """

    @abstractmethod
    def on_key_change(self, key, callback, restarter=None):
        """
        The callback parameter takes in a KeyChange object as a parameter.
        """
        pass

    @abstractmethod
    def get_prefixed_keys(self, prefix):
        """
        :returns: a dict of key value pairs beginning with prefix
        :rtype: {str: str}
        """
        pass

    @abstractmethod
    def get_key(self, key):
        """
        :returns: the value stored at the provided key
        :rtype: str
        """
        pass

    @abstractmethod
    def set_key(self, key, value, overwrite=False, expiration=None):
        """
        :param key: the identifier for the value
        :type key: str
        :param value: the value being stored
        :type value: str
        :param overwrite: whether or not a KeyError is thrown if the key already exists
        :type overwrite: bool
        :param expiration: the duration in seconds that a key should be available
        :type expiration: int
        """
        pass

    @abstractmethod
    def delete_key(self, key):
        """
        Deletes a key that has been set in the orchestrator.

        :param key: the identifier for the key
        :type key: str
        """
        pass

    @abstractmethod
    def lock(self, key, expiration=DEFAULT_LOCK_EXPIRATION):
        """
        Takes a lock for synchronizing exclusive operations cluster-wide.

        :param key: the identifier for the lock
        :type key: str
        :param expiration: the duration until the lock expires
        :type expiration: :class:`datetime.timedelta` or int (seconds)
        :returns: whether or not the lock was acquired
        :rtype: bool
        """
        pass

    @abstractmethod
    def shutdown():
        """
        This function should shutdown any final resources allocated by the Orchestrator.
        """
        pass


def _sleep_orchestrator():
    """
    This function blocks by sleeping in order to backoff if a failure
    such as a ConnectionError has occurred.
    """
    logger.exception(
        "Connecting to orchestrator failed; sleeping for %s and then trying again",
        ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION,
    )
    time.sleep(ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION)
    logger.exception(
        "Connecting to orchestrator failed; slept for %s and now trying again",
        ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION,
    )


class MemoryOrchestrator(Orchestrator):
    def __init__(self, **kwargs):
        self.state = ExpiresDict()
        self.callbacks = {}

    def _callbacks_prefixed(self, key):
        return (callback for (prefix, callback) in self.callbacks.items() if key.startswith(prefix))

    def on_key_change(self, key, callback, restarter=None):
        self.callbacks[key] = callback

    def get_prefixed_keys(self, prefix):
        return {
            k: value
            for (k, value) in list(self.state.items())
            if k.startswith(prefix)
            and not k.endswith(REDIS_EXPIRED_SUFFIX)
            and not k.endswith(REDIS_EXPIRING_SUFFIX)
        }

    def get_key(self, key):
        return self.state[key]

    def set_key(self, key, value, overwrite=False, expiration=None):
        preexisting_key = key in self.state
        if preexisting_key and not overwrite:
            raise KeyError(key)

        # Simulate redis' behavior when using xx and the key does not exist.
        if not preexisting_key and overwrite:
            return

        absolute_expiration = None
        if expiration is not None:
            absolute_expiration = datetime.datetime.now() + datetime.timedelta(seconds=expiration)

        self.state.set(key, value, expires=absolute_expiration)
        self.state.set(slash_join(key, REDIS_EXPIRING_SUFFIX), value, expires=absolute_expiration)

        event = KeyEvent.CREATE if not preexisting_key else KeyEvent.SET
        for callback in self._callbacks_prefixed(key):
            callback(KeyChange(event, key, value))

    def delete_key(self, key):
        value = self.state[key]
        del self.state[key]

        for callback in self._callbacks_prefixed(key):
            callback(KeyChange(KeyEvent.DELETE, key, value))

    def lock(self, key, expiration=DEFAULT_LOCK_EXPIRATION):
        try:
            self.set_key(key, "", overwrite=False, expiration=expiration)
        except KeyError:
            return False
        return True

    def shutdown(self):
        self.state = None
        self.callbacks = None


class RedisOrchestrator(Orchestrator):
    def __init__(
        self,
        host="127.0.0.1",
        port=6379,
        password=None,
        db=0,
        cert_and_key=None,
        ca_cert=None,
        ssl=False,
        skip_keyspace_event_setup=False,
        canceller_only=False,
        **kwargs,
    ):
        self.is_canceller_only = canceller_only
        (cert, key) = tuple(cert_and_key) if cert_and_key is not None else (None, None)
        self._client = redis.StrictRedis(
            host=host,
            port=port,
            password=password,
            db=db,
            ssl_certfile=cert,
            ssl_keyfile=key,
            ssl_ca_certs=ca_cert,
            ssl=ssl,
            socket_connect_timeout=1,
            socket_timeout=2,
            health_check_interval=2,
        )

        self._shutting_down = False
        self._watched_keys = {}
        self._pubsub_key = slash_join(
            kwargs.get("orchestrator_prefix", ""), REDIS_DEFAULT_PUBSUB_KEY
        ).lstrip("/")

        if not self.is_canceller_only:
            # sleep_time is not really calling time.sleep(). It is the socket's timeout value.
            # run_in_thread uses an event loop that uses a non-blocking `parse_response` of the PubSub object.
            # This means the event loop will return immedietely even if there are no new messages.
            # Setting a value other than the default 0 prevents that thread from exhausting CPU time.
            # https://github.com/andymccurdy/redis-py/issues/821

            # Configure a subscription to watch events that the orchestrator manually publishes.
            logger.debug("creating pubsub with key %s", self._pubsub_key)
            self._pubsub = self._client.pubsub()
            self._pubsub.subscribe(**{self._pubsub_key: self._published_key_handler})
            self._pubsub_thread = self._pubsub.run_in_thread(daemon=True, sleep_time=5)

            # Configure a subscription to watch expired keyspace events.
            if not skip_keyspace_event_setup:
                self._client.config_set(
                    REDIS_KEYSPACE_EVENT_CONFIG_KEY, REDIS_KEYSPACE_EXPIRED_EVENT_CONFIG_VALUE
                )

            self._pubsub_expiring = self._client.pubsub()
            self._pubsub_expiring.psubscribe(
                **{REDIS_EXPIRED_KEYSPACE_PATTERN % (db, "*"): self._expiring_key_handler}
            )
            self._pubsub_expiring_thread = self._pubsub_expiring.run_in_thread(
                daemon=True, sleep_time=5
            )

    def _expiring_key_handler(self, message):
        try:
            message_tup = (
                message.get("type"),
                message.get("pattern").decode("utf-8"),
                message.get("channel").decode("utf-8"),
                message.get("data").decode("utf-8"),
            )
            if self._is_expired_keyspace_event(message_tup):
                # Get the value of the original key before the expiration happened.
                key = self._key_from_expiration(message_tup)
                expired_value = self._client.get(key)

                # Mark key as expired. This key is used to track post job cleanup in the callback,
                # to allow another manager to pickup the cleanup if this fails.
                self._client.set(slash_join(key, REDIS_EXPIRED_SUFFIX), expired_value)
                self._client.delete(key)
        except redis.ConnectionError:
            _sleep_orchestrator()
        except redis.RedisError as re:
            logger.exception("Redis exception watching redis expirations: %s - %s", key, re)
        except Exception as e:
            logger.exception("Unknown exception watching redis expirations: %s - %s", key, e)

        if self._is_expired_keyspace_event(message_tup) and expired_value is not None:
            for watched_key, callback in self._watched_keys.items():
                if key.startswith(watched_key):
                    callback(KeyChange(KeyEvent.EXPIRE, key, expired_value))

    def _published_key_handler(self, message):
        try:
            redis_event, event_key, event_value = (
                message.get("type"),
                message.get("channel").decode("utf-8"),
                message.get("data").decode("utf-8"),
            )
        except redis.ConnectionError:
            _sleep_orchestrator()
        except redis.RedisError as re:
            logger.exception("Redis exception watching redis expirations: %s - %s", key, re)
        except Exception as e:
            logger.exception("Unknown exception watching redis expirations: %s - %s", key, e)

        if redis_event == REDIS_EVENT_KIND_MESSAGE:
            keychange = self._publish_to_keychange(event_value)
            for watched_key, callback in self._watched_keys.items():
                if keychange.key.startswith(watched_key):
                    callback(keychange)

    def on_key_change(self, key, callback, restarter=None):
        assert not self.is_canceller_only

        logger.debug("watching key: %s", key)
        self._watched_keys[key] = callback

    @staticmethod
    def _is_expired_keyspace_event(event_result):
        """
        Sanity check that this isn't an unrelated keyspace event.

        There could be a more efficient keyspace event config to avoid this client-side filter.
        """
        if event_result is None:
            return False

        (redis_event, _pattern, matched_key, expired) = event_result
        return (
            redis_event == REDIS_EVENT_KIND_PMESSAGE
            and expired == "expired"
            and REDIS_EXPIRED_KEYSPACE_REGEX.match(matched_key) is not None
        )

    @staticmethod
    def _key_from_expiration(event_result):
        (_redis_event, _pattern, matched_key, _expired) = event_result
        return REDIS_EXPIRED_KEYSPACE_REGEX.match(matched_key).groups()[1]

    @staticmethod
    def _publish_to_keychange(event_value):
        e = json.loads(event_value)
        return KeyChange(KeyEvent(e["event"]), e["key"], e["value"])

    def get_prefixed_keys(self, prefix):
        assert not self.is_canceller_only

        # TODO: This can probably be done with redis pipelines to make it transactional.
        keys = self._client.keys(prefix + "*")

        # Yielding to the event loop is required, thus this cannot be written as a dict comprehension.
        results = {}
        for key in keys:
            if key.decode("utf-8").endswith(REDIS_EXPIRING_SUFFIX) or key.decode("utf-8").endswith(
                REDIS_EXPIRED_SUFFIX
            ):
                continue
            ttl = self._client.ttl(key)
            if ttl == REDIS_NONEXPIRING_KEY:
                # Only redis keys without expirations are live build manager keys.
                try:
                    value = self._client.get(key)
                    if value is None:
                        raise KeyError(key)
                except redis.ConnectionError as rce:
                    raise OrchestratorConnectionError(rce)
                except redis.RedisError as re:
                    raise OrchestratorError(re)

                results.update({key.decode("utf-8"): value.decode("utf-8")})

        return results

    def _key_is_expired(self, key):
        expired_key = slash_join(key, REDIS_EXPIRED_SUFFIX)
        expired_val = self._client.get(key)
        if expired_val is None:
            return False
        return True

    def get_key(self, key):
        assert not self.is_canceller_only

        try:
            value = self._client.get(key)
            if value is None:
                # If expired, the expired key should have been removed but still exists.
                # Delete the key if that's the case.
                if self._key_is_expired(key):
                    self._client.delete(slash_join(key, REDIS_EXPIRED_SUFFIX))
                raise KeyError(key)
        except redis.ConnectionError as rce:
            raise OrchestratorConnectionError(rce)
        except redis.RedisError as re:
            raise OrchestratorError(re)

        return value.decode("utf-8")

    def set_key(self, key, value, overwrite=False, expiration=None):
        try:
            already_exists = self._client.exists(key)
            if already_exists and not overwrite:
                raise KeyError(key)

            # Set an expiration in case that the handler was not able to delete the the original key.
            # The extra leeway is so the expire event handler has time to get the original value and publish the event.
            self._client.set(key, value, xx=overwrite)
            if expiration is not None:
                self._client.expire(key, expiration + ONE_DAY)
                overwrite_expiring_key = self._client.exists(slash_join(key, REDIS_EXPIRING_SUFFIX))
                # The "expiring/*" are only used to publish the EXPIRE event. A separate key is needed
                # because the the EXPIRE event does not include the original key value.
                self._client.set(
                    slash_join(key, REDIS_EXPIRING_SUFFIX),
                    "",
                    xx=overwrite_expiring_key,
                    ex=expiration,
                )
                # Remove any expired key that might have previously been created but not removed
                # if a new expiration is set.
                self._client.delete(slash_join(key, REDIS_EXPIRED_SUFFIX))
            key_event = KeyEvent.SET if already_exists else KeyEvent.CREATE
            self._publish(event=key_event, key=key, value=value)
        except redis.ConnectionError as rce:
            raise OrchestratorConnectionError(rce)
        except redis.RedisError as re:
            raise OrchestratorError(re)

    def _publish(self, **kwargs):
        kwargs["event"] = int(kwargs["event"])
        event_json = json.dumps(kwargs)
        logger.debug("publishing event: %s", event_json)
        self._client.publish(self._pubsub_key, event_json)

    def delete_key(self, key):
        assert not self.is_canceller_only

        try:
            value = self._client.get(key)
            if value is None:
                raise KeyError(key)
            self._client.delete(key)
            self._client.delete(slash_join(key, REDIS_EXPIRING_SUFFIX))
            self._client.delete(slash_join(key, REDIS_EXPIRED_SUFFIX))
            if value is not None:
                self._publish(event=KeyEvent.DELETE, key=key, value=value.decode("utf-8"))
        except redis.ConnectionError as rce:
            raise OrchestratorConnectionError(rce)
        except redis.RedisError as re:
            raise OrchestratorError(re)

    def lock(self, key, expiration=DEFAULT_LOCK_EXPIRATION):
        assert not self.is_canceller_only
        try:
            self.set_key(key, "", overwrite=False, expiration=expiration)
        except KeyError:
            return False
        return True

    def shutdown(self):
        logger.debug("Shutting down redis client.")
        self._shutting_down = True

        if self.is_canceller_only:
            return

        self._pubsub_thread.stop()
        self._pubsub_expiring_thread.stop()
