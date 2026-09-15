from unittest.mock import Mock

from redis import RedisError, TimeoutError

from util.locking import GlobalLock


def test_acquire_logs_timeout_as_connection_warning(caplog):
    lock = GlobalLock.__new__(GlobalLock)
    lock._lock_name = "test-lock"
    lock._lock_ttl = 600
    lock._auto_renewal = False
    lock._lock = None
    lock_factory = Mock()
    lock_factory.return_value.acquire.side_effect = TimeoutError("Timeout reading from socket")

    original_lock_factory = GlobalLock.lock_factory
    GlobalLock.lock_factory = lock_factory
    try:
        assert lock.acquire() is False
    finally:
        GlobalLock.lock_factory = original_lock_factory

    assert (
        "Could not connect to Redis for lock test-lock: Timeout reading from socket" in caplog.text
    )


def test_acquire_logs_other_redis_errors_as_connection_warning(caplog):
    lock = GlobalLock.__new__(GlobalLock)
    lock._lock_name = "test-lock"
    lock._lock_ttl = 600
    lock._auto_renewal = False
    lock._lock = None
    lock_factory = Mock()
    lock_factory.return_value.acquire.side_effect = RedisError("connection failed")

    original_lock_factory = GlobalLock.lock_factory
    GlobalLock.lock_factory = lock_factory
    try:
        assert lock.acquire() is False
    finally:
        GlobalLock.lock_factory = original_lock_factory

    assert "Could not connect to Redis for lock test-lock: connection failed" in caplog.text
