import functools
import logging
import os
import socket
import time
import uuid

import redis_lock
from redis import Redis, RedisError

logger = logging.getLogger(__name__)

# How often a GlobalLock with a blocking_timeout retries a lock held by someone else.
_BOUNDED_ACQUIRE_POLL_INTERVAL = 0.05


class _SkipFailedAcquireWarning(logging.Filter):
    """redis_lock logs a WARNING on every failed non-blocking acquire; GlobalLock's bounded poll
    (_acquire_before_deadline) calls acquire(blocking=False) up to blocking_timeout /
    _BOUNDED_ACQUIRE_POLL_INTERVAL times per wait, which would flood logs with an expected,
    already-handled event. GlobalLock logs its own WARNING once the deadline is reached."""

    def filter(self, record):
        return not record.getMessage().startswith("Failed to acquire Lock")


logging.getLogger("redis_lock.acquire").addFilter(_SkipFailedAcquireWarning())


class LockNotAcquiredException(Exception):
    """
    Exception raised if a GlobalLock could not be acquired.
    """


class LockAcquireTimeout(LockNotAcquiredException):
    """
    Exception raised if a GlobalLock with a blocking_timeout was still held by another holder
    when the timeout ran out, as opposed to Redis being unavailable.
    """


def _redis_lock_factory(config):
    _redis_info = dict(config["USER_EVENTS_REDIS"])
    _redis_info.update(
        {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "single_connection_client": True,
        }
    )

    _conn = Redis(**_redis_info)

    return functools.partial(redis_lock.Lock, _conn)


class GlobalLock(object):
    """
    A lock object that blocks globally via Redis.
    """

    lock_factory = None

    @classmethod
    def configure(cls, config):
        if cls.lock_factory is None:
            cls.lock_factory = _redis_lock_factory(config)

    def __init__(self, name, lock_ttl=600, auto_renewal=False, blocking_timeout=None):
        """
        :param blocking_timeout:
            Maximum number of seconds, measured across all retries, to wait for the lock.
            None (the default) blocks until the lock is acquired.
        """
        if GlobalLock.lock_factory is None:
            raise LockNotAcquiredException("GlobalLock not configured")

        self._lock_name = name
        self._lock_ttl = lock_ttl
        self._auto_renewal = auto_renewal
        self._blocking_timeout = blocking_timeout
        self._lock = None
        self._timed_out = False
        # Identifies the current process to other waiters if this instance acquires the lock;
        # the uuid suffix keeps ids unique across concurrent GlobalLock instances in this same
        # process, so one greenlet's held lock is never mistaken for another's acquire attempt.
        self._holder_id = "%s:%s:%s" % (socket.gethostname(), os.getpid(), uuid.uuid4().hex[:8])

    def __enter__(self):
        if not self.acquire():
            if self._timed_out:
                raise LockAcquireTimeout()
            raise LockNotAcquiredException()

    def __exit__(self, type, value, traceback):
        self.release()

    def acquire(self):
        logger.debug("Acquiring global lock %s", self._lock_name)
        try:
            self._lock = GlobalLock.lock_factory(
                self._lock_name,
                expire=self._lock_ttl,
                auto_renewal=self._auto_renewal,
                id=self._holder_id,
            )

            if self._blocking_timeout is None:
                acquired = self._lock.acquire()
            else:
                acquired = self._acquire_before_deadline()
            if not acquired:
                self._timed_out = True
                logger.warning(
                    "Timed out acquiring lock %s (currently held by %s)",
                    self._lock_name,
                    self._current_holder(),
                )
                return False

            logger.debug("Acquired lock %s", self._lock_name)
            return True
        except RedisError as re:
            logger.warning("Could not connect to Redis for lock %s: %s", self._lock_name, re)
            return False
        except:
            logger.debug("Could not acquire lock %s", self._lock_name)
            return False

    def _acquire_before_deadline(self):
        # Poll with non-blocking SETs instead of redis_lock's blocking wait. That wait is a BLPOP
        # on the lock client's single shared connection, so every other greenlet's commands on it
        # (including the holder's release and extend) queue behind the waiter, and its timeout
        # restarts whenever a release wakes the waiter but another contender wins the lock.
        deadline = time.monotonic() + self._blocking_timeout
        while not self._lock.acquire(blocking=False):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(_BOUNDED_ACQUIRE_POLL_INTERVAL, remaining))
        return True

    def _current_holder(self):
        try:
            return self._lock.get_owner_id()
        except RedisError:
            return None

    def release(self):
        if self._lock is not None:
            logger.debug("Releasing lock %s", self._lock_name)
            try:
                self._lock.release()
            except RedisError as re:
                logger.debug(
                    "Could not connect to Redis for releasing lock %s: %s", self._lock_name, re
                )
            except:
                logger.debug("Could not release lock %s", self._lock_name)

            logger.debug("Released lock %s", self._lock_name)
            self._lock = None
