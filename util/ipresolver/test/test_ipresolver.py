import pytest

from mock import patch

from util.ipresolver import IPResolver, ResolvedLocation
from test.fixtures import *


@pytest.fixture()
def fake_aws_ip():
    return "10.0.0.1"


@pytest.fixture()
def fake_aws_someregion_ip():
    return "3.0.0.1"


@pytest.fixture()
def aws_ip_range_data():
    fake_range_doc = {
        "syncToken": 123456789,
        "prefixes": [
            {"ip_prefix": "10.0.0.0/8", "region": "GLOBAL", "service": "EC2",},
            {"ip_prefix": "6.0.0.0/8", "region": "GLOBAL", "service": "EC2",},
            {"ip_prefix": "3.0.0.0/8", "region": "someregion", "service": "EC2",},
        ],
    }
    return fake_range_doc


@pytest.fixture()
def fake_ip_range_cache(aws_ip_range_data):
    sync_token = aws_ip_range_data["syncToken"]
    all_amazon, by_region = IPResolver._parse_amazon_ranges(aws_ip_range_data)
    fake_cache = {
        "sync_token": sync_token,
        "all_amazon": all_amazon,
        "by_region": by_region,
    }
    return fake_cache


def test_resolved(aws_ip_range_data, fake_ip_range_cache, fake_aws_ip, app):
    ipresolver = IPResolver(app)
    ipresolver.amazon_ranges = fake_ip_range_cache["all_amazon"]
    ipresolver.amazon_ranges_by_region = fake_ip_range_cache["by_region"]
    ipresolver.sync_token = fake_ip_range_cache["sync_token"]

    assert ipresolver.resolve_ip(fake_aws_ip) == ResolvedLocation(
        provider="aws", service=None, sync_token=123456789, country_iso_code=None
    )
    assert ipresolver.resolve_ip("10.0.0.2") == ResolvedLocation(
        provider="aws", service=None, sync_token=123456789, country_iso_code=None
    )
    assert ipresolver.resolve_ip("6.0.0.2") == ResolvedLocation(
        provider="aws", service=None, sync_token=123456789, country_iso_code=u"US"
    )
    assert ipresolver.resolve_ip("1.2.3.4") == ResolvedLocation(
        provider="internet", service=u"US", sync_token=123456789, country_iso_code=u"US"
    )
    assert ipresolver.resolve_ip("127.0.0.1") == ResolvedLocation(
        provider="internet", service=None, sync_token=123456789, country_iso_code=None
    )
