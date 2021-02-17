"""
Swift storage driver.

Uses: http://docs.openstack.org/developer/swift/overview_large_objects.html
"""
import os.path
import copy
import hmac
import string
import logging
import json
import sys

from io import IOBase

from collections import namedtuple
from hashlib import sha1
from random import SystemRandom
from time import time
from urllib.parse import urlparse
from uuid import uuid4

from cachetools.func import lru_cache
from swiftclient.client import Connection, ClientException, ReadableToIterable

from storage.basestorage import BaseStorage
from util.registry import filelike
from util.registry.generatorfile import GeneratorFile


logger = logging.getLogger(__name__)

_PartUploadMetadata = namedtuple("_PartUploadMetadata", ["path", "offset", "length"])
_SEGMENTS_KEY = "segments"
_EMPTY_SEGMENTS_KEY = "emptysegments"
_SEGMENT_DIRECTORY = "segments"
_MAXIMUM_SEGMENT_SIZE = 200000000  # ~200 MB
_DEFAULT_SWIFT_CONNECT_TIMEOUT = 5  # seconds
_CHUNK_CLEANUP_DELAY = 30  # seconds
_DEFAULT_RETRY_COUNT = 5


class SwiftStorage(BaseStorage):
    def __init__(
        self,
        context,
        swift_container,
        storage_path,
        auth_url,
        swift_user,
        swift_password,
        auth_version=None,
        os_options=None,
        ca_cert_path=None,
        temp_url_key=None,
        simple_path_concat=False,
        connect_timeout=None,
        retry_count=None,
        retry_on_ratelimit=True,
    ):
        super(SwiftStorage, self).__init__()
        self._swift_container = swift_container
        self._context = context

        self._storage_path = storage_path.lstrip("/")
        self._simple_path_concat = simple_path_concat

        self._auth_url = auth_url
        self._ca_cert_path = ca_cert_path

        self._swift_user = swift_user
        self._swift_password = swift_password

        self._temp_url_key = temp_url_key
        self._connect_timeout = connect_timeout

        try:
            self._retry_count = int(retry_count or _DEFAULT_RETRY_COUNT)
        except ValueError:
            self._retry_count = _DEFAULT_RETRY_COUNT

        self._retry_on_ratelimit = retry_on_ratelimit

        try:
            self._auth_version = int(auth_version or "2")
        except ValueError:
            self._auth_version = 2

        self._os_options = os_options or {}

        self._initialized = False

    def _get_connection(self):
        return Connection(
            authurl=self._auth_url,
            cacert=self._ca_cert_path,
            user=self._swift_user,
            key=self._swift_password,
            auth_version=self._auth_version,
            os_options=self._os_options,
            retry_on_ratelimit=self._retry_on_ratelimit,
            timeout=self._connect_timeout or _DEFAULT_SWIFT_CONNECT_TIMEOUT,
            retries=self._retry_count,
        )

    def _normalize_path(self, object_path):
        """
        No matter what inputs we get, we are going to return a path without a leading or trailing
        '/'.
        """
        if self._simple_path_concat:
            return (self._storage_path + object_path).rstrip("/")
        else:
            return os.path.join(self._storage_path, object_path).rstrip("/")

    def _get_object(self, path, chunk_size=None):
        path = self._normalize_path(path)
        try:
            _, obj = self._get_connection().get_object(
                self._swift_container, path, resp_chunk_size=chunk_size
            )
            return obj
        except ClientException as ex:
            logger.exception("Could not get object at path %s: %s", path, ex)
            raise IOError("Path %s not found" % path)

    def _put_object(
        self, path, content, chunk=None, content_type=None, content_encoding=None, headers=None
    ):
        # ReadableToIterable supports both file-like objects yielding str or bytes,
        # and will try utf-8 encode the result if it is a string.
        # The following assertion make sure that the content is either some bytes or
        # a file-like stream of bytes, for consistency across all storage implementations.
        assert isinstance(content, bytes) or issubclass(
            type(content), (IOBase, GeneratorFile, ReadableToIterable, filelike.BaseStreamFilelike)
        )

        path = self._normalize_path(path)
        headers = headers or {}

        if content_encoding is not None:
            headers["Content-Encoding"] = content_encoding

        is_filelike = hasattr(content, "read")
        if is_filelike:
            content = ReadableToIterable(content, md5=True)

        try:
            etag = self._get_connection().put_object(
                self._swift_container,
                path,
                content,
                chunk_size=chunk,
                content_type=content_type,
                headers=headers,
            )
        except ClientException:
            # We re-raise client exception here so that validation of config during setup can see
            # the client exception messages.
            raise

        # If we wrapped the content in a ReadableToIterable, compare its MD5 to the etag returned. If
        # they don't match, raise an IOError indicating a write failure.
        if is_filelike:
            if etag != content.get_md5sum():
                logger.error(
                    "Got mismatch in md5 etag for path %s: Expected %s, but server has %s",
                    path,
                    content.get_md5sum(),
                    etag,
                )
                raise IOError(
                    "upload verification failed for path {0}:"
                    "md5 mismatch, local {1} != remote {2}".format(path, content.get_md5sum(), etag)
                )

    def _head_object(self, path):
        path = self._normalize_path(path)
        try:
            return self._get_connection().head_object(self._swift_container, path)
        except ClientException as ce:
            if ce.http_status != 404:
                logger.exception("Could not head object at path %s: %s", path, ce)

            return None

    @lru_cache(maxsize=1)
    def _get_root_storage_url(self):
        """
        Returns the root storage URL for this Swift storage.

        Note that since this requires a call to Swift, we cache the result of this function call.
        """
        storage_url, _ = self._get_connection().get_auth()
        return storage_url

    def get_direct_download_url(
        self, object_path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        if requires_cors:
            return None

        # Reference: http://docs.openstack.org/juno/config-reference/content/object-storage-tempurl.html
        if not self._temp_url_key:
            return None

        # Retrieve the root storage URL for the connection.
        try:
            root_storage_url = self._get_root_storage_url()
        except ClientException:
            logger.exception("Got client exception when trying to load Swift auth")
            return None

        parsed_storage_url = urlparse(root_storage_url)
        scheme = parsed_storage_url.scheme
        path = parsed_storage_url.path.rstrip("/")
        hostname = parsed_storage_url.netloc

        object_path = self._normalize_path(object_path)

        # Generate the signed HMAC body.
        method = "HEAD" if head else "GET"
        expires = int(time() + expires_in)
        full_path = "%s/%s/%s" % (path, self._swift_container, object_path)

        hmac_body = "%s\n%s\n%s" % (method, expires, full_path)
        sig = hmac.new(
            self._temp_url_key.encode("utf-8"), hmac_body.encode("utf-8"), sha1
        ).hexdigest()

        surl = "{scheme}://{host}{full_path}?temp_url_sig={sig}&temp_url_expires={expires}"
        return surl.format(
            scheme=scheme, host=hostname, full_path=full_path, sig=sig, expires=expires
        )

    def validate(self, client):
        super(SwiftStorage, self).validate(client)

        if self._temp_url_key:
            # Generate a direct download URL.
            dd_url = self.get_direct_download_url("_verify")

            if not dd_url:
                raise Exception("Could not validate direct download URL; the token may be invalid.")

            # Try to retrieve the direct download URL.
            response = client.get(dd_url, timeout=2)
            if response.status_code != 200:
                logger.debug(
                    "Direct download failure: %s => %s with body %s",
                    dd_url,
                    response.status_code,
                    response.text,
                )

                msg = "Direct download URL failed with status code %s. Please check your temp-url-key."
                raise Exception(msg % response.status_code)

    def get_content(self, path):
        return self._get_object(path)

    def put_content(self, path, content):
        self._put_object(path, content)

    def stream_read(self, path):
        for data in self._get_object(path, self.buffer_size):
            if isinstance(data, int):
                yield data.to_bytes(1, sys.byteorder)
            else:
                yield data

    def stream_read_file(self, path):
        return GeneratorFile(self.stream_read(path))

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        self._put_object(
            path, fp, self.buffer_size, content_type=content_type, content_encoding=content_encoding
        )

    def exists(self, path):
        return bool(self._head_object(path))

    def remove(self, path):
        # Retrieve the object so we can see if it is segmented. If so, we'll delete its segments after
        # removing the object.
        try:
            headers = self._head_object(path)
        except ClientException as ex:
            logger.exception("Could not head for delete of path %s: %s", path, str(ex))
            raise IOError("Cannot delete path: %s" % path)

        logger.debug("Found headers for path %s to delete: %s", path, headers)

        # Delete the path itself.
        path = self._normalize_path(path)
        try:
            self._get_connection().delete_object(self._swift_container, path)
        except ClientException as ex:
            logger.exception("Could not delete path %s: %s", path, str(ex))
            raise IOError("Cannot delete path: %s" % path)

        # Delete the segments.
        object_manifest = headers.get("x-object-manifest", headers.get("X-Object-Manifest"))
        if object_manifest is not None:
            logger.debug("Found DLO for path %s: %s", path, object_manifest)

            # Remove the container name from the beginning.
            container_name, prefix_path = object_manifest.split("/", 1)
            if container_name != self._swift_container:
                logger.error(
                    "Expected container name %s, found path %s", self._swift_container, prefix_path
                )
                raise Exception("How did we end up with an invalid container name?")

            logger.debug("Loading Dynamic Large Object segments for path prefix %s", prefix_path)
            try:
                _, container_objects = self._get_connection().get_container(
                    self._swift_container, full_listing=True, prefix=prefix_path
                )
            except ClientException as ex:
                logger.exception(
                    "Could not load objects with prefix path %s: %s", prefix_path, str(ex)
                )
                raise IOError("Cannot load path: %s" % prefix_path)

            logger.debug(
                "Found Dynamic Large Object segments for path prefix %s: %s",
                prefix_path,
                len(container_objects),
            )
            for obj in container_objects:
                try:
                    logger.debug(
                        "Deleting Dynamic Large Object segment %s for path prefix %s",
                        obj["name"],
                        prefix_path,
                    )
                    self._get_connection().delete_object(self._swift_container, obj["name"])
                except ClientException as ex:
                    logger.exception(
                        "Could not delete object with path %s: %s", obj["name"], str(ex)
                    )
                    raise IOError("Cannot delete path: %s" % obj["name"])

    def _random_checksum(self, count):
        chars = string.ascii_uppercase + string.digits
        return "".join(SystemRandom().choice(chars) for _ in range(count))

    def get_checksum(self, path):
        headers = self._head_object(path)
        if not headers:
            raise IOError("Cannot lookup path: %s" % path)

        return headers.get("etag", "")[1:-1][:7] or self._random_checksum(7)

    @staticmethod
    def _segment_list_from_metadata(storage_metadata, key=_SEGMENTS_KEY):
        return [_PartUploadMetadata(*segment_args) for segment_args in storage_metadata[key]]

    def initiate_chunked_upload(self):
        random_uuid = str(uuid4())

        metadata = {
            _SEGMENTS_KEY: [],
            _EMPTY_SEGMENTS_KEY: [],
        }

        return random_uuid, metadata

    def stream_upload_chunk(self, uuid, offset, length, in_fp, storage_metadata, content_type=None):
        if length == 0:
            return 0, storage_metadata, None

        # Note: Swift limits segments in size, so we need to sub-divide chunks into segments
        # based on the configured maximum.
        total_bytes_written = 0
        upload_error = None
        read_until_end = length == filelike.READ_UNTIL_END

        while True:
            try:
                bytes_written, storage_metadata = self._stream_upload_segment(
                    uuid, offset, length, in_fp, storage_metadata, content_type
                )
            except IOError as ex:
                message = (
                    "Error writing to stream in stream_upload_chunk for uuid %s (offset %s"
                    + ", length %s, metadata: %s): %s"
                )
                logger.exception(message, uuid, offset, length, storage_metadata, ex)
                upload_error = ex
                break

            if not read_until_end:
                length = length - bytes_written

            offset = offset + bytes_written
            total_bytes_written = total_bytes_written + bytes_written

            if bytes_written == 0 or (not read_until_end and length <= 0):
                return total_bytes_written, storage_metadata, upload_error

        return total_bytes_written, storage_metadata, upload_error

    def _stream_upload_segment(self, uuid, offset, length, in_fp, storage_metadata, content_type):
        updated_metadata = copy.deepcopy(storage_metadata)
        segment_count = len(updated_metadata[_SEGMENTS_KEY])
        segment_path = "%s/%s/%s" % (_SEGMENT_DIRECTORY, uuid, "%09d" % segment_count)

        # Track the number of bytes read and if an explicit length is specified, limit the
        # file stream to that length.
        if length == filelike.READ_UNTIL_END:
            length = _MAXIMUM_SEGMENT_SIZE
        else:
            length = min(_MAXIMUM_SEGMENT_SIZE, length)

        # If retries are requested, then we need to allow the LimitingStream to seek() backward
        # on retries from within the Swift client.
        limiting_fp = filelike.LimitingStream(in_fp, length, allow_backward=self._retry_count > 0)

        # Write the segment to Swift.
        self.stream_write(segment_path, limiting_fp, content_type)

        # We are only going to track keys to which data was confirmed written.
        bytes_written = limiting_fp.tell()
        if bytes_written > 0:
            updated_metadata[_SEGMENTS_KEY].append(
                _PartUploadMetadata(segment_path, offset, bytes_written)
            )
        else:
            updated_metadata[_EMPTY_SEGMENTS_KEY].append(
                _PartUploadMetadata(segment_path, offset, bytes_written)
            )

        return bytes_written, updated_metadata

    def complete_chunked_upload(self, uuid, final_path, storage_metadata):
        """
        Complete the chunked upload and store the final results in the path indicated.

        Returns nothing.
        """
        # Check all potentially empty segments against the segments that were uploaded; if the path
        # is still empty, then we queue the segment to be deleted.
        if self._context.chunk_cleanup_queue is not None:
            nonempty_segments = SwiftStorage._segment_list_from_metadata(
                storage_metadata, key=_SEGMENTS_KEY
            )
            potentially_empty_segments = SwiftStorage._segment_list_from_metadata(
                storage_metadata, key=_EMPTY_SEGMENTS_KEY
            )

            nonempty_paths = set([segment.path for segment in nonempty_segments])
            for segment in potentially_empty_segments:
                if segment.path in nonempty_paths:
                    continue

                # Queue the chunk to be deleted, as it is empty and therefore unused.
                self._context.chunk_cleanup_queue.put(
                    ["segment/%s/%s" % (self._context.location, uuid)],
                    json.dumps(
                        {
                            "location": self._context.location,
                            "uuid": uuid,
                            "path": segment.path,
                        }
                    ),
                    available_after=_CHUNK_CLEANUP_DELAY,
                )

        # Finally, we write an empty file at the proper location with a X-Object-Manifest
        # header pointing to the prefix for the segments.
        segments_prefix_path = self._normalize_path("%s/%s" % (_SEGMENT_DIRECTORY, uuid))
        contained_segments_prefix_path = "%s/%s" % (self._swift_container, segments_prefix_path)

        self._put_object(
            final_path, b"", headers={"X-Object-Manifest": contained_segments_prefix_path}
        )

    def cancel_chunked_upload(self, uuid, storage_metadata):
        """
        Cancel the chunked upload and clean up any outstanding partially uploaded data.

        Returns nothing.
        """
        if not self._context.chunk_cleanup_queue:
            return

        segments = list(
            SwiftStorage._segment_list_from_metadata(storage_metadata, key=_SEGMENTS_KEY)
        )
        segments.extend(
            SwiftStorage._segment_list_from_metadata(storage_metadata, key=_EMPTY_SEGMENTS_KEY)
        )

        # Queue all the uploaded segments to be deleted.
        for segment in segments:
            # Queue the chunk to be deleted.
            self._context.chunk_cleanup_queue.put(
                ["segment/%s/%s" % (self._context.location, uuid)],
                json.dumps(
                    {
                        "location": self._context.location,
                        "uuid": uuid,
                        "path": segment.path,
                    }
                ),
                available_after=_CHUNK_CLEANUP_DELAY,
            )

    def copy_to(self, destination, path):
        if (
            self.__class__ == destination.__class__
            and self._swift_user == destination._swift_user
            and self._swift_password == destination._swift_password
            and self._auth_url == destination._auth_url
            and self._auth_version == destination._auth_version
        ):
            logger.debug(
                "Copying file from swift %s to swift %s via a Swift copy",
                self._swift_container,
                destination,
            )

            normalized_path = self._normalize_path(path)
            target = "/%s/%s" % (destination._swift_container, normalized_path)

            try:
                self._get_connection().copy_object(self._swift_container, normalized_path, target)
            except ClientException as ex:
                logger.exception("Could not swift copy path %s: %s", path, ex)
                raise IOError("Failed to swift copy path %s" % path)

            return

        # Fallback to a slower, default copy.
        logger.debug(
            "Copying file from swift %s to %s via a streamed copy",
            self._swift_container,
            destination,
        )
        with self.stream_read_file(path) as fp:
            destination.stream_write(path, fp)
