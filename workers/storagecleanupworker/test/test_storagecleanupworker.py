import logging
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import pytest
from mock import Mock, patch

from app import app as realapp
from storage import DistributedStorage, LocalStorage, StorageContext
from test.fixtures import *
from workers.storagecleanupworker.models_pre_oci import pre_oci_model as model
from workers.storagecleanupworker.storagecleanupworker import (
    LOCK_TTL,
    MPU_DELETION_DATE_THRESHOLD,
    StorageCleanupWorker,
)

_TEST_LOG_PATH = "exportedactionlogs/"


def test_storagecleanupworker(initialized_db):
    # Create a blob upload older than the threshold.
    blob_upload = model.create_stale_upload_for_testing()

    # Note: We need to override UseThenDisconnect to ensure to remains connected to the test DB.
    @contextmanager
    def noop(_):
        yield

    storage_mock = Mock()
    with patch("workers.storagecleanupworker.storagecleanupworker.UseThenDisconnect", noop):
        with patch("workers.storagecleanupworker.storagecleanupworker.storage", storage_mock):
            # Call cleanup and ensure it is canceled.
            worker = StorageCleanupWorker()
            worker._cleanup_uploads()

            storage_mock.locations = ["default"]
            worker._try_clean_partial_uploads()

    storage_mock.clean_partial_uploads.assert_called_once()
    storage_mock.cancel_chunked_upload.assert_called_once()

    # Ensure the blob no longer exists.
    model.blob_upload_exists(blob_upload.uuid)


def test_storagecleanupworker_calls_mpu_cleanup(initialized_db):
    """
    Asserts that the MPU cleanup function is called from the worker.
    """
    storage_mock = Mock()
    storage_mock.preferred_locations = ["default"]

    # verify that the deletion threshold is always 1 day
    assert MPU_DELETION_DATE_THRESHOLD == timedelta(days=1)

    # we'll mock the deleted count
    storage_mock.clean_orphaned_multipart_uploads.return_value = 5

    with patch("workers.storagecleanupworker.storagecleanupworker.GlobalLock"):
        with patch("workers.storagecleanupworker.storagecleanupworker.storage", storage_mock):

            # call cleanup and ensure it's cancelled
            worker = StorageCleanupWorker()
            worker._try_clean_stale_multipart_uploads()

        storage_mock.clean_orphaned_multipart_uploads.assert_called_once_with(
            ["default"], MPU_DELETION_DATE_THRESHOLD
        )


def test_mpu_cleanup_exits_if_no_preferred_storage_location_is_found(initialized_db):
    """
    Checks that the MPU cleanup is not called if preferred storage engine is not set.
    """
    storage_mock = Mock()
    storage_mock.preferred_locations = []

    with patch("workers.storagecleanupworker.storagecleanupworker.GlobalLock"):
        with patch("workers.storagecleanupworker.storagecleanupworker.storage", storage_mock):
            worker = StorageCleanupWorker()
            worker._try_clean_stale_multipart_uploads()

    storage_mock.clean_orphaned_multipart_uploads.assert_not_called()


def test_partial_blob_cleanup_exits_if_no_preferred_storage_location_is_found(initialized_db):
    """
    Checks that the partial blob cleanup is not called if preferred storage engine is not set.
    """
    storage_mock = Mock()
    storage_mock.preferred_locations = []

    with patch("workers.storagecleanupworker.storagecleanupworker.GlobalLock"):
        with patch("workers.storagecleanupworker.storagecleanupworker.storage", storage_mock):
            worker = StorageCleanupWorker()
            worker._try_clean_partial_uploads()

    storage_mock.clean_partial_uploads.assert_not_called()


def test_verify_operation_is_not_registered_if_feature_flag_is_disabled(initialized_db):
    """
    Verifies that the job is not scheduled unless the feature flag is set.
    """
    with patch.dict(realapp.config, {"FEATURE_ENABLE_STALE_MPU_CLEANUP": False}):
        with patch.object(StorageCleanupWorker, "add_operation") as mock_add:
            StorageCleanupWorker()

        registered = [c.args[0].__name__ for c in mock_add.call_args_list]
        assert "_try_clean_stale_multipart_uploads" not in registered


def test_verify_operation_is_registered_if_feature_flag_is_enabled(initialized_db):
    """
    Asserts that the job operation is scheduled if the feature flag is set.
    """
    with patch.dict(realapp.config, {"FEATURE_ENABLE_STALE_MPU_CLEANUP": True}):
        with patch.object(StorageCleanupWorker, "add_operation") as mock_add:
            StorageCleanupWorker()

        registered = [c.args[0].__name__ for c in mock_add.call_args_list]
        assert "_try_clean_stale_multipart_uploads" in registered


def test_verify_that_worker_acquires_a_global_lock_with_proper_values(initialized_db):
    """
    Verifies that a GlobalLock is acquired if the worker is called and that proper values
    were sent.
    """
    from util.locking import GlobalLock

    captured = {}

    class _FakeLock:
        def __init__(self, name, expire=None, auto_renewal=False):
            self._name = name
            self._expire = expire
            self._auto_renewal = auto_renewal
            captured.update(name=name, expire=expire, auto_renewal=auto_renewal)

        def acquire(self):
            return True

        def release(self):
            pass

    storage_mock = Mock()

    storage_mock.preferred_locations = ["default"]
    storage_mock.clean_orphaned_multipart_uploads.return_value = 0

    with patch.object(GlobalLock, "lock_factory", staticmethod(_FakeLock)):
        with patch("workers.storagecleanupworker.storagecleanupworker.storage", storage_mock):
            worker = StorageCleanupWorker()
            worker._try_clean_stale_multipart_uploads()

        # verify that the lock is initialized with proper values
        assert captured["name"] == "STALE_MPU_CLEANUP"
        assert captured["expire"] == LOCK_TTL
        assert captured["auto_renewal"] is False

        storage_mock.clean_orphaned_multipart_uploads.assert_called_once_with(
            ["default"], MPU_DELETION_DATE_THRESHOLD
        )


def test_verify_that_multipart_cleanup_does_not_run_if_lock_cannot_be_acquired(initialized_db):
    """
    Verifies that cleanup of orphaned MPUs is not called if GlobalLock cannot be acquired.
    """
    from util.locking import GlobalLock, LockNotAcquiredException

    class _FakeLock:
        def __init__(self, name, expire=None, auto_renewal=False):
            self._name = name

        def acquire(self):
            return False

        def release(self):
            pass

    storage_mock = Mock()
    storage_mock.preferred_locations = ["default"]

    with patch.object(GlobalLock, "lock_factory", staticmethod(_FakeLock)):
        with patch("workers.storagecleanupworker.storagecleanupworker.storage", storage_mock):
            worker = StorageCleanupWorker()
            worker._try_clean_stale_multipart_uploads()

        storage_mock.clean_orphaned_multipart_uploads.assert_not_called()


def test_verify_log_export_cleanup_is_not_registered_if_feature_flag_is_disabled(initialized_db):
    """
    Verifies that the job is not scheduled unless the feature flag is set.
    """
    with patch.dict(realapp.config, {"FEATURE_LOG_EXPORT": False}):
        with patch.object(StorageCleanupWorker, "add_operation") as mock_add:
            StorageCleanupWorker()

        registered = [c.args[0].__name__ for c in mock_add.call_args_list]
        assert "_try_cleanup_exported_logs" not in registered


def test_verify_export_cleanup_is_registered_if_feature_flag_is_enabled(initialized_db):
    """
    Asserts that the job operation is scheduled if the feature flag is set.
    """
    with patch.dict(realapp.config, {"FEATURE_LOG_EXPORT": True}):
        with patch.object(StorageCleanupWorker, "add_operation") as mock_add:
            StorageCleanupWorker()

        registered = [c.args[0].__name__ for c in mock_add.call_args_list]
        assert "_try_cleanup_exported_logs" in registered


@pytest.fixture
def temp_storage_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_end_to_end_export_logs_cleanup(initialized_db, tmpdir):
    """
    Verifies that calling the worker deletes files from storage.
    """
    from util.locking import GlobalLock

    store_path = str(tmpdir)
    log_path = os.path.join(tmpdir, _TEST_LOG_PATH)

    local_storage = LocalStorage(StorageContext("local", None, None, None), store_path)
    distributed = DistributedStorage({"local": local_storage}, ["local"])

    # need to acquire lock, otherwise deletion will fail
    captured = {}

    class _FakeLock:
        def __init__(self, name, expire=None, auto_renewal=False):
            self._name = name
            self._expire = expire
            self._auto_renewal = auto_renewal
            captured.update(name=name, expire=expire, auto_renewal=auto_renewal)

        def acquire(self):
            return True

        def release(self):
            pass

    storage_mock = Mock()

    # write files
    keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for _ in range(5)]
    for k in keys:
        payload = os.urandom(1024)
        local_storage.put_content(path=k, content=payload)

    # backdate mtime by 2 hours so cleanup can be tried
    old_time = time.time() - (2 * 60 * 60)
    for k in keys:
        full_path = os.path.join(store_path, k)
        os.utime(full_path, (old_time, old_time))

    # assert that all files are there
    dir_path = Path(log_path)
    logging.debug("FILE LIST:")
    for f in dir_path.rglob("*"):
        if f.is_file():
            stats = f.stat()
            logging.debug("PATH: %s, stats: %s", f, stats)

    dir_path = Path(log_path)
    files = [str(f) for f in dir_path.rglob("*") if f.is_file()]
    assert len(files) == 5

    with patch.object(GlobalLock, "lock_factory", staticmethod(_FakeLock)):
        with patch("workers.storagecleanupworker.storagecleanupworker.storage", distributed):
            worker = StorageCleanupWorker()
            worker._try_cleanup_exported_logs()

    # verify that files were removed
    files = [f for f in Path(log_path).rglob("*") if f.is_file()]
    assert len(files) == 0
