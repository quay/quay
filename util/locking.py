import logging

from redis import RedisError
from redlock import RedLockFactory, RedLockError

logger = logging.getLogger(__name__)


class LockNotAcquiredException(Exception):
    """
    Exception raised if a GlobalLock could not be acquired.
    """


def _redlock_factory(config):
    _redis_info = dict(config["USER_EVENTS_REDIS"])
    _redis_info.update(
        {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "single_connection_client": True,
        }
    )
    lock_factory = RedLockFactory(connection_details=[_redis_info])
    return lock_factory


# TODO(kleesc): GlobalLock should either renew the lock until the caller is done,
# or signal that it is no longer valid to the caller. Currently, GlobalLock will
# just silently expire the redis key, making the lock available again while any
# ongoing job in a GlobalLock context will still be running
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
            cls.lock_factory = _redlock_factory(config)

    def __init__(self, name, lock_ttl=600):
        if GlobalLock.lock_factory is None:
            raise LockNotAcquiredException("GlobalLock not configured")

        self._lock_name = name
        self._lock_ttl = lock_ttl
        self._redlock = None

    def __enter__(self):
        if not self.acquire():
            raise LockNotAcquiredException()

    def __exit__(self, type, value, traceback):
        self.release()

    def acquire(self):
        logger.debug("Acquiring global lock %s", self._lock_name)
        try:
            self._redlock = GlobalLock.lock_factory.create_lock(
                self._lock_name, ttl=self._lock_ttl * 1000
            )

            acquired = self._redlock.acquire()
            if not acquired:
                logger.debug("Was unable to not acquire lock %s", self._lock_name)
                return False

            logger.debug("Acquired lock %s", self._lock_name)
            return True
        except RedLockError:
            logger.debug("Could not acquire lock %s", self._lock_name)
            return False
        except RedisError as re:
            logger.debug("Could not connect to Redis for lock %s: %s", self._lock_name, re)
            return False

    def release(self):
        if self._redlock is not None:
            logger.debug("Releasing lock %s", self._lock_name)
            try:
                self._redlock.release()
            except RedLockError:
                logger.debug("Could not release lock %s", self._lock_name)
            except RedisError as re:
                logger.debug(
                    "Could not connect to Redis for releasing lock %s: %s", self._lock_name, re
                )

            logger.debug("Released lock %s", self._lock_name)
            self._redlock = None
