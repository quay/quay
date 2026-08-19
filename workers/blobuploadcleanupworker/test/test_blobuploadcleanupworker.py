from contextlib import contextmanager

import boto3
from mock import Mock, patch
from moto import mock_s3

from test.fixtures import *
from workers.blobuploadcleanupworker.blobuploadcleanupworker import (
    MPU_DELETION_DATE_THRESHOLD,
    BlobUploadCleanupWorker,
)
from workers.blobuploadcleanupworker.models_pre_oci import pre_oci_model as model


def test_blobuploadcleanupworker(initialized_db):
    # Create a blob upload older than the threshold.
    blob_upload = model.create_stale_upload_for_testing()

    # Note: We need to override UseThenDisconnect to ensure to remains connected to the test DB.
    @contextmanager
    def noop(_):
        yield

    storage_mock = Mock()
    with patch("workers.blobuploadcleanupworker.blobuploadcleanupworker.UseThenDisconnect", noop):
        with patch("workers.blobuploadcleanupworker.blobuploadcleanupworker.storage", storage_mock):
            # Call cleanup and ensure it is canceled.
            worker = BlobUploadCleanupWorker()
            worker._cleanup_uploads()

            storage_mock.locations = ["default"]
            worker._try_clean_partial_uploads()

    storage_mock.clean_partial_uploads.assert_called_once()
    storage_mock.cancel_chunked_upload.assert_called_once()

    # Ensure the blob no longer exists.
    model.blob_upload_exists(blob_upload.uuid)


def test_blobuploadcleanupworker_calls_mpu_cleanup(initialized_db):
    """
    Asserts that the MPU cleanup function is called from the worker.
    """
    storage_mock = Mock()
    storage_mock.preferred_locations = ["default"]

    # we'll mock the deleted count
    storage_mock.clean_orphaned_multipart_uploads.return_value = 5

    with patch("workers.blobuploadcleanupworker.blobuploadcleanupworker.storage", storage_mock):
        # call cleanup and ensure it's cancelled
        worker = BlobUploadCleanupWorker()
        worker._try_clean_stale_multipart_uploads()

    storage_mock.clean_orphaned_multipart_uploads.assert_called_once_with(
        ["default"], MPU_DELETION_DATE_THRESHOLD
    )
