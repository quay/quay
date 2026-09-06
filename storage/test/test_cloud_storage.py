import datetime
import hashlib
import logging
import os
import time
import uuid
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

import boto3
import botocore
import botocore.exceptions
import pytest
from botocore.client import BaseClient
from freezegun import freeze_time
from moto import mock_s3

from storage import S3Storage, StorageContext
from storage.cloud import (
    _CHUNKS_KEY,
    _build_endpoint_url,
    _CloudStorage,
    _PartUploadMetadata,
)

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "somebucket"
_TEST_USER = "someuser"
_TEST_PASSWORD = "somepassword"
_TEST_REGION = "us-bacon-1"
_TEST_PATH = "some/cool/path"
_TEST_UPLOADS_PATH = "uploads/ee160658-9444-4950-8ec6-30faab40529c"
_TEST_LOG_PATH = "exportedactionlogs/"
_TEST_CONTEXT = StorageContext("nyc", None, None, None)


@pytest.fixture(scope="function")
def storage_engine():
    with mock_s3():
        # Create a test bucket and put some test content.
        boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)
        engine = S3Storage(
            _TEST_CONTEXT, "some/path", _TEST_BUCKET, _TEST_USER, _TEST_PASSWORD, _TEST_REGION
        )
        assert engine._connect_kwargs["endpoint_url"] == "https://s3.{}.amazonaws.com".format(
            _TEST_REGION
        )
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        yield engine


@pytest.mark.parametrize(
    "hostname, port, is_secure, expected",
    [
        pytest.param("somehost", None, False, "http://somehost"),
        pytest.param("somehost", 8080, False, "http://somehost:8080"),
        pytest.param("somehost", 8080, True, "https://somehost:8080"),
        pytest.param("https://somehost.withscheme", None, False, "https://somehost.withscheme"),
        pytest.param("http://somehost.withscheme", None, True, "http://somehost.withscheme"),
        pytest.param("somehost.withport:8080", 9090, True, "https://somehost.withport:8080"),
    ],
)
def test_build_endpoint_url(hostname, port, is_secure, expected):
    assert _build_endpoint_url(hostname, port, is_secure) == expected


def test_basicop(storage_engine):
    # Ensure the content exists.
    assert storage_engine.exists(_TEST_PATH)

    # Verify it can be retrieved.
    assert storage_engine.get_content(_TEST_PATH) == _TEST_CONTENT

    # Retrieve a checksum for the content.
    storage_engine.get_checksum(_TEST_PATH)

    # Remove the file.
    result = storage_engine.remove(_TEST_PATH)
    assert result is None

    # Ensure it no longer exists.
    with pytest.raises(IOError):
        storage_engine.get_content(_TEST_PATH)

    with pytest.raises(IOError):
        storage_engine.get_checksum(_TEST_PATH)

    assert not storage_engine.exists(_TEST_PATH)


def test_remove_returns_version_id_on_versioned_bucket():
    with mock_s3():
        client = boto3.client("s3", region_name=_TEST_REGION)
        client.create_bucket(
            Bucket=_TEST_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": _TEST_REGION},
        )
        client.put_bucket_versioning(
            Bucket=_TEST_BUCKET,
            VersioningConfiguration={"Status": "Enabled"},
        )

        engine = S3Storage(
            _TEST_CONTEXT, "some/path", _TEST_BUCKET, _TEST_USER, _TEST_PASSWORD, _TEST_REGION
        )
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        version_id = engine.remove(_TEST_PATH)
        assert version_id is not None


def test_remove_nonexistent_returns_none(storage_engine):
    result = storage_engine.remove("does/not/exist")
    assert result is None


def test_storage_setup(storage_engine):
    storage_engine.setup()


def test_remove_dir(storage_engine):
    # Ensure the content exists.
    assert storage_engine.exists(_TEST_PATH)

    # Verify it can be retrieved.
    assert storage_engine.get_content(_TEST_PATH) == _TEST_CONTENT

    # Retrieve a checksum for the content.
    storage_engine.get_checksum(_TEST_PATH)

    # Remove the "directory".
    storage_engine.remove(_TEST_PATH.split("/")[0])

    assert not storage_engine.exists(_TEST_PATH)


@pytest.mark.parametrize(
    "bucket, username, password",
    [
        pytest.param(_TEST_BUCKET, _TEST_USER, _TEST_PASSWORD, id="same credentials"),
        pytest.param("another_bucket", "blech", "password", id="different credentials"),
    ],
)
def test_copy(bucket, username, password, storage_engine):
    # Copy the content to another engine.
    another_engine = S3Storage(
        _TEST_CONTEXT, "another/path", _TEST_BUCKET, _TEST_USER, _TEST_PASSWORD
    )
    boto3.client("s3").create_bucket(Bucket="another_bucket")
    storage_engine.copy_to(another_engine, _TEST_PATH)

    # Verify it can be retrieved.
    assert another_engine.get_content(_TEST_PATH) == _TEST_CONTENT


def test_copy_with_error(storage_engine):
    another_engine = S3Storage(_TEST_CONTEXT, "another/path", "anotherbucket", "foo", "bar")

    with pytest.raises(IOError):
        storage_engine.copy_to(another_engine, _TEST_PATH)


def test_stream_read(storage_engine):
    # Read the streaming content.
    data = b"".join(storage_engine.stream_read(_TEST_PATH))
    assert data == _TEST_CONTENT


def test_stream_read_file(storage_engine):
    with storage_engine.stream_read_file(_TEST_PATH) as f:
        assert f.read() == _TEST_CONTENT


def test_stream_write(storage_engine):
    new_data = os.urandom(4096)
    storage_engine.stream_write(_TEST_PATH, BytesIO(new_data), content_type="Cool/Type")
    assert storage_engine.get_content(_TEST_PATH) == new_data


def test_stream_write_error():
    with mock_s3():
        # Create an engine but not the bucket.
        engine = S3Storage(_TEST_CONTEXT, "some/path", _TEST_BUCKET, _TEST_USER, _TEST_PASSWORD)

        # Attempt to write to the uncreated bucket, which should raise an error.
        with pytest.raises(IOError):
            engine.stream_write(_TEST_PATH, BytesIO(b"hello world"), content_type="Cool/Type")

        with pytest.raises(botocore.exceptions.ClientError) as excinfo:
            engine.exists(_TEST_PATH)
            assert s3r.value.response["Error"]["Code"] == "NoSuchBucket"


@pytest.mark.parametrize(
    "chunk_count",
    [
        0,
        1,
        2,
        50,
    ],
)
@pytest.mark.parametrize("force_client_side", [False, True])
def test_chunk_upload(storage_engine, chunk_count, force_client_side):
    if chunk_count == 0 and force_client_side:
        return

    upload_id, metadata = storage_engine.initiate_chunked_upload()
    final_data = b""

    for index in range(0, chunk_count):
        chunk_data = os.urandom(1024)
        final_data = final_data + chunk_data
        bytes_written, new_metadata, error = storage_engine.stream_upload_chunk(
            upload_id, 0, len(chunk_data), BytesIO(chunk_data), metadata
        )
        metadata = new_metadata

        assert bytes_written == len(chunk_data)
        assert error is None
        assert len(metadata[_CHUNKS_KEY]) == index + 1

    # Complete the chunked upload.
    storage_engine.complete_chunked_upload(
        upload_id, "some/chunked/path", metadata, force_client_side=force_client_side
    )

    # Ensure the file contents are valid.
    if chunk_count != 0:
        assert storage_engine.get_content("some/chunked/path") == final_data


@pytest.mark.parametrize(
    "chunk_count",
    [
        0,
        1,
        50,
    ],
)
def test_cancel_chunked_upload(storage_engine, chunk_count):
    upload_id, metadata = storage_engine.initiate_chunked_upload()

    for _ in range(0, chunk_count):
        chunk_data = os.urandom(1024)
        _, new_metadata, _ = storage_engine.stream_upload_chunk(
            upload_id, 0, len(chunk_data), BytesIO(chunk_data), metadata
        )
        metadata = new_metadata

    # Cancel the upload.
    storage_engine.cancel_chunked_upload(upload_id, metadata)

    # Ensure all chunks were deleted.
    for chunk in metadata[_CHUNKS_KEY]:
        assert not storage_engine.exists(chunk.path)


def test_large_chunks_upload(storage_engine):
    # Make the max chunk size much smaller for testing.
    storage_engine.maximum_chunk_size = storage_engine.minimum_chunk_size * 2

    upload_id, metadata = storage_engine.initiate_chunked_upload()

    # Write a "super large" chunk, to ensure that it is broken into smaller chunks.
    chunk_data = os.urandom(int(storage_engine.maximum_chunk_size * 2.5))
    bytes_written, new_metadata, _ = storage_engine.stream_upload_chunk(
        upload_id, 0, -1, BytesIO(chunk_data), metadata
    )
    assert len(chunk_data) == bytes_written

    # Complete the chunked upload.
    storage_engine.complete_chunked_upload(upload_id, "some/chunked/path", new_metadata)

    # Ensure the file contents are valid.
    assert len(chunk_data) == len(storage_engine.get_content("some/chunked/path"))
    assert storage_engine.get_content("some/chunked/path") == chunk_data


def test_large_chunks_with_ragged_edge(storage_engine):
    # Make the max chunk size much smaller for testing and force it to have a ragged edge.
    storage_engine.maximum_chunk_size = storage_engine.minimum_chunk_size * 2 + 10

    upload_id, metadata = storage_engine.initiate_chunked_upload()

    # Write a few "super large" chunks, to ensure that it is broken into smaller chunks.
    all_data = b""
    for _ in range(0, 2):
        chunk_data = os.urandom(int(storage_engine.maximum_chunk_size) + 20)
        bytes_written, new_metadata, _ = storage_engine.stream_upload_chunk(
            upload_id, 0, -1, BytesIO(chunk_data), metadata
        )
        assert len(chunk_data) == bytes_written
        all_data = all_data + chunk_data
        metadata = new_metadata

    # Complete the chunked upload.
    storage_engine.complete_chunked_upload(upload_id, "some/chunked/path", new_metadata)

    # Ensure the file contents are valid.
    assert len(all_data) == len(storage_engine.get_content("some/chunked/path"))
    assert storage_engine.get_content("some/chunked/path") == all_data


@pytest.mark.parametrize(
    "max_size, parts",
    [
        (
            50,
            [
                _PartUploadMetadata("foo", 0, 50),
                _PartUploadMetadata("foo", 50, 50),
            ],
        ),
        (
            40,
            [
                _PartUploadMetadata("foo", 0, 25),
                _PartUploadMetadata("foo", 25, 25),
                _PartUploadMetadata("foo", 50, 25),
                _PartUploadMetadata("foo", 75, 25),
            ],
        ),
        (
            51,
            [
                _PartUploadMetadata("foo", 0, 50),
                _PartUploadMetadata("foo", 50, 50),
            ],
        ),
        (
            49,
            [
                _PartUploadMetadata("foo", 0, 25),
                _PartUploadMetadata("foo", 25, 25),
                _PartUploadMetadata("foo", 50, 25),
                _PartUploadMetadata("foo", 75, 25),
            ],
        ),
        (
            99,
            [
                _PartUploadMetadata("foo", 0, 50),
                _PartUploadMetadata("foo", 50, 50),
            ],
        ),
        (
            100,
            [
                _PartUploadMetadata("foo", 0, 100),
            ],
        ),
    ],
)
def test_rechunked(max_size, parts):
    chunk = _PartUploadMetadata("foo", 0, 100)
    rechunked = list(_CloudStorage._rechunk(chunk, max_size))
    assert len(rechunked) == len(parts)
    for index, chunk in enumerate(rechunked):
        assert chunk == parts[index]


@pytest.mark.parametrize("path", ["/", _TEST_PATH])
def test_clean_partial_uploads(storage_engine, path):

    # Setup root path and add come content to _root_path/uploads
    storage_engine._root_path = path
    storage_engine.put_content(_TEST_UPLOADS_PATH, _TEST_CONTENT)
    assert storage_engine.exists(_TEST_UPLOADS_PATH)
    assert storage_engine.get_content(_TEST_UPLOADS_PATH) == _TEST_CONTENT

    # Test ensure fresh blobs are not deleted
    storage_engine.clean_partial_uploads(timedelta(days=2))
    assert storage_engine.exists(_TEST_UPLOADS_PATH)
    assert storage_engine.get_content(_TEST_UPLOADS_PATH) == _TEST_CONTENT

    # Test deletion of stale blobs
    time.sleep(1)
    storage_engine.clean_partial_uploads(timedelta(seconds=0))
    assert not storage_engine.exists(_TEST_UPLOADS_PATH)

    # Test if uploads folder does not exist
    storage_engine.remove("uploads")
    assert not storage_engine.exists("uploads")
    storage_engine.clean_partial_uploads(timedelta(seconds=0))


@pytest.fixture
def mock_mpu_dates():
    """
    Fixture to allow freezegun control moto's multipart upload dates. Needed since Moto
    hardcodes MPU creation date in its source code which goes back to 2010.
    Clears state automatically between tests.
    """
    _UPLOAD_DATES = {}
    original_make_api_call = BaseClient._make_api_call

    def _mock_make_api_call(self, operation_name, api_params):
        response = original_make_api_call(self, operation_name, api_params)

        if operation_name == "CreateMultipartUpload":
            _UPLOAD_DATES[response["UploadId"]] = datetime.datetime.now(datetime.timezone.utc)

        elif operation_name == "ListMultipartUploads" and "Uploads" in response:
            for upload in response["Uploads"]:
                upload_id = upload["UploadId"]
                if upload_id in _UPLOAD_DATES:
                    upload["Initiated"] = _UPLOAD_DATES[upload_id]

        return response

    with patch.object(BaseClient, "_make_api_call", new=_mock_make_api_call):
        yield


def test_clean_orphaned_multipart_uploads(storage_engine, mock_mpu_dates):
    """
    Tests clean up of stale multipart uploads based on specific threshold.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)

    # initialize an MPU
    with freeze_time(now):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/test/multipart/upload.txt"
        )

    # verify that the upload exists
    assert mpu_response
    print(mpu_response)
    upload_id = mpu_response["UploadId"]
    storage_engine._root_path = _TEST_PATH

    uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)

    assert len(uploads.get("Uploads", [])) == 1
    assert uploads["Uploads"][0]["UploadId"] == upload_id

    # Check that the multipart upload is not cleaned for a very large threshold
    with freeze_time(now):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(days=1))
        assert deleted == 0
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)
        assert len(uploads.get("Uploads", [])) == 1

    # Check that the upload is deleted with a threshold of 0
    with freeze_time(now + timedelta(seconds=5)):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(seconds=0))
        assert deleted == 1
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)
        assert len(uploads.get("Uploads", [])) == 0


def test_cleanup_multiple_orphaned_multipart_uploads(storage_engine, mock_mpu_dates):
    """
    Tests that all created multipart uploads are cleaned after a certain threshold.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    storage_engine._root_path = _TEST_PATH

    now = datetime.datetime.now(datetime.timezone.utc)
    file_list = ["apple", "ibm", "redhat", "github", "jira", "email"]

    # create multiple MPUs
    with freeze_time(now):
        for keyname in file_list:
            mpu_response = client.create_multipart_upload(
                Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/test/multipart/%s" % keyname + ".txt"
            )
            assert mpu_response

    # check that we can list all MPUs
    uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)["Uploads"]
    assert len(uploads) == len(file_list)

    # check that multipart uploads are not delte with a high enough threshold
    with freeze_time(now):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(days=1))
        assert deleted == 0
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)["Uploads"]
        assert len(uploads) == len(file_list)

    # assert that all multipart uploads are deleted with a threshold of 0
    with freeze_time(now + timedelta(seconds=5)):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(seconds=0))
        assert deleted == 6
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)
        assert len(uploads.get("Uploads", [])) == 0


def test_partial_cleanup_of_multipart_uploads(storage_engine, mock_mpu_dates):
    """
    Tests that partial MPU deletion occurs after a provided threshold. Stale MPUs should
    be deleted, active MPUs should not be touched.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)
    file_list = ["apple", "ibm", "redhat", "github", "jira", "email"]
    storage_engine._root_path = _TEST_PATH

    # create multiple MPUs with a timedelta of 1 hour between them
    for i, keyname in enumerate(file_list):
        with freeze_time(now + timedelta(hours=1 * i)):
            mpu_response = client.create_multipart_upload(
                Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/test/multipart/%s" % keyname + ".txt"
            )
            assert mpu_response

    # check that we can list all MPUs
    uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)["Uploads"]
    assert len(uploads) == len(file_list)

    # check that multipart uploads are not deleted with a high enough threshold
    with freeze_time(now + timedelta(hours=5)):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(days=1))
        assert deleted == 0
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)["Uploads"]
        assert len(uploads) == len(file_list)

    # assert that only some multipart uploads are deleted after a certain threshold
    # fast forward time by 6 hours, set timedelta to 3.5 hours meaning that
    # cutoff rate is at now + 2.5 hours. So 3 out of 6 MPUs should be deleted.
    with freeze_time(now + timedelta(hours=6)):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(hours=3.5))
        assert deleted == 3
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)["Uploads"]
        assert len(uploads) == 3
        assert uploads[0]["Key"] == _TEST_PATH + "/test/multipart/github.txt"
        assert uploads[1]["Key"] == _TEST_PATH + "/test/multipart/jira.txt"
        assert uploads[2]["Key"] == _TEST_PATH + "/test/multipart/email.txt"


def test_cleanup_does_not_impact_multipart_uploads_under_different_paths(
    storage_engine, mock_mpu_dates
):
    """
    Verifies that we only clean up multipart uploads under the root path and not under all paths in
    the bucket.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._root_path = _TEST_PATH

    # create an MPU under the default path
    with freeze_time(now):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/test/correct/deletion/path.txt"
        )
        assert mpu_response

    # create an MPU under a completely different path
    with freeze_time(now):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key="/completely/different/deletion/path.txt"
        )

    # check that on the bucket we have two MPUs
    uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET)["Uploads"]
    assert len(uploads) == 2

    # clean up only MPUs under the proper path
    with freeze_time(now + timedelta(seconds=5)):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(seconds=0))
        assert deleted == 1

        # list MPUs on the bucket
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET)["Uploads"]
        assert len(uploads) == 1

        # explicitly verify that the key matches
        assert uploads[0]["Key"] == "/completely/different/deletion/path.txt"


def test_cleanup_triggers_on_non_normalized_root(storage_engine, mock_mpu_dates):
    """
    Asserts that deletion happens even if our root prefix contains a slash at the beginning.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)

    # root path has a slash
    storage_engine._root_path = "/" + _TEST_PATH

    # create an MPU
    with freeze_time(now):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/test/root_prefix/starts/with/slash.txt"
        )
        assert mpu_response

    uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET)["Uploads"]
    assert len(uploads) == 1

    # clean up MPU
    with freeze_time(now + timedelta(seconds=5)):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(seconds=0))
        assert deleted == 1

        # list MPUs on the bucket
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH)
        assert len(uploads.get("Uploads", [])) == 0


def test_cleanup_does_not_trigger_on_sibling_suffix(storage_engine, mock_mpu_dates):
    """
    Asserts that deletion does not happen on sibling suffixes. Eg: cleanup should happen on
    some/cool/path/testfile.txt but not on /some/cool/path-with-suffix/testfile.txt.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)

    storage_engine._root_path = _TEST_PATH

    # create MPU
    with freeze_time(now):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/testfile.txt"
        )
        assert mpu_response

    # create MPU under different suffix
    with freeze_time(now):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key=_TEST_PATH + "-with-suffix/testfile.txt"
        )
        assert mpu_response

    # verify we have both MPUs present
    uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET)["Uploads"]
    assert len(uploads) == 2

    # clean up only under default path
    with freeze_time(now + timedelta(seconds=5)):
        deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(seconds=0))
        assert deleted == 1

        # specifically verify that the key that's left is the 2nd MPU
        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET, Prefix=_TEST_PATH + "/")
        assert len(uploads.get("Uploads", [])) == 0

        uploads = client.list_multipart_uploads(Bucket=_TEST_BUCKET)["Uploads"]
        assert len(uploads) == 1
        assert uploads[0]["Key"] == _TEST_PATH + "-with-suffix/testfile.txt"


def test_cleanup_handles_already_aborted_mpu(storage_engine, mock_mpu_dates):
    """
    Asserts that the NoSuchUpload exception is caught by the code and not raised.
    """

    err = botocore.exceptions.ClientError(
        {"Error": {"Code": "NoSuchUpload", "Message": "The specified upload does not exist."}},
        "AbortMultipartUpload",
    )

    def abort_side_effects(Bucket, Key, UploadId):
        """
        Helper function to simulate NoSuchUpload exception raised
        """
        if Key.endswith("gone.txt"):
            raise err
        return {}

    client = boto3.client("s3", region_name=_TEST_REGION)
    storage_engine._root_path = _TEST_PATH
    now = datetime.datetime.now(datetime.timezone.utc)

    # create two multipart uploads
    with freeze_time(now):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/keep.txt"
        )
        assert mpu_response

    with freeze_time(now + timedelta(seconds=30)):
        mpu_response = client.create_multipart_upload(
            Bucket=_TEST_BUCKET, Key=_TEST_PATH + "/gone.txt"
        )
        assert mpu_response

    # conduct deletion
    with patch.object(
        storage_engine.get_cloud_conn(), "abort_multipart_upload", side_effect=abort_side_effects
    ):
        with freeze_time(now + timedelta(hours=1)):
            deleted = storage_engine.clean_orphaned_multipart_uploads(timedelta(seconds=0))
            assert deleted == 1


def test_cleanup_of_orphaned_export_log_files_successful(storage_engine):
    """
    Verifies that the worker can clean up orphaned exported log files.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)

    storage_engine._root_path = ""

    payload = '{"logs": []}'
    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key = f"{_TEST_LOG_PATH}{logfile}"

    # put object into the bucket
    resp = client.put_object(Bucket=_TEST_BUCKET, Key=upload_key, Body=payload)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # attempt to clean
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # list all bucket content on that specific path to ensure that the file was removed
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=_TEST_LOG_PATH)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    remaining_keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert upload_key not in remaining_keys


def test_export_log_cleanup_does_not_touch_user_files(storage_engine):
    """
    Verifies that other files in the same path are not picked up by the
    cleanup worker.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)

    storage_engine._root_path = ""

    payload1 = '{"logs": []}'
    payload2 = "Hello world!!!"

    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
    userfile = "hello.txt"
    upload_key_userfile = f"{_TEST_LOG_PATH}{userfile}"

    # put both files in the bucket
    resp1 = client.put_object(Bucket=_TEST_BUCKET, Key=upload_key_logfile, Body=payload1)
    assert resp1["ResponseMetadata"]["HTTPStatusCode"] == 200
    resp2 = client.put_object(Bucket=_TEST_BUCKET, Key=upload_key_userfile, Body=payload2)
    assert resp2["ResponseMetadata"]["HTTPStatusCode"] == 200

    # attempt to clean
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # list all content under the specified prefix
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=_TEST_LOG_PATH)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    remaining_keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert upload_key_logfile not in remaining_keys
    assert upload_key_userfile in remaining_keys


def test_export_log_cleanup_doesnt_touch_other_paths(storage_engine):
    """
    Verifies that all other paths other than the log path are untouched by the
    cleanup worker.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)

    storage_engine._root_path = ""

    payload1 = '{"logs": []}'
    payload2 = "Hello world!!!"

    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
    userfile = "hello.txt"
    upload_key_userfile = f"different/path/altogether/{userfile}"

    # put both files in the bucket
    resp1 = client.put_object(Bucket=_TEST_BUCKET, Key=upload_key_logfile, Body=payload1)
    assert resp1["ResponseMetadata"]["HTTPStatusCode"] == 200
    resp2 = client.put_object(Bucket=_TEST_BUCKET, Key=upload_key_userfile, Body=payload2)
    assert resp2["ResponseMetadata"]["HTTPStatusCode"] == 200

    # attempt to clean
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # list all content in the bucket
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    remaining_keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert upload_key_logfile not in remaining_keys
    assert upload_key_userfile in remaining_keys


def test_export_log_cleanup_doesnt_pick_up_files_that_are_inside_the_timedelta(storage_engine):
    """
    Verifies that we only delete files that are older than 1 hour and not any other files that are in the same path
    """

    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)

    storage_engine._root_path = ""

    # create a list of files
    keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for i in range(5)]
    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        with freeze_time(now + timedelta(hours=i)):
            resp = client.put_object(Bucket=_TEST_BUCKET, Key=k, Body=payload)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # list all content on that specific path and confirm that there are 5
    # files present
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=_TEST_LOG_PATH)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp.get("Contents", [])) == 5

    # add 6th file only 30 minutes *after* the last file was uploaded
    final_key = f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    payload = os.urandom(1024)
    with freeze_time(now + timedelta(hours=5.5)):
        resp = client.put_object(Bucket=_TEST_BUCKET, Key=final_key, Body=payload)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # at 6th hour do cleanup
    with freeze_time(now + timedelta(hours=6)):
        storage_engine.clean_exported_action_logs(timedelta(hours=1), _TEST_LOG_PATH)

    # only one file should remain
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=_TEST_LOG_PATH)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp.get("Contents", [])) == 1
    remaining_keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert final_key in remaining_keys


def test_export_log_cleanup_correctly_identifies_root_path(storage_engine):
    """
    Verifies that the root path (defined through storage_path in the driver) is
    properly taken into account during wiping.
    """

    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._root_path = "datastorage/registry"

    # create a list of files
    keys = [
        f"datastorage/registry/{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
        for i in range(5)
    ]
    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        with freeze_time(now):
            resp = client.put_object(Bucket=_TEST_BUCKET, Key=k, Body=payload)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # add a specific file with a SHA digest to mimick real storage
    payload = os.urandom(1024)
    filename = hashlib.sha256(payload).hexdigest()
    final_key = "datastorage/registry/sha256/%s/%s" % (filename[:2], filename)

    # upload the key
    with freeze_time(now):
        resp = client.put_object(Bucket=_TEST_BUCKET, Key=final_key, Body=payload)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # verify all files are uploaded properly and are visible
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=storage_engine._root_path)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp.get("Contents", [])) == 6

    # attempt to clean up expired logs
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

    # only one file should remain
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=storage_engine._root_path)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp.get("Contents", [])) == 1
    remaining_keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert final_key in remaining_keys


def test_export_log_cleanup_does_not_return_error_on_empty_directory(storage_engine):
    """
    Verifies that cleanup does not error when nothing is cleaned. Simple regression test.
    """
    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._root_path = "datastorage/registry"

    # add a specific file with a SHA digest to mimick real storage
    payload = os.urandom(1024)
    filename = hashlib.sha256(payload).hexdigest()
    keyname = "datastorage/registry/sha256/%s/%s" % (filename[:2], filename)

    # upload the key
    with freeze_time(now):
        resp = client.put_object(Bucket=_TEST_BUCKET, Key=keyname, Body=payload)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # assert that we only have one key under datastorage/registry path
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=storage_engine._root_path)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp.get("Contents", [])) == 1

    # call cleanup on real directory
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

    # assert that we still have only one file under storage path
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=storage_engine._root_path)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp.get("Contents", [])) == 1


def test_cleanup_of_expired_logs_gracefully_handles_errors(storage_engine, mock_mpu_dates):
    """
    Asserts that the NoSuchUpload exception is caught by the code and not raised.
    """
    err = botocore.exceptions.ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}},
        "HeadObject",
    )

    # reference to the original API call
    orig_make_api_call = botocore.client.BaseClient._make_api_call

    # create a list of files
    keys = [
        f"datastorage/registry/{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
        for i in range(5)
    ]

    def mock_make_api_call(self, operation_name, kwargs):
        """
        Helper function to simulate the 404.
        """
        if operation_name == "HeadObject" and kwargs.get("Key", "") == keys[2]:
            raise err

        return orig_make_api_call(self, operation_name, kwargs)

    client = boto3.client("s3", region_name=_TEST_REGION)
    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._root_path = "datastorage/registry"

    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        with freeze_time(now):
            resp = client.put_object(Bucket=_TEST_BUCKET, Key=k, Body=payload)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # conduct deletion
    with patch.object(botocore.client.BaseClient, "_make_api_call", new=mock_make_api_call):
        with freeze_time(now + timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(hours=2), _TEST_LOG_PATH)

    # verify that all keys *except* 2 are removed
    resp = client.list_objects_v2(Bucket=_TEST_BUCKET, Prefix=storage_engine._root_path)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp.get("Contents", [])) == 1

    remaining_keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert keys[2] in remaining_keys
