from abc import ABCMeta, abstractmethod
from collections import namedtuple

import asyncio
import datetime
import json
import logging
import re
import time

from enum import IntEnum, unique
from six import add_metaclass, iteritems
from urllib3.exceptions import ReadTimeoutError, ProtocolError

import etcd
import redis

from buildman.asyncutil import wrap_with_threadpool
from util import slash_join
from util.expiresdict import ExpiresDict


logger = logging.getLogger(__name__)

ONE_DAY = 60 * 60 * 24
ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION = 5
DEFAULT_LOCK_EXPIRATION = 10000

ETCD_READ_TIMEOUT = 5
ETCD_MAX_WATCH_TIMEOUT = 30

REDIS_EXPIRING_SUFFIX = "/expiring"
REDIS_DEFAULT_PUBSUB_KEY = "orchestrator_events"
REDIS_EVENT_KIND_MESSAGE = "message"
REDIS_EVENT_KIND_PMESSAGE = "pmessage"
REDIS_NONEXPIRING_KEY = -1

# This constant defines the Redis configuration flags used to watch [K]eyspace and e[x]pired
# events on keys. For more info, see https://redis.io/topics/notifications#configuration
REDIS_KEYSPACE_EVENT_CONFIG_VALUE = "Kx"
REDIS_KEYSPACE_EVENT_CONFIG_KEY = "notify-keyspace-events"
REDIS_KEYSPACE_KEY_PATTERN = "__keyspace@%s__:%s"
REDIS_EXPIRED_KEYSPACE_PATTERN = slash_join(REDIS_KEYSPACE_KEY_PATTERN, REDIS_EXPIRING_SUFFIX)
REDIS_EXPIRED_KEYSPACE_REGEX = re.compile(REDIS_EXPIRED_KEYSPACE_PATTERN % (r"(\S+)", r"(\S+)"))


def orchestrator_from_config(manager_config, canceller_only=False):
    """
    Allocates a new Orchestrator from the 'ORCHESTRATOR' block from provided manager config. Checks
    for legacy configuration prefixed with 'ETCD_' when the 'ORCHESTRATOR' is not present.

    :param manager_config: the configuration for the orchestrator
    :type manager_config: dict
    :rtype: :class: Orchestrator
    """
    # Legacy codepath only knows how to configure etcd.
    if manager_config.get("ORCHESTRATOR") is None:
        manager_config["ORCHESTRATOR"] = {
            key: value
            for (key, value) in iteritems(manager_config)
            if key.startswith("ETCD_") and not key.endswith("_PREFIX")
        }

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
        format_key(key): value for (key, value) in iteritems(manager_config["ORCHESTRATOR"])
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
        "etcd": Etcd2Orchestrator,
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


@add_metaclass(ABCMeta)
class Orchestrator(object):
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
    def set_key_sync(self, key, value, overwrite=False, expiration=None):
        """
        set_key, but without asyncio coroutines.
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
    This function blocks the asyncio event loop by sleeping in order to backoff if a failure
    such as a ConnectionError has occurred.
    """
    logger.exception(
        "Connecting to etcd failed; sleeping for %s and then trying again",
        ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION,
    )
    time.sleep(ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION)
    logger.exception(
        "Connecting to etcd failed; slept for %s and now trying again",
        ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION,
    )


class EtcdAction(object):
    """
    Enumeration of the various kinds of etcd actions we can observe via a watch.
    """

    GET = "get"
    SET = "set"
    EXPIRE = "expire"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    COMPARE_AND_SWAP = "compareAndSwap"
    COMPARE_AND_DELETE = "compareAndDelete"


class Etcd2Orchestrator(Orchestrator):
    def __init__(
        self,
        host="127.0.0.1",
        port=2379,
        cert_and_key=None,
        ca_cert=None,
        client_threads=5,
        canceller_only=False,
        **kwargs,
    ):
        self.is_canceller_only = canceller_only

        logger.debug("initializing async etcd client")
        self._sync_etcd_client = etcd.Client(
            host=host,
            port=port,
            cert=tuple(cert_and_key) if cert_and_key is not None else None,
            ca_cert=ca_cert,
            protocol="http" if cert_and_key is None else "https",
            read_timeout=ETCD_READ_TIMEOUT,
        )

        if not self.is_canceller_only:
            (self._etcd_client, self._async_executor) = wrap_with_threadpool(
                self._sync_etcd_client, client_threads
            )

        logger.debug("creating initial orchestrator state")
        self._shutting_down = False
        self._watch_tasks = {}

    @staticmethod
    def _sanity_check_ttl(ttl):
        """
        A TTL of < 0 in etcd results in the key *never being expired*.

        We use a max here to ensure that if the TTL is < 0, the key will expire immediately.
        """
        return max(ttl, 0)

    def _watch_etcd(self, key, callback, restarter=None, start_index=None):
        def callback_wrapper(changed_key_future):
            new_index = start_index
            etcd_result = None

            if not changed_key_future.cancelled():
                try:
                    etcd_result = changed_key_future.result()
                    existing_index = getattr(etcd_result, "etcd_index", None)
                    new_index = etcd_result.modifiedIndex + 1

                    logger.debug(
                        "Got watch of key: %s at #%s with result: %s",
                        key,
                        existing_index,
                        etcd_result,
                    )

                except ReadTimeoutError:
                    logger.debug("Read-timeout on etcd watch %s, rescheduling", key)

                except etcd.EtcdEventIndexCleared:
                    # This happens if etcd2 has moved forward too fast for us to start watching at the index
                    # we retrieved. We therefore start a new watch at HEAD and (if specified) call the
                    # restarter method which should conduct a read and reset the state of the manager.
                    logger.debug("Etcd moved forward too quickly. Restarting watch cycle.")
                    new_index = None
                    if restarter is not None:
                        asyncio.create_task(restarter())

                except (KeyError, etcd.EtcdKeyError):
                    logger.debug("Etcd key already cleared: %s", key)
                    return

                except etcd.EtcdConnectionFailed:
                    _sleep_orchestrator()

                except etcd.EtcdException as eex:
                    # TODO: This is a quick and dirty hack and should be replaced with a proper
                    # exception check.
                    if str(eex).find("Read timed out") >= 0:
                        logger.debug("Read-timeout on etcd watch %s, rescheduling", key)
                    else:
                        logger.exception("Exception on etcd watch: %s", key)

                except ProtocolError:
                    logger.exception("Exception on etcd watch: %s", key)

            if key not in self._watch_tasks or self._watch_tasks[key].done():
                self._watch_etcd(key, callback, start_index=new_index, restarter=restarter)

            if etcd_result and etcd_result.value is not None:
                asyncio.create_task(callback(self._etcd_result_to_keychange(etcd_result)))

        if not self._shutting_down:
            logger.debug("Scheduling watch of key: %s at start index %s", key, start_index)
            watch_future = self._etcd_client.watch(
                key, recursive=True, index=start_index, timeout=ETCD_MAX_WATCH_TIMEOUT
            )
            watch_future.add_done_callback(callback_wrapper)

            self._watch_tasks[key] = asyncio.create_task(watch_future)

    @staticmethod
    def _etcd_result_to_keychange(etcd_result):
        event = Etcd2Orchestrator._etcd_result_to_keyevent(etcd_result)
        return KeyChange(event, etcd_result.key, etcd_result.value)

    @staticmethod
    def _etcd_result_to_keyevent(etcd_result):
        if etcd_result.action == EtcdAction.CREATE:
            return KeyEvent.CREATE
        if etcd_result.action == EtcdAction.SET:
            return (
                KeyEvent.CREATE
                if etcd_result.createdIndex == etcd_result.modifiedIndex
                else KeyEvent.SET
            )
        if etcd_result.action == EtcdAction.DELETE:
            return KeyEvent.DELETE
        if etcd_result.action == EtcdAction.EXPIRE:
            return KeyEvent.EXPIRE
        raise AssertionError("etcd action must have equivalant keyevent")

    def on_key_change(self, key, callback, restarter=None):
        assert not self.is_canceller_only

        logger.debug("creating watch on %s", key)
        self._watch_etcd(key, callback, restarter=restarter)

    async def get_prefixed_keys(self, prefix):
        assert not self.is_canceller_only

        try:
            etcd_result = await self._etcd_client.read(prefix, recursive=True)
            return {leaf.key: leaf.value for leaf in etcd_result.leaves}
        except etcd.EtcdKeyError:
            raise KeyError
        except etcd.EtcdConnectionFailed as ex:
            raise OrchestratorConnectionError(ex)
        except etcd.EtcdException as ex:
            raise OrchestratorError(ex)

    async def get_key(self, key):
        assert not self.is_canceller_only

        try:
            # Ignore pylint: the value property on EtcdResult is added dynamically using setattr.
            etcd_result = await self._etcd_client.read(key)
            return etcd_result.value
        except etcd.EtcdKeyError:
            raise KeyError
        except etcd.EtcdConnectionFailed as ex:
            raise OrchestratorConnectionError(ex)
        except etcd.EtcdException as ex:
            raise OrchestratorError(ex)

    async def set_key(self, key, value, overwrite=False, expiration=None):
        assert not self.is_canceller_only

        await (
            self._etcd_client.write(
                key, value, prevExists=overwrite, ttl=self._sanity_check_ttl(expiration)
            )
        )

    def set_key_sync(self, key, value, overwrite=False, expiration=None):
        self._sync_etcd_client.write(
            key, value, prevExists=overwrite, ttl=self._sanity_check_ttl(expiration)
        )

    async def delete_key(self, key):
        assert not self.is_canceller_only

        try:
            await self._etcd_client.delete(key)
        except etcd.EtcdKeyError:
            raise KeyError
        except etcd.EtcdConnectionFailed as ex:
            raise OrchestratorConnectionError(ex)
        except etcd.EtcdException as ex:
            raise OrchestratorError(ex)

    async def lock(self, key, expiration=DEFAULT_LOCK_EXPIRATION):
        assert not self.is_canceller_only

        try:
            await (
                self._etcd_client.write(
                    key, {}, prevExist=False, ttl=self._sanity_check_ttl(expiration)
                )
            )
            return True
        except (KeyError, etcd.EtcdKeyError):
            return False
        except etcd.EtcdConnectionFailed:
            logger.exception("Could not get etcd atomic lock as etcd is down")
            return False
        except etcd.EtcdException as ex:
            raise OrchestratorError(ex)

    def shutdown(self):
        logger.debug("Shutting down etcd client.")
        self._shutting_down = True

        if self.is_canceller_only:
            return

        for (key, _), task in list(self._watch_tasks.items()):
            if not task.done():
                logger.debug("Canceling watch task for %s", key)
                task.cancel()

        if self._async_executor is not None:
            self._async_executor.shutdown()


class MemoryOrchestrator(Orchestrator):
    def __init__(self, **kwargs):
        self.state = ExpiresDict()
        self.callbacks = {}

    def _callbacks_prefixed(self, prefix):
        return (callback for (key, callback) in iteritems(self.callbacks) if key.startswith(prefix))

    def on_key_change(self, key, callback, restarter=None):
        self.callbacks[key] = callback

    async def get_prefixed_keys(self, prefix):
        return {k: value for (k, value) in list(self.state.items()) if k.startswith(prefix)}

    async def get_key(self, key):
        return self.state[key]

    async def set_key(self, key, value, overwrite=False, expiration=None):
        preexisting_key = "key" in self.state
        if preexisting_key and not overwrite:
            raise KeyError

        absolute_expiration = None
        if expiration is not None:
            absolute_expiration = datetime.datetime.now() + datetime.timedelta(seconds=expiration)

        self.state.set(key, value, expires=absolute_expiration)

        event = KeyEvent.CREATE if not preexisting_key else KeyEvent.SET
        for callback in self._callbacks_prefixed(key):
            await callback(KeyChange(event, key, value))

    def set_key_sync(self, key, value, overwrite=False, expiration=None):
        """
        set_key, but without asyncio coroutines.
        """
        preexisting_key = "key" in self.state
        if preexisting_key and not overwrite:
            raise KeyError

        absolute_expiration = None
        if expiration is not None:
            absolute_expiration = datetime.datetime.now() + datetime.timedelta(seconds=expiration)

        self.state.set(key, value, expires=absolute_expiration)

        event = KeyEvent.CREATE if not preexisting_key else KeyEvent.SET
        for callback in self._callbacks_prefixed(key):
            callback(KeyChange(event, key, value))

    async def delete_key(self, key):
        value = self.state[key]
        del self.state[key]

        for callback in self._callbacks_prefixed(key):
            await callback(KeyChange(KeyEvent.DELETE, key, value))

    async def lock(self, key, expiration=DEFAULT_LOCK_EXPIRATION):
        if key in self.state:
            return False
        self.state.set(key, None, expires=expiration)
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
        client_threads=5,
        ssl=False,
        skip_keyspace_event_setup=False,
        canceller_only=False,
        **kwargs,
    ):
        self.is_canceller_only = canceller_only
        (cert, key) = tuple(cert_and_key) if cert_and_key is not None else (None, None)
        self._sync_client = redis.StrictRedis(
            host=host,
            port=port,
            password=password,
            db=db,
            ssl_certfile=cert,
            ssl_keyfile=key,
            ssl_ca_certs=ca_cert,
            ssl=ssl,
        )

        self._shutting_down = False
        self._tasks = {}
        self._watched_keys = {}
        self._pubsub_key = slash_join(
            kwargs.get("orchestrator_prefix", ""), REDIS_DEFAULT_PUBSUB_KEY
        ).lstrip("/")

        if not self.is_canceller_only:
            (self._client, self._async_executor) = wrap_with_threadpool(
                self._sync_client, client_threads
            )

            # Configure a subscription to watch events that the orchestrator manually publishes.
            logger.debug("creating pubsub with key %s", self._pubsub_key)
            published_pubsub = self._sync_client.pubsub()
            published_pubsub.subscribe(self._pubsub_key)
            (self._pubsub, self._async_executor_pub) = wrap_with_threadpool(published_pubsub)
            self._watch_published_key()

            # Configure a subscription to watch expired keyspace events.
            if not skip_keyspace_event_setup:
                self._sync_client.config_set(
                    REDIS_KEYSPACE_EVENT_CONFIG_KEY, REDIS_KEYSPACE_EVENT_CONFIG_VALUE
                )

            expiring_pubsub = self._sync_client.pubsub()
            expiring_pubsub.psubscribe(REDIS_EXPIRED_KEYSPACE_PATTERN % (db, "*"))
            (self._pubsub_expiring, self._async_executor_ex) = wrap_with_threadpool(expiring_pubsub)
            self._watch_expiring_key()

    def _watch_published_key(self):
        def published_callback_wrapper(event_future):
            logger.debug("published callback called")
            event_result = None

            if not event_future.cancelled():
                try:
                    event_result = event_future.result()
                    (redis_event, event_key, event_value) = event_result
                    logger.debug(
                        "Got watch of key: (%s, %s, %s)", redis_event, event_key, event_value
                    )
                except redis.ConnectionError:
                    _sleep_orchestrator()
                except redis.RedisError:
                    logger.exception("Exception watching redis publish: %s", event_key)

            # Schedule creating a new future if this one has been consumed.
            if "pub" not in self._tasks or self._tasks["pub"].done():
                self._watch_published_key()

            if event_result is not None and redis_event == REDIS_EVENT_KIND_MESSAGE:
                keychange = self._publish_to_keychange(event_value)
                for watched_key, callback in iteritems(self._watched_keys):
                    if keychange.key.startswith(watched_key):
                        asyncio.create_task(callback(keychange))

        if not self._shutting_down:
            logger.debug("Scheduling watch of publish stream")
            watch_future = self._pubsub.parse_response()
            watch_future.add_done_callback(published_callback_wrapper)
            self._tasks["pub"] = asyncio.create_task(watch_future)

    def _watch_expiring_key(self):
        async def expiring_callback_wrapper(event_future):
            logger.debug("expiring callback called")
            event_result = None

            if not event_future.cancelled():
                try:
                    event_result = event_future.result()
                    if self._is_expired_keyspace_event(event_result):
                        # Get the value of the original key before the expiration happened.
                        key = self._key_from_expiration(event_future)
                        expired_value = await self._client.get(key)

                        # $KEY/expiring is gone, but the original key still remains, set an expiration for it
                        # so that other managers have time to get the event and still read the expired value.
                        await self._client.expire(key, ONE_DAY)
                except redis.ConnectionError:
                    _sleep_orchestrator()
                except redis.RedisError:
                    logger.exception("Exception watching redis expirations: %s", key)

            # Schedule creating a new future if this one has been consumed.
            if "expire" not in self._tasks or self._tasks["expire"].done():
                self._watch_expiring_key()

            if self._is_expired_keyspace_event(event_result) and expired_value is not None:
                for watched_key, callback in iteritems(self._watched_keys):
                    if key.startswith(watched_key):
                        asyncio.create_task(
                            callback(KeyChange(KeyEvent.EXPIRE, key, expired_value))
                        )

        if not self._shutting_down:
            logger.debug("Scheduling watch of expiration")
            watch_future = self._pubsub_expiring.parse_response()
            watch_future.add_done_callback(expiring_callback_wrapper)
            self._tasks["expire"] = asyncio.create_task(watch_future)

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

    async def get_prefixed_keys(self, prefix):
        assert not self.is_canceller_only

        # TODO: This can probably be done with redis pipelines to make it transactional.
        keys = await self._client.keys(prefix + "*")

        # Yielding to the event loop is required, thus this cannot be written as a dict comprehension.
        results = {}
        for key in keys:
            if key.endswith(REDIS_EXPIRING_SUFFIX):
                continue
            ttl = await self._client.ttl(key)
            if ttl != REDIS_NONEXPIRING_KEY:
                # Only redis keys without expirations are live build manager keys.
                value = await self._client.get(key)
                results.update({key: value})

        return results

    async def get_key(self, key):
        assert not self.is_canceller_only

        value = await self._client.get(key)
        return value

    async def set_key(self, key, value, overwrite=False, expiration=None):
        assert not self.is_canceller_only

        already_exists = await self._client.exists(key)

        await self._client.set(key, value, xx=overwrite)
        if expiration is not None:
            await (
                self._client.set(
                    slash_join(key, REDIS_EXPIRING_SUFFIX), value, xx=overwrite, ex=expiration
                )
            )

        key_event = KeyEvent.SET if already_exists else KeyEvent.CREATE
        await self._publish(event=key_event, key=key, value=value)

    def set_key_sync(self, key, value, overwrite=False, expiration=None):
        already_exists = self._sync_client.exists(key)

        self._sync_client.set(key, value, xx=overwrite)
        if expiration is not None:
            self._sync_client.set(
                slash_join(key, REDIS_EXPIRING_SUFFIX), value, xx=overwrite, ex=expiration
            )

        self._sync_client.publish(
            self._pubsub_key,
            json.dumps(
                {
                    "event": int(KeyEvent.SET if already_exists else KeyEvent.CREATE),
                    "key": key,
                    "value": value,
                }
            ),
        )

    async def _publish(self, **kwargs):
        kwargs["event"] = int(kwargs["event"])
        event_json = json.dumps(kwargs)
        logger.debug("publishing event: %s", event_json)
        await self._client.publish(self._pubsub_key, event_json)

    async def delete_key(self, key):
        assert not self.is_canceller_only

        value = await self._client.get(key)
        await self._client.delete(key)
        await self._client.delete(slash_join(key, REDIS_EXPIRING_SUFFIX))
        await self._publish(event=KeyEvent.DELETE, key=key, value=value)

    async def lock(self, key, expiration=DEFAULT_LOCK_EXPIRATION):
        assert not self.is_canceller_only

        await self.set_key(key, "", ex=expiration)
        return True

    async def shutdown(self):
        logger.debug("Shutting down redis client.")

        self._shutting_down = True

        if self.is_canceller_only:
            return

        for key, task in iteritems(self._tasks):
            if not task.done():
                logger.debug("Canceling watch task for %s", key)
                task.cancel()

        if self._async_executor is not None:
            self._async_executor.shutdown()
        if self._async_executor_ex is not None:
            self._async_executor_ex.shutdown()
        if self._async_executor_pub is not None:
            self._async_executor_pub.shutdown()
