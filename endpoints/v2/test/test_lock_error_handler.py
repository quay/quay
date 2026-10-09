import pytest

from app import app as realapp
from endpoints.v2 import handle_lock_acquire_timeout
from util.locking import LockAcquireTimeout, LockOwnershipLost


@pytest.mark.parametrize("exc_cls", [LockAcquireTimeout, LockOwnershipLost])
def test_handle_lock_acquire_timeout_returns_503(exc_cls):
    with realapp.app_context():
        response = handle_lock_acquire_timeout(exc_cls("test"))

    assert response.status_code == 503
    assert response.get_json()["errors"][0]["code"] == "UNAVAILABLE"
