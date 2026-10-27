"""
Covers RadosGWStorage-specific behaviour (custom endpoint, assembly modes, chunk
sizes, presigned URLs, CORS), plus the inherited object, cancel and
partial-upload cleanup operations run through RadosGWStorage. The generic
_CloudStorage behaviour is also covered for S3Storage by test_cloud_storage.py.

RadosGWStorage is the on-premise S3-compatible driver used with backends such as
Ceph RGW, ODF/NooBaa, IBM Storage Scale CES-S3, and similar endpoints.
"""

import os
import unittest.mock
from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import boto3
import pytest
import requests
from freezegun import freeze_time
from moto import mock_s3

from storage import RadosGWStorage, StorageContext
from storage.cloud import _CHUNKS_KEY

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "quay-registry"
_TEST_USER = "someuser"
_TEST_PASSWORD = "somepassword"
_TEST_PATH = "some/cool/path"
_TEST_CONTEXT = StorageContext("nyc", None, None, None)

# Neutral hostnames for endpoint-URL tests.
# _DNS_HOST is a generic example name; _IP_HOST is from the RFC 5737
# documentation range (not a real address).
_DNS_HOST = "s3.example.com"
_IP_HOST = "192.0.2.10"
_PORT = 6443
_CUSTOM_ENDPOINTS = [
    "https://{}:{}".format(_DNS_HOST, _PORT),
    "https://{}:{}".format(_IP_HOST, _PORT),
    "http://{}:{}".format(_IP_HOST, 8008),
]


def _engine(hostname=_DNS_HOST, port=_PORT, is_secure=True, bucket=_TEST_BUCKET, **kwargs):
    return RadosGWStorage(
        _TEST_CONTEXT,
        hostname,
        is_secure,
        "some/path",
        _TEST_USER,
        _TEST_PASSWORD,
        bucket,
        port=port,
        **kwargs,
    )


def _bucket_keys(engine):
    return sorted(obj.key for obj in engine.get_cloud_bucket().objects.all())


def _query_params(url):
    return set(parse_qs(urlparse(url).query))


# Query parameters of a presigned URL. RadosGWStorage signs with SigV2 unless
# signature_version is set (e.g. "s3v4").
_SIGV2_PARAMS = {"AWSAccessKeyId", "Expires", "Signature"}
_SIGV4_PARAMS = {"X-Amz-Algorithm", "X-Amz-Credential", "X-Amz-Expires", "X-Amz-Signature"}


def _create_bucket(endpoint_url, bucket=_TEST_BUCKET):
    boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=_TEST_USER,
        aws_secret_access_key=_TEST_PASSWORD,
        region_name="us-east-1",
    ).create_bucket(Bucket=bucket)


@pytest.fixture(autouse=True)
def custom_endpoints(monkeypatch):
    monkeypatch.setenv("MOTO_S3_CUSTOM_ENDPOINTS", ",".join(_CUSTOM_ENDPOINTS))
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", _TEST_USER)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", _TEST_PASSWORD)


@pytest.fixture(scope="function", params=[True, False], ids=["server_side", "client_side"])
def storage_engine(request):
    with mock_s3():
        _create_bucket(_CUSTOM_ENDPOINTS[0])
        engine = _engine(server_side_assembly=request.param)
        assert engine._connect_kwargs["endpoint_url"] == _CUSTOM_ENDPOINTS[0]
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        yield engine


@pytest.mark.parametrize(
    "hostname, port, is_secure, expected",
    [
        pytest.param(_DNS_HOST, _PORT, True, "https://s3.example.com:6443", id="dns-https"),
        pytest.param(_IP_HOST, _PORT, True, "https://192.0.2.10:6443", id="ip-https"),
        pytest.param(_IP_HOST, 8008, False, "http://192.0.2.10:8008", id="ip-http"),
        pytest.param(_DNS_HOST, None, True, "https://s3.example.com", id="no-port"),
    ],
)
def test_endpoint_url(hostname, port, is_secure, expected):
    engine = _engine(hostname=hostname, port=port, is_secure=is_secure)
    assert engine._connect_kwargs["endpoint_url"] == expected


@pytest.mark.parametrize(
    "server_side_assembly, timeout",
    [
        pytest.param(True, 60, id="server_side"),
        pytest.param(False, 600, id="client_side"),
    ],
)
def test_timeouts_follow_assembly_mode(server_side_assembly, timeout):
    engine = _engine(server_side_assembly=server_side_assembly)
    config = engine._connect_kwargs["config"]
    assert config.connect_timeout == timeout
    assert config.read_timeout == timeout
    assert engine.server_side_assembly is server_side_assembly


@pytest.mark.parametrize(
    "kwargs, min_mb, max_mb",
    [
        pytest.param({}, 5, 100, id="defaults"),
        pytest.param(
            {"minimum_chunk_size_mb": 10, "maximum_chunk_size_mb": 200}, 10, 200, id="set"
        ),
    ],
)
def test_chunk_size_settings(kwargs, min_mb, max_mb):
    engine = _engine(**kwargs)
    assert engine.minimum_chunk_size == min_mb * 1024 * 1024
    assert engine.maximum_chunk_size == max_mb * 1024 * 1024


def test_object_lifecycle(storage_engine):
    path = "some/object/path"
    assert not storage_engine.exists(path)

    storage_engine.put_content(path, _TEST_CONTENT)
    assert storage_engine.exists(path)
    assert storage_engine.get_content(path) == _TEST_CONTENT
    assert b"".join(storage_engine.stream_read(path)) == _TEST_CONTENT

    storage_engine.remove(path)
    assert not storage_engine.exists(path)
    # Only the fixture's object is left in the bucket.
    assert _bucket_keys(storage_engine) == [storage_engine._init_path(_TEST_PATH)]


@pytest.mark.parametrize("chunk_count", [0, 1, 2, 50])
def test_chunk_upload(request, storage_engine, chunk_count):
    # 1 KiB chunks are below the 5 MiB minimum_chunk_size, so multi-chunk cases
    # (chunk_count >= 2) fall back to client-side join even in server_side mode.
    # Server-side multipart assembly for chunks that meet the minimum is covered
    # by test_server_side_assembly_multi_chunk.
    if chunk_count == 0 and not storage_engine.server_side_assembly:
        # client-side assembly of an empty chunk list raises StopIteration
        # inside _client_side_chunk_join() (PROJQUAY-13782); strict, so the fix
        # surfaces as an unexpected pass and this marker gets removed.
        request.applymarker(
            pytest.mark.xfail(
                raises=StopIteration,
                strict=True,
                reason="PROJQUAY-13782: client-side assembly of a zero-chunk upload raises StopIteration",
            )
        )

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

    # RadosGWStorage decides server-side vs client-side assembly from its own setting.
    storage_engine.complete_chunked_upload(upload_id, "some/chunked/path", metadata)

    if chunk_count != 0:
        assert storage_engine.get_content("some/chunked/path") == final_data


@pytest.mark.parametrize("chunk_count", [1, 3])
def test_cancel_chunked_upload(storage_engine, chunk_count):
    upload_id, metadata = storage_engine.initiate_chunked_upload()
    for _ in range(chunk_count):
        chunk_data = os.urandom(1024)
        _, metadata, error = storage_engine.stream_upload_chunk(
            upload_id, 0, len(chunk_data), BytesIO(chunk_data), metadata
        )
        assert error is None

    chunk_paths = [chunk.path for chunk in metadata[_CHUNKS_KEY]]
    assert len(chunk_paths) == chunk_count
    for chunk_path in chunk_paths:
        assert chunk_path.startswith("uploads/")
        assert storage_engine.exists(chunk_path)

    storage_engine.cancel_chunked_upload(upload_id, metadata)

    for chunk_path in chunk_paths:
        assert not storage_engine.exists(chunk_path)
    # No final object was created and no temporary uploads/ objects are left.
    assert _bucket_keys(storage_engine) == [storage_engine._init_path(_TEST_PATH)]


def test_clean_partial_uploads(storage_engine):
    stale_path = "uploads/stale-upload"
    fresh_path = "uploads/fresh-upload"

    with freeze_time(datetime.now(timezone.utc) - timedelta(days=3)):
        storage_engine.put_content(stale_path, _TEST_CONTENT)
    storage_engine.put_content(fresh_path, _TEST_CONTENT)

    storage_engine.clean_partial_uploads(timedelta(days=2))

    assert not storage_engine.exists(stale_path)
    assert storage_engine.exists(fresh_path)
    # Objects outside uploads/ are never touched.
    assert storage_engine.get_content(_TEST_PATH) == _TEST_CONTENT


def test_server_side_assembly_multi_chunk(storage_engine):
    """Two chunks, each at least minimum_chunk_size bytes.

    When server_side_assembly is True the chunks are assembled via S3
    multipart-copy (UploadPartCopy) and _client_side_chunk_join must NOT be
    called.  When server_side_assembly is False the chunks are joined locally
    and _client_side_chunk_join MUST be called.
    """
    min_size = storage_engine.minimum_chunk_size
    chunk_sizes = [min_size, min_size + 10]

    upload_id, metadata = storage_engine.initiate_chunked_upload()
    all_data = b""
    for size in chunk_sizes:
        chunk_data = os.urandom(size)
        all_data += chunk_data
        bytes_written, metadata, error = storage_engine.stream_upload_chunk(
            upload_id, 0, len(chunk_data), BytesIO(chunk_data), metadata
        )
        assert bytes_written == len(chunk_data)
        assert error is None

    with unittest.mock.patch.object(
        storage_engine,
        "_client_side_chunk_join",
        wraps=storage_engine._client_side_chunk_join,
    ) as mock_join:
        storage_engine.complete_chunked_upload(upload_id, "some/multi/path", metadata)

    if storage_engine.server_side_assembly:
        mock_join.assert_not_called()
    else:
        mock_join.assert_called_once()

    assert storage_engine.get_content("some/multi/path") == all_data


def test_large_chunks_with_ragged_edge(storage_engine):
    storage_engine.maximum_chunk_size = storage_engine.minimum_chunk_size * 2 + 10

    upload_id, metadata = storage_engine.initiate_chunked_upload()

    all_data = b""
    for _ in range(0, 2):
        chunk_data = os.urandom(int(storage_engine.maximum_chunk_size) + 20)
        bytes_written, new_metadata, _ = storage_engine.stream_upload_chunk(
            upload_id, 0, -1, BytesIO(chunk_data), metadata
        )
        assert len(chunk_data) == bytes_written
        all_data = all_data + chunk_data
        metadata = new_metadata

    storage_engine.complete_chunked_upload(upload_id, "some/chunked/path", new_metadata)

    assert storage_engine.get_content("some/chunked/path") == all_data


@pytest.mark.parametrize(
    "endpoint_index, hostname, port, is_secure",
    [
        pytest.param(0, _DNS_HOST, _PORT, True, id="dns-https"),
        pytest.param(1, _IP_HOST, _PORT, True, id="ip-https"),
        pytest.param(2, _IP_HOST, 8008, False, id="ip-http"),
    ],
)
def test_presigned_download_url_uses_custom_endpoint(endpoint_index, hostname, port, is_secure):
    with mock_s3():
        endpoint = _CUSTOM_ENDPOINTS[endpoint_index]
        _create_bucket(endpoint)
        engine = _engine(hostname=hostname, port=port, is_secure=is_secure)
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        url = engine.get_direct_download_url(_TEST_PATH, expires_in=300)
        parsed = urlparse(url)

        # Clients are redirected to the S3 endpoint itself (path-style for an IP address).
        assert parsed.scheme == ("https" if is_secure else "http")
        assert parsed.port == port
        assert hostname in parsed.netloc
        assert _SIGV2_PARAMS <= _query_params(url)

        # The presigned URL works without credentials.
        response = requests.get(url)
        assert response.status_code == 200
        assert response.content == _TEST_CONTENT


def test_presigned_urls_skipped_when_cors_required(storage_engine):
    # RadosGW does not support CORS, so CORS-requiring URLs are not handed out.
    assert storage_engine.get_direct_download_url(_TEST_PATH, requires_cors=True) is None
    assert storage_engine.get_direct_upload_url(_TEST_PATH, "Cool/Type", requires_cors=True) is None


def test_presigned_upload_url_without_cors(storage_engine):
    url = storage_engine.get_direct_upload_url(_TEST_PATH, "Cool/Type", requires_cors=False)
    assert url is not None
    assert url.startswith(_CUSTOM_ENDPOINTS[0])
    assert _SIGV2_PARAMS <= _query_params(url)


def test_presigned_url_sigv4():
    with mock_s3():
        _create_bucket(_CUSTOM_ENDPOINTS[0])
        engine = _engine(signature_version="s3v4")
        engine.put_content(_TEST_PATH, _TEST_CONTENT)

        url = engine.get_direct_download_url(_TEST_PATH, expires_in=300)
        assert url.startswith(_CUSTOM_ENDPOINTS[0])
        params = _query_params(url)
        assert _SIGV4_PARAMS <= params
        assert not params & {"AWSAccessKeyId", "Signature"}

        response = requests.get(url)
        assert response.status_code == 200
        assert response.content == _TEST_CONTENT
