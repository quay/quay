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


class TestIPLocateMMDB:
    """Integration tests that validate the embedded ip-to-country.mmdb file.

    These use the real database (no mocking) to ensure the file is loadable,
    the schema matches what IPResolver expects, and lookups return sane results.
    """

    @pytest.fixture()
    def real_resolver(self, app):
        return IPResolver(app)

    def test_mmdb_loads_successfully(self, real_resolver):
        assert real_resolver.geoip_db is not None

    @pytest.mark.parametrize(
        "ip, expected_country, expected_continent",
        [
            ("8.8.8.8", "US", "NA"),
            ("1.1.1.1", "AU", "OC"),
        ],
    )
    def test_known_ip_lookups(self, real_resolver, ip, expected_country, expected_continent):
        result = real_resolver.resolve_ip(ip)
        assert result is not None
        assert result.country_iso_code == expected_country
        assert result.continent == expected_continent

    def test_resolve_ip_returns_expected_fields(self, real_resolver):
        result = real_resolver.resolve_ip("8.8.8.8")
        assert isinstance(result.country_iso_code, str)
        assert len(result.country_iso_code) == 2
        assert isinstance(result.continent, str)
        assert len(result.continent) == 2

    def test_private_ip_returns_no_geo(self, real_resolver):
        result = real_resolver.resolve_ip("192.168.1.1")
        assert result.provider == "internet"
        assert result.country_iso_code is None
        assert result.continent is None

    def test_loopback_returns_no_geo(self, real_resolver):
        result = real_resolver.resolve_ip("127.0.0.1")
        assert result.provider == "internet"
        assert result.country_iso_code is None
