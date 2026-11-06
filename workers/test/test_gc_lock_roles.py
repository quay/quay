import runpy

import pytest

import features
from app import app
from data.model.storage import _GC_LOCK_ROLES
from util.locking import GlobalLock
from workers.worker import Worker


class _Started(Exception):
    pass


@pytest.mark.parametrize(
    "module, feature, expected_role",
    [
        ("workers.gc.gcworker", "GARBAGE_COLLECTION", "gcworker"),
        ("workers.namespacegcworker", "NAMESPACE_GARBAGE_COLLECTION", "namespacegcworker"),
        ("workers.repositorygcworker", "REPOSITORY_GARBAGE_COLLECTION", "repositorygcworker"),
    ],
)
def test_gc_worker_lock_role(module, feature, expected_role, monkeypatch):
    """
    Each GC worker must configure GlobalLock with a role present in _GC_LOCK_ROLES, otherwise
    data.model.storage cannot recognize its locks as GC lock holders.
    """
    monkeypatch.setattr(features, feature, True)
    monkeypatch.setitem(app.config, "DISABLE_PUSHES", False)
    monkeypatch.setitem(app.config, "ACCOUNT_RECOVERY_MODE", False)

    configured = []
    monkeypatch.setattr(
        GlobalLock,
        "configure",
        classmethod(lambda cls, config, lock_role=None: configured.append(lock_role)),
    )

    def fake_start(self, *args, **kwargs):
        raise _Started()

    monkeypatch.setattr(Worker, "start", fake_start)

    with pytest.raises(_Started):
        runpy.run_module(module, run_name="__main__")

    assert configured == [expected_role]
    assert expected_role in _GC_LOCK_ROLES
