import logging
import time

from contextlib import contextmanager
from collections import namedtuple

import bitmath
import rehash

from prometheus_client import Counter, Histogram

from data.registry_model import registry_model
from data.database import CloseForLongOperation, db_transaction
from digest import digest_tools
from util.registry.filelike import wrap_with_handler, StreamSlice
from util.registry.gzipstream import calculate_size_handler


logger = logging.getLogger(__name__)


chunk_upload_duration = Histogram(
    "quay_chunk_upload_duration_seconds",
    "number of seconds for a chunk to be uploaded to the registry",
    labelnames=["region"],
)
pushed_bytes_total = Counter(
    "quay_registry_image_pushed_bytes_total", "number of bytes pushed to the registry"
)


BLOB_CONTENT_TYPE = "application/octet-stream"


class BlobUploadException(Exception):
    """
    Base for all exceptions raised when uploading blobs.
    """


class BlobRangeMismatchException(BlobUploadException):
    """
    Exception raised if the range to be uploaded does not match.
    """


class BlobDigestMismatchException(BlobUploadException):
    """
    Exception raised if the digest requested does not match that of the contents uploaded.
    """


class BlobTooLargeException(BlobUploadException):
    """
    Exception raised if the data uploaded exceeds the maximum_blob_size.
    """

    def __init__(self, uploaded, max_allowed):
        super(BlobTooLargeException, self).__init__()
        self.uploaded = uploaded
        self.max_allowed = max_allowed


BlobUploadSettings = namedtuple(
    "BlobUploadSettings",
    ["maximum_blob_size", "committed_blob_expiration"],
)


def create_blob_upload(repository_ref, storage, settings, extra_blob_stream_handlers=None):
    """
    Creates a new blob upload in the specified repository and returns a manager for interacting with
    that upload.

    Returns None if a new blob upload could not be started.
    """
    location_name = storage.preferred_locations[0]
    new_upload_uuid, upload_metadata = storage.initiate_chunked_upload(location_name)
    blob_upload = registry_model.create_blob_upload(
        repository_ref, new_upload_uuid, location_name, upload_metadata
    )
    if blob_upload is None:
        return None

    return _BlobUploadManager(
        repository_ref, blob_upload, settings, storage, extra_blob_stream_handlers
    )


def retrieve_blob_upload_manager(repository_ref, blob_upload_id, storage, settings):
    """
    Retrieves the manager for an in-progress blob upload with the specified ID under the given
    repository or None if none.
    """
    blob_upload = registry_model.lookup_blob_upload(repository_ref, blob_upload_id)
    if blob_upload is None:
        return None

    return _BlobUploadManager(repository_ref, blob_upload, settings, storage)


@contextmanager
def complete_when_uploaded(blob_upload):
    """
    Wraps the given blob upload in a context manager that completes the upload when the context
    closes.
    """
    try:
        yield blob_upload
    except Exception as ex:
        logger.exception("Exception when uploading blob `%s`", blob_upload.blob_upload_id)
        raise ex
    finally:
        # Cancel the upload if something went wrong or it was not commit to a blob.
        if blob_upload.committed_blob is None:
            blob_upload.cancel_upload()


@contextmanager
def upload_blob(repository_ref, storage, settings, extra_blob_stream_handlers=None):
    """
    Starts a new blob upload in the specified repository and yields a manager for interacting with
    that upload.

    When the context manager completes, the blob upload is deleted, whether committed to a blob or
    not. Yields None if a blob upload could not be started.
    """
    assert repository_ref is not None

    created = create_blob_upload(repository_ref, storage, settings, extra_blob_stream_handlers)
    if not created:
        yield None
        return

    try:
        yield created
    except Exception as ex:
        logger.exception("Exception when uploading blob `%s`", created.blob_upload_id)
        raise ex
    finally:
        # Cancel the upload if something went wrong or it was not commit to a blob.
        if created.committed_blob is None:
            created.cancel_upload()


class _BlobUploadManager(object):
    """
    Defines a helper class for easily interacting with blob uploads in progress, including handling
    of database and storage calls.
    """

    def __init__(
        self, repository_ref, blob_upload, settings, storage, extra_blob_stream_handlers=None
    ):
        assert repository_ref is not None
        assert blob_upload is not None

        self.repository_ref = repository_ref
        self.blob_upload = blob_upload
        self.settings = settings
        self.storage = storage
        self.extra_blob_stream_handlers = extra_blob_stream_handlers
        self.committed_blob = None

    @property
    def blob_upload_id(self):
        """
        Returns the unique ID for the blob upload.
        """
        return self.blob_upload.upload_id

    def upload_chunk(self, app_config, input_fp, start_offset=0, length=-1):
        """
        Uploads a chunk of data found in the given input file-like interface. start_offset and
        length are optional and should match a range header if any was given.

        Returns the total number of bytes uploaded after this upload has completed. Raises a
        BlobUploadException if the upload failed.
        """
        assert start_offset is not None
        assert length is not None

        if start_offset > 0 and start_offset > self.blob_upload.byte_count:
            logger.error("start_offset provided greater than blob_upload.byte_count")
            raise BlobRangeMismatchException()

        # Ensure that we won't go over the allowed maximum size for blobs.
        max_blob_size = bitmath.parse_string_unsafe(self.settings.maximum_blob_size)
        uploaded = bitmath.Byte(length + start_offset)
        if length > -1 and uploaded > max_blob_size:
            raise BlobTooLargeException(uploaded=uploaded.bytes, max_allowed=max_blob_size.bytes)

        location_set = {self.blob_upload.location_name}
        upload_error = None
        with CloseForLongOperation(app_config):
            if start_offset > 0 and start_offset < self.blob_upload.byte_count:
                # Skip the bytes which were received on a previous push, which are already stored and
                # included in the sha calculation
                overlap_size = self.blob_upload.byte_count - start_offset
                input_fp = StreamSlice(input_fp, overlap_size)

                # Update our upload bounds to reflect the skipped portion of the overlap
                start_offset = self.blob_upload.byte_count
                length = max(length - overlap_size, 0)

            # We use this to escape early in case we have already processed all of the bytes the user
            # wants to upload.
            if length == 0:
                return self.blob_upload.byte_count

            input_fp = wrap_with_handler(input_fp, self.blob_upload.sha_state.update)

            if self.extra_blob_stream_handlers:
                for handler in self.extra_blob_stream_handlers:
                    input_fp = wrap_with_handler(input_fp, handler)

            # If this is the first chunk and we're starting at the 0 offset, add a handler to gunzip the
            # stream so we can determine the uncompressed size. We'll throw out this data if another chunk
            # comes in, but in the common case the docker client only sends one chunk.
            size_info = None
            if start_offset == 0 and self.blob_upload.chunk_count == 0:
                size_info, fn = calculate_size_handler()
                input_fp = wrap_with_handler(input_fp, fn)

            start_time = time.time()
            length_written, new_metadata, upload_error = self.storage.stream_upload_chunk(
                location_set,
                self.blob_upload.upload_id,
                start_offset,
                length,
                input_fp,
                self.blob_upload.storage_metadata,
                content_type=BLOB_CONTENT_TYPE,
            )

            if upload_error is not None:
                logger.error("storage.stream_upload_chunk returned error %s", upload_error)
                raise BlobUploadException(upload_error)

            # Update the chunk upload time and push bytes metrics.
            chunk_upload_duration.labels(list(location_set)[0]).observe(time.time() - start_time)
            pushed_bytes_total.inc(length_written)

        # Ensure we have not gone beyond the max layer size.
        new_blob_bytes = self.blob_upload.byte_count + length_written
        new_blob_size = bitmath.Byte(new_blob_bytes)
        if new_blob_size > max_blob_size:
            raise BlobTooLargeException(uploaded=new_blob_size, max_allowed=max_blob_size.bytes)

        # If we determined an uncompressed size and this is the first chunk, add it to the blob.
        # Otherwise, we clear the size from the blob as it was uploaded in multiple chunks.
        uncompressed_byte_count = self.blob_upload.uncompressed_byte_count
        if size_info is not None and self.blob_upload.chunk_count == 0 and size_info.is_valid:
            uncompressed_byte_count = size_info.uncompressed_size
        elif length_written > 0:
            # Otherwise, if we wrote some bytes and the above conditions were not met, then we don't
            # know the uncompressed size.
            uncompressed_byte_count = None

        self.blob_upload = registry_model.update_blob_upload(
            self.blob_upload,
            uncompressed_byte_count,
            new_metadata,
            new_blob_bytes,
            self.blob_upload.chunk_count + 1,
            self.blob_upload.sha_state,
        )
        if self.blob_upload is None:
            raise BlobUploadException("Could not complete upload of chunk")

        return new_blob_bytes

    def cancel_upload(self):
        """
        Cancels the blob upload, deleting any data uploaded and removing the upload itself.
        """
        if self.blob_upload is None:
            return

        # Tell storage to cancel the chunked upload, deleting its contents.
        self.storage.cancel_chunked_upload(
            {self.blob_upload.location_name},
            self.blob_upload.upload_id,
            self.blob_upload.storage_metadata,
        )

        # Remove the blob upload record itself.
        registry_model.delete_blob_upload(self.blob_upload)

    def commit_to_blob(self, app_config, expected_digest=None):
        """
        Commits the blob upload to a blob under the repository. The resulting blob will be marked to
        not be GCed for some period of time (as configured by `committed_blob_expiration`).

        If expected_digest is specified, the content digest of the data uploaded for the blob is
        compared to that given and, if it does not match, a BlobDigestMismatchException is raised.
        The digest given must be of type `Digest` and not a string.
        """
        # Compare the content digest.
        if expected_digest is not None:
            self._validate_digest(expected_digest)

        # Finalize the storage.
        storage_already_existed = self._finalize_blob_storage(app_config)

        # Convert the upload to a blob.
        computed_digest_str = digest_tools.sha256_digest_from_hashlib(self.blob_upload.sha_state)

        with db_transaction():
            blob = registry_model.commit_blob_upload(
                self.blob_upload, computed_digest_str, self.settings.committed_blob_expiration
            )
            if blob is None:
                return None

        self.committed_blob = blob
        return blob

    def _validate_digest(self, expected_digest):
        """
        Verifies that the digest's SHA matches that of the uploaded data.
        """
        try:
            computed_digest = digest_tools.sha256_digest_from_hashlib(self.blob_upload.sha_state)
            if not digest_tools.digests_equal(computed_digest, expected_digest):
                logger.error(
                    "Digest mismatch for upload %s: Expected digest %s, found digest %s",
                    self.blob_upload.upload_id,
                    expected_digest,
                    computed_digest,
                )
                raise BlobDigestMismatchException()
        except digest_tools.InvalidDigestException:
            raise BlobDigestMismatchException()

    def _finalize_blob_storage(self, app_config):
        """
        When an upload is successful, this ends the uploading process from the storage's
        perspective.

        Returns True if the blob already existed.
        """
        computed_digest = digest_tools.sha256_digest_from_hashlib(self.blob_upload.sha_state)
        final_blob_location = digest_tools.content_path(computed_digest)

        # Close the database connection before we perform this operation, as it can take a while
        # and we shouldn't hold the connection during that time.
        with CloseForLongOperation(app_config):
            # Move the storage into place, or if this was a re-upload, cancel it
            already_existed = self.storage.exists(
                {self.blob_upload.location_name}, final_blob_location
            )
            if already_existed:
                # It already existed, clean up our upload which served as proof that the
                # uploader had the blob.
                self.storage.cancel_chunked_upload(
                    {self.blob_upload.location_name},
                    self.blob_upload.upload_id,
                    self.blob_upload.storage_metadata,
                )
            else:
                # We were the first ones to upload this image (at least to this location)
                # Let's copy it into place
                self.storage.complete_chunked_upload(
                    {self.blob_upload.location_name},
                    self.blob_upload.upload_id,
                    final_blob_location,
                    self.blob_upload.storage_metadata,
                )

        return already_existed
