import functools
import logging
import time

import fakeredis
import redis_lock

import data.model.storage as storage_module
from data.model.storage import (
    BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT,
    get_or_create_blob_with_lock,
    with_blob_lock_or_fallback,
)
from test.fixtures import *
from util.locking import GlobalLock


def _digest(byte):
    return "sha256:" + (str(byte) * 64)[:64]


def _hold_lock(server, digest, holder_id="other-worker:1:aaaaaaaa", expire=30):
    conn = fakeredis.FakeStrictRedis(server=server)
    lock = redis_lock.Lock(conn, f"BLOB_DELETE_{digest}", expire=expire, id=holder_id)
    assert lock.acquire()
    return lock


def _patch_lock_factory(monkeypatch):
    # initialized_db permanently replaces data.model.storage.GlobalLock with a no-op
    # MockGlobalLock (test/fixtures.py) the first time any test uses it, so point storage.py
    # back at the real, fakeredis-backed GlobalLock for the duration of this test only.
    server = fakeredis.FakeServer()
    conn = fakeredis.FakeStrictRedis(server=server)
    monkeypatch.setattr(GlobalLock, "lock_factory", functools.partial(redis_lock.Lock, conn))
    monkeypatch.setattr(storage_module, "GlobalLock", GlobalLock)
    return server


def test_with_blob_lock_or_fallback_bounded_when_lock_held(initialized_db, monkeypatch):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(1)
    _hold_lock(server, digest)

    calls = []

    def func(**kwargs):
        calls.append(kwargs.get("skip_lock"))
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    start = time.time()
    result = with_blob_lock_or_fallback(digest, func)
    elapsed = time.time() - start

    assert elapsed < BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT + 3, f"took too long: {elapsed}s"
    assert result.content_checksum == digest
    assert calls == [True]


def test_with_blob_lock_or_fallback_acquires_lock_once_on_fallback(initialized_db, monkeypatch):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(2)
    _hold_lock(server, digest)

    acquire_attempts = []
    original_acquire = redis_lock.Lock.acquire

    def spy_acquire(self, *args, **kwargs):
        acquire_attempts.append(self._name)
        return original_acquire(self, *args, **kwargs)

    monkeypatch.setattr(redis_lock.Lock, "acquire", spy_acquire)

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    with_blob_lock_or_fallback(digest, func)

    lock_key = f"lock:BLOB_DELETE_{digest}"
    assert acquire_attempts.count(lock_key) == 1, acquire_attempts


def test_with_blob_lock_or_fallback_logs_holder_on_timeout(initialized_db, monkeypatch, caplog):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(3)
    _hold_lock(server, digest, holder_id="registry-worker-9:4242:c0ffee42")

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    with caplog.at_level(logging.WARNING):
        with_blob_lock_or_fallback(digest, func)

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        f"BLOB_DELETE_{digest}" in m and "registry-worker-9:4242:c0ffee42" in m for m in messages
    ), messages


def test_with_blob_lock_or_fallback_no_contention(initialized_db, monkeypatch):
    _patch_lock_factory(monkeypatch)
    digest = _digest(4)

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    result = with_blob_lock_or_fallback(digest, func)
    assert result.content_checksum == digest
