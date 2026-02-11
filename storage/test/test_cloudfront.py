import os
import urllib.parse
from contextlib import contextmanager
from unittest.mock import MagicMock

import boto3
import pytest
from cryptography import exceptions as crypto_exceptions
from mock import patch
from moto import mock_s3

from app import config_provider
from storage import CloudFlareS3Storage, CloudFrontedS3Storage, StorageContext
from test.fixtures import *
from util.ipresolver import IPResolver

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "somebucket"
_TEST_REGION = "us-east-1"
_TEST_USER = "someuser"
_TEST_PASSWORD = "somepassword"
_TEST_PATH = "some/cool/path"
_TEST_REPO = "somerepo"


@pytest.fixture(params=[True, False])
def ipranges_populated(request):
    return request.param


@pytest.fixture()
def test_empty_ip_range_cache(empty_range_data):
    sync_token = empty_range_data["syncToken"]
    all_amazon = IPResolver._parse_amazon_ranges(empty_range_data)
    return {
        "sync_token": sync_token,
    }


@pytest.fixture()
def empty_range_data():
    return {
        "syncToken": 123456789,
        "prefixes": [],
    }


@mock_s3
def test_direct_download(
    test_aws_ip,
    test_empty_ip_range_cache,
    test_ip_range_cache,
    aws_ip_range_data,
    ipranges_populated,
    mock_ipresolver,
):
    ipresolver = mock_ipresolver
    if ipranges_populated:
        ipresolver.sync_token = (
            test_ip_range_cache["sync_token"]
            if ipranges_populated
            else test_empty_ip_range_cache["sync_token"]
        )
        ipresolver.amazon_ranges = (
            test_ip_range_cache["all_amazon"]
            if ipranges_populated
            else test_empty_ip_range_cache["all_amazon"]
        )
        context = StorageContext("nyc", None, config_provider, ipresolver)

        # Create a test bucket and put some test content.
        boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)

        engine = CloudFrontedS3Storage(
            context,
            "cloudfrontdomain",
            "keyid",
            "test/data/test.pem",
            "some/path",
            _TEST_BUCKET,
            _TEST_REGION,
            None,
            _TEST_USER,
            _TEST_PASSWORD,
        )
        engine.put_content(_TEST_PATH, _TEST_CONTENT)
        assert engine.exists(_TEST_PATH)

        # Request a direct download URL for a request from a known AWS IP but not in the same region, returned CloudFront URL.
        assert "cloudfrontdomain" in engine.get_direct_download_url(_TEST_PATH, test_aws_ip)

        # Request a direct download URL for a request from a known AWS IP and in the same region, returned S3 URL.
        # with initializing the boto library through super on a region we shall never have a return of s3.amazonaws.com
        assert f"s3.{_TEST_REGION}.amazonaws.com" in engine.get_direct_download_url(
            _TEST_PATH, "4.0.0.2"
        )

        if ipranges_populated:
            # Request a direct download URL for a request from a non-AWS IP, and ensure we are returned a CloudFront URL.
            assert "cloudfrontdomain" in engine.get_direct_download_url(_TEST_PATH, "1.2.3.4")
        else:
            # Request a direct download URL for a request from a non-AWS IP, but since IP Ranges isn't populated, we still
            # get back an S3 URL.
            # with initializing the boto library through super on a region we shall never have a return of s3.amazonaws.com
            assert f"s3.{_TEST_REGION}.amazonaws.com" in engine.get_direct_download_url(
                _TEST_PATH, "1.2.3.4"
            )

        engine = CloudFrontedS3Storage(
            context,
            "defaultdomain",
            "keyid",
            "test/data/test.pem",
            "some/path",
            _TEST_BUCKET,
            _TEST_REGION,
            {"testnamespace": "overridedomain"},
            _TEST_USER,
            _TEST_PASSWORD,
        )

        engine.put_content(_TEST_PATH, _TEST_CONTENT)
        assert engine.exists(_TEST_PATH)

        # Request a direct download URL for a request from a known AWS IP but not in the same region, returned CloudFront URL.
        assert "overridedomain" in engine.get_direct_download_url(
            _TEST_PATH, test_aws_ip, namespace="testnamespace"
        )

        assert "defaultdomain" in engine.get_direct_download_url(
            _TEST_PATH, test_aws_ip, namespace="defaultnamespace"
        )

        # Request a direct download URL for a request from a known AWS IP and in the same region, returned S3 URL.
        # with initializing the boto library through super on a region we shall never have a return of s3.amazonaws.com
        assert f"s3.{_TEST_REGION}.amazonaws.com" in engine.get_direct_download_url(
            _TEST_PATH, "4.0.0.2", namespace="testnamespace"
        )

        if ipranges_populated:
            # Request a direct download URL for a request from a non-AWS IP, and ensure we are returned a CloudFront URL.
            assert "overridedomain" in engine.get_direct_download_url(
                _TEST_PATH, "1.2.3.4", namespace="testnamespace"
            )
        else:
            # Request a direct download URL for a request from a non-AWS IP, but since IP Ranges isn't populated, we still
            # get back an S3 URL.
            # with initializing the boto library through super on a region we shall never have a return of s3.amazonaws.com
            assert f"s3.{_TEST_REGION}.amazonaws.com" in engine.get_direct_download_url(
                _TEST_PATH, "1.2.3.4", namespace="testnamespace"
            )


@mock_s3
def test_direct_download_no_ip(test_aws_ip, aws_ip_range_data, ipranges_populated, mock_ipresolver):
    ipresolver = mock_ipresolver
    context = StorageContext("nyc", None, config_provider, ipresolver)

    # Create a test bucket and put some test content.
    boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)

    engine = CloudFrontedS3Storage(
        context,
        "cloudfrontdomain",
        "keyid",
        "test/data/test.pem",
        "some/path",
        _TEST_BUCKET,
        _TEST_REGION,
        None,
        _TEST_USER,
        _TEST_PASSWORD,
    )
    engine.put_content(_TEST_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_PATH)
    # with initializing the boto library through super on a region we shall never have a return of s3.amazonaws.com
    assert f"s3.{_TEST_REGION}.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH)


@mock_s3
def test_direct_download_with_username(
    test_aws_ip, aws_ip_range_data, ipranges_populated, mock_ipresolver
):
    ipresolver = mock_ipresolver
    context = StorageContext("nyc", None, config_provider, ipresolver)

    # Create a test bucket and put some test content.
    boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)

    engine = CloudFrontedS3Storage(
        context,
        "cloudfrontdomain",
        "keyid",
        "test/data/test.pem",
        "some/path",
        _TEST_BUCKET,
        _TEST_REGION,
        None,
        _TEST_USER,
        _TEST_PASSWORD,
    )
    engine.put_content(_TEST_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_PATH)
    url = engine.get_direct_download_url(_TEST_PATH, request_ip="1.2.3.4", username=_TEST_USER)
    assert f"username={_TEST_USER}" in url


@mock_s3
def test_direct_download_with_repo_name(
    test_aws_ip, aws_ip_range_data, ipranges_populated, mock_ipresolver
):
    ipresolver = mock_ipresolver
    context = StorageContext("nyc", None, config_provider, ipresolver)

    # Create a test bucket and put some test content.
    boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)

    engine = CloudFrontedS3Storage(
        context,
        "cloudfrontdomain",
        "keyid",
        "test/data/test.pem",
        "some/path",
        _TEST_BUCKET,
        _TEST_REGION,
        None,
        _TEST_USER,
        _TEST_PASSWORD,
    )
    engine.put_content(_TEST_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_PATH)
    url = engine.get_direct_download_url(_TEST_PATH, request_ip="1.2.3.4", repo_name=_TEST_REPO)
    assert f"repo_name={_TEST_REPO}" in url


@mock_s3
def test_direct_download_cdn_specific(ipranges_populated, test_ip_range_cache, mock_ipresolver):
    ipresolver = mock_ipresolver
    if ipranges_populated:
        ipresolver.sync_token = test_ip_range_cache["sync_token"]
        ipresolver.amazon_ranges = test_ip_range_cache["all_amazon"]
        context = StorageContext("nyc", None, config_provider, ipresolver)

        # Create a test bucket and put some test content.
        boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)

        engine = CloudFlareS3Storage(
            context,
            "cloudflare-domain",
            "test/data/test.pem",
            "some/path",
            _TEST_BUCKET,
            _TEST_REGION,
            None,
        )

        engine.put_content(_TEST_PATH, _TEST_CONTENT)
        assert engine.exists(_TEST_PATH)
        assert "amazonaws.com" in engine.get_direct_download_url(
            _TEST_PATH, request_ip="4.0.0.2", cdn_specific=False
        )
        assert "cloudflare-domain" in engine.get_direct_download_url(
            _TEST_PATH, request_ip="4.0.0.2", cdn_specific=True
        )


@mock_s3
def test_direct_download_regions(
    mock_ipresolver,
):
    ipresolver = mock_ipresolver
    context = StorageContext("nyc", None, config_provider, ipresolver)
    # Create a test bucket and put some test content.
    boto3.client("s3").create_bucket(Bucket="bucket")
    for region_name in boto3.Session("s3").get_available_regions("s3"):
        engine = CloudFlareS3Storage(
            context,
            "cloudflare-domain",
            "test/data/test.pem",
            "some/path",
            "bucket",
            region_name,
            None,
        )
        presign = engine.get_direct_download_url(
            "some/path", request_ip="4.0.0.2", cdn_specific=False
        )
        parsed = urllib.parse.urlparse(presign)
        region = urllib.parse.unquote(parsed.query.split("&")[1]).split("/")[2]
        assert region == region_name


@mock_s3
def test_rsa_sha1_fallback_when_crypto_policy_blocks_sha1(
    test_aws_ip, aws_ip_range_data, ipranges_populated, app
):
    """Verify CloudFront URL signing falls back to pure-Python rsa library
    when the system crypto policy blocks SHA-1 (e.g., RHEL9)."""
    ipresolver = IPResolver(app)
    context = StorageContext("nyc", None, config_provider, ipresolver)

    boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)

    engine = CloudFrontedS3Storage(
        context,
        "cloudfrontdomain",
        "keyid",
        "test/data/test.pem",
        "some/path",
        _TEST_BUCKET,
        _TEST_REGION,
        None,
        _TEST_USER,
        _TEST_PASSWORD,
    )
    engine.put_content(_TEST_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_PATH)

    # Clear the cached signer so our mock takes effect
    engine._get_rsa_signer.cache_clear()
    engine._get_cloudfront_signer.cache_clear()

    # Build a mock private key that raises UnsupportedAlgorithm on sign()
    # but delegates private_numbers() to the real key, so the rsa fallback
    # can extract key material.
    real_key = engine.cloudfront_privatekey
    mock_key = MagicMock()
    mock_key.sign.side_effect = crypto_exceptions.UnsupportedAlgorithm(
        "SHA1 blocked by crypto policy"
    )
    mock_key.private_numbers.return_value = real_key.private_numbers()
    engine.cloudfront_privatekey = mock_key

    url = engine.get_direct_download_url(_TEST_PATH, request_ip="1.2.3.4")

    assert "cloudfrontdomain" in url
    assert "Signature=" in url or "Signature" in url
    assert "Key-Pair-Id=keyid" in url
