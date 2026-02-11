from unittest.mock import MagicMock, patch

import pytest

from util.ipresolver import IPResolver


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
def test_aws_ip():
    return "10.0.0.1"


@pytest.fixture()
def test_ip_range_cache(aws_ip_range_data):
    sync_token = aws_ip_range_data["syncToken"]
    all_amazon = IPResolver._parse_amazon_ranges(aws_ip_range_data)
    return {
        "sync_token": sync_token,
        "all_amazon": all_amazon,
    }


@pytest.fixture()
def mock_ipresolver(app):
    with patch("util.ipresolver.maxminddb") as mock_maxminddb:
        mock_maxminddb.open_database.return_value = MagicMock()
        yield IPResolver(app)
