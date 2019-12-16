import pytest

from mock import patch

from util.ipresolver import IPResolver, ResolvedLocation
from test.fixtures import *


@pytest.fixture()
def test_aws_ip():
    return "10.0.0.1"


@pytest.fixture()
def aws_ip_range_data():
    fake_range_doc = {
        "syncToken": 123456789,
        "prefixes": [
            {"ip_prefix": "10.0.0.0/8", "region": "GLOBAL", "service": "EC2",},
            {"ip_prefix": "6.0.0.0/8", "region": "GLOBAL", "service": "EC2",},
        ],
    }
    return fake_range_doc


@pytest.fixture()
def test_ip_range_cache(aws_ip_range_data):
    sync_token = aws_ip_range_data["syncToken"]
    all_amazon = IPResolver._parse_amazon_ranges(aws_ip_range_data)
    fake_cache = {
        "sync_token": sync_token,
        "all_amazon": all_amazon,
    }
    return fake_cache


def test_resolved(aws_ip_range_data, test_ip_range_cache, test_aws_ip, app):
    ipresolver = IPResolver(app)
    ipresolver.amazon_ranges = test_ip_range_cache["all_amazon"]
    ipresolver.sync_token = test_ip_range_cache["sync_token"]

    assert ipresolver.resolve_ip(test_aws_ip) == ResolvedLocation(
        provider="aws", service=None, sync_token=123456789, country_iso_code=None
    )
    assert ipresolver.resolve_ip("10.0.0.2") == ResolvedLocation(
        provider="aws", service=None, sync_token=123456789, country_iso_code=None
    )
    assert ipresolver.resolve_ip("6.0.0.2") == ResolvedLocation(
        provider="aws", service=None, sync_token=123456789, country_iso_code="US"
    )
    assert ipresolver.resolve_ip("1.2.3.4") == ResolvedLocation(
        provider="internet", service="US", sync_token=123456789, country_iso_code="US"
    )
    assert ipresolver.resolve_ip("127.0.0.1") == ResolvedLocation(
        provider="internet", service=None, sync_token=123456789, country_iso_code=None
    )
