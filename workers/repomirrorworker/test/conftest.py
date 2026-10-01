"""Shared fixtures for repomirrorworker tests."""

import logging
from unittest.mock import patch

import pytest

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _mock_dns_for_ssrf_validation():
    """Keep mirror worker tests independent of external DNS."""
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns
