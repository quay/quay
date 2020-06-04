import os

from io import BytesIO

import pytest

import moto
import boto

from moto import mock_s3_deprecated as mock_s3

from storage import S3Storage, StorageContext
from storage.cloud import _CloudStorage, _PartUploadMetadata
from storage.cloud import _CHUNKS_KEY

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "some_bucket"
_TEST_USER = "someuser"
_TEST_PASSWORD = "somepassword"
_TEST_PATH = "some/cool/path"
_TEST_CONTEXT = StorageContext("nyc", None, None, None)


@pytest.fixture(scope="function")
def storage_engine():
    with mock_s3():
        # Create a test bucket and put some test content.
        boto.connect_s3().create_bucket(_TEST_BUCKET)
        engine = S3Storage(_TEST_CONTEXT, "some/path", _TEST_BUCKET, _TEST_USER, _TEST_PASSWORD)
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        yield engine


def test_basicop(storage_engine):
    # Ensure the content exists.
    assert storage_engine.exists(_TEST_PATH)

    # Verify it can be retrieved.
    assert storage_engine.get_content(_TEST_PATH) == _TEST_CONTENT

    # Retrieve a checksum for the content.
    storage_engine.get_checksum(_TEST_PATH)

    # Remove the file.
    storage_engine.remove(_TEST_PATH)

    # Ensure it no longer exists.
    with pytest.raises(IOError):
        storage_engine.get_content(_TEST_PATH)

    with pytest.raises(IOError):
        storage_engine.get_checksum(_TEST_PATH)

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
    boto.connect_s3().create_bucket("another_bucket")
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

        assert not engine.exists(_TEST_PATH)


@pytest.mark.parametrize("chunk_count", [0, 1, 50,])
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
    assert storage_engine.get_content("some/chunked/path") == final_data


@pytest.mark.parametrize("chunk_count", [0, 1, 50,])
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
        (50, [_PartUploadMetadata("foo", 0, 50), _PartUploadMetadata("foo", 50, 50),]),
        (
            40,
            [
                _PartUploadMetadata("foo", 0, 25),
                _PartUploadMetadata("foo", 25, 25),
                _PartUploadMetadata("foo", 50, 25),
                _PartUploadMetadata("foo", 75, 25),
            ],
        ),
        (51, [_PartUploadMetadata("foo", 0, 50), _PartUploadMetadata("foo", 50, 50),]),
        (
            49,
            [
                _PartUploadMetadata("foo", 0, 25),
                _PartUploadMetadata("foo", 25, 25),
                _PartUploadMetadata("foo", 50, 25),
                _PartUploadMetadata("foo", 75, 25),
            ],
        ),
        (99, [_PartUploadMetadata("foo", 0, 50), _PartUploadMetadata("foo", 50, 50),]),
        (100, [_PartUploadMetadata("foo", 0, 100),]),
    ],
)
def test_rechunked(max_size, parts):
    chunk = _PartUploadMetadata("foo", 0, 100)
    rechunked = list(_CloudStorage._rechunk(chunk, max_size))
    assert len(rechunked) == len(parts)
    for index, chunk in enumerate(rechunked):
        assert chunk == parts[index]
