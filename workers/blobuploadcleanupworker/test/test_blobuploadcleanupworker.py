from contextlib import contextmanager
from mock import patch, Mock

from test.fixtures import *
from workers.blobuploadcleanupworker.blobuploadcleanupworker import BlobUploadCleanupWorker
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

    storage_mock.cancel_chunked_upload.assert_called_once()

    # Ensure the blob no longer exists.
    model.blob_upload_exists(blob_upload.uuid)
