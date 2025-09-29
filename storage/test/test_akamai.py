import os
from urllib.parse import parse_qs, urlparse

import boto3
import pytest
from moto import mock_s3

from app import config_provider
from storage import AkamaiS3Storage, StorageContext
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
        # Request a direct download URL for a request from a known AWS IP and in the same region, returned S3 URL.
        assert engine.get_direct_download_url(_TEST_PATH, request_ip="4.0.0.2").startswith(
            "https://s3.us-east-1.amazonaws.com"
        )
        # Request a direct download URL for a request from a non-AWS IP, and ensure we are returned Akamai URL.
        assert engine.get_direct_download_url(_TEST_PATH, "1.2.3.4").startswith(
            "https://akamai-domain"
        )

        assert engine.get_direct_download_url(
            _TEST_PATH, request_ip="4.0.0.2", cdn_specific=False
        ).startswith("https://s3.us-east-1.amazonaws.com")
        assert engine.get_direct_download_url(
            _TEST_PATH, request_ip="4.0.0.2", cdn_specific=True
        ).startswith("https://akamai-domain")
        assert engine.get_direct_download_url(_TEST_PATH).startswith(
            "https://s3.us-east-1.amazonaws.com"
        )

        engine = AkamaiS3Storage(
            context,
            "akamai-domain",
            "eee7e9157f81b2f6d471bf2c",
            "some/path",
            _TEST_BUCKET,
            _TEST_REGION,
            "88b91ccead2baffe122df4b5e23d720d",  # akamai encryption key
        )
        engine.put_content(_TEST_PATH, _TEST_CONTENT)
        download_url = engine.get_direct_download_url(
            _TEST_PATH, request_ip="4.0.0.2", cdn_specific=True
        )
        parsed_url = urlparse(download_url)
        query_params = parse_qs(parsed_url.query)

        assert query_params.get("initializationVector", None) is not None
        assert query_params.get("X-Amz-Signature", None) is not None
        assert query_params.get("akamai_signature", None) is not None
