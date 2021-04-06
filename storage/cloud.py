import os
import logging
import copy

from collections import namedtuple
from datetime import datetime, timedelta
from io import BufferedIOBase, StringIO, BytesIO
from itertools import chain
from uuid import uuid4

import botocore.config
import botocore.exceptions
import boto3.session
from botocore.client import Config

from botocore.signers import CloudFrontSigner
from cachetools.func import lru_cache
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from prometheus_client import Counter

from util.registry import filelike
from storage.basestorage import BaseStorageV2


logger = logging.getLogger(__name__)


multipart_uploads_started = Counter(
    "quay_multipart_uploads_started_total",
    "number of multipart uploads to Quay storage that started",
)
multipart_uploads_completed = Counter(
    "quay_multipart_uploads_completed_total",
    "number of multipart uploads to Quay storage that completed",
)


_PartUpload = namedtuple("_PartUpload", ["part_number", "e_tag"])
_PartUploadMetadata = namedtuple("_PartUploadMetadata", ["path", "offset", "length"])
_CHUNKS_KEY = "chunks"


# This is for HEAD requests to check if a key exists.
# Since the HEAD request does not have a response body, boto3 uses the status code as error code
# Ref: https://github.com/boto/boto3/issues/2442
_MISSING_KEY_ERROR_CODES = ("NoSuchKey", "404")
_LIST_OBJECT_VERSIONS = {"v1": "list_objects", "v2": "list_objects_v2"}


def _build_endpoint_url(hostname, port=None, is_secure=True):
    """Normalize the formats from boto2 and boto3. """

    # If the scheme is not in the hostname, check if is_secure is set to set http or https as the scheme
    if not hostname.startswith("http://") and not hostname.startswith("https://"):
        hostname = "https://" + hostname if is_secure else "http://" + hostname

    # If port is set but not already part of the hostname
    if port and not hostname.split(":")[-1].strip(" /").isdigit():
        hostname = hostname + ":" + str(port)

    return hostname


class StreamReadKeyAsFile(BufferedIOBase):
    """
    Wrapper for botocore.StreamingBody

    NOTE: Moving from boto2 to boto3, the file-like interface implementation between bn both versions behave differently.
          In boto3, once the stream is out of data, it will keep returning an empty string until it is closed.
          In boto2, once the stream is out of data, it will return an empty string once, and subsequent read will start reading
          the stream from the beginning again (by making a new GET request, since it is server streaming the content
          (calling `close()` does not seem to have any effect). This wrapper provides a more consistent file-like interface and
          allows to check whether a key is closed or not.

          References:
          - https://github.com/boto/boto/blob/develop/boto/s3/key.py#L51 (boto2's "Key")
          - https://github.com/boto/botocore/blob/develop/botocore/response.py (boto3's "StreamingBody")
          - https://github.com/boto/boto3/issues/564
    """

    def __init__(self, key):
        self._key = key
        self._closed = False

    def read(self, amt=None):
        if self.closed:
            return None

        resp = self._key.read(amt)
        return resp

    def readable(self):
        return True

    @property
    def closed(self):
        return self._closed

    def close(self):
        self._closed = True
        self._key.close()


class _CloudStorage(BaseStorageV2):
    def __init__(
        self,
        context,
        connection_class,
        connect_kwargs,
        upload_params,
        storage_path,
        bucket_name,
        access_key=None,
        secret_key=None,
    ):
        super(_CloudStorage, self).__init__()

        self.minimum_chunk_size = 5 * 1024 * 1024
        self.maximum_chunk_size = None

        self._initialized = False
        self._bucket_name = bucket_name
        self._access_key = access_key
        self._secret_key = secret_key
        self._root_path = storage_path
        self._connection_class = connection_class
        self._upload_params = upload_params
        self._connect_kwargs = connect_kwargs
        self._cloud_conn = None
        self._cloud_bucket = None
        self._context = context
        self._list_object_version = _LIST_OBJECT_VERSIONS["v2"]

        self._session = self._connection_class(
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    def _initialize_cloud_conn(self):
        if not self._initialized:
            # Low-level client. Needed to generate presigned urls
            self._cloud_conn = self._session.client("s3", **self._connect_kwargs)
            self._cloud_bucket = self._session.resource("s3", **self._connect_kwargs).Bucket(
                self._bucket_name
            )
            # This will raise a ClientError if the bucket does ot exists.
            # We actually want an exception raised if the bucket does not exists (same as in boto2)
            self._cloud_conn.head_bucket(Bucket=self._bucket_name)
            self._initialized = True

    def _debug_key(self, obj):
        """
        Used for debugging only.
        """
        import types

        valid_debug_methods = [
            "copy",
            "copy_from",
            "delete",
            "download_file",
            "download_fileobj",
            "get",
            "get_available_subresources",
            "initiate_multipart_upload",
            "load",
            "put",
            "reload",
            "restore_object",
            "upload_file",
            "upload_fileobj",
        ]

        # Wraps the method to debug
        def debug_method_decorator(f):
            @wraps(f)
            def wrapper(self, *args, **kwargs):
                print("#" * 16)
                print(args)
                print(kwargs)
                print("#" * 16)
                return f(*args, **kwargs)

            return wrapper

        # Binds the new methods to the instance
        for method in valid_debug_methods:
            new_meth = debug_method_decorator(getattr(obj, method))
            obj.__setattr__(method, types.MethodType(new_meth, obj))

    def _init_path(self, path=None):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if path and path[0] == "/":
            return path[1:]
        return path

    def get_cloud_conn(self):
        self._initialize_cloud_conn()
        return self._cloud_conn

    def get_cloud_bucket(self):
        return self._cloud_bucket

    def get_content(self, path):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)
        try:
            return obj.get()["Body"].read()
        except botocore.exceptions.ClientError as s3r:
            # Raise an IOError in case the key was not found, to maintain the current
            # interface.
            if s3r.response["Error"]["Code"] in _MISSING_KEY_ERROR_CODES:
                raise IOError("No such key: '{0}'".format(path))

            raise

    def put_content(self, path, content):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)
        obj.put(Body=content, **self._upload_params)
        return path

    def get_supports_resumable_downloads(self):
        return True

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        self._initialize_cloud_conn()
        path = self._init_path(path)

        client_method = "get_object"
        if head:
            client_method = "head_object"

        return self.get_cloud_conn().generate_presigned_url(
            client_method,
            Params={"Bucket": self._bucket_name, "Key": path},
            ExpiresIn=expires_in,
        )

    def get_direct_upload_url(self, path, mime_type, requires_cors=True):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        return self.get_cloud_conn().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket_name,
                "Key": path,
                "ServerSideEncryption": "AES256",
                "ContentType": mime_type,
            },
            ExpiresIn=300,
        )

    def stream_read(self, path):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)
        try:
            obj.load()
        except botocore.exceptions.ClientError as s3r:
            if s3r.response["Error"]["Code"] in _MISSING_KEY_ERROR_CODES:
                raise IOError("No such key: '{0}'".format(path))
            raise

        buf = obj.get()["Body"]
        while True:
            data = buf.read(self.buffer_size)
            if not data:
                break
            yield data

    def stream_read_file(self, path):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)
        try:
            obj.load()
        except botocore.exceptions.ClientError as s3r:
            if s3r.response["Error"]["Code"] in _MISSING_KEY_ERROR_CODES:
                raise IOError("No such key: '{0}'".format(path))
            raise
        return StreamReadKeyAsFile(obj.get()["Body"])

    def __initiate_multipart_upload(self, path, content_type, content_encoding):
        # Minimum size of upload part size on S3 is 5MB
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)

        metadata = {}
        if content_type is not None:
            metadata["ContentType"] = content_type

        if content_encoding is not None:
            metadata["ContentEncoding"] = content_encoding

        metadata = {**metadata, **self._upload_params}

        multipart_uploads_started.inc()
        return obj.initiate_multipart_upload(**metadata)

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        """
        Writes the data found in the file-like stream to the given path.

        Raises an IOError if the write fails.
        """
        _, write_error = self._stream_write_internal(path, fp, content_type, content_encoding)
        if write_error is not None:
            logger.error("Error when trying to stream_write path `%s`: %s", path, write_error)
            raise IOError("Exception when trying to stream_write path")

    def _stream_write_internal(
        self,
        path,
        fp,
        content_type=None,
        content_encoding=None,
        cancel_on_error=True,
        size=filelike.READ_UNTIL_END,
    ):
        """
        Writes the data found in the file-like stream to the given path, with optional limit on
        size. Note that this method returns a *tuple* of (bytes_written, write_error) and should.

        *not* raise an exception (such as IOError) if a problem uploading occurred. ALWAYS check
        the returned tuple on calls to this method.
        """
        write_error = None

        try:
            mp = self.__initiate_multipart_upload(path, content_type, content_encoding)
        except botocore.exceptions.ClientError as s3r:
            logger.exception("Exception when initiating multipart upload")
            return 0, s3r

        # [_PartUpload]
        upload_parts = []

        num_part = 1
        total_bytes_written = 0
        while size == filelike.READ_UNTIL_END or total_bytes_written < size:
            bytes_to_copy = self.minimum_chunk_size
            if size != filelike.READ_UNTIL_END:
                # We never want to ask for more bytes than our caller has indicated to copy
                bytes_to_copy = min(bytes_to_copy, size - total_bytes_written)

            with BytesIO() as buf:
                try:
                    # Stage the bytes into the buffer for use with the multipart upload file API
                    bytes_staged = self.stream_write_to_fp(fp, buf, bytes_to_copy)

                    if bytes_staged == 0:
                        break

                    buf.seek(0)
                    part = mp.Part(num_part)
                    part_upload = part.upload(
                        Body=buf,
                        ContentLength=bytes_staged,
                    )
                    upload_parts.append(_PartUpload(num_part, part_upload["ETag"]))
                    total_bytes_written += bytes_staged
                    num_part += 1
                except (
                    botocore.exceptions.ClientError,
                    botocore.exceptions.ConnectionClosedError,
                    IOError,
                ) as e:
                    logger.warn(
                        "Error when writing to stream in stream_write_internal at path %s: %s",
                        path,
                        e,
                    )
                    write_error = e

                    multipart_uploads_completed.inc()

                    if cancel_on_error:
                        try:
                            mp.abort()
                        except (botocore.exceptions.ClientError, IOError):
                            logger.exception("Could not cancel upload")

                        return 0, write_error
                    else:
                        break

        if total_bytes_written > 0:
            multipart_uploads_completed.inc()
            self._perform_action_with_retry(
                mp.complete,
                MultipartUpload={
                    "Parts": [{"ETag": p.e_tag, "PartNumber": p.part_number} for p in upload_parts],
                },
            )

        return total_bytes_written, write_error

    def exists(self, path):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)
        try:
            obj.load()
        except botocore.exceptions.ClientError as s3r:
            if s3r.response["Error"]["Code"] in _MISSING_KEY_ERROR_CODES:
                return False
            raise
        return True

    def remove(self, path):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)
        try:
            obj.load()
            obj.delete()
            return
        except botocore.exceptions.ClientError as s3r:
            if not s3r.response["Error"]["Code"] in _MISSING_KEY_ERROR_CODES:
                raise
        # We assume it's a directory
        if not path.endswith("/"):
            path += "/"

        paginator = self.get_cloud_conn().get_paginator(self._list_object_version)
        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=path):
            for content in page.get("Contents", ()):
                obj = self.get_cloud_bucket().Object(content["Key"])
                obj.delete()

    def get_checksum(self, path):
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)
        try:
            obj.load()
        except botocore.exceptions.ClientError as s3r:
            if s3r.response["Error"]["Code"] in _MISSING_KEY_ERROR_CODES:
                raise IOError("No such key: '{0}'".format(path))
            raise

        return obj.e_tag[1:-1][:7]

    def copy_to(self, destination, path):
        """
        Copies the given path from this storage to the destination storage.
        """
        self._initialize_cloud_conn()

        # First try to copy directly via boto, but only if the storages are the
        # same type, with the same access information.
        if (
            self.__class__ == destination.__class__
            and self._access_key
            and self._secret_key
            and self._access_key == destination._access_key
            and self._secret_key == destination._secret_key
            and self._connect_kwargs == destination._connect_kwargs
        ):

            # Initialize the cloud connection on the destination as well.
            destination._initialize_cloud_conn()

            # Check the buckets for both the source and destination locations.
            if self._cloud_bucket is None:
                logger.error(
                    "Cloud bucket not found for location %s; Configuration is probably invalid!",
                    self._bucket_name,
                )
                return

            if destination._cloud_bucket is None:
                logger.error(
                    "Cloud bucket not found for location %s; Configuration is probably invalid!",
                    destination._bucket_name,
                )
                return

            # Perform the copy.
            logger.debug(
                "Copying file from %s to %s via a direct boto copy",
                self._cloud_bucket,
                destination._cloud_bucket,
            )

            source_path = self._init_path(path)
            source_obj = self.get_cloud_bucket().Object(source_path)

            dest_path = destination._init_path(path)
            dest_obj = destination.get_cloud_bucket().Object(dest_path)
            dest_obj.copy_from(CopySource={"Bucket": source_obj.bucket_name, "Key": source_obj.key})
            return

        # Fallback to a slower, default copy.
        logger.debug(
            "Copying file from %s to %s via a streamed copy", self._cloud_bucket, destination
        )
        with self.stream_read_file(path) as fp:
            destination.stream_write(path, fp)

    def _rel_upload_path(self, uuid):
        return "uploads/{0}".format(uuid)

    def initiate_chunked_upload(self):
        self._initialize_cloud_conn()
        random_uuid = str(uuid4())

        metadata = {
            _CHUNKS_KEY: [],
        }

        return random_uuid, metadata

    def stream_upload_chunk(self, uuid, offset, length, in_fp, storage_metadata, content_type=None):
        self._initialize_cloud_conn()

        # We are going to upload each chunk to a separate key
        chunk_path = self._rel_upload_path(str(uuid4()))
        bytes_written, write_error = self._stream_write_internal(
            chunk_path, in_fp, cancel_on_error=False, size=length, content_type=content_type
        )

        new_metadata = copy.deepcopy(storage_metadata)

        # We are only going to track keys to which data was confirmed written
        if bytes_written > 0:
            new_metadata[_CHUNKS_KEY].append(_PartUploadMetadata(chunk_path, offset, bytes_written))

        return bytes_written, new_metadata, write_error

    def _chunk_generator(self, chunk_list):
        for chunk in chunk_list:
            yield filelike.StreamSlice(self.stream_read_file(chunk.path), 0, chunk.length)

    @staticmethod
    def _chunk_list_from_metadata(storage_metadata):
        return [_PartUploadMetadata(*chunk_args) for chunk_args in storage_metadata[_CHUNKS_KEY]]

    def _client_side_chunk_join(self, final_path, chunk_list):
        # If there's only one chunk, just "move" (copy and delete) the key and call it a day.
        if len(chunk_list) == 1:
            chunk_path = self._init_path(chunk_list[0].path)
            abs_final_path = self._init_path(final_path)

            # Let the copy raise an exception if it fails.
            #
            # TODO(kleesc): copy_from() is used instead of copy, since the latter is a managed transfer which uses S3's
            #               multipart api, which GCS and Rados does not support. Going forward, we should try moving
            #               non-aws implementations to use library's with better support (e.g GCS supports its own version
            #               of parallel uploads).
            new_obj = self.get_cloud_bucket().Object(abs_final_path)
            new_obj.copy_from(CopySource={"Bucket": self._bucket_name, "Key": chunk_path})

            # Attempt to clean up the old chunk.
            try:
                self.get_cloud_bucket().Object(chunk_path).delete()
            except (botocore.exceptions.ClientError, IOError):
                # We failed to delete a chunk. This sucks, but we shouldn't fail the push.
                msg = "Failed to clean up chunk %s for move of %s"
                logger.exception(msg, chunk_path, abs_final_path)
        else:
            # Concatenate and write all the chunks as one key.
            concatenated = filelike.FilelikeStreamConcat(self._chunk_generator(chunk_list))
            self.stream_write(final_path, concatenated)

            # Attempt to clean up all the chunks.
            for chunk in chunk_list:
                try:
                    self.get_cloud_bucket().Object(chunk.path).delete()
                except (botocore.exceptions.ClientError, IOError):
                    # We failed to delete a chunk. This sucks, but we shouldn't fail the push.
                    msg = "Failed to clean up chunk %s for reupload of %s"
                    logger.exception(msg, chunk.path, final_path)

    @staticmethod
    def _perform_action_with_retry(action, *args, **kwargs):
        # Note: Sometimes Amazon S3 simply raises an internal error when trying to complete a
        # an action. The recommendation is to simply try calling the action again.
        for remaining_retries in range(2, -1, -1):
            try:
                return action(*args, **kwargs)
                break
            except botocore.exceptions.ClientError as s3re:
                if (
                    remaining_retries
                    and s3re.response["Error"]["HTTPStatusCode"] == 200
                    and s3re.response["Error"]["Code"] == "InternalError"
                ):
                    # Weird internal error case. Retry.
                    continue

                # Otherwise, raise it.
                logger.exception("Exception trying to perform action %s", action)
                raise s3re

    @staticmethod
    def _rechunk(chunk, max_chunk_size):
        """
        Rechunks the chunk list to meet maximum chunk size restrictions for the storage engine.
        """
        if max_chunk_size is None or chunk.length <= max_chunk_size:
            yield chunk
        else:
            newchunk_length = chunk.length // 2
            first_subchunk = _PartUploadMetadata(chunk.path, chunk.offset, newchunk_length)
            second_subchunk = _PartUploadMetadata(
                chunk.path, chunk.offset + newchunk_length, chunk.length - newchunk_length
            )
            for subchunk in chain(
                _CloudStorage._rechunk(first_subchunk, max_chunk_size),
                _CloudStorage._rechunk(second_subchunk, max_chunk_size),
            ):
                yield subchunk

    def complete_chunked_upload(self, uuid, final_path, storage_metadata, force_client_side=False):
        self._initialize_cloud_conn()
        chunk_list = self._chunk_list_from_metadata(storage_metadata)

        # Here is where things get interesting: we are going to try to assemble this server side
        # In order to be a candidate all parts (after offsets have been computed) must be at least 5MB
        server_side_assembly = False
        if not force_client_side:
            server_side_assembly = True
            for chunk_offset, chunk in enumerate(chunk_list):
                # If the chunk is both too small, and not the last chunk, we rule out server side assembly
                if chunk.length < self.minimum_chunk_size and (chunk_offset + 1) < len(chunk_list):
                    server_side_assembly = False
                    break

        if server_side_assembly:
            logger.debug("Performing server side assembly of multi-part upload for: %s", final_path)
            try:
                # Awesome, we can do this completely server side, now we have to start a new multipart
                # upload and use copy_part_from_key to set all of the chunks.
                mpu = self.__initiate_multipart_upload(
                    final_path, content_type=None, content_encoding=None
                )
                updated_chunks = chain.from_iterable(
                    [_CloudStorage._rechunk(c, self.maximum_chunk_size) for c in chunk_list]
                )

                # [_PartUpload]
                upload_parts = []
                for index, chunk in enumerate(updated_chunks):
                    abs_chunk_path = self._init_path(chunk.path)

                    part = mpu.Part(index + 1)
                    part_copy = part.copy_from(
                        CopySource={"Bucket": self.get_cloud_bucket().name, "Key": abs_chunk_path},
                        CopySourceRange="bytes=%s-%s"
                        % (chunk.offset, chunk.length + chunk.offset - 1),
                    )

                    part_copy = self._perform_action_with_retry(
                        mpu.Part(index + 1).copy_from,
                        CopySource={"Bucket": self.get_cloud_bucket().name, "Key": abs_chunk_path},
                        CopySourceRange="bytes=%s-%s"
                        % (chunk.offset, chunk.length + chunk.offset - 1),
                    )

                    upload_parts.append(_PartUpload(index + 1, part_copy["CopyPartResult"]["ETag"]))

                self._perform_action_with_retry(
                    mpu.complete,
                    MultipartUpload={
                        "Parts": [
                            {"ETag": p.e_tag, "PartNumber": p.part_number} for p in upload_parts
                        ]
                    },
                )
            except (botocore.exceptions.ClientError, IOError) as ioe:
                # Something bad happened, log it and then give up
                msg = "Exception when attempting server-side assembly for: %s"
                logger.exception(msg, final_path)
                mpu.abort()
                raise ioe

        else:
            # We are going to turn all of the server side objects into a single file-like stream, and
            # pass that to stream_write to chunk and upload the final object.
            self._client_side_chunk_join(final_path, chunk_list)

    def cancel_chunked_upload(self, uuid, storage_metadata):
        self._initialize_cloud_conn()

        # We have to go through and delete all of the uploaded chunks
        for chunk in self._chunk_list_from_metadata(storage_metadata):
            self.remove(chunk.path)


class S3Storage(_CloudStorage):
    def __init__(
        self,
        context,
        storage_path,
        s3_bucket,
        s3_access_key=None,
        s3_secret_key=None,
        # Boto2 backward compatible options (host excluding scheme or port)
        host=None,
        port=None,
        # Boto3 options (Full url including scheme anbd optionally port)
        endpoint_url=None,
    ):
        upload_params = {"ServerSideEncryption": "AES256"}
        connect_kwargs = {"config": Config(signature_version="s3v4")}
        if host or endpoint_url:
            connect_kwargs["endpoint_url"] = endpoint_url or _build_endpoint_url(
                host, port=port, is_secure=True
            )

        super(S3Storage, self).__init__(
            context,
            boto3.session.Session,
            connect_kwargs,
            upload_params,
            storage_path,
            s3_bucket,
            access_key=s3_access_key or None,
            secret_key=s3_secret_key or None,
        )

        self.maximum_chunk_size = 5 * 1024 * 1024 * 1024  # 5GB.

    def setup(self):
        self.get_cloud_bucket().Cors().put(
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedOrigins": ["*"],
                        "AllowedMethods": ["GET"],
                        "MaxAgeSeconds": 3000,
                        "AllowedHeaders": ["Authorization"],
                    },
                    {
                        "AllowedOrigins": ["*"],
                        "AllowedMethods": ["PUT"],
                        "MaxAgeSeconds": 3000,
                        "AllowedHeaders": ["Content-Type", "x-amz-acl", "origin"],
                    },
                ]
            }
        )


class GoogleCloudStorage(_CloudStorage):
    ENDPOINT_URL = "https://storage.googleapis.com"

    def __init__(self, context, storage_path, access_key, secret_key, bucket_name):
        # GCS does not support ListObjectV2
        self._list_object_version = _LIST_OBJECT_VERSIONS["v1"]
        upload_params = {}
        connect_kwargs = {"endpoint_url": GoogleCloudStorage.ENDPOINT_URL}
        super(GoogleCloudStorage, self).__init__(
            context,
            boto3.session.Session,
            connect_kwargs,
            upload_params,
            storage_path,
            bucket_name,
            access_key,
            secret_key,
        )

        # Workaround for setting GCS cors at runtime with boto
        cors_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <CorsConfig>
          <Cors>
            <Origins>
              <Origin>*</Origin>
            </Origins>
            <Methods>
              <Method>GET</Method>
              <Method>PUT</Method>
            </Methods>
            <ResponseHeaders>
              <ResponseHeader>Content-Type</ResponseHeader>
            </ResponseHeaders>
            <MaxAgeSec>3000</MaxAgeSec>
          </Cors>
        </CorsConfig>"""

        def update_cors_xml(request, **kwargs):
            request.data = cors_xml

        def validate_cors_xml(request, **kwargs):
            assert request.body == cors_xml

        self._session.events.register("request-created.s3.PutBucketCors", update_cors_xml)
        self._session.events.register("before-send.s3.PutBucketCors", validate_cors_xml)

    def setup(self):
        self._initialize_cloud_conn()
        self.get_cloud_bucket().Cors().put(
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedOrigins": ["*"],
                        "AllowedMethods": ["GET", "PUT"],
                        "MaxAgeSeconds": 3000,
                        "AllowedHeaders": ["Content-Type"],
                    },
                ]
            }
        )

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        return (
            super(GoogleCloudStorage, self)
            .get_direct_download_url(path, request_ip, expires_in, requires_cors, head)
            .replace("AWSAccessKeyId", "GoogleAccessId")
        )

    def _stream_write_internal(
        self,
        path,
        fp,
        content_type=None,
        content_encoding=None,
        cancel_on_error=True,
        size=filelike.READ_UNTIL_END,
    ):
        """
        Writes the data found in the file-like stream to the given path, with optional limit on
        size. Note that this method returns a *tuple* of (bytes_written, write_error) and should.

        *not* raise an exception (such as IOError) if a problem uploading occurred. ALWAYS check
        the returned tuple on calls to this method.
        """
        # Minimum size of upload part size on S3 is 5MB
        self._initialize_cloud_conn()
        path = self._init_path(path)
        obj = self.get_cloud_bucket().Object(path)

        extra_args = {}
        if content_type is not None:
            extra_args["ContentType"] = content_type

        if content_encoding is not None:
            extra_args["ContentEncoding"] = content_encoding

        if size != filelike.READ_UNTIL_END:
            fp = filelike.StreamSlice(fp, 0, size)

        with BytesIO() as buf:
            # Stage the bytes into the buffer for use with the multipart upload file API
            bytes_staged = self.stream_write_to_fp(fp, buf, size)
            buf.seek(0)

            # TODO figure out how to handle cancel_on_error=False
            try:
                obj.put(Body=buf, **extra_args)
            except Exception as ex:
                return 0, ex

        return bytes_staged, None

    def complete_chunked_upload(self, uuid, final_path, storage_metadata):
        self._initialize_cloud_conn()

        # Boto does not support GCS's multipart upload API because it differs from S3, so
        # we are forced to join it all locally and then reupload.
        # See https://github.com/boto/boto/issues/3355
        chunk_list = self._chunk_list_from_metadata(storage_metadata)
        self._client_side_chunk_join(final_path, chunk_list)


class RadosGWStorage(_CloudStorage):
    def __init__(
        self,
        context,
        hostname,
        is_secure,
        storage_path,
        access_key,
        secret_key,
        bucket_name,
        port=None,
    ):
        upload_params = {}
        connect_kwargs = {
            "endpoint_url": _build_endpoint_url(hostname, port=port, is_secure=is_secure),
        }

        super(RadosGWStorage, self).__init__(
            context,
            boto3.session.Session,
            connect_kwargs,
            upload_params,
            storage_path,
            bucket_name,
            access_key,
            secret_key,
        )

    # TODO remove when radosgw supports cors: http://tracker.ceph.com/issues/8718#change-38624
    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        if requires_cors:
            return None

        return super(RadosGWStorage, self).get_direct_download_url(
            path, request_ip, expires_in, requires_cors, head
        )

    # TODO remove when radosgw supports cors: http://tracker.ceph.com/issues/8718#change-38624
    def get_direct_upload_url(self, path, mime_type, requires_cors=True):
        if requires_cors:
            return None

        return super(RadosGWStorage, self).get_direct_upload_url(path, mime_type, requires_cors)

    def complete_chunked_upload(self, uuid, final_path, storage_metadata):
        self._initialize_cloud_conn()

        # RadosGW does not support multipart copying from keys, so we are forced to join
        # it all locally and then reupload.
        # See https://github.com/ceph/ceph/pull/5139
        chunk_list = self._chunk_list_from_metadata(storage_metadata)
        self._client_side_chunk_join(final_path, chunk_list)


class RHOCSStorage(RadosGWStorage):
    """
    RHOCSStorage implements storage explicitly via RHOCS.

    For now, this uses the same protocol as RadowsGW, but we create a distinct driver for future
    additional capabilities.
    """

    pass


class CloudFrontedS3Storage(S3Storage):
    """
    An S3Storage engine that redirects to CloudFront for all requests outside of AWS.
    """

    def __init__(
        self,
        context,
        cloudfront_distribution_domain,
        cloudfront_key_id,
        cloudfront_privatekey_filename,
        storage_path,
        s3_bucket,
        *args,
        **kwargs,
    ):
        super(CloudFrontedS3Storage, self).__init__(
            context, storage_path, s3_bucket, *args, **kwargs
        )

        self.cloudfront_distribution_domain = cloudfront_distribution_domain
        self.cloudfront_key_id = cloudfront_key_id
        self.cloudfront_privatekey = self._load_private_key(cloudfront_privatekey_filename)

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        # If CloudFront could not be loaded, fall back to normal S3.
        if self.cloudfront_privatekey is None or request_ip is None:
            return super(CloudFrontedS3Storage, self).get_direct_download_url(
                path, request_ip, expires_in, requires_cors, head
            )

        resolved_ip_info = None
        logger.debug('Got direct download request for path "%s" with IP "%s"', path, request_ip)

        # Lookup the IP address in our resolution table and determine whether it is under AWS.
        # If it is, then return an S3 signed URL, since we are in-network.
        resolved_ip_info = self._context.ip_resolver.resolve_ip(request_ip)
        logger.debug("Resolved IP information for IP %s: %s", request_ip, resolved_ip_info)
        if resolved_ip_info and resolved_ip_info.provider == "aws":
            return super(CloudFrontedS3Storage, self).get_direct_download_url(
                path, request_ip, expires_in, requires_cors, head
            )

        url = "https://%s/%s" % (self.cloudfront_distribution_domain, path)
        expire_date = datetime.now() + timedelta(seconds=expires_in)
        signer = self._get_cloudfront_signer()
        signed_url = signer.generate_presigned_url(url, date_less_than=expire_date)
        logger.debug(
            'Returning CloudFront URL for path "%s" with IP "%s": %s',
            path,
            resolved_ip_info,
            signed_url,
        )
        return signed_url

    @lru_cache(maxsize=1)
    def _get_cloudfront_signer(self):
        return CloudFrontSigner(self.cloudfront_key_id, self._get_rsa_signer())

    @lru_cache(maxsize=1)
    def _get_rsa_signer(self):
        private_key = self.cloudfront_privatekey

        def handler(message):
            return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

        return handler

    @lru_cache(maxsize=1)
    def _load_private_key(self, cloudfront_privatekey_filename):
        """
        Returns the private key, loaded from the config provider, used to sign direct download URLs
        to CloudFront.
        """
        if self._context.config_provider is None:
            return None

        with self._context.config_provider.get_volume_file(
            cloudfront_privatekey_filename,
            mode="rb",
        ) as key_file:
            return serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )
