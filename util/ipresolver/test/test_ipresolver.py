from unittest.mock import MagicMock, patch

import pytest

from test.fixtures import *
from util.ipresolver import IPResolver, ResolvedLocation


@pytest.fixture()
def aws_ip_range_data():
    return {
        "syncToken": 123456789,
        "prefixes": [
            {"ip_prefix": "10.0.0.0/8", "region": "GLOBAL", "service": "EC2"},
            {"ip_prefix": "6.0.0.0/8", "region": "GLOBAL", "service": "EC2"},
            {"ip_prefix": "5.0.0.0/8", "region": "af-south-1", "service": "AMAZON"},
            {"ip_prefix": "4.0.0.0/8", "region": "us-east-1", "service": "EC2"},
        ],
    }


@pytest.fixture()
def mock_geoip_db():
    db = MagicMock()
    lookup = {
        "4.0.0.2": {"country_code": "US", "continent_code": "NA"},
        "6.0.0.2": {"country_code": "US", "continent_code": "NA"},
        "8.8.8.8": {"country_code": "US", "continent_code": "NA"},
        "56.0.0.2": {"country_code": "US", "continent_code": "NA"},
    }
    db.get.side_effect = lambda ip: lookup.get(ip)
    return db


@pytest.fixture()
def ipresolver(app, aws_ip_range_data, mock_geoip_db):
    with patch("util.ipresolver.maxminddb") as mock_maxminddb:
        mock_maxminddb.open_database.return_value = mock_geoip_db
        resolver = IPResolver(app)
    resolver.amazon_ranges = IPResolver._parse_amazon_ranges(aws_ip_range_data)
    resolver.sync_token = aws_ip_range_data["syncToken"]
    return resolver


def test_resolve_aws_ip_no_geoinfo(ipresolver):
    result = ipresolver.resolve_ip("10.0.0.1")
    assert result.provider == "aws"
    assert result.aws_region == "GLOBAL"
    assert result.country_iso_code is None


def test_resolve_aws_ip_with_geoinfo(ipresolver):
    result = ipresolver.resolve_ip("6.0.0.2")
    assert result.provider == "aws"
    assert result.aws_region == "GLOBAL"
    assert result.country_iso_code == "US"


def test_resolve_aws_ip_specific_region(ipresolver):
    result = ipresolver.resolve_ip("4.0.0.2")
    assert result.provider == "aws"
    assert result.aws_region == "us-east-1"


def test_resolve_non_aws_ip_with_geoinfo(ipresolver):
    result = ipresolver.resolve_ip("56.0.0.2")
    assert result.provider == "internet"
    assert result.aws_region is None
    assert result.country_iso_code == "US"


def test_resolve_non_aws_ip_no_geoinfo(ipresolver):
    result = ipresolver.resolve_ip("127.0.0.1")
    assert result.provider == "internet"
    assert result.aws_region is None
    assert result.country_iso_code is None


def test_resolve_none_ip(ipresolver):
    assert ipresolver.resolve_ip(None) is None


def test_resolve_invalid_ip(ipresolver):
    result = ipresolver.resolve_ip("not-an-ip")
    assert result.provider == "invalid_ip"


def test_amazon_only_parses_ec2_and_codebuild():
    ranges = {
        "syncToken": 1,
        "prefixes": [
            {"ip_prefix": "1.0.0.0/8", "region": "us-east-1", "service": "EC2"},
            {"ip_prefix": "2.0.0.0/8", "region": "us-east-1", "service": "AMAZON"},
            {"ip_prefix": "3.0.0.0/8", "region": "us-east-1", "service": "CODEBUILD"},
        ],
    }
    parsed = IPResolver._parse_amazon_ranges(ranges)
    ipset = parsed["us-east-1"]
    from netaddr import IPAddress

    assert IPAddress("1.0.0.1") in ipset
    assert IPAddress("2.0.0.1") not in ipset
    assert IPAddress("3.0.0.1") in ipset
