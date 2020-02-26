from abc import ABCMeta, abstractmethod
from collections import namedtuple
from six import add_metaclass


class BlobUpload(
    namedtuple("BlobUpload", ["uuid", "storage_metadata", "location_name", "created"])
):
    """
    BlobUpload represents a single upload of a blob in progress or previously started.
    """


@add_metaclass(ABCMeta)
class BlobUploadCleanupWorkerDataInterface(object):
    """
    Interface that represents all data store interactions required by the blob upload cleanup
    worker.
    """

    @abstractmethod
    def get_stale_blob_upload(self, stale_threshold):
        """
        Returns a BlobUpload that was created on or before the current date/time minus the stale
        threshold.

        If none, returns None.
        """
        pass

    @abstractmethod
    def delete_blob_upload(self, blob_upload):
        """
        Deletes a blob upload from the database.
        """
        pass

    @abstractmethod
    def create_stale_upload_for_testing(self):
        """
        Creates a new stale blob upload for testing.
        """
        pass

    @abstractmethod
    def blob_upload_exists(self, upload_uuid):
        """
        Returns True if a blob upload with the given UUID exists.
        """
        pass
