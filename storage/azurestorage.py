"""
Azure storage driver.

Based on: https://docs.microsoft.com/en-us/azure/storage/blobs/storage-python-how-to-use-blob-storage
"""

import logging
import os
import io
import uuid
import copy
import time

from datetime import datetime, timedelta

from azure.common import AzureException
from azure.storage.blob import BlockBlobService, ContentSettings, BlobBlock, ContainerPermissions
from azure.storage.common.models import CorsRule

from storage.basestorage import BaseStorage
from util.registry.filelike import LimitingStream, READ_UNTIL_END

logger = logging.getLogger(__name__)

_COPY_POLL_SLEEP = 0.25  # seconds
_MAX_COPY_POLL_COUNT = 120  # _COPY_POLL_SLEEPs => 120s
_MAX_BLOCK_SIZE = 1024 * 1024 * 100  # 100MB
_BLOCKS_KEY = "blocks"
_CONTENT_TYPE_KEY = "content-type"


class AzureStorage(BaseStorage):
    def __init__(
        self,
        context,
        azure_container,
        storage_path,
        azure_account_name,
        azure_account_key=None,
        sas_token=None,
        connection_string=None,
        is_emulated=False,
        socket_timeout=20,
        request_timeout=20,
    ):
        super(AzureStorage, self).__init__()
        self._context = context
        self._storage_path = storage_path.lstrip("/")

        self._azure_account_name = azure_account_key
        self._azure_account_key = azure_account_key
        self._azure_sas_token = sas_token
        self._azure_container = azure_container
        self._azure_connection_string = connection_string
        self._request_timeout = request_timeout

        self._blob_service = BlockBlobService(
            account_name=azure_account_name,
            account_key=azure_account_key,
            sas_token=sas_token,
            is_emulated=is_emulated,
            connection_string=connection_string,
            socket_timeout=socket_timeout,
        )

    def _blob_name_from_path(self, object_path):
        if ".." in object_path:
            raise Exception("Relative paths are not allowed; found %s" % object_path)

        return os.path.join(self._storage_path, object_path).rstrip("/")

    def _upload_blob_path_from_uuid(self, uuid):
        return self._blob_name_from_path(self._upload_blob_name_from_uuid(uuid))

    def _upload_blob_name_from_uuid(self, uuid):
        return "uploads/{0}".format(uuid)

    def get_direct_download_url(
        self, object_path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        blob_name = self._blob_name_from_path(object_path)

        try:
            sas_token = self._blob_service.generate_blob_shared_access_signature(
                self._azure_container,
                blob_name,
                ContainerPermissions.READ,
                datetime.utcnow() + timedelta(seconds=expires_in),
            )

            blob_url = self._blob_service.make_blob_url(
                self._azure_container, blob_name, sas_token=sas_token
            )
        except AzureException:
            logger.exception(
                "Exception when trying to get direct download for path %s", object_path
            )
            raise IOError("Exception when trying to get direct download")

        return blob_url

    def validate(self, client):
        super(AzureStorage, self).validate(client)
        self._blob_service.get_container_properties(
            self._azure_container, timeout=self._request_timeout
        )

    def get_content(self, path):
        blob_name = self._blob_name_from_path(path)
        try:
            blob = self._blob_service.get_blob_to_bytes(self._azure_container, blob_name)
        except AzureException:
            logger.exception("Exception when trying to get path %s", path)
            raise IOError("Exception when trying to get path")

        return blob.content

    def put_content(self, path, content):
        blob_name = self._blob_name_from_path(path)
        try:
            self._blob_service.create_blob_from_bytes(self._azure_container, blob_name, content)
        except AzureException:
            logger.exception("Exception when trying to put path %s", path)
            raise IOError("Exception when trying to put path")

    def stream_read(self, path):
        with self.stream_read_file(path) as f:
            while True:
                buf = f.read(self.buffer_size)
                if not buf:
                    break
                yield buf

    def stream_read_file(self, path):
        blob_name = self._blob_name_from_path(path)

        try:
            output_stream = io.BytesIO()
            self._blob_service.get_blob_to_stream(self._azure_container, blob_name, output_stream)
            output_stream.seek(0)
        except AzureException:
            logger.exception("Exception when trying to stream_file_read path %s", path)
            raise IOError("Exception when trying to stream_file_read path")

        return output_stream

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        blob_name = self._blob_name_from_path(path)
        content_settings = ContentSettings(
            content_type=content_type, content_encoding=content_encoding,
        )

        try:
            self._blob_service.create_blob_from_stream(
                self._azure_container, blob_name, fp, content_settings=content_settings
            )
        except AzureException as ae:
            logger.exception("Exception when trying to stream_write path %s", path)
            raise IOError("Exception when trying to stream_write path", ae)

    def exists(self, path):
        blob_name = self._blob_name_from_path(path)
        try:
            return self._blob_service.exists(
                self._azure_container, blob_name, timeout=self._request_timeout
            )
        except AzureException:
            logger.exception("Exception when trying to check exists path %s", path)
            raise IOError("Exception when trying to check exists path")

    def remove(self, path):
        blob_name = self._blob_name_from_path(path)
        try:
            self._blob_service.delete_blob(self._azure_container, blob_name)
        except AzureException:
            logger.exception("Exception when trying to remove path %s", path)
            raise IOError("Exception when trying to remove path")

    def get_checksum(self, path):
        blob_name = self._blob_name_from_path(path)
        try:
            blob = self._blob_service.get_blob_properties(self._azure_container, blob_name)
        except AzureException:
            logger.exception("Exception when trying to get_checksum for path %s", path)
            raise IOError("Exception when trying to get_checksum path")
        return blob.properties.etag

    def initiate_chunked_upload(self):
        random_uuid = str(uuid.uuid4())
        metadata = {
            _BLOCKS_KEY: [],
            _CONTENT_TYPE_KEY: None,
        }
        return random_uuid, metadata

    def stream_upload_chunk(self, uuid, offset, length, in_fp, storage_metadata, content_type=None):
        if length == 0:
            return 0, storage_metadata, None

        upload_blob_path = self._upload_blob_path_from_uuid(uuid)
        new_metadata = copy.deepcopy(storage_metadata)

        total_bytes_written = 0

        while True:
            current_length = length - total_bytes_written
            max_length = (
                min(current_length, _MAX_BLOCK_SIZE)
                if length != READ_UNTIL_END
                else _MAX_BLOCK_SIZE
            )
            if max_length <= 0:
                break

            limited = LimitingStream(in_fp, max_length, seekable=False)

            # Note: Azure fails if a zero-length block is uploaded, so we read all the data here,
            # and, if there is none, terminate early.
            block_data = b""
            for chunk in iter(lambda: limited.read(4096), b""):
                block_data += chunk

            if len(block_data) == 0:
                break

            block_index = len(new_metadata[_BLOCKS_KEY])
            block_id = format(block_index, "05")
            new_metadata[_BLOCKS_KEY].append(block_id)

            try:
                self._blob_service.put_block(
                    self._azure_container,
                    upload_blob_path,
                    block_data,
                    block_id,
                    validate_content=True,
                )
            except AzureException as ae:
                logger.exception(
                    "Exception when trying to stream_upload_chunk block %s for %s", block_id, uuid
                )
                return total_bytes_written, new_metadata, ae

            bytes_written = len(block_data)
            total_bytes_written += bytes_written
            if bytes_written == 0 or bytes_written < max_length:
                break

        if content_type is not None:
            new_metadata[_CONTENT_TYPE_KEY] = content_type

        return total_bytes_written, new_metadata, None

    def complete_chunked_upload(self, uuid, final_path, storage_metadata):
        """
        Complete the chunked upload and store the final results in the path indicated.

        Returns nothing.
        """
        # Commit the blob's blocks.
        upload_blob_path = self._upload_blob_path_from_uuid(uuid)
        block_list = [BlobBlock(block_id) for block_id in storage_metadata[_BLOCKS_KEY]]

        try:
            self._blob_service.put_block_list(self._azure_container, upload_blob_path, block_list)
        except AzureException:
            logger.exception(
                "Exception when trying to put block list for path %s from upload %s",
                final_path,
                uuid,
            )
            raise IOError("Exception when trying to put block list")

        # Set the content type on the blob if applicable.
        if storage_metadata[_CONTENT_TYPE_KEY] is not None:
            content_settings = ContentSettings(content_type=storage_metadata[_CONTENT_TYPE_KEY])
            try:
                self._blob_service.set_blob_properties(
                    self._azure_container, upload_blob_path, content_settings=content_settings
                )
            except AzureException:
                logger.exception(
                    "Exception when trying to set blob properties for path %s", final_path
                )
                raise IOError("Exception when trying to set blob properties")

        # Copy the blob to its final location.
        upload_blob_name = self._upload_blob_name_from_uuid(uuid)
        copy_source_url = self.get_direct_download_url(upload_blob_name, expires_in=300)

        try:
            blob_name = self._blob_name_from_path(final_path)
            copy_prop = self._blob_service.copy_blob(
                self._azure_container, blob_name, copy_source_url
            )
        except AzureException:
            logger.exception(
                "Exception when trying to set copy uploaded blob %s to path %s", uuid, final_path
            )
            raise IOError("Exception when trying to copy uploaded blob")

        self._await_copy(self._azure_container, blob_name, copy_prop)

        # Delete the original blob.
        logger.debug("Deleting chunked upload %s at path %s", uuid, upload_blob_path)
        try:
            self._blob_service.delete_blob(self._azure_container, upload_blob_path)
        except AzureException:
            logger.exception("Exception when trying to set delete uploaded blob %s", uuid)
            raise IOError("Exception when trying to delete uploaded blob")

    def cancel_chunked_upload(self, uuid, storage_metadata):
        """
        Cancel the chunked upload and clean up any outstanding partially uploaded data.

        Returns nothing.
        """
        upload_blob_path = self._upload_blob_path_from_uuid(uuid)
        logger.debug("Canceling chunked upload %s at path %s", uuid, upload_blob_path)
        self._blob_service.delete_blob(self._azure_container, upload_blob_path)

    def _await_copy(self, container, blob_name, copy_prop):
        # Poll for copy completion.
        count = 0
        while copy_prop.status == "pending":
            props = self._blob_service.get_blob_properties(container, blob_name)
            copy_prop = props.properties.copy

            if copy_prop.status == "success":
                return

            if copy_prop.status == "failed" or copy_prop.status == "aborted":
                raise IOError(
                    "Copy of blob %s failed with status %s" % (blob_name, copy_prop.status)
                )

            count = count + 1
            if count > _MAX_COPY_POLL_COUNT:
                raise IOError("Timed out waiting for copy to complete")

            time.sleep(_COPY_POLL_SLEEP)

    def copy_to(self, destination, path):
        if self.__class__ == destination.__class__:
            logger.debug(
                "Starting copying file from Azure %s to Azure %s via an Azure copy",
                self._azure_container,
                destination,
            )
            blob_name = self._blob_name_from_path(path)
            copy_source_url = self.get_direct_download_url(path)
            copy_prop = self._blob_service.copy_blob(
                destination._azure_container, blob_name, copy_source_url
            )
            self._await_copy(destination._azure_container, blob_name, copy_prop)
            logger.debug(
                "Finished copying file from Azure %s to Azure %s via an Azure copy",
                self._azure_container,
                destination,
            )
            return

        # Fallback to a slower, default copy.
        logger.debug(
            "Copying file from Azure container %s to %s via a streamed copy",
            self._azure_container,
            destination,
        )
        with self.stream_read_file(path) as fp:
            destination.stream_write(path, fp)

    def setup(self):
        # From: https://docs.microsoft.com/en-us/rest/api/storageservices/cross-origin-resource-sharing--cors--support-for-the-azure-storage-services
        cors = [
            CorsRule(
                allowed_origins="*",
                allowed_methods=["GET", "PUT"],
                max_age_in_seconds=3000,
                exposed_headers=["x-ms-meta-*"],
                allowed_headers=[
                    "x-ms-meta-data*",
                    "x-ms-meta-target*",
                    "x-ms-meta-abc",
                    "Content-Type",
                ],
            )
        ]

        self._blob_service.set_blob_service_properties(cors=cors)
