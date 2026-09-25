import functools
import json
import logging
import os
import subprocess
import sys
import textwrap
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
    assert 1 <= elapsed < 2, f"bounded acquire did not honour its 1s deadline: {elapsed}s"


def test_acquire_without_blocking_timeout_passes_no_timeout_through(fake_lock_server, monkeypatch):
    """blocking_timeout=None (the default) must not change behavior for existing callers: it
    makes the same blocking redis_lock.Lock.acquire() call, with no timeout, as before the fix."""
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


def test_acquire_timeout_logs_exactly_one_warning(fake_lock_server, caplog):
    """The bounded poll retries acquire(blocking=False) ~20 times over a 1s deadline; redis_lock
    logs a WARNING on every failed non-blocking attempt, which must not reach the logs."""
    _hold_lock(fake_lock_server, "BLOB_DELETE_sha256:fff")

    lock = GlobalLock("BLOB_DELETE_sha256:fff", lock_ttl=30, blocking_timeout=1)
    with caplog.at_level(logging.WARNING):
        acquired = lock.acquire()

    assert acquired is False
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, warnings


def test_acquire_succeeds_when_lock_is_free(fake_lock_server):
    lock = GlobalLock("BLOB_DELETE_sha256:ccc", lock_ttl=30, blocking_timeout=1)
    assert lock.acquire() is True
    lock.release()


# Production shape: gevent-patched workers sharing GlobalLock's single_connection_client. Run in a
# subprocess so monkey-patching cannot leak into the rest of the test session.
_GEVENT_SCENARIOS = textwrap.dedent("""
    from gevent import monkey

    monkey.patch_all()

    import functools
    import json
    import time

    import fakeredis
    import gevent
    import redis_lock

    from util.locking import GlobalLock

    DEADLINE = 1

    server = fakeredis.FakeServer()
    conn = fakeredis.FakeStrictRedis(server=server, single_connection_client=True)
    GlobalLock.lock_factory = functools.partial(redis_lock.Lock, conn)

    # fakeredis runs no Lua without lupa, so issue redis_lock's release/extend script commands
    # one by one. They still go through the shared client connection, which is what is under test.
    def unlock(client, keys, args):
        if client.get(keys[0]) != args[0].encode():
            return 1
        client.delete(keys[1])
        client.lpush(keys[1], 1)
        client.pexpire(keys[1], args[1])
        client.delete(keys[0])
        return 0

    def extend(client, keys, args):
        if client.get(keys[0]) != args[0].encode():
            return 1
        client.expire(keys[0], args[1])
        return 0

    redis_lock.Lock.register_scripts(conn)
    redis_lock.Lock.unlock_script = staticmethod(unlock)
    redis_lock.Lock.extend_script = staticmethod(extend)

    def timed(fn):
        start = time.monotonic()
        result = fn()
        return result, time.monotonic() - start

    def bounded_waiter(name):
        return timed(GlobalLock(name, lock_ttl=30, blocking_timeout=DEADLINE).acquire)

    def holder_with_waiter():
        holder = GlobalLock("holder", lock_ttl=30)
        assert holder.acquire()
        waiter = gevent.spawn(bounded_waiter, "holder")
        gevent.sleep(0.2)
        _, extend_took = timed(holder._lock.extend)
        _, release_took = timed(holder._lock.release)
        acquired, waited = waiter.get()
        return {
            "extend": extend_took,
            "release": release_took,
            "waiter_acquired": acquired,
            "waiter_elapsed": waited,
        }

    def queued_waiters():
        assert GlobalLock("queued", lock_ttl=30).acquire()
        waiters = [gevent.spawn(bounded_waiter, "queued") for _ in range(3)]
        return [waiter.get() for waiter in waiters]

    def wake_and_steal():
        # Another process keeps releasing and immediately re-taking the lock.
        other = fakeredis.FakeStrictRedis(server=server)
        thief = redis_lock.Lock(other, "stolen", expire=30, id="thief")
        assert thief.acquire()

        def steal():
            nonlocal thief
            for _ in range(5):
                gevent.sleep(0.15)
                thief.release()
                thief = redis_lock.Lock(other, "stolen", expire=30, id="thief")
                assert thief.acquire(blocking=False)

        stealer = gevent.spawn(steal)
        result = bounded_waiter("stolen")
        stealer.join()
        return result

    print(
        json.dumps(
            {
                "deadline": DEADLINE,
                "holder_with_waiter": holder_with_waiter(),
                "queued_waiters": queued_waiters(),
                "wake_and_steal": wake_and_steal(),
            }
        )
    )
    """)


@pytest.fixture(scope="module")
def gevent_scenarios():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proc = subprocess.run(
        [sys.executable, "-c", _GEVENT_SCENARIOS],
        cwd=repo_root,
        env=dict(os.environ, PYTHONPATH=repo_root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_bounded_waiter_does_not_delay_holder_on_shared_connection(gevent_scenarios):
    result = gevent_scenarios["holder_with_waiter"]

    assert result["extend"] < 0.5, result
    assert result["release"] < 0.5, result
    assert result["waiter_acquired"] is True, result
    assert result["waiter_elapsed"] < gevent_scenarios["deadline"], result


def test_bounded_waiters_on_shared_connection_each_honour_deadline(gevent_scenarios):
    deadline = gevent_scenarios["deadline"]

    for acquired, elapsed in gevent_scenarios["queued_waiters"]:
        assert acquired is False
        assert deadline <= elapsed < deadline + 0.5, gevent_scenarios["queued_waiters"]


def test_bounded_waiter_deadline_is_total_across_lost_wakeups(gevent_scenarios):
    deadline = gevent_scenarios["deadline"]
    acquired, elapsed = gevent_scenarios["wake_and_steal"]

    assert acquired is False
    assert deadline <= elapsed < deadline + 0.5, elapsed
