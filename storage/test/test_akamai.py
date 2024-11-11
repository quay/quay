import os

import boto3
import pytest
from moto import mock_s3

from app import config_provider
from storage import AkamaiS3Storage, StorageContext
from test.fixtures import *
from util.ipresolver import IPResolver
from util.ipresolver.test.test_ipresolver import aws_ip_range_data, test_ip_range_cache

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


@mock_s3
def test_direct_download_cdn_specific(ipranges_populated, test_ip_range_cache, app):
    ipresolver = IPResolver(app)
    if ipranges_populated:
        ipresolver.sync_token = test_ip_range_cache["sync_token"]
        ipresolver.amazon_ranges = test_ip_range_cache["all_amazon"]
        context = StorageContext("nyc", None, config_provider, ipresolver)

        # Create a test bucket and put some test content.
        boto3.client("s3").create_bucket(Bucket=_TEST_BUCKET)

        engine = AkamaiS3Storage(
            context,
            "akamai-domain",
            "eee7e9157f81b2f6d471bf2c",
            "some/path",
            _TEST_BUCKET,
            _TEST_REGION,
            None,
        )

        engine.put_content(_TEST_PATH, _TEST_CONTENT)
        assert engine.exists(_TEST_PATH)
        assert "akamai-domain" in engine.get_direct_download_url(_TEST_PATH, request_ip="4.0.0.2")
