import pytest

from contextlib import contextmanager
from mock import patch
from moto import mock_s3_deprecated as mock_s3
import boto

from app import config_provider
from storage import CloudFrontedS3Storage, StorageContext
from util.ipresolver import IPResolver
from util.ipresolver.test.test_ipresolver import (
    fake_aws_ip,
    aws_ip_range_data,
    fake_ip_range_cache,
    fake_aws_someregion_ip,
)
from test.fixtures import *

_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "some_bucket"
_TEST_USER = "someuser"
_TEST_PASSWORD = "somepassword"
_TEST_PATH = "some/cool/path"


@pytest.fixture(params=[True, False])
def ipranges_populated(request):
    return request.param


@pytest.fixture()
def fake_empty_ip_range_cache(empty_range_data):
    sync_token = empty_range_data["syncToken"]
    fake_cache = {
        "sync_token": sync_token,
        "all_amazon": [],
        "by_region": [],
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
    fake_aws_ip,
    fake_empty_ip_range_cache,
    fake_ip_range_cache,
    aws_ip_range_data,
    ipranges_populated,
    app,
):
    ipresolver = IPResolver(app)
    if ipranges_populated:
        ipresolver.sync_token = (
            fake_ip_range_cache["sync_token"]
            if ipranges_populated
            else fake_empty_ip_range_cache["sync_token"]
        )
        ipresolver.amazon_ranges = (
            fake_ip_range_cache["all_amazon"]
            if ipranges_populated
            else fake_empty_ip_range_cache["all_amazon"]
        )
        context = StorageContext("nyc", None, config_provider, ipresolver)

        # Create a test bucket and put some test content.
        boto.connect_s3().create_bucket(_TEST_BUCKET)

        engine = CloudFrontedS3Storage(
            context,
            "cloudfrontdomain",
            "keyid",
            "test/data/test.pem",
            "some/path",
            _TEST_BUCKET,
            s3_access_key=_TEST_USER,
            s3_secret_key=_TEST_PASSWORD,
        )
        engine.put_content(_TEST_PATH, _TEST_CONTENT)
        assert engine.exists(_TEST_PATH)

        # Request a direct download URL for a request from a known AWS IP, and ensure we are returned an S3 URL.
        assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH, fake_aws_ip)

        if ipranges_populated:
            # Request a direct download URL for a request from a non-AWS IP, and ensure we are returned a CloudFront URL.
            assert "cloudfrontdomain" in engine.get_direct_download_url(_TEST_PATH, "1.2.3.4")
        else:
            # Request a direct download URL for a request from a non-AWS IP, but since IP Ranges isn't populated, we still
            # get back an S3 URL.
            assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH, "1.2.3.4")


@mock_s3
def test_direct_download_no_ip(fake_aws_ip, aws_ip_range_data, ipranges_populated, app):
    ipresolver = IPResolver(app)
    context = StorageContext("nyc", None, config_provider, ipresolver)

    # Create a test bucket and put some test content.
    boto.connect_s3().create_bucket(_TEST_BUCKET)

    engine = CloudFrontedS3Storage(
        context,
        "cloudfrontdomain",
        "keyid",
        "test/data/test.pem",
        "some/path",
        _TEST_BUCKET,
        s3_access_key=_TEST_USER,
        s3_secret_key=_TEST_PASSWORD,
    )
    engine.put_content(_TEST_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_PATH)
    assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH)


@mock_s3
def test_direct_download_blacklisted_region(
    fake_aws_someregion_ip, fake_ip_range_cache, ipranges_populated, app
):
    ipresolver = IPResolver(app)
    ipresolver.amazon_ranges = fake_ip_range_cache["all_amazon"]
    ipresolver.amazon_ranges_by_region = fake_ip_range_cache["by_region"]

    context = StorageContext("nyc", None, config_provider, ipresolver)

    # Create a test bucket and put some test content.
    boto.connect_s3().create_bucket(_TEST_BUCKET)

    # Try pulling the `someregion` IP without a blacklist.
    engine = CloudFrontedS3Storage(
        context,
        "cloudfrontdomain",
        "keyid",
        "test/data/test.pem",
        "some/path",
        _TEST_BUCKET,
        s3_access_key=_TEST_USER,
        s3_secret_key=_TEST_PASSWORD,
    )
    engine.put_content(_TEST_PATH, _TEST_CONTENT)
    assert engine.exists(_TEST_PATH)

    assert "s3.amazonaws.com" in engine.get_direct_download_url(_TEST_PATH, fake_aws_someregion_ip)

    # Now try with the blacklist.
    engine = CloudFrontedS3Storage(
        context,
        "cloudfrontdomain",
        "keyid",
        "test/data/test.pem",
        "some/path",
        _TEST_BUCKET,
        s3_access_key=_TEST_USER,
        s3_secret_key=_TEST_PASSWORD,
        cloudfront_force_cf_aws_regions=["someregion"],
    )
    assert "cloudfrontdomain" in engine.get_direct_download_url(_TEST_PATH, fake_aws_someregion_ip)
