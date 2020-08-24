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

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import (
    BlobServiceClient,
    BlobType,
    ContainerSasPermissions,
    ContentSettings,
    BlobBlock,
    CorsRule,
    generate_blob_sas,
)

from storage.basestorage import BaseStorage
from util.registry.filelike import LimitingStream, READ_UNTIL_END

logger = logging.getLogger(__name__)

_COPY_POLL_SLEEP = 0.25  # seconds
_MAX_COPY_POLL_COUNT = 120  # _COPY_POLL_SLEEPs => 120s
_API_VERSION_LIMITS = {
    "2016-05-31": (datetime.strptime("2016-05-31", "%Y-%m-%d"), 1024 * 1024 * 4),  # 4MiB
    "2019-07-07": (datetime.strptime("2019-07-07", "%Y-%m-%d"), 1024 * 1024 * 100),  # 100MiB
    "2019-12-12": (datetime.strptime("2019-12-12", "%Y-%m-%d"), 1024 * 1024 * 1000 * 4),  # 4000MiB
}
_BLOCKS_KEY = "blocks"
_CONTENT_TYPE_KEY = "content-type"


AZURE_STORAGE_URL_STRING = "https://{}.blob.core.windows.net"


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
    ):
        super(AzureStorage, self).__init__()
        self._context = context
        self._storage_path = storage_path.lstrip("/")

        self._azure_account_name = azure_account_name
        self._azure_account_key = azure_account_key
        self._azure_sas_token = sas_token
        self._azure_container = azure_container
        self._azure_connection_string = connection_string

        self._blob_service_client = BlobServiceClient(
            AZURE_STORAGE_URL_STRING.format(self._azure_account_name),
            credential=self._azure_account_key,
        )

        # https://docs.microsoft.com/en-us/rest/api/storageservices/understanding-block-blobs--append-blobs--and-page-blobs
        api_version = self._blob_service_client.api_version
        api_version_dt = datetime.strptime(api_version, "%Y-%m-%d")
        if api_version_dt < _API_VERSION_LIMITS["2016-05-31"][0]:
            self._max_block_size = _API_VERSION_LIMITS["2016-05-31"][1]
        elif api_version_dt <= _API_VERSION_LIMITS["2019-07-07"][0]:
            self._max_block_size = _API_VERSION_LIMITS["2019-07-07"][1]
        elif api_version_dt >= _API_VERSION_LIMITS["2019-12-12"][0]:
            self._max_block_size = _API_VERSION_LIMITS["2019-12-12"][1]
        else:
            raise Exception("Unknown Azure api version %s" % api_version)

    def _blob_name_from_path(self, object_path):
        if ".." in object_path:
            raise Exception("Relative paths are not allowed; found %s" % object_path)

        return os.path.join(self._storage_path, object_path).rstrip("/")

    def _upload_blob_path_from_uuid(self, uuid):
        return self._blob_name_from_path(self._upload_blob_name_from_uuid(uuid))

    def _upload_blob_name_from_uuid(self, uuid):
        return "uploads/{0}".format(uuid)

    def _blob(self, blob_name):
        return self._blob_service_client.get_blob_client(self._azure_container, blob_name)

    @property
    def _container(self):
        return self._blob_service_client.get_container_client(self._azure_container)

    def get_direct_download_url(
        self, object_path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        blob_name = self._blob_name_from_path(object_path)

        try:
            sas_token = generate_blob_sas(
                self._azure_account_name,
                self._azure_container,
                blob_name,
                account_key=self._azure_account_key,
                permission=ContainerSasPermissions.from_string("r"),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in),
            )

            blob_url = "{}?{}".format(self._blob(blob_name).url, sas_token)

        except AzureError:
            logger.exception(
                "Exception when trying to get direct download for path %s", object_path
            )
            raise IOError("Exception when trying to get direct download")

        return blob_url

    def validate(self, client):
        super(AzureStorage, self).validate(client)

    def get_content(self, path):
        blob_name = self._blob_name_from_path(path)
        try:
            blob_stream = self._blob(blob_name).download_blob()
        except AzureError:
            logger.exception("Exception when trying to get path %s", path)
            raise IOError("Exception when trying to get path")

        return blob_stream.content_as_bytes()

    def put_content(self, path, content):
        blob_name = self._blob_name_from_path(path)
        try:
            self._blob(blob_name).upload_blob(content, blob_type=BlobType.BlockBlob, overwrite=True)
        except AzureError:
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
            self._blob(blob_name).download_blob().download_to_stream(output_stream)
            output_stream.seek(0)
        except AzureError:
            logger.exception("Exception when trying to stream_file_read path %s", path)
            raise IOError("Exception when trying to stream_file_read path")

        return output_stream

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        blob_name = self._blob_name_from_path(path)
        content_settings = ContentSettings(
            content_type=content_type, content_encoding=content_encoding,
        )

        try:
            self._blob(blob_name).upload_blob(fp, content_settings=content_settings, overwrite=True)
        except AzureError as ae:
            logger.exception("Exception when trying to stream_write path %s", path)
            raise IOError("Exception when trying to stream_write path", ae)

    def exists(self, path):
        blob_name = self._blob_name_from_path(path)

        try:
            self._blob(blob_name).get_blob_properties()
        except ResourceNotFoundError:
            return False
        except AzureError:
            logger.exception("Exception when trying to check exists path %s", path)
            raise IOError("Exception when trying to check exists path")

        return True

    def remove(self, path):
        blob_name = self._blob_name_from_path(path)
        try:
            self._blob(blob_name).delete_blob()
        except AzureError:
            logger.exception("Exception when trying to remove path %s", path)
            raise IOError("Exception when trying to remove path")

    def get_checksum(self, path):
        blob_name = self._blob_name_from_path(path)
        try:
            blob_properties = self._blob(blob_name).get_blob_properties()
        except AzureError:
            logger.exception("Exception when trying to get_checksum for path %s", path)
            raise IOError("Exception when trying to get_checksum path")
        return blob_properties.etag

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
                min(current_length, self._max_block_size)
                if length != READ_UNTIL_END
                else self._max_block_size
            )
            if max_length <= 0:
                break

            limited = LimitingStream(in_fp, max_length, seekable=False)

            # Note: Azure fails if a zero-length block is uploaded, so we read all the data here,
            # and, if there is none, terminate early.
            block_data = b""
            for chunk in iter(lambda: limited.read(31457280), b""):
                block_data += chunk

            if len(block_data) == 0:
                break

            block_index = len(new_metadata[_BLOCKS_KEY])
            block_id = format(block_index, "05")
            new_metadata[_BLOCKS_KEY].append(block_id)

            try:
                self._blob(upload_blob_path).stage_block(
                    block_id, block_data, validate_content=True
                )
            except AzureError as ae:
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
        upload_blob_name = self._upload_blob_name_from_uuid(uuid)  # upload/<uuid>
        upload_blob_path = self._upload_blob_path_from_uuid(uuid)  # storage/path/upload/<uuid>
        block_list = [BlobBlock(block_id) for block_id in storage_metadata[_BLOCKS_KEY]]

        try:
            if storage_metadata[_CONTENT_TYPE_KEY] is not None:
                content_settings = ContentSettings(content_type=storage_metadata[_CONTENT_TYPE_KEY])
                self._blob(upload_blob_path).commit_block_list(
                    block_list, content_settings=content_settings
                )
            else:
                self._blob(upload_blob_path).commit_block_list(block_list)
        except AzureError:
            logger.exception(
                "Exception when trying to put block list for path %s from upload %s",
                final_path,
                uuid,
            )
            raise IOError("Exception when trying to put block list")

        # Copy the blob to its final location.
        upload_blob_name = self._upload_blob_name_from_uuid(uuid)
        copy_source_url = self.get_direct_download_url(upload_blob_name, expires_in=300)

        try:
            final_blob_name = self._blob_name_from_path(final_path)
            cp = self._blob(final_blob_name).start_copy_from_url(copy_source_url)
        except AzureError:
            logger.exception(
                "Exception when trying to set copy uploaded blob %s to path %s", uuid, final_path
            )
            raise IOError("Exception when trying to copy uploaded blob")

        self._await_copy(final_blob_name)

        # Delete the original blob.
        logger.debug("Deleting chunked upload %s at path %s", uuid, upload_blob_path)
        try:
            self._blob(upload_blob_path).delete_blob()
        except AzureError:
            logger.exception("Exception when trying to set delete uploaded blob %s", uuid)
            raise IOError("Exception when trying to delete uploaded blob")

    def cancel_chunked_upload(self, uuid, storage_metadata):
        """
        Cancel the chunked upload and clean up any outstanding partially uploaded data.

        Returns nothing.
        """
        upload_blob_path = self._upload_blob_path_from_uuid(uuid)
        logger.debug("Canceling chunked upload %s at path %s", uuid, upload_blob_path)
        try:
            self._blob(upload_blob_path).delete_blob()
        except ResourceNotFoundError:
            pass

    def _await_copy(self, blob_name):
        # Poll for copy completion.
        blob = self._blob(blob_name)
        copy_prop = blob.get_blob_properties().copy

        count = 0
        while copy_prop.status == "pending":
            props = blob.get_blob_properties()
            copy_prop = props.copy

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
                destination._azure_container,
            )
            copy_source_url = self.get_direct_download_url(path)
            blob_name = destination._blob_name_from_path(path)
            dest_blob = destination._blob(blob_name)

            destination._blob(blob_name).start_copy_from_url(copy_source_url)
            destination._await_copy(blob_name)
            logger.debug(
                "Finished copying file from Azure %s to Azure %s via an Azure copy",
                self._azure_container,
                destination._azure_container,
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

        self._blob_service_client.set_service_properties(cors=cors)
