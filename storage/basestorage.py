import logging
import tempfile

from digest.digest_tools import content_path
from util.registry.filelike import READ_UNTIL_END

logger = logging.getLogger(__name__)


class StoragePaths(object):
    shared_images = "sharedimages"

    @staticmethod
    def temp_store_handler():
        tmpf = tempfile.TemporaryFile()

        def fn(buf):
            try:
                tmpf.write(buf)
            except IOError:
                pass

        return tmpf, fn

    def _image_path(self, storage_uuid):
        return "{0}/{1}/".format(self.shared_images, storage_uuid)

    def v1_image_layer_path(self, storage_uuid):
        base_path = self._image_path(storage_uuid)
        return "{0}layer".format(base_path)

    def blob_path(self, digest_str):
        return content_path(digest_str)


class BaseStorage(StoragePaths):
    def __init__(self):
        # Set the IO buffer to 64kB
        self.buffer_size = 64 * 1024

    def setup(self):
        """
        Called to perform any storage system setup.
        """
        pass

    def validate(self, client):
        """
        Called to perform storage system validation.

        The client is an HTTP client to use for any external calls.
        """
        # Put a temporary file to make sure the normal storage paths work.
        self.put_content("_verify", b"testing 123")
        if not self.exists("_verify"):
            raise Exception("Could not find verification file")

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        return None

    def get_direct_upload_url(self, path, mime_type, requires_cors=True):
        return None

    def get_supports_resumable_downloads(self):
        return False

    def get_content(self, path):
        raise NotImplementedError

    def put_content(self, path, content):
        raise NotImplementedError

    def stream_read(self, path):
        raise NotImplementedError

    def stream_read_file(self, path):
        raise NotImplementedError

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        raise NotImplementedError

    def exists(self, path):
        raise NotImplementedError

    def remove(self, path):
        raise NotImplementedError

    def get_checksum(self, path):
        raise NotImplementedError

    def stream_write_to_fp(self, in_fp, out_fp, num_bytes=READ_UNTIL_END):
        """
        Copy the specified number of bytes from the input file stream to the output stream.

        If num_bytes < 0 copy until the stream ends. Returns the number of bytes copied.
        """
        bytes_copied = 0
        while bytes_copied < num_bytes or num_bytes == READ_UNTIL_END:
            size_to_read = min(num_bytes - bytes_copied, self.buffer_size)
            if size_to_read < 0:
                size_to_read = self.buffer_size

            buf = in_fp.read(size_to_read)
            if not buf:
                break
            out_fp.write(buf)
            bytes_copied += len(buf)

        return bytes_copied

    def copy_to(self, destination, path):
        raise NotImplementedError


class BaseStorageV2(BaseStorage):
    def initiate_chunked_upload(self):
        """
        Start a new chunked upload, returning the uuid and any associated storage metadata.
        """
        raise NotImplementedError

    def stream_upload_chunk(self, uuid, offset, length, in_fp, storage_metadata, content_type=None):
        """
        Upload the specified amount of data from the given file pointer to the chunked destination
        specified, starting at the given offset.

        Returns the number of bytes uploaded, a new version of the storage_metadata and an error
        object (if one occurred or None if none). Pass length as -1 to upload as much data from the
        in_fp as possible.
        """
        raise NotImplementedError

    def complete_chunked_upload(self, uuid, final_path, storage_metadata):
        """
        Complete the chunked upload and store the final results in the path indicated.

        Returns nothing.
        """
        raise NotImplementedError

    def cancel_chunked_upload(self, uuid, storage_metadata):
        """
        Cancel the chunked upload and clean up any outstanding partially uploaded data.

        Returns nothing.
        """
        raise NotImplementedError
