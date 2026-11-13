"""
Tests for RadosGWStorage backend.

RadosGWStorage provides S3-compatible object storage using Ceph RadosGW.
Key features tested:
- Basic CRUD operations
- Streaming reads/writes
- Chunked uploads (server-side and client-side assembly)
- Large file handling with configurable chunk sizes
- CORS limitation handling
- Partial upload cleanup
- Error handling
"""

import os
import time
from datetime import timedelta
from io import BytesIO

import boto3
import botocore.exceptions
import pytest
from moto import mock_s3

from storage import RadosGWStorage, S3Storage, StorageContext
from storage.cloud import _CHUNKS_KEY, _PartUploadMetadata

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "test-radosgw-bucket"
_TEST_USER = "test-radosgw-user"
_TEST_PASSWORD = "test-radosgw-password"
_TEST_REGION = "us-east-1"
_TEST_PATH = "radosgw/test/path"
_TEST_UPLOADS_PATH = "uploads/radosgw-test-upload-id"
_TEST_CONTEXT = StorageContext("radosgw-location", None, None, None)


@pytest.fixture(scope="function")
def radosgw_storage_engine():
    """
    Fixture providing RadosGWStorage instance with mocked S3 backend.

    Uses moto to create an in-memory S3-compatible endpoint that simulates
    RadosGW behavior. The fixture creates a bucket and seeds test data.
    """
    with mock_s3():
        # Create bucket using standard S3 endpoint (moto will intercept)
        boto3.client("s3", region_name=_TEST_REGION).create_bucket(Bucket=_TEST_BUCKET)

        # Initialize RadosGWStorage with server-side assembly enabled
        # Use standard S3 endpoint format that moto can intercept
        engine = RadosGWStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name=_TEST_BUCKET,
            region_name=_TEST_REGION,
            signature_version="s3v4",
            server_side_assembly=True,
            minimum_chunk_size_mb=5,
            maximum_chunk_size_mb=100,
        )

        # Seed test data
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        yield engine


@pytest.fixture(scope="function")
def radosgw_storage_engine_client_side():
    """
    Fixture providing RadosGWStorage with client-side assembly enabled.

    Used to test the fallback assembly mode for RadosGW implementations
    that don't support server-side multipart copying.
    """
    with mock_s3():
        # Create bucket
        boto3.client("s3", region_name=_TEST_REGION).create_bucket(Bucket=_TEST_BUCKET)

        # Initialize RadosGWStorage with client-side assembly
        # Use standard S3 endpoint format that moto can intercept
        engine = RadosGWStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name=_TEST_BUCKET,
            region_name=_TEST_REGION,
            signature_version="s3v4",
            server_side_assembly=False,  # Client-side assembly
            minimum_chunk_size_mb=5,
            maximum_chunk_size_mb=100,
        )

        # Seed test data
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        yield engine


def test_radosgw_basicop(radosgw_storage_engine):
    """Test basic CRUD operations on RadosGWStorage (Acceptance Criteria Test 1)."""
    engine = radosgw_storage_engine

    # Ensure the content exists
    assert engine.exists(_TEST_PATH)

    # Verify it can be retrieved
    assert engine.get_content(_TEST_PATH) == _TEST_CONTENT

    # Retrieve a checksum for the content
    checksum = engine.get_checksum(_TEST_PATH)
    assert checksum is not None

    # Remove the file
    engine.remove(_TEST_PATH)

    # Ensure it no longer exists
    with pytest.raises(IOError):
        engine.get_content(_TEST_PATH)

    with pytest.raises(IOError):
        engine.get_checksum(_TEST_PATH)

    assert not engine.exists(_TEST_PATH)


def test_radosgw_stream_read(radosgw_storage_engine):
    """Test stream reading as generator (Acceptance Criteria Test 2)."""
    engine = radosgw_storage_engine

    # Read the streaming content
    data = b"".join(engine.stream_read(_TEST_PATH))
    assert data == _TEST_CONTENT


def test_radosgw_stream_read_file(radosgw_storage_engine):
    """Test stream reading as file-like object (Acceptance Criteria Test 2)."""
    engine = radosgw_storage_engine

    # Read using file-like interface
    with engine.stream_read_file(_TEST_PATH) as f:
        assert f.read() == _TEST_CONTENT


def test_radosgw_stream_write(radosgw_storage_engine):
    """Test stream writing with content type (Acceptance Criteria Test 2)."""
    engine = radosgw_storage_engine

    # Write new data with content type
    new_data = os.urandom(2048)
    engine.stream_write(_TEST_PATH, BytesIO(new_data), content_type="application/octet-stream")

    # Verify the content was written correctly
    assert engine.get_content(_TEST_PATH) == new_data


@pytest.mark.parametrize(
    "chunk_count",
    [
        0,
        1,
        2,
        10,
    ],
)
def test_radosgw_chunk_upload_server_side(radosgw_storage_engine, chunk_count):
    """Test chunked upload with server-side assembly (Acceptance Criteria Test 3)."""
    engine = radosgw_storage_engine

    # Initiate chunked upload
    upload_id, metadata = engine.initiate_chunked_upload()
    assert upload_id is not None
    final_data = b""

    # Upload chunks
    for index in range(0, chunk_count):
        chunk_data = os.urandom(1024)
        final_data = final_data + chunk_data

        bytes_written, new_metadata, error = engine.stream_upload_chunk(
            upload_id, 0, len(chunk_data), BytesIO(chunk_data), metadata
        )
        metadata = new_metadata

        assert bytes_written == len(chunk_data)
        assert error is None
        assert len(metadata[_CHUNKS_KEY]) == index + 1

    # Complete the chunked upload with server-side assembly
    final_path = "radosgw/chunked/server-side"
    engine.complete_chunked_upload(upload_id, final_path, metadata)

    # Verify expected behavior based on chunk count
    if chunk_count == 0:
        # Empty uploads should not create a file (early return in cloud.py:648-650)
        assert not engine.exists(final_path), "Empty upload should not create file"
    else:
        # Non-empty uploads should create file with correct content
        assert engine.exists(final_path)
        assert engine.get_content(final_path) == final_data


@pytest.mark.parametrize(
    "chunk_count",
    [
        1,
        2,
        5,
    ],
)
def test_radosgw_chunk_upload_client_side(radosgw_storage_engine_client_side, chunk_count):
    """Test chunked upload with client-side assembly (Acceptance Criteria Test 4)."""
    engine = radosgw_storage_engine_client_side

    # Verify client-side assembly is configured
    assert engine.server_side_assembly is False

    # Initiate chunked upload
    upload_id, metadata = engine.initiate_chunked_upload()
    final_data = b""

    # Upload chunks
    for _ in range(0, chunk_count):
        chunk_data = os.urandom(1024)
        final_data = final_data + chunk_data

        bytes_written, new_metadata, error = engine.stream_upload_chunk(
            upload_id, 0, len(chunk_data), BytesIO(chunk_data), metadata
        )
        metadata = new_metadata

        assert bytes_written == len(chunk_data)
        assert error is None

    # Complete the chunked upload with client-side assembly
    final_path = "radosgw/chunked/client-side"
    engine.complete_chunked_upload(upload_id, final_path, metadata)

    # Verify file exists and has correct content
    assert engine.exists(final_path)
    assert engine.get_content(final_path) == final_data


def test_radosgw_cancel_chunked_upload(radosgw_storage_engine):
    """Test chunk cancellation and cleanup."""
    engine = radosgw_storage_engine

    # Initiate chunked upload
    upload_id, metadata = engine.initiate_chunked_upload()

    # Upload some chunks
    for _ in range(0, 3):
        chunk_data = os.urandom(1024)
        _, new_metadata, _ = engine.stream_upload_chunk(
            upload_id, 0, len(chunk_data), BytesIO(chunk_data), metadata
        )
        metadata = new_metadata

    # Cancel the upload
    engine.cancel_chunked_upload(upload_id, metadata)

    # Ensure all chunks were deleted
    for chunk in metadata[_CHUNKS_KEY]:
        assert not engine.exists(chunk.path)


def test_radosgw_large_file_handling(radosgw_storage_engine):
    """Test large file handling with configurable chunk sizes (Acceptance Criteria Test 5)."""
    engine = radosgw_storage_engine

    # Verify configurable chunk sizes are set
    assert engine.minimum_chunk_size == 5 * 1024 * 1024  # 5 MB
    assert engine.maximum_chunk_size == 100 * 1024 * 1024  # 100 MB

    # Make the max chunk size smaller for testing
    engine.maximum_chunk_size = engine.minimum_chunk_size * 2

    upload_id, metadata = engine.initiate_chunked_upload()

    # Write a "super large" chunk to ensure it's broken into smaller chunks
    chunk_data = os.urandom(int(engine.maximum_chunk_size * 2.5))
    bytes_written, new_metadata, _ = engine.stream_upload_chunk(
        upload_id, 0, -1, BytesIO(chunk_data), metadata
    )
    assert len(chunk_data) == bytes_written

    # Complete the chunked upload
    final_path = "radosgw/large/file"
    engine.complete_chunked_upload(upload_id, final_path, new_metadata)

    # Ensure the file contents are valid
    assert engine.get_content(final_path) == chunk_data


def test_radosgw_cors_limitation(radosgw_storage_engine):
    """Test CORS limitation handling (Acceptance Criteria Test 6).

    RadosGW has incomplete CORS support (tracker.ceph.com/issues/8718).
    Direct presigned URLs should return None when CORS is required.
    """
    engine = radosgw_storage_engine

    # Test get_direct_download_url with CORS required
    download_url = engine.get_direct_download_url(_TEST_PATH, requires_cors=True)
    assert download_url is None

    # Test get_direct_upload_url with CORS required (default)
    upload_url = engine.get_direct_upload_url(_TEST_PATH, "application/octet-stream")
    assert upload_url is None

    # Test get_direct_upload_url with CORS not required
    upload_url_no_cors = engine.get_direct_upload_url(
        _TEST_PATH, "application/octet-stream", requires_cors=False
    )
    # Should work without CORS
    assert upload_url_no_cors is not None


@pytest.mark.parametrize("path", ["/", "radosgw/test"])
def test_radosgw_clean_partial_uploads(radosgw_storage_engine, path):
    """Test cleanup of stale upload artifacts (Acceptance Criteria Test 7)."""
    engine = radosgw_storage_engine

    # Setup root path and add content to _root_path/uploads
    engine._root_path = path
    engine.put_content(_TEST_UPLOADS_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_UPLOADS_PATH)
    assert engine.get_content(_TEST_UPLOADS_PATH) == _TEST_CONTENT

    # Test ensure fresh uploads are not deleted
    engine.clean_partial_uploads(timedelta(days=2))
    assert engine.exists(_TEST_UPLOADS_PATH)
    assert engine.get_content(_TEST_UPLOADS_PATH) == _TEST_CONTENT

    # Test deletion of stale uploads
    time.sleep(1)
    engine.clean_partial_uploads(timedelta(seconds=0))
    assert not engine.exists(_TEST_UPLOADS_PATH)

    # Test if uploads folder does not exist
    engine.remove("uploads")
    assert not engine.exists("uploads")
    engine.clean_partial_uploads(timedelta(seconds=0))


def test_radosgw_copy_operations(radosgw_storage_engine):
    """Test copy operations between storage backends (Acceptance Criteria Test 8)."""
    engine = radosgw_storage_engine

    # Create a second bucket for the target engine to simulate cross-backend copy
    another_bucket = "test-radosgw-bucket-2"
    boto3.client("s3", region_name=_TEST_REGION).create_bucket(Bucket=another_bucket)

    # Create another RadosGW storage engine with different bucket
    # Use standard S3 endpoint format that moto can intercept
    another_engine = RadosGWStorage(
        _TEST_CONTEXT,
        hostname=f"s3.{_TEST_REGION}.amazonaws.com",
        is_secure=True,
        storage_path="/another",
        access_key=_TEST_USER,
        secret_key=_TEST_PASSWORD,
        bucket_name=another_bucket,
        region_name=_TEST_REGION,
    )

    # Copy the content to another engine
    engine.copy_to(another_engine, _TEST_PATH)

    # Verify it can be retrieved from the target engine
    assert another_engine.get_content(_TEST_PATH) == _TEST_CONTENT

    # Verify checksum is preserved
    assert another_engine.get_checksum(_TEST_PATH) == engine.get_checksum(_TEST_PATH)


def test_radosgw_configuration_validation(radosgw_storage_engine):
    """Test configuration validation (Acceptance Criteria Test 9)."""
    engine = radosgw_storage_engine

    # Verify endpoint URL is correctly built
    expected_endpoint = f"https://s3.{_TEST_REGION}.amazonaws.com"
    assert engine._connect_kwargs["endpoint_url"] == expected_endpoint

    # Verify region is set
    assert engine._connect_kwargs["region_name"] == _TEST_REGION

    # Verify signature version is set
    assert engine._connect_kwargs["config"].signature_version == "s3v4"

    # Verify timeout configuration (60s for server-side assembly)
    assert engine._connect_kwargs["config"].connect_timeout == 60
    assert engine._connect_kwargs["config"].read_timeout == 60

    # Test with custom port
    with mock_s3():
        boto3.client("s3", region_name=_TEST_REGION).create_bucket(Bucket="test-bucket-port")

        engine_with_port = RadosGWStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name="test-bucket-port",
            region_name=_TEST_REGION,
            port=8080,
        )

        assert (
            engine_with_port._connect_kwargs["endpoint_url"]
            == f"https://s3.{_TEST_REGION}.amazonaws.com:8080"
        )


def test_radosgw_error_handling():
    """Test error handling for various failure scenarios (Acceptance Criteria Test 10)."""
    with mock_s3():
        # Create an engine but not the bucket
        engine = RadosGWStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name="nonexistent-bucket",
            region_name=_TEST_REGION,
        )

        # Test missing bucket error
        with pytest.raises(IOError):
            engine.stream_write(_TEST_PATH, BytesIO(b"test data"), content_type="text/plain")

        # Test exists() on missing bucket
        with pytest.raises(botocore.exceptions.ClientError):
            engine.exists(_TEST_PATH)


def test_radosgw_timeout_configuration():
    """Test timeout configuration for client-side vs server-side assembly."""
    with mock_s3():
        # Server-side assembly: 60s timeout
        engine_server_side = RadosGWStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name=_TEST_BUCKET,
            server_side_assembly=True,
        )
        assert engine_server_side._connect_kwargs["config"].connect_timeout == 60
        assert engine_server_side._connect_kwargs["config"].read_timeout == 60

        # Client-side assembly: 600s timeout
        engine_client_side = RadosGWStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name=_TEST_BUCKET,
            server_side_assembly=False,
        )
        assert engine_client_side._connect_kwargs["config"].connect_timeout == 600
        assert engine_client_side._connect_kwargs["config"].read_timeout == 600
