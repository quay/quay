import logging
import logging.config

from datetime import timedelta, datetime

from app import app, storage
from data.database import UseThenDisconnect
from workers.blobuploadcleanupworker.models_pre_oci import pre_oci_model as model
from workers.worker import Worker
from util.log import logfile_path
from util.locking import GlobalLock, LockNotAcquiredException
from workers.gunicorn_worker import GunicornWorker


logger = logging.getLogger(__name__)

threshold = app.config.get("BLOBUPLOAD_DELETION_DATE_THRESHOLD", 60 * 48)  # 2 days
DELETION_DATE_THRESHOLD = timedelta(minutes=threshold)
BLOBUPLOAD_CLEANUP_FREQUENCY = app.config.get("BLOBUPLOAD_CLEANUP_FREQUENCY", 60 * 60)
LOCK_TTL = 60 * 20  # 20 minutes


class BlobUploadCleanupWorker(Worker):
    def __init__(self):
        super(BlobUploadCleanupWorker, self).__init__()
        self.add_operation(self._try_cleanup_uploads, BLOBUPLOAD_CLEANUP_FREQUENCY)

    def _try_cleanup_uploads(self):
        """
        Performs garbage collection on the blobupload table.
        Will also perform garbage collection on the uploads folder in the S3 bucket,
        if applicable.
        """
        try:
            with GlobalLock("BLOB_CLEANUP", lock_ttl=LOCK_TTL):
                self._cleanup_uploads()
                if app.config.get("CLEAN_BLOB_UPLOAD_FOLDER", False):
                    self._try_clean_partial_uploads()
        except LockNotAcquiredException:
            logger.debug("Could not acquire global lock for blob upload cleanup worker")

    def _try_clean_partial_uploads(self):
        """
        Uploads cancelled before completion leaves the possibility of untracked blobs being
        leftover in the uploads storage folder.
        This function cleans those blobs older than DELETION_DATE_THRESHOLD
        """
        try:
            storage.clean_partial_uploads(storage.preferred_locations, DELETION_DATE_THRESHOLD)
        except NotImplementedError:
            if len(storage.preferred_locations) > 0:
                logger.debug(
                    'Cleaning partial uploads not applicable to storage location "%s"',
                    storage.preferred_locations[0],
                )
            else:
                logger.debug("No preferred locations found")

    def _cleanup_uploads(self):
        """
        Performs cleanup on the blobupload table.
        """
        logger.debug("Performing blob upload cleanup")

        while True:
            # Find all blob uploads older than the threshold (typically a week) and delete them.
            with UseThenDisconnect(app.config):
                stale_upload = model.get_stale_blob_upload(DELETION_DATE_THRESHOLD)
                if stale_upload is None:
                    logger.debug("No additional stale blob uploads found")
                    return

            # Remove the stale upload from storage.
            logger.debug("Removing stale blob upload %s", stale_upload.uuid)
            assert stale_upload.created <= (datetime.utcnow() - DELETION_DATE_THRESHOLD)

            try:
                storage.cancel_chunked_upload(
                    [stale_upload.location_name], stale_upload.uuid, stale_upload.storage_metadata
                )
            except Exception as ex:
                logger.debug(
                    "Got error when trying to cancel chunked upload %s: %s",
                    stale_upload.uuid,
                    str(ex),
                )

            # Delete the stale upload's row.
            with UseThenDisconnect(app.config):
                model.delete_blob_upload(stale_upload)

            logger.debug("Removed stale blob upload %s", stale_upload.uuid)


def create_gunicorn_worker() -> GunicornWorker:
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, BlobUploadCleanupWorker())
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    GlobalLock.configure(app.config)
    worker = BlobUploadCleanupWorker()
    worker.start()
