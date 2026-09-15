# -*- coding: utf-8 -*-
"""SSRF + proxy routing integration for RegistryAdapter (no autouse SSRF mock)."""

from socket import gaierror
from unittest.mock import patch

import pytest

from util.orgmirror.registry_adapter import RegistryAdapter
from util.security.ssrf import (
    ProxyRoute,
    SSRFBlockedError,
    proxy_route_for_url,
)


class _StubRegistryAdapter(RegistryAdapter):
    def list_repositories(self):
        return []

    def test_connection(self):
        return True, "ok"


class TestRegistryAdapterSSRFProxy:
    """RegistryAdapter SSRF validation uses the same proxy mapping as HTTP requests."""

    _PROXY_CONFIG = {
        "proxy": {
            "http_proxy": "http://proxy:8080",
            "https_proxy": "http://proxy:8080",
        }
    }

    def test_allowlisted_unresolved_host_skips_dns_with_explicit_proxy(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = AssertionError("DNS should not be queried")
            adapter = _StubRegistryAdapter(
                url="https://unresolved-mirror.example.com",
                namespace="testorg",
                config=self._PROXY_CONFIG,
                allowed_hosts=["unresolved-mirror.example.com"],
            )
            assert adapter.proxy == self._PROXY_CONFIG["proxy"]
            route = proxy_route_for_url(adapter.base_url, adapter.proxy)
            assert route is ProxyRoute.PROXY
            proxies = adapter._build_proxies(f"{adapter.base_url}/api/v1/repository")
            assert proxies["https"] == "http://proxy:8080"

    def test_no_proxy_target_runs_dns_validation(self):
        config = {
            "proxy": {
                "https_proxy": "http://proxy:8080",
                "no_proxy": "unresolved-mirror.example.com",
            }
        }
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                _StubRegistryAdapter(
                    url="https://unresolved-mirror.example.com",
                    namespace="testorg",
                    config=config,
                )
            mock_dns.assert_called_once()
            route = proxy_route_for_url("https://unresolved-mirror.example.com", config["proxy"])
            assert route is ProxyRoute.DIRECT

    def test_proxy_without_hostname_allowlist_still_runs_dns(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = gaierror("fail")
            with pytest.raises(ValueError, match="Cannot resolve hostname"):
                _StubRegistryAdapter(
                    url="https://unresolved-mirror.example.com",
                    namespace="testorg",
                    config=self._PROXY_CONFIG,
                )
            mock_dns.assert_called_once()

    def test_validation_proxy_mapping_matches_build_proxies(self):
        with patch("util.security.ssrf.validate_external_registry_url") as mock_validate:
            _StubRegistryAdapter(
                url="https://quay.io",
                namespace="testorg",
                config=self._PROXY_CONFIG,
                allowed_hosts=["quay.io"],
            )
            mock_validate.assert_called_once()
            _, kwargs = mock_validate.call_args
            assert kwargs["proxy_config"] == self._PROXY_CONFIG["proxy"]
            adapter_proxy = self._PROXY_CONFIG["proxy"]
            assert proxy_route_for_url(
                "https://quay.io", kwargs["proxy_config"]
            ) == proxy_route_for_url("https://quay.io", adapter_proxy)
