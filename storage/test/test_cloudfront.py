import os
from contextlib import contextmanager

import boto3
import pytest
from mock import patch
from moto import mock_s3

from app import config_provider
from storage import CloudFlareS3Storage, CloudFrontedS3Storage, StorageContext
from test.fixtures import *
from util.ipresolver import IPResolver
from util.ipresolver.test.test_ipresolver import (
    aws_ip_range_data,
    test_aws_ip,
    test_ip_range_cache,
)

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
    fake_cache = {
        "sync_token": sync_token,
    }
    return fake_cache


@pytest.fixture()
def empty_range_data():
    empty_range_data = {
        "syncToken": 123456789,
        "prefixes": [],
    }
    return empty_range_data


@mock_s3
def test_direct_download(
    test_aws_ip,
    test_empty_ip_range_cache,
    test_ip_range_cache,
    aws_ip_range_data,
    ipranges_populated,
    app,
):
    ipresolver = IPResolver(app)
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
        assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH, "4.0.0.2")

        if ipranges_populated:
            # Request a direct download URL for a request from a non-AWS IP, and ensure we are returned a CloudFront URL.
            assert "cloudfrontdomain" in engine.get_direct_download_url(_TEST_PATH, "1.2.3.4")
        else:
            # Request a direct download URL for a request from a non-AWS IP, but since IP Ranges isn't populated, we still
            # get back an S3 URL.
            assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH, "1.2.3.4")

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
        assert "s3.amazonaws.com" in engine.get_direct_download_url(
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
            assert "s3.amazonaws.com" in engine.get_direct_download_url(
                _TEST_PATH, "1.2.3.4", namespace="testnamespace"
            )


@mock_s3
def test_direct_download_no_ip(test_aws_ip, aws_ip_range_data, ipranges_populated, app):
    ipresolver = IPResolver(app)
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
    assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH)


@mock_s3
def test_direct_download_with_username(test_aws_ip, aws_ip_range_data, ipranges_populated, app):
    ipresolver = IPResolver(app)
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
def test_direct_download_with_repo_name(test_aws_ip, aws_ip_range_data, ipranges_populated, app):
    ipresolver = IPResolver(app)
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
def test_direct_download_cdn_specific(ipranges_populated, test_ip_range_cache, app):
    ipresolver = IPResolver(app)
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
