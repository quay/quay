"""
Tests for the role-aware BLOB_DELETE lock logic introduced to prevent false
503s caused by registry workers misinterpreting Redis responses under load
(response mixing on a shared single_connection_client).

Coverage map
------------
test_is_gcworker_holder_*           -- _is_gcworker_holder() unit tests
test_blob_lock_fallback_*            -- with_blob_lock_or_fallback() decision
"""

import functools

import fakeredis
import pytest
import redis_lock

import data.model.storage as storage_module
from data.model.storage import (
    _BLOB_LOCK_UNAVAILABLE,
    _GC_LOCK_ROLES,
    _blob_lock_fallback,
    _is_gcworker_holder,
    with_blob_lock_or_fallback,
)
from util.locking import GlobalLock, LockAcquireTimeout

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_lock_server(monkeypatch):
    """Inject a fakeredis server as the GlobalLock backend and reset the
    process role to "registry" so tests start from a known, clean state."""
    server = fakeredis.FakeServer()
    conn = fakeredis.FakeStrictRedis(server=server)
    monkeypatch.setattr(GlobalLock, "lock_factory", functools.partial(redis_lock.Lock, conn))
    monkeypatch.setattr(GlobalLock, "_process_lock_role", "registry")
    return server


@pytest.fixture
def fast_timeout(monkeypatch):
    """Reduce BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT from 3 s to 0.1 s so tests
    that exercise the timeout path complete quickly."""
    monkeypatch.setattr(storage_module, "BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT", 0.1)


def _hold_lock(server, digest, holder_id):
    """Acquire and hold a BLOB_DELETE lock on the fakeredis server so that a
    subsequent GlobalLock acquisition on the same digest will fail/time-out."""
    conn = fakeredis.FakeStrictRedis(server=server)
    lock = redis_lock.Lock(conn, f"BLOB_DELETE_{digest}", expire=30, id=holder_id)
    assert lock.acquire(), f"_hold_lock: failed to acquire lock for {digest}"
    return lock


# ---------------------------------------------------------------------------
# _is_gcworker_holder — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    list(_GC_LOCK_ROLES),
)
def test_is_gcworker_holder_true_for_each_gc_role(role):
    # Every role in _GC_LOCK_ROLES must be recognised as a GC worker.
    # If a new GC worker type is added to _GC_LOCK_ROLES without a matching
    # entry here the parametrize will surface a new case automatically.
    holder_id = f"{role}:some-host:1234:abcdef01"
    assert _is_gcworker_holder(holder_id) is True, f"Expected True for GC role {role!r}, got False"


@pytest.mark.parametrize(
    "holder_id",
    [
        # Explicit registry role — concurrent blob commits, IntegrityError handles races.
        "registry:some-host:265:abcdef01",
        # Bare hostname:pid:uuid from old code that predates the role feature
        # (e.g. during a rolling deploy where GC pods have not been updated yet).
        # Must return False so the writer proceeds rather than 503-ing forever.
        "some-host:265:abcdef01",
        # "OK" — a SET NX success response delivered to the wrong greenlet's
        # GET read on a shared single_connection_client.  The smoking-gun artifact
        # that first confirmed the response-mixing hypothesis in production logs.
        "OK",
        # None — the lock key expired between the polling deadline and the
        # _current_holder() GET, i.e. the ghost holder's TTL ran out.
        None,
        # Empty string — malformed but must not crash.
        "",
    ],
)
def test_is_gcworker_holder_false_for_non_gc_holders(holder_id):
    # None of these must trigger the GC-worker guard.  Treating them as GC
    # would cause permanent 503s for normal concurrent blob pushes.
    assert (
        _is_gcworker_holder(holder_id) is False
    ), f"Expected False for holder_id={holder_id!r}, got True"


# ---------------------------------------------------------------------------
# with_blob_lock_or_fallback — decision-tree tests
# ---------------------------------------------------------------------------


def test_blob_lock_fallback_acquires_normally_when_lock_is_free(fake_lock_server):
    # Happy path: the lock is free, so GlobalLock acquires it immediately and
    # calls func inside the with-block.  _blob_lock_fallback must remain at its
    # default (None), meaning the caller genuinely holds the lock and may_create
    # defaults to True inside _get_or_create_blob_with_lock.
    fallback_seen = []

    def func(*args, skip_lock=False, **kwargs):
        fallback_seen.append(_blob_lock_fallback.get())
        return "ok"

    result = with_blob_lock_or_fallback("sha256:aabbcc", func)

    assert result == "ok"
    assert fallback_seen == [
        None
    ], "fallback ContextVar must be None when we hold the lock ourselves"


def test_blob_lock_fallback_proceeds_when_registry_worker_holds_lock(
    fake_lock_server, fast_timeout
):
    # A registry worker (or any non-GC process) holds the BLOB_DELETE lock.
    # This is the response-mixing scenario where another greenlet's SET NX
    # response was delivered to the wrong reader, leaving a ghost lock entry.
    # with_blob_lock_or_fallback must proceed (not 503) because
    # registry-vs-registry races are resolved safely by the IntegrityError
    # guard in _get_or_create_blob_with_lock.
    _hold_lock(fake_lock_server, "sha256:ddeeff", holder_id="registry:host:265:00112233")

    fallback_seen = []

    def func(*args, skip_lock=False, **kwargs):
        # Capture the fallback state that with_blob_lock_or_fallback sets
        # before calling func in the non-lock-acquired path.
        fallback_seen.append(_blob_lock_fallback.get())
        return "ok"

    result = with_blob_lock_or_fallback("sha256:ddeeff", func)

    assert result == "ok", "must not raise a 503 for a registry-held lock"
    assert fallback_seen == [
        _BLOB_LOCK_UNAVAILABLE
    ], "fallback must be UNAVAILABLE (allow creation) not TIMED_OUT (block creation)"


@pytest.mark.parametrize(
    "artifact",
    [
        # SET NX "OK" response stolen by the wrong greenlet's GET read.
        "OK",
        # Expired ghost lock — key was gone before _current_holder() ran.
        None,
        # Pre-role legacy holder ID format (hostname:pid:uuid, no role prefix).
        # Seen during rolling deploys when some workers have the new code but GC
        # pods still run the old binary without _process_lock_role set.
        "9c9dc7:265:a3f1bc",
    ],
)
def test_blob_lock_fallback_proceeds_for_response_mixing_artifacts(
    fake_lock_server, fast_timeout, artifact, monkeypatch
):
    # Simulate response-mixing: the lock IS held in Redis (by "placeholder"),
    # but _current_holder() returns a garbled value due to the shared connection
    # delivering the wrong response frame.  with_blob_lock_or_fallback must
    # proceed safely — none of these artifacts represent a real GC worker.
    _hold_lock(fake_lock_server, "sha256:998877", holder_id="placeholder:0:0:00000000")
    monkeypatch.setattr(GlobalLock, "_current_holder", lambda self: artifact)

    called = []

    def func(*args, skip_lock=False, **kwargs):
        called.append(True)
        return "ok"

    result = with_blob_lock_or_fallback("sha256:998877", func)

    assert result == "ok", f"must not 503 for artifact holder_id={artifact!r}"
    assert called, "func must be called when holder is a response-mixing artifact"


@pytest.mark.parametrize("gc_role", list(_GC_LOCK_ROLES))
def test_blob_lock_fallback_raises_when_gc_worker_holds_lock(
    fake_lock_server, fast_timeout, gc_role
):
    # The only case that must 503: a genuine GC worker holds BLOB_DELETE_<digest>
    # while it is actively removing the blob from object storage.  Creating a DB
    # record pointing to the (soon-to-be-missing) object would leave a dangling
    # reference.  LockAcquireTimeout must propagate so the v2 endpoint returns 503
    # and the client retries after GC finishes.
    _hold_lock(
        fake_lock_server,
        "sha256:112233",
        holder_id=f"{gc_role}:gc-host:115:deadbeef",
    )

    def func(*args, skip_lock=False, **kwargs):
        pytest.fail(
            f"func must not be called while {gc_role!r} holds the lock — "
            "blob object may be mid-deletion"
        )

    with pytest.raises(LockAcquireTimeout):
        with_blob_lock_or_fallback("sha256:112233", func)
