import pytest

from contextlib import contextmanager
from mock import patch
from moto import mock_s3
import boto3

from app import config_provider
from storage import CloudFrontedS3Storage, StorageContext
from util.ipresolver import IPResolver
from util.ipresolver.test.test_ipresolver import test_aws_ip, aws_ip_range_data, test_ip_range_cache
from test.fixtures import *

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "somebucket"
_TEST_USER = "someuser"
_TEST_PASSWORD = "somepassword"
_TEST_PATH = "some/cool/path"


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
            _TEST_USER,
            _TEST_PASSWORD,
        )
        engine.put_content(_TEST_PATH, _TEST_CONTENT)
        assert engine.exists(_TEST_PATH)

        # Request a direct download URL for a request from a known AWS IP, and ensure we are returned an S3 URL.
        assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH, test_aws_ip)

        if ipranges_populated:
            # Request a direct download URL for a request from a non-AWS IP, and ensure we are returned a CloudFront URL.
            assert "cloudfrontdomain" in engine.get_direct_download_url(_TEST_PATH, "1.2.3.4")
        else:
            # Request a direct download URL for a request from a non-AWS IP, but since IP Ranges isn't populated, we still
            # get back an S3 URL.
            assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH, "1.2.3.4")


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
        _TEST_USER,
        _TEST_PASSWORD,
    )
    engine.put_content(_TEST_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_PATH)
    assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH)
