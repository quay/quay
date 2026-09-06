import base64
import datetime
import email.utils
import io
import os.path
from contextlib import contextmanager
from datetime import timedelta
from hashlib import md5
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from xml.dom import minidom

import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobClient, BlobServiceClient
from freezegun import freeze_time
from httmock import HTTMock, urlmatch

from storage.azurestorage import AZURE_STORAGE_URL_STRING, AzureStorage

_TEST_LOG_PATH = "exportedactionlogs/"
import hashlib
import uuid


@contextmanager
def fake_azure_storage(files=None):
    container_name = "somecontainer"
    account_name = "someaccount"
    account_key = "somekey"
    storage_path = ""

    service = BlobServiceClient(AZURE_STORAGE_URL_STRING["global"].format("someaccount"))
    endpoint = service.primary_hostname
    files = files if files is not None else {}

    container_prefix = os.path.join("/" + container_name, storage_path).rstrip("/")

    @urlmatch(netloc=endpoint[0], path=container_prefix + "$")
    def get_container(url, request):
        query_params = parse_qs(url.query)

        if query_params.get("comp") == ["list"] and query_params.get("restype") == ["container"]:
            prefix = query_params.get("prefix", [""])[0]
            blobs_xml = ""

            for filename, file_info in files.items():
                if filename.startswith(prefix) and isinstance(file_info, dict):
                    last_modified = file_info.get(
                        "last_modified", email.utils.formatdate(usegmt=True)
                    )
                    blobs_xml += f"""<Blob><Name>{filename}</Name><Properties>
                        <Last-Modified>{last_modified}</Last-Modified>
                        <Etag>"etag"</Etag><Content-Length>0</Content-Length>
                        <BlobType>BlockBlob</BlobType>
                        <LeaseStatus>unlocked</LeaseStatus>
                        <LeaseState>available</LeaseState>
                        </Properties></Blob>"""

            xml = (
                f'<?xml version="1.0" encoding="utf-8"?>'
                f'<EnumerationResults ServiceEndpoint="{AZURE_STORAGE_URL_STRING["global"].format(account_name)}/" ContainerName="{container_name}">'
                f"<Prefix>{prefix}</Prefix>"
                f"<Blobs>{blobs_xml}</Blobs>"
                f"<NextMarker />"
                f"</EnumerationResults>"
            )
            return {
                "status_code": 200,
                "content": xml,
                "headers": {"Content-Type": "application/xml"},
            }

        return {"status_code": 200, "content": "{}"}

    @urlmatch(netloc=endpoint[0], path=container_prefix + "/.+")
    def container_file(url, request):
        filename = url.path[len(container_prefix) + 1 :]

        if request.method == "GET":
            return {
                "status_code": 200 if filename in files else 404,
                "headers": {
                    "ETag": "foobar",
                    "Last-Modified": (
                        files[filename].get("last_modified", "") if filename in files else ""
                    ),
                },
                "content": files[filename]["content"] if filename in files else "",
            }

        if request.method == "HEAD":
            return {
                "status_code": 200 if filename in files else 404,
                "headers": (
                    {
                        "ETag": "foobar",
                        "Last-Modified": (
                            files[filename].get("last_modified", "") if filename in files else ""
                        ),
                    }
                    if filename in files
                    else {"x-ms-error-code": "ResourceNotFound"}
                ),
                "content": "",
            }

        if request.method == "DELETE":
            files.pop(filename)
            return {
                "status_code": 202,
            }

        if request.method == "PUT":
            query_params = parse_qs(url.query)

            upload_time = email.utils.formatdate(usegmt=True)

            if query_params.get("comp") == ["properties"]:
                if filename in files:
                    files[filename]["last-modified"] = upload_time

                    return {
                        "status_code": 201,
                        "content": "{}",
                        "headers": {
                            "x-ms-server-encrypted": "false",
                            "Last-Modified": upload_time,
                        },
                    }

            if query_params.get("comp") == ["block"]:
                block_id = query_params["blockid"][0]
                if filename not in files:
                    files[filename] = {"content": b"", "last_modified": upload_time}

                body_content = (
                    request.body.read() if hasattr(request.body, "read") else request.body
                )
                files[filename][block_id] = body_content

                return {
                    "status_code": 201,
                    "content": "{}",
                    "headers": {
                        "Content-MD5": base64.b64encode(
                            md5(files[filename][block_id]).digest()
                        ).decode("ascii"),
                        "ETag": "foo",
                        "x-ms-request-server-encrypted": "false",
                        "last-modified": upload_time,
                    },
                }

            if query_params.get("comp") == ["blocklist"]:
                parsed = minidom.parseString(request.body)
                latest = parsed.getElementsByTagName("Latest")
                combined = []
                for latest_block in latest:
                    combined.append(files[filename][latest_block.childNodes[0].data])

                files[filename]["content"] = b"".join(combined)
                files[filename]["last_modified"] = upload_time

                return {
                    "status_code": 201,
                    "content": "{}",
                    "headers": {
                        "Content-MD5": base64.b64encode(
                            md5(files[filename]["content"]).digest()
                        ).decode("ascii"),
                        "ETag": "foo",
                        "x-ms-request-server-encrypted": "false",
                        "last-modified": upload_time,
                    },
                }

            if request.headers.get("x-ms-copy-source"):
                copy_source = request.headers["x-ms-copy-source"]
                print("DEBUG REQUEST SOURCE:", copy_source)
                copy_path = urlparse(copy_source).path[len(container_prefix) + 1 :]

                files[filename] = {
                    "content": files[copy_path]["content"],
                    "last_modified": upload_time,
                }

                return {
                    "status_code": 202,
                    "content": "",
                    "headers": {
                        "x-ms-request-server-encrypted": "false",
                        "x-ms-copy-status": "success",
                        "last-modified": upload_time,
                    },
                }

            files[filename] = {
                "content": request.body,
                "last_modified": upload_time,
            }

            return {
                "status_code": 201,
                "content": "{}",
                "headers": {
                    "Content-MD5": base64.b64encode(
                        md5(
                            request.body
                            if isinstance(request.body, bytes)
                            else request.body.encode()
                        ).digest()
                    ).decode("ascii"),
                    "ETag": "foo",
                    "x-ms-request-server-encrypted": "false",
                    "last-modified": upload_time,
                },
            }

        return {"status_code": 405, "content": ""}

    @urlmatch(netloc=endpoint[0], path=".+")
    def catchall(url, request):
        return {"status_code": 405, "content": ""}

    with HTTMock(get_container, container_file, catchall):
        yield AzureStorage(None, container_name, storage_path, account_name)


def test_validate():
    with fake_azure_storage() as s:
        s.validate(None)


def test_basics():
    with fake_azure_storage() as s:
        s.put_content("hello", b"hello world")
        assert s.exists("hello")
        assert s.get_content("hello") == b"hello world"
        assert s.get_checksum("hello")
        assert b"".join(list(s.stream_read("hello"))) == b"hello world"
        assert s.stream_read_file("hello").read() == b"hello world"

        s.remove("hello")
        assert not s.exists("hello")


def test_does_not_exist():
    with fake_azure_storage() as s:
        assert not s.exists("hello")

        with pytest.raises(IOError):
            s.get_content("hello")

        with pytest.raises(IOError):
            s.get_checksum("hello")

        with pytest.raises(IOError):
            list(s.stream_read("hello"))

        with pytest.raises(IOError):
            s.stream_read_file("hello")


def test_stream_write():
    fp = io.BytesIO()
    fp.write(b"hello world!")
    fp.seek(0)

    with fake_azure_storage() as s:
        s.stream_write("hello", fp)

        assert s.get_content("hello") == b"hello world!"


@pytest.mark.parametrize(
    "chunk_size",
    [
        (1),
        (5),
        (10),
    ],
)
def test_chunked_uploading(chunk_size):
    with (
        fake_azure_storage() as s,
        patch(
            "storage.azurestorage.generate_blob_sas",
            return_value="se=2020-08-18T18%3A24%3A36Z&sp=r&sv=2019-12-12&sr=b&sig=SOMESIG",
        ),
    ):
        string_data = b"hello world!"
        chunks = [
            string_data[index : index + chunk_size]
            for index in range(0, len(string_data), chunk_size)
        ]

        uuid, metadata = s.initiate_chunked_upload()
        start_index = 0

        for chunk in chunks:
            fp = io.BytesIO()
            fp.write(chunk)
            fp.seek(0)

            total_bytes_written, metadata, error = s.stream_upload_chunk(
                uuid, start_index, -1, fp, metadata
            )
            assert total_bytes_written == len(chunk)
            assert metadata
            assert not error

            start_index += total_bytes_written

        s.complete_chunked_upload(uuid, "chunked", metadata)
        assert s.get_content("chunked") == string_data


def test_get_direct_download_url():
    with fake_azure_storage() as s:
        with patch(
            "storage.azurestorage.generate_blob_sas",
            return_value="se=2020-08-18T18%3A24%3A36Z&sp=r&sv=2019-12-12&sr=b&sig=SOMESIG",
        ):
            s.put_content("hello", b"world")
            assert "sig" in s.get_direct_download_url("hello")


def test_copy_to():
    files = {}

    with fake_azure_storage(files=files) as s:
        s.put_content("hello", b"hello world")
        with (
            fake_azure_storage(files=files) as s2,
            patch(
                "storage.azurestorage.generate_blob_sas",
                return_value="se=2020-08-18T18%3A24%3A36Z&sp=r&sv=2019-12-12&sr=b&sig=SOMESIG",
            ),
        ):
            s.copy_to(s2, "hello")
            assert s2.exists("hello")


def test_cleanup_of_orphaned_export_log_files_successful():
    """
    Verifies that the worker can clean up orphaned exported log files.
    """
    with fake_azure_storage() as storage_engine:
        now = datetime.datetime.now(datetime.timezone.utc)
        storage_engine._storage_path = ""

        payload = b'{"logs": []}'
        logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
        upload_key = f"{_TEST_LOG_PATH}{logfile}"

        # put blob into the container
        with freeze_time(now):
            storage_engine._container.upload_blob(name=upload_key, data=payload)

        # attempt to clean
        with freeze_time(now + timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

        # list all container content on that specific path to ensure that the file was removed
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=_TEST_LOG_PATH)
        )
        remaining_keys = [blob.name for blob in remaining_blobs]

        assert upload_key not in remaining_keys


def test_export_log_cleanup_does_not_touch_user_files():
    """
    Verifies that other files in the same path are not picked up by the
    cleanup worker.
    """
    with fake_azure_storage() as storage_engine:
        now = datetime.datetime.now(datetime.timezone.utc)
        storage_engine._storage_path = ""

        payload1 = b'{"logs": []}'
        payload2 = b"Hello world!!!"

        logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
        upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
        userfile = "hello.txt"
        upload_key_userfile = f"{_TEST_LOG_PATH}{userfile}"

        # put both blobs in the container
        with freeze_time(now):
            storage_engine._container.upload_blob(name=upload_key_logfile, data=payload1)
            storage_engine._container.upload_blob(name=upload_key_userfile, data=payload2)

        # attempt to clean
        with freeze_time(now + timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

        # list all content under the specified prefix
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=_TEST_LOG_PATH)
        )
        remaining_keys = [blob.name for blob in remaining_blobs]

        assert upload_key_logfile not in remaining_keys
        assert upload_key_userfile in remaining_keys


def test_export_log_cleanup_doesnt_touch_other_paths():
    """
    Verifies that all other paths other than the log path are untouched by the
    cleanup worker.
    """
    with fake_azure_storage() as storage_engine:
        now = datetime.datetime.now(datetime.timezone.utc)
        storage_engine._storage_path = ""

        payload1 = b'{"logs": []}'
        payload2 = b"Hello world!!!"

        logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
        upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
        userfile = "hello.txt"
        upload_key_userfile = f"different/path/altogether/{userfile}"

        # put both blobs in the container
        with freeze_time(now):
            storage_engine._container.upload_blob(name=upload_key_logfile, data=payload1)
            storage_engine._container.upload_blob(name=upload_key_userfile, data=payload2)

        # attempt to clean
        with freeze_time(now + timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

        # list all content in the container
        remaining_blobs = list(storage_engine._container.list_blobs())
        remaining_keys = [blob.name for blob in remaining_blobs]

        assert upload_key_logfile not in remaining_keys
        assert upload_key_userfile in remaining_keys


def test_export_log_cleanup_doesnt_pick_up_files_that_are_inside_the_timedelta():
    """
    Verifies that we only delete files that are older than 1 hour and not any other files that are in the same path
    """
    with fake_azure_storage() as storage_engine:
        now = datetime.datetime.now(datetime.timezone.utc)
        storage_engine._storage_path = ""

        # create a list of files
        keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for i in range(5)]
        for i, k in enumerate(keys):
            payload = os.urandom(1024)
            with freeze_time(now + timedelta(hours=i)):
                storage_engine._container.upload_blob(name=k, data=payload)

        # list all content on that specific path and confirm that there are 5 blobs present
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=_TEST_LOG_PATH)
        )
        assert len(remaining_blobs) == 5

        # add 6th file only 30 minutes *after* the last file was uploaded
        final_key = f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
        payload = os.urandom(1024)
        with freeze_time(now + timedelta(hours=5.5)):
            storage_engine._container.upload_blob(name=final_key, data=payload)

        # at 6th hour do cleanup
        with freeze_time(
            now + timedelta(hours=6)
        ):  # Changed from 5 to 6 so it occurs after the 5.5h upload
            storage_engine.clean_exported_action_logs(timedelta(hours=1), _TEST_LOG_PATH)

        # only one file should remain
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=_TEST_LOG_PATH)
        )
        assert len(remaining_blobs) == 1
        remaining_keys = [blob.name for blob in remaining_blobs]
        assert final_key in remaining_keys


def test_export_log_cleanup_correctly_identifies_storage_path():
    """
    Verifies that the root path (defined through storage_path in the driver) is
    properly taken into account during wiping.
    """
    with fake_azure_storage() as storage_engine:
        now = datetime.datetime.now(datetime.timezone.utc)
        storage_engine._storage_path = "datastorage/registry"

        # create a list of files
        keys = [
            f"datastorage/registry/{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
            for i in range(5)
        ]
        for i, k in enumerate(keys):
            payload = os.urandom(1024)
            with freeze_time(now):
                storage_engine._container.upload_blob(name=k, data=payload)

        # add a specific file with a SHA digest to mimick real storage
        payload = os.urandom(1024)
        filename = hashlib.sha256(payload).hexdigest()
        final_key = f"datastorage/registry/sha256/{filename[:2]}/{filename}"

        # upload the final key
        with freeze_time(now):
            storage_engine._container.upload_blob(name=final_key, data=payload)

        # verify all blobs are uploaded properly and are visible
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=storage_engine._storage_path)
        )
        assert len(remaining_blobs) == 6

        # attempt to clean up expired logs
        with freeze_time(now + timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

        # only one file should remain
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=storage_engine._storage_path)
        )
        assert len(remaining_blobs) == 1
        remaining_keys = [blob.name for blob in remaining_blobs]
        assert final_key in remaining_keys


def test_export_log_cleanup_does_not_return_error_on_empty_directory():
    """
    Verifies that cleanup does not error when nothing is cleaned. Simple regression test.
    """
    with fake_azure_storage() as storage_engine:
        now = datetime.datetime.now(datetime.timezone.utc)
        storage_engine._storage_path = "datastorage/registry"

        # add a specific file with a SHA digest to mimick real storage
        payload = os.urandom(1024)
        filename = hashlib.sha256(payload).hexdigest()
        keyname = f"datastorage/registry/sha256/{filename[:2]}/{filename}"

        # upload the key
        with freeze_time(now):
            storage_engine._container.upload_blob(name=keyname, data=payload)

        # assert that we only have one key under datastorage/registry path
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=storage_engine._storage_path)
        )
        assert len(remaining_blobs) == 1

        # call cleanup on real directory
        with freeze_time(now + timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

        # assert that we still have only one file under storage path
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=storage_engine._storage_path)
        )
        assert len(remaining_blobs) == 1


def test_cleanup_of_expired_logs_gracefully_handles_errors():
    """
    Asserts that the ResourceNotFoundError exception is caught by the code and not raised.
    """
    with fake_azure_storage() as storage_engine:
        err = ResourceNotFoundError("The specified blob does not exist.")

        # Reference to the original delete method
        orig_delete_blob = BlobClient.delete_blob

        # create a list of files
        keys = [
            f"datastorage/registry/{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
            for i in range(5)
        ]

        def mock_delete_blob(self, *args, **kwargs):
            """
            Helper function to simulate the 404.
            """
            if self.blob_name == keys[2]:
                raise err

            return orig_delete_blob(self, *args, **kwargs)

        now = datetime.datetime.now(datetime.timezone.utc)
        storage_engine._storage_path = "datastorage/registry"

        for i, k in enumerate(keys):
            payload = os.urandom(1024)
            with freeze_time(now):
                storage_engine._container.upload_blob(name=k, data=payload)

        # conduct deletion using BlobClient interceptor
        with patch.object(BlobClient, "delete_blob", new=mock_delete_blob):
            with freeze_time(now + timedelta(hours=2)):
                storage_engine.clean_exported_action_logs(timedelta(hours=2), _TEST_LOG_PATH)

        # verify that all keys *except* 2 are removed
        remaining_blobs = list(
            storage_engine._container.list_blobs(name_starts_with=storage_engine._storage_path)
        )
        assert len(remaining_blobs) == 1

        remaining_keys = [blob.name for blob in remaining_blobs]
        assert keys[2] in remaining_keys
