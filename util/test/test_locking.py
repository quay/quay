import functools
import logging
import time

import fakeredis
import pytest
import redis_lock

from util.locking import GlobalLock


@pytest.fixture
def fake_lock_server(monkeypatch):
    server = fakeredis.FakeServer()
    conn = fakeredis.FakeStrictRedis(server=server)
    monkeypatch.setattr(GlobalLock, "lock_factory", functools.partial(redis_lock.Lock, conn))
    return server


def _hold_lock(server, name, holder_id="other-host:999:deadbeef", expire=30):
    conn = fakeredis.FakeStrictRedis(server=server)
    lock = redis_lock.Lock(conn, name, expire=expire, id=holder_id)
    assert lock.acquire()
    return lock


def test_acquire_bounded_wait_returns_promptly(fake_lock_server):
    _hold_lock(fake_lock_server, "BLOB_DELETE_sha256:aaa")

    lock = GlobalLock("BLOB_DELETE_sha256:aaa", lock_ttl=30, blocking_timeout=1)
    start = time.time()
    acquired = lock.acquire()
    elapsed = time.time() - start

    assert acquired is False
    assert elapsed < 5, f"bounded acquire took too long: {elapsed}s"


def test_acquire_without_blocking_timeout_passes_no_timeout_through(fake_lock_server, monkeypatch):
    """blocking_timeout=None (the default) must not change behavior for existing callers: it
    passes timeout=None straight through to redis_lock.Lock.acquire(), matching the pre-fix
    call `self._lock.acquire()`."""
    seen = {}
    original_acquire = redis_lock.Lock.acquire

    def spy_acquire(self, *args, **kwargs):
        seen["timeout"] = kwargs.get("timeout", args[1] if len(args) > 1 else None)
        return original_acquire(self, *args, **kwargs)

    monkeypatch.setattr(redis_lock.Lock, "acquire", spy_acquire)

    lock = GlobalLock("BLOB_DELETE_sha256:ddd", lock_ttl=30)
    assert lock.acquire() is True
    lock.release()

    assert seen["timeout"] is None


def test_acquire_timeout_logs_lock_name_and_holder(fake_lock_server, caplog):
    _hold_lock(fake_lock_server, "BLOB_DELETE_sha256:bbb", holder_id="registry-9:4242:c0ffee42")

    lock = GlobalLock("BLOB_DELETE_sha256:bbb", lock_ttl=30, blocking_timeout=1)
    with caplog.at_level(logging.WARNING):
        acquired = lock.acquire()

    assert acquired is False
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "BLOB_DELETE_sha256:bbb" in m and "registry-9:4242:c0ffee42" in m for m in messages
    ), messages


def test_acquire_succeeds_when_lock_is_free(fake_lock_server):
    lock = GlobalLock("BLOB_DELETE_sha256:ccc", lock_ttl=30, blocking_timeout=1)
    assert lock.acquire() is True
    lock.release()
