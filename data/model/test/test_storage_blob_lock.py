import functools
import logging
import time

import fakeredis
import pytest
import redis_lock

import data.model.storage as storage_module
from data.database import ImageStorage
from data.model.storage import (
    BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT,
    get_or_create_blob_with_lock,
    with_blob_lock_or_fallback,
)
from test.fixtures import *
from util.locking import GlobalLock, LockAcquireTimeout


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


def test_with_blob_lock_or_fallback_timeout_does_not_create_missing_blob(
    initialized_db, monkeypatch
):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(1)
    _hold_lock(server, digest, holder_id="gc-worker:7:aaaaaaaa")

    calls = []

    def func(**kwargs):
        calls.append(kwargs.get("skip_lock"))
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    start = time.time()
    with pytest.raises(LockAcquireTimeout):
        with_blob_lock_or_fallback(digest, func)
    elapsed = time.time() - start

    assert elapsed < BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT + 2, f"took too long: {elapsed}s"
    assert calls == [True]
    assert not ImageStorage.select().where(ImageStorage.content_checksum == digest).exists()


def test_with_blob_lock_or_fallback_timeout_returns_existing_blob(
    initialized_db, monkeypatch, caplog
):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(5)
    existing = ImageStorage.create(content_checksum=digest, image_size=1)
    _hold_lock(server, digest)

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    start = time.time()
    with caplog.at_level(logging.WARNING):
        result = with_blob_lock_or_fallback(digest, func)
    elapsed = time.time() - start

    assert elapsed < BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT + 2, f"took too long: {elapsed}s"
    assert result.id == existing.id
    assert "proceeding without lock" not in caplog.text


def test_with_blob_lock_or_fallback_redis_down_creates_without_lock(
    initialized_db, monkeypatch, caplog
):
    server = _patch_lock_factory(monkeypatch)
    server.connected = False
    digest = _digest(6)

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    with caplog.at_level(logging.WARNING):
        result = with_blob_lock_or_fallback(digest, func)

    assert result.content_checksum == digest
    assert f"Blob {digest}: proceeding without lock" in caplog.text


def test_with_blob_lock_or_fallback_acquires_lock_once_on_fallback(initialized_db, monkeypatch):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(2)
    _hold_lock(server, digest)

    acquire_attempts = []
    original_acquire = GlobalLock.acquire

    def spy_acquire(self):
        acquire_attempts.append(self._lock_name)
        return original_acquire(self)

    monkeypatch.setattr(GlobalLock, "acquire", spy_acquire)

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    with pytest.raises(LockAcquireTimeout):
        with_blob_lock_or_fallback(digest, func)

    assert acquire_attempts == [f"BLOB_DELETE_{digest}"], acquire_attempts


def test_with_blob_lock_or_fallback_logs_holder_on_timeout(initialized_db, monkeypatch, caplog):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(3)
    _hold_lock(server, digest, holder_id="registry-worker-9:4242:c0ffee42")

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(LockAcquireTimeout):
            with_blob_lock_or_fallback(digest, func)

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        f"BLOB_DELETE_{digest}" in m and "registry-worker-9:4242:c0ffee42" in m for m in messages
    ), messages


def test_with_blob_lock_or_fallback_no_contention(initialized_db, monkeypatch, caplog):
    _patch_lock_factory(monkeypatch)
    digest = _digest(4)

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    with caplog.at_level(logging.WARNING):
        result = with_blob_lock_or_fallback(digest, func)
    assert result.content_checksum == digest
    assert "proceeding without lock" not in caplog.text
