import logging

from redis import RedisError
from redlock import RedLock, RedLockError

from app import app

logger = logging.getLogger(__name__)


class LockNotAcquiredException(Exception):
    """
    Exception raised if a GlobalLock could not be acquired.
    """


class GlobalLock(object):
    """
    A lock object that blocks globally via Redis.

    Note that Redis is not considered a tier-1 service, so this lock should not be used for any
    critical code paths.
    """

    def __init__(self, name, lock_ttl=600):
        self._lock_name = name
        self._redis_info = dict(app.config["USER_EVENTS_REDIS"])
        self._redis_info.update(
            {"socket_connect_timeout": 5, "socket_timeout": 5, "single_connection_client": True}
        )

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
            self._redlock = RedLock(
                self._lock_name, connection_details=[self._redis_info], ttl=self._lock_ttl
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
