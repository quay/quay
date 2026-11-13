"""
Tests for RHOCSStorage backend.

RHOCSStorage (Red Hat OpenShift Container Storage) is currently a thin wrapper
around RadosGWStorage. These tests verify the wrapper works correctly and
establish baseline for future RHOCS-specific features.
"""

import os
from io import BytesIO

import boto3
import pytest
from moto import mock_s3

from storage import RadosGWStorage, RHOCSStorage, StorageContext
from storage.cloud import _CHUNKS_KEY

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "test-rhocs-bucket"
_TEST_USER = "test-rhocs-user"
_TEST_PASSWORD = "test-rhocs-password"
_TEST_REGION = "us-east-1"
_TEST_PATH = "rhocs/test/path"
_TEST_CONTEXT = StorageContext("rhocs-location", None, None, None)


@pytest.fixture(scope="function")
def rhocs_storage_engine():
    """
    Fixture providing RHOCSStorage instance with mocked S3 backend.

    RHOCSStorage is currently identical to RadosGWStorage but uses a
    distinct driver for future RHOCS-specific capabilities.
    """
    with mock_s3():
        # Create bucket
        boto3.client("s3", region_name=_TEST_REGION).create_bucket(Bucket=_TEST_BUCKET)

        # Initialize RHOCSStorage
        engine = RHOCSStorage(
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


def test_rhocs_basicop(rhocs_storage_engine):
    """Test basic CRUD operations on RHOCSStorage (Acceptance Criteria Test 11)."""
    engine = rhocs_storage_engine

    # Ensure the content exists
    assert engine.exists(_TEST_PATH)

    # Verify it can be retrieved
    assert engine.get_content(_TEST_PATH) == _TEST_CONTENT

    # Retrieve a checksum for the content
    checksum = engine.get_checksum(_TEST_PATH)
    assert checksum is not None

    # Test stream read
    data = b"".join(engine.stream_read(_TEST_PATH))
    assert data == _TEST_CONTENT

    # Test stream write
    new_data = os.urandom(2048)
    engine.stream_write(_TEST_PATH, BytesIO(new_data), content_type="application/octet-stream")
    assert engine.get_content(_TEST_PATH) == new_data

    # Remove the file
    engine.remove(_TEST_PATH)

    # Ensure it no longer exists
    assert not engine.exists(_TEST_PATH)


def test_rhocs_chunk_upload(rhocs_storage_engine):
    """Test chunked upload via RHOCS (Acceptance Criteria Test 12)."""
    engine = rhocs_storage_engine

    # Initiate chunked upload
    upload_id, metadata = engine.initiate_chunked_upload()
    assert upload_id is not None
    final_data = b""

    # Upload chunks
    chunk_count = 5
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

    # Complete the chunked upload
    final_path = "rhocs/chunked/upload"
    engine.complete_chunked_upload(upload_id, final_path, metadata)

    # Verify file exists and has correct content
    assert engine.exists(final_path)
    assert engine.get_content(final_path) == final_data


def test_rhocs_identical_to_radosgw():
    """Verify RHOCS behaves identically to RadosGW (Acceptance Criteria Test 13)."""
    with mock_s3():
        # Create bucket
        boto3.client("s3", region_name=_TEST_REGION).create_bucket(Bucket=_TEST_BUCKET)

        # Create both RHOCS and RadosGW storage engines with identical config
        rhocs_engine = RHOCSStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name=_TEST_BUCKET,
            region_name=_TEST_REGION,
            signature_version="s3v4",
            minimum_chunk_size_mb=10,
            maximum_chunk_size_mb=200,
        )

        radosgw_engine = RadosGWStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name=_TEST_BUCKET,
            region_name=_TEST_REGION,
            signature_version="s3v4",
            minimum_chunk_size_mb=10,
            maximum_chunk_size_mb=200,
        )

        # Verify both engines have identical configuration
        # Compare _connect_kwargs excluding the 'config' object (instances differ but values match)
        rhocs_kwargs = {k: v for k, v in rhocs_engine._connect_kwargs.items() if k != "config"}
        radosgw_kwargs = {k: v for k, v in radosgw_engine._connect_kwargs.items() if k != "config"}
        assert rhocs_kwargs == radosgw_kwargs

        # Verify config objects have matching signature versions
        rhocs_config = rhocs_engine._connect_kwargs.get("config")
        radosgw_config = radosgw_engine._connect_kwargs.get("config")

        # Both engines should always have config objects
        assert rhocs_config is not None, "RHOCS engine missing config object"
        assert radosgw_config is not None, "RadosGW engine missing config object"

        # Verify config objects have matching properties
        assert rhocs_config.signature_version == radosgw_config.signature_version
        assert rhocs_config.connect_timeout == radosgw_config.connect_timeout
        assert rhocs_config.read_timeout == radosgw_config.read_timeout

        assert rhocs_engine.minimum_chunk_size == radosgw_engine.minimum_chunk_size
        assert rhocs_engine.maximum_chunk_size == radosgw_engine.maximum_chunk_size
        assert rhocs_engine.server_side_assembly == radosgw_engine.server_side_assembly

        # Test that basic operations work identically
        test_data = os.urandom(512)
        test_path = "test/identical/behavior"

        # Put content with RHOCS
        rhocs_engine.put_content(test_path, test_data)
        assert rhocs_engine.exists(test_path)
        assert rhocs_engine.get_content(test_path) == test_data

        # Verify RadosGW can read the same content (same bucket)
        assert radosgw_engine.exists(test_path)
        assert radosgw_engine.get_content(test_path) == test_data

        # Verify checksums match
        assert rhocs_engine.get_checksum(test_path) == radosgw_engine.get_checksum(test_path)


def test_rhocs_cors_limitation(rhocs_storage_engine):
    """Test that RHOCS inherits RadosGW CORS limitations."""
    engine = rhocs_storage_engine

    # RHOCS should have the same CORS limitations as RadosGW
    download_url = engine.get_direct_download_url(_TEST_PATH, requires_cors=True)
    assert download_url is None

    upload_url = engine.get_direct_upload_url(_TEST_PATH, "application/octet-stream")
    assert upload_url is None

    # Without CORS requirement, URLs should work
    upload_url_no_cors = engine.get_direct_upload_url(
        _TEST_PATH, "application/octet-stream", requires_cors=False
    )
    assert upload_url_no_cors is not None


def test_rhocs_inheritance():
    """Test that RHOCSStorage is a subclass of RadosGWStorage."""
    assert issubclass(RHOCSStorage, RadosGWStorage)

    with mock_s3():
        boto3.client("s3", region_name=_TEST_REGION).create_bucket(Bucket=_TEST_BUCKET)

        engine = RHOCSStorage(
            _TEST_CONTEXT,
            hostname=f"s3.{_TEST_REGION}.amazonaws.com",
            is_secure=True,
            storage_path="/quay",
            access_key=_TEST_USER,
            secret_key=_TEST_PASSWORD,
            bucket_name=_TEST_BUCKET,
        )

        # Verify it's an instance of both RHOCSStorage and RadosGWStorage
        assert isinstance(engine, RHOCSStorage)
        assert isinstance(engine, RadosGWStorage)
