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
    # holder_id must use an exact name from _GC_LOCK_ROLES — "gc-worker" (with
    # hyphen) is not recognised and would be treated as a non-GC holder.
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(1)
    _hold_lock(server, digest, holder_id="repositorygcworker:7:aaaaaaaa")

    calls = []

    def func(**kwargs):
        calls.append(kwargs.get("skip_lock"))
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    start = time.time()
    with pytest.raises(LockAcquireTimeout):
        with_blob_lock_or_fallback(digest, func)
    elapsed = time.time() - start

    assert elapsed < BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT + 2, f"took too long: {elapsed}s"
    # func is called once (skip_lock=True) with _BLOB_LOCK_TIMED_OUT set, which causes
    # _get_or_create_blob_with_lock to raise LockAcquireTimeout rather than create the row.
    assert calls == [True]
    assert not ImageStorage.select().where(ImageStorage.content_checksum == digest).exists()


def test_with_blob_lock_or_fallback_timeout_returns_existing_blob(
    initialized_db, monkeypatch, caplog
):
    # Lock held by a non-GC worker (the default holder in _hold_lock).
    # New behaviour: a non-GC timeout is not a blocking condition — the function
    # proceeds and returns the existing blob.  It also logs a warning because it
    # is running without the lock, unlike the old silent TIMED_OUT fallback.
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
    # Non-GC contention is now logged as a warning rather than silently falling
    # back — "proceeding without lock" must appear in the log.
    assert "proceeding without lock" in caplog.text


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

    # Non-GC holder: with_blob_lock_or_fallback now proceeds rather than raising.
    # The key invariant — GlobalLock.acquire is called exactly once for the outer
    # lock and never again inside the fallback func call — still holds.
    with_blob_lock_or_fallback(digest, func)

    assert acquire_attempts == [f"BLOB_DELETE_{digest}"], acquire_attempts


def test_with_blob_lock_or_fallback_logs_holder_on_timeout(initialized_db, monkeypatch, caplog):
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(3)
    _hold_lock(server, digest, holder_id="registry-worker-9:4242:c0ffee42")

    def func(**kwargs):
        return get_or_create_blob_with_lock(digest=digest, image_size=1, **kwargs)

    # Non-GC holder: with_blob_lock_or_fallback now proceeds (no exception) but
    # still logs a warning containing the lock name and the holder ID before
    # doing so, giving operators visibility into what was contending.
    with caplog.at_level(logging.WARNING):
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


def test_get_or_create_blob_with_lock_timeout_does_not_create_missing_blob(
    initialized_db, monkeypatch
):
    # A recognised GC worker role holds the lock while the blob is missing from
    # the DB.  The function must raise LockAcquireTimeout and must NOT create the
    # ImageStorage row — blob object storage deletion may be in progress and a
    # dangling DB record must not be left behind.
    # Note: the holder_id must use one of the exact role names in _GC_LOCK_ROLES
    # (e.g. "repositorygcworker", not "gc-worker" with a hyphen).
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(8)
    _hold_lock(server, digest, holder_id="repositorygcworker:7:aaaaaaaa")

    with pytest.raises(LockAcquireTimeout):
        get_or_create_blob_with_lock(digest=digest, image_size=1)

    assert not ImageStorage.select().where(ImageStorage.content_checksum == digest).exists()


def test_get_or_create_blob_with_lock_timeout_returns_existing_blob(initialized_db, monkeypatch):
    # A recognised GC worker holds the lock but the blob already exists in the DB
    # (e.g. another writer created it before GC could delete it).  The function
    # must not raise — it should find and return the existing row.  This exercises
    # the may_create=False path in _get_or_create_blob_with_lock: ImageStorage.get
    # succeeds, so the LockAcquireTimeout branch that guards missing blobs is never
    # reached.
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(9)
    existing = ImageStorage.create(content_checksum=digest, image_size=1)
    _hold_lock(server, digest, holder_id="repositorygcworker:1:aaaaaaaa")

    assert get_or_create_blob_with_lock(digest=digest, image_size=1).id == existing.id


def test_get_or_create_blob_with_lock_timeout_with_non_gc_holder_creates_blob(
    initialized_db, monkeypatch
):
    """
    Verifies that blobs will indeed be created if a non-GC worker is holding the lock. Unlike the case
    of GC workers, this operation must **not** raise a 503, it must fall through and create the
    ImageStorage blob entry.

    Guards from regression where the non-GC branch has no fallback return.
    """
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(10)
    _hold_lock(server, digest, holder_id="other_worker:1:abcd1234")

    result = get_or_create_blob_with_lock(digest=digest, image_size=1)

    assert result is not None, "most not implicitly return None when holder is not GC"
    assert result.content_checksum == digest
    assert ImageStorage.select().where(ImageStorage.content_checksum == digest).exists()


@pytest.mark.parametrize(
    "artifact",
    [
        None,  # ghost holder
        "OK",  # misinterpreted response
    ],
)
def test_get_or_create_blob_with_lock_timeout_with_response_mixing_artifact_creates_blob(
    initialized_db, monkeypatch, artifact
):
    """
    Same regression test as above, but this time tests against responses instead of the worker name.
    """
    server = _patch_lock_factory(monkeypatch)
    digest = _digest(11)

    _hold_lock(server, digest, holder_id="placeholder:0:0:00000000")
    monkeypatch.setattr(GlobalLock, "_current_holder", lambda self: artifact)

    result = get_or_create_blob_with_lock(digest=digest, image_size=1)

    assert result is not None, f"must not implicitly return none for artifact={artifact!r}"
    assert result.content_checksum == digest
