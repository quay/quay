import functools
import logging

from redis import Redis, RedisError
import redis_lock

logger = logging.getLogger(__name__)


class LockNotAcquiredException(Exception):
    """
    Exception raised if a GlobalLock could not be acquired.
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

    Note that Redis is not considered a tier-1 service, so this lock should not be used for any
    critical code paths.
    """

    lock_factory = None

    @classmethod
    def configure(cls, config):
        if cls.lock_factory is None:
            cls.lock_factory = _redis_lock_factory(config)

    def __init__(self, name, lock_ttl=600, auto_renewal=False):
        if GlobalLock.lock_factory is None:
            raise LockNotAcquiredException("GlobalLock not configured")

        self._lock_name = name
        self._lock_ttl = lock_ttl
        self._auto_renewal = auto_renewal
        self._lock = None

    def __enter__(self):
        if not self.acquire():
            raise LockNotAcquiredException()

    def __exit__(self, type, value, traceback):
        self.release()

    def acquire(self):
        logger.debug("Acquiring global lock %s", self._lock_name)
        try:
            self._lock = GlobalLock.lock_factory(
                self._lock_name, expire=self._lock_ttl, auto_renewal=self._auto_renewal
            )

            acquired = self._lock.acquire()
            if not acquired:
                logger.debug("Was unable to not acquire lock %s", self._lock_name)
                return False

            logger.debug("Acquired lock %s", self._lock_name)
            return True
        except RedisError as re:
            logger.warning("Could not connect to Redis for lock %s: %s", self._lock_name, re)
            return False
        except:
            logger.debug("Could not acquire lock %s", self._lock_name)
            return False

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
