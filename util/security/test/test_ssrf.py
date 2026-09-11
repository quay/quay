# -*- coding: utf-8 -*-
"""
Unit tests for SSRF prevention in util/security/ssrf.py.
"""

import os
from socket import gaierror
from unittest.mock import patch

import pytest

from util.security.ssrf import (
    ProxyRoute,
    SSRFBlockedError,
    get_environment_proxy_config,
    proxy_route_for_url,
    validate_external_registry_reference,
    validate_external_registry_url,
)


class TestSSRFBlockedError:
    """Tests for the SSRFBlockedError exception type."""

    def test_is_subclass_of_value_error(self):
        """SSRFBlockedError must be a ValueError subclass for backward compatibility."""
        assert issubclass(SSRFBlockedError, ValueError)


class TestValidateExternalRegistryUrl:
    """Tests for validate_external_registry_url()."""

    # ---- Valid URLs (should pass without raising) ----

    @pytest.mark.parametrize(
        "url",
        [
            "https://quay.io",
            "https://harbor.example.com",
            "http://registry.company.com",
            "https://registry.company.com:5000",
            "https://quay.io/",
            "https://my-registry.us-east-1.example.com",
        ],
    )
    def test_valid_urls_pass(self, url):
        # Should not raise; mock DNS to return a public IP
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),
            ]
            validate_external_registry_url(url)

    # ---- Empty / None URLs ----

    @pytest.mark.parametrize("url", [None, "", "   "])
    def test_empty_or_none_url_rejected(self, url):
        with pytest.raises(ValueError, match="required"):
            validate_external_registry_url(url)

    # ---- Invalid schemes ----

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://registry.example.com",
            "file:///etc/passwd",
            "gopher://evil.com",
            "data:text/html,<h1>hi</h1>",
            "javascript:alert(1)",
            "ssh://registry.example.com",
        ],
    )
    def test_invalid_schemes_rejected(self, url):
        with pytest.raises(ValueError, match="scheme"):
            validate_external_registry_url(url)

    # ---- Invalid scheme if allow_only_secure is raised ----
    @pytest.mark.parametrize(
        "url, expected_failure",
        [
            ("https://registry.redhat.io", False),
            ("http://quay.io", True),
        ],
    )
    def test_allow_only_secure_schemas(self, url, expected_failure):
        if expected_failure:
            with pytest.raises(ValueError, match="only HTTPS"):
                validate_external_registry_url(url=url, allow_only_secure=True)
        else:
            validate_external_registry_url(url=url, allow_only_secure=True)

    # ---- URLs with embedded credentials ----

    def test_url_with_userinfo_rejected(self):
        with pytest.raises(ValueError, match="credentials"):
            validate_external_registry_url("https://user:pass@registry.example.com")

    def test_url_with_username_only_rejected(self):
        with pytest.raises(ValueError, match="credentials"):
            validate_external_registry_url("https://user@registry.example.com")

    # ---- Missing hostname ----

    def test_url_without_hostname_rejected(self):
        with pytest.raises(ValueError, match="hostname"):
            validate_external_registry_url("https://")

    # ---- Blocked hostnames ----

    @pytest.mark.parametrize(
        "hostname",
        [
            "localhost",
            "metadata.google.internal",
            "metadata.azure.internal",
            "metadata",
            "kubernetes.default.svc",
            "kubernetes.default.svc.cluster.local",
            "kubernetes.default",
            "kubernetes",
        ],
    )
    def test_blocked_hostnames_rejected(self, hostname):
        """Blocked hostnames are rejected even when they resolve to a public IP."""
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            with pytest.raises(SSRFBlockedError, match="not allowed"):
                validate_external_registry_url(f"https://{hostname}")

    def test_blocked_hostnames_rejected_no_dns(self):
        """Blocked hostnames are rejected immediately when resolve_dns=False."""
        with pytest.raises(SSRFBlockedError, match="not allowed"):
            validate_external_registry_url("https://localhost", resolve_dns=False)

    def test_internal_suffix_rejected(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            with pytest.raises(SSRFBlockedError, match="not allowed"):
                validate_external_registry_url("https://my-service.internal")

    def test_local_suffix_rejected(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            with pytest.raises(SSRFBlockedError, match="not allowed"):
                validate_external_registry_url("https://printer.local")

    # ---- Private/reserved IPv4 addresses (as literals in URL) ----

    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",  # Loopback
            "127.0.0.2",  # Loopback range
            "10.0.0.1",  # Private Class A
            "10.255.255.255",  # Private Class A upper bound
            "172.16.0.1",  # Private Class B
            "172.31.255.255",  # Private Class B upper bound
            "192.168.0.1",  # Private Class C
            "192.168.255.255",  # Private Class C upper bound
            "169.254.169.254",  # AWS metadata (link-local)
            "169.254.0.1",  # Link-local
            "0.0.0.0",  # Unspecified
        ],
    )
    def test_private_ipv4_rejected(self, ip):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url(f"https://{ip}")

    # ---- Private/reserved IPv6 addresses ----

    @pytest.mark.parametrize(
        "ip",
        [
            "[::]",  # Unspecified; routes to loopback on Linux
            "[::1]",  # Loopback
            "[fc00::1]",  # Unique local
            "[fd00::1]",  # Unique local
            "[fe80::1]",  # Link-local
            "[fec0::1]",  # Deprecated site-local
            "[ff02::1]",  # Multicast
        ],
    )
    def test_private_ipv6_rejected(self, ip):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url(f"https://{ip}")

    # ---- Public IP literals should pass ----

    def test_public_ipv4_literal_passes(self):
        validate_external_registry_url("https://93.184.216.34")

    def test_public_ipv6_literal_passes(self):
        validate_external_registry_url("https://[2606:2800:220:1:248:1893:25c8:1946]")

    # ---- DNS resolution to private IP ----

    def test_dns_resolving_to_private_ip_rejected(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("127.0.0.1", 0)),
            ]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                validate_external_registry_url("https://evil-redirect.example.com")

    def test_dns_resolving_to_aws_metadata_rejected(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("169.254.169.254", 0)),
            ]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                validate_external_registry_url("https://evil-aws.example.com")

    def test_dns_with_mixed_ips_one_private_rejected(self):
        """If any resolved IP is private, the URL should be rejected."""
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),  # Public
                (2, 1, 6, "", ("10.0.0.1", 0)),  # Private
            ]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                validate_external_registry_url("https://dual-homed.example.com")

    def test_dns_resolution_failure_rejected(self):
        import socket

        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = socket.gaierror("Name resolution failed")
            with pytest.raises(ValueError, match="Cannot resolve"):
                validate_external_registry_url("https://nonexistent.example.com")

    def test_dns_resolving_to_public_ip_passes(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),
            ]
            validate_external_registry_url("https://registry.example.com")

    # ---- CGN / Shared address space ----

    def test_cgn_address_rejected(self):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://100.64.0.1")

    # ---- Multicast / reserved ranges ----

    def test_multicast_address_rejected(self):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://224.0.0.1")

    def test_reserved_future_address_rejected(self):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://240.0.0.1")

    # ---- IPv4-mapped IPv6 ----

    def test_ipv4_mapped_ipv6_private_rejected(self):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://[::ffff:127.0.0.1]")

    def test_ipv4_mapped_ipv6_metadata_rejected(self):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://[::ffff:169.254.169.254]")

    # ---- NAT64 prefix (RFC 6052) ----

    def test_nat64_metadata_rejected(self):
        """NAT64 prefix wrapping AWS metadata IP should be blocked."""
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://[64:ff9b::169.254.169.254]")

    def test_nat64_loopback_rejected(self):
        """NAT64 prefix wrapping loopback should be blocked."""
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://[64:ff9b::127.0.0.1]")

    def test_nat64_private_ip_rejected(self):
        """NAT64 prefix wrapping private IP should be blocked."""
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://[64:ff9b::10.0.0.1]")

    # ---- Discard-Only (RFC 6666) ----

    def test_discard_only_rejected(self):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://[100::1]")

    # ---- Documentation prefix (RFC 3849) ----

    def test_documentation_ipv6_rejected(self):
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url("https://[2001:db8::1]")

    # ---- resolve_dns=False skips DNS check ----

    def test_resolve_dns_false_skips_dns_check(self):
        """With resolve_dns=False, hostnames pass without DNS resolution."""
        validate_external_registry_url("https://registry.example.com", resolve_dns=False)

    def test_dns_resolving_to_unspecified_ipv6_rejected(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(10, 1, 6, "", ("::", 0, 0, 0))]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                validate_external_registry_url("https://registry.example.com")


class TestValidateExternalRegistryReference:
    """Tests for scheme-less repository mirror references."""

    @pytest.mark.parametrize(
        "reference",
        [
            "quay.io/projectquay/quay",
            "quay.io/Team/Nested.Repository:Tag",
            "quay.io/team/repository@sha256:abc",
            "registry.example.com:5000/team/repository",
            "93.184.216.34/team/repository",
            "[2606:2800:220:1:248:1893:25c8:1946]/team/repository",
            "[2606:2800:220:1:248:1893:25c8:1946]:5000/team/repository",
        ],
    )
    def test_valid_references_pass(self, reference):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            validate_external_registry_reference(reference)

    @pytest.mark.parametrize("reference", [None, "", "   "])
    def test_empty_reference_rejected(self, reference):
        with pytest.raises(ValueError, match="required"):
            validate_external_registry_reference(reference)

    @pytest.mark.parametrize(
        "reference",
        [
            "https://quay.io/project/repository",
            "quay.io/project repo",
            "/project/repository",
            "quay.io?#/project/repository",
            "quay.io:bad/repository",
            "quay.io:/repository",
            "quay.io:70000/repository",
            "quay.io:0/repository",
            "[2606:2800:220:1:248:1893:25c8:1946]:/repository",
            "quay.io/repository?query=value",
            "quay.io/repository#fragment",
            "quay.io",
            "quay.io/",
            "quay.io\\repository",
            "quay.io/%2e%2e",
        ],
    )
    def test_malformed_reference_rejected(self, reference):
        with pytest.raises(ValueError, match="reference"):
            validate_external_registry_reference(reference, resolve_dns=False)

    @pytest.mark.parametrize(
        "reference",
        [
            "localhost/project/repository",
            "127.0.0.1/project/repository",
            "169.254.169.254/latest/meta-data",
            "10.0.0.1/project/repository",
            "[::1]:5000/project/repository",
        ],
    )
    def test_blocked_registry_rejected(self, reference):
        with pytest.raises(SSRFBlockedError):
            validate_external_registry_reference(reference, resolve_dns=False)

    def test_dns_resolving_to_private_ip_rejected(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                validate_external_registry_reference("registry.example.com/team/repository")

    def test_allowlisted_private_registry_passes(self):
        validate_external_registry_reference(
            "10.0.0.1/team/repository",
            allowed_hosts=["10.0.0.0/8"],
        )


class TestSSRFAllowlist:
    """Tests for SSRF_ALLOWED_HOSTS allowlist functionality."""

    def test_allowed_hostname_bypasses_blocked_hostname(self):
        """Allowlisted hostname bypasses the blocked hostname check."""
        validate_external_registry_url(
            "https://localhost",
            resolve_dns=False,
            allowed_hosts=["localhost"],
        )

    def test_allowed_cidr_bypasses_blocked_ip_literal(self):
        """Allowlisted CIDR range bypasses blocked IP literal check."""
        validate_external_registry_url(
            "https://10.0.0.1",
            allowed_hosts=["10.0.0.0/8"],
        )

    def test_allowed_cidr_bypasses_dns_resolution_check(self):
        """Allowlisted CIDR bypasses DNS-resolved-to-private check."""
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("192.168.1.100", 0))]
            validate_external_registry_url(
                "https://internal-harbor.example.com",
                allowed_hosts=["192.168.0.0/16"],
            )

    def test_allowed_specific_ip_bypasses_blocked(self):
        """Allowlisting a specific IP address works."""
        validate_external_registry_url(
            "https://172.16.5.10",
            allowed_hosts=["172.16.5.10"],
        )

    def test_allowlist_does_not_bypass_scheme_check(self):
        """Allowlist does not bypass scheme validation."""
        with pytest.raises(ValueError, match="scheme"):
            validate_external_registry_url(
                "ftp://10.0.0.1",
                allowed_hosts=["10.0.0.0/8"],
            )

    def test_allowlist_does_not_bypass_credential_check(self):
        """Allowlist does not bypass embedded credential check."""
        with pytest.raises(ValueError, match="credentials"):
            validate_external_registry_url(
                "https://user:pass@10.0.0.1",
                allowed_hosts=["10.0.0.0/8"],
            )

    def test_non_matching_allowlist_still_blocks(self):
        """Non-matching allowlist entries don't bypass the block."""
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url(
                "https://10.0.0.1",
                allowed_hosts=["192.168.0.0/16"],
            )

    def test_empty_allowlist_blocks_normally(self):
        """Empty allowlist maintains normal blocking behavior."""
        with pytest.raises(SSRFBlockedError, match="private or reserved"):
            validate_external_registry_url(
                "https://10.0.0.1",
                allowed_hosts=[],
            )

    def test_cidr_allowlist_bypasses_internal_suffix_block(self):
        """CIDR allowlist can bypass .internal hostname block via DNS resolution."""
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.1.5", 0))]
            validate_external_registry_url(
                "https://registry.internal",
                allowed_hosts=["10.0.0.0/8"],
            )

    def test_cidr_allowlist_bypasses_local_suffix_block(self):
        """CIDR allowlist can bypass .local hostname block via DNS resolution."""
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("192.168.1.100", 0))]
            validate_external_registry_url(
                "https://registry.local",
                allowed_hosts=["192.168.0.0/16"],
            )

    def test_cidr_allowlist_bypasses_blocked_hostname(self):
        """CIDR allowlist can bypass blocked hostname via DNS resolution."""
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.0.50", 0))]
            validate_external_registry_url(
                "https://kubernetes",
                allowed_hosts=["10.0.0.0/8"],
            )

    def test_cidr_allowlist_does_not_bypass_without_dns(self):
        """CIDR allowlist cannot bypass name block when resolve_dns=False."""
        with pytest.raises(SSRFBlockedError, match="not allowed"):
            validate_external_registry_url(
                "https://registry.internal",
                resolve_dns=False,
                allowed_hosts=["10.0.0.0/8"],
            )

    def test_non_matching_cidr_still_blocks_internal_hostname(self):
        """Non-matching CIDR still blocks .internal hostname."""
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.1.5", 0))]
            with pytest.raises(SSRFBlockedError, match="not allowed"):
                validate_external_registry_url(
                    "https://registry.internal",
                    allowed_hosts=["192.168.0.0/16"],
                )


class TestEnvironmentProxyConfig:
    def test_get_environment_proxy_config_reads_standard_vars(self):
        with patch.dict(
            os.environ,
            {
                "HTTPS_PROXY": "http://proxy.corp:8080",
                "HTTP_PROXY": "http://proxy.corp:8080",
                "NO_PROXY": "localhost",
            },
            clear=True,
        ):
            config = get_environment_proxy_config()
            assert config == {
                "http_proxy": "http://proxy.corp:8080",
                "https_proxy": "http://proxy.corp:8080",
                "all_proxy": None,
                "no_proxy": "localhost",
            }

    def test_get_environment_proxy_config_reads_all_proxy(self):
        with patch.dict(
            os.environ,
            {"ALL_PROXY": "http://proxy.corp:8080", "NO_PROXY": "localhost"},
            clear=True,
        ):
            config = get_environment_proxy_config()
            assert config == {
                "http_proxy": None,
                "https_proxy": None,
                "all_proxy": "http://proxy.corp:8080",
                "no_proxy": "localhost",
            }
            assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.PROXY

    def test_get_environment_proxy_config_prefers_lowercase_over_uppercase(self):
        # Conflicting values: uppercase would route via proxy; lowercase no_proxy
        # lists the host. Requests prefers lowercase — Quay must match.
        with patch.dict(
            os.environ,
            {
                "HTTPS_PROXY": "http://uppercase-proxy:8080",
                "https_proxy": "http://lowercase-proxy:8080",
                "NO_PROXY": "other.example.com",
                "no_proxy": "registry.example.com",
            },
            clear=True,
        ):
            config = get_environment_proxy_config()
            assert config["https_proxy"] == "http://lowercase-proxy:8080"
            assert config["no_proxy"] == "registry.example.com"
            assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.DIRECT

    def test_get_environment_proxy_config_returns_none_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_environment_proxy_config() is None


class TestProxyRouteForUrl:
    """Tests for proxy_route_for_url() routing contract."""

    def test_no_proxy_config_is_direct(self):
        assert proxy_route_for_url("https://registry.example.com", None) is ProxyRoute.DIRECT
        assert proxy_route_for_url("https://registry.example.com", {}) is ProxyRoute.DIRECT

    def test_https_proxy_routes_https_url(self):
        config = {"https_proxy": "http://corp-proxy:8080"}
        assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.PROXY

    def test_http_proxy_routes_http_url(self):
        config = {"http_proxy": "http://corp-proxy:8080"}
        assert proxy_route_for_url("http://registry.example.com", config) is ProxyRoute.PROXY

    def test_all_proxy_routes_https_and_http(self):
        config = {"all_proxy": "http://corp-proxy:8080"}
        assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.PROXY
        assert proxy_route_for_url("http://registry.example.com", config) is ProxyRoute.PROXY

    def test_scheme_proxy_wins_over_all_proxy(self):
        config = {
            "https_proxy": "http://https-proxy:8080",
            "all_proxy": "http://all-proxy:8080",
        }
        assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.PROXY
        # Empty scheme-specific key falls back to all_proxy (requests-compatible).
        config_empty_scheme = {
            "https_proxy": "",
            "all_proxy": "http://all-proxy:8080",
        }
        assert (
            proxy_route_for_url("https://registry.example.com", config_empty_scheme)
            is ProxyRoute.PROXY
        )

    def test_scheme_mismatch_uses_direct_not_proxy(self):
        assert (
            proxy_route_for_url(
                "https://registry.example.com",
                {"http_proxy": "http://corp-proxy:8080"},
            )
            is ProxyRoute.DIRECT
        )
        assert (
            proxy_route_for_url(
                "http://registry.example.com",
                {"https_proxy": "http://corp-proxy:8080"},
            )
            is ProxyRoute.DIRECT
        )

    def test_no_proxy_exact_hostname_is_direct(self):
        config = {
            "https_proxy": "http://corp-proxy:8080",
            "no_proxy": "registry.example.com",
        }
        assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.DIRECT

    def test_no_proxy_hostname_with_port_is_direct(self):
        config = {
            "https_proxy": "http://corp-proxy:8080",
            "no_proxy": "registry.example.com:443",
        }
        assert proxy_route_for_url("https://registry.example.com:443", config) is ProxyRoute.DIRECT

    def test_no_proxy_comma_separated_entries(self):
        config = {
            "https_proxy": "http://corp-proxy:8080",
            "no_proxy": "localhost,registry.example.com",
        }
        assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.DIRECT
        assert proxy_route_for_url("https://other.example.com", config) is ProxyRoute.PROXY

    def test_no_proxy_suffix_match_is_direct(self):
        config = {
            "https_proxy": "http://corp-proxy:8080",
            "no_proxy": ".internal",
        }
        assert proxy_route_for_url("https://registry.internal", config) is ProxyRoute.DIRECT

    def test_malformed_proxy_config_is_unknown(self):
        config = {"https_proxy": "   "}
        assert proxy_route_for_url("https://registry.example.com", config) is ProxyRoute.UNKNOWN

    def test_missing_hostname_is_unknown(self):
        config = {"https_proxy": "http://corp-proxy:8080"}
        assert proxy_route_for_url("https://", config) is ProxyRoute.UNKNOWN

    def test_unsupported_scheme_is_unknown(self):
        config = {"https_proxy": "http://corp-proxy:8080"}
        assert proxy_route_for_url("ftp://registry.example.com", config) is ProxyRoute.UNKNOWN

    def test_ambient_env_does_not_change_route_when_proxy_config_empty(self):
        with patch.dict(
            os.environ,
            {"HTTPS_PROXY": "http://corp-proxy:8080", "HTTP_PROXY": "http://corp-proxy:8080"},
            clear=True,
        ):
            assert proxy_route_for_url("https://registry.example.com", None) is ProxyRoute.DIRECT


class TestProxyAwareSSRFValidation:
    """SSRF validation when outbound traffic is routed through an HTTP(S) proxy."""

    _PROXY = {"https_proxy": "http://corp-proxy:8080"}

    def test_allowlisted_hostname_proxy_skips_dns_on_gaierror(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = gaierror("Name or service not known")
            validate_external_registry_url(
                "https://registry.example.com",
                proxy_config=self._PROXY,
                allowed_hosts=["registry.example.com"],
            )
            mock_dns.assert_not_called()

    def test_allowlisted_hostname_direct_route_queries_dns(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = gaierror("Name or service not known")
            with pytest.raises(ValueError, match="Cannot resolve hostname"):
                validate_external_registry_url(
                    "https://registry.example.com",
                    allowed_hosts=["registry.example.com"],
                )
            mock_dns.assert_called_once()

    def test_non_allowlisted_hostname_proxy_still_requires_dns(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = gaierror("Name or service not known")
            with pytest.raises(ValueError, match="Cannot resolve hostname"):
                validate_external_registry_url(
                    "https://registry.example.com",
                    proxy_config=self._PROXY,
                )
            mock_dns.assert_called_once()

    def test_no_proxy_match_runs_dns_and_rejects_private_resolution(self):
        config = {
            "https_proxy": "http://corp-proxy:8080",
            "no_proxy": "registry.example.com",
        }
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                validate_external_registry_url(
                    "https://registry.example.com",
                    proxy_config=config,
                )
            mock_dns.assert_called_once()

    def test_cidr_only_allowlist_proxy_does_not_skip_dns_on_failure(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = gaierror("Name or service not known")
            with pytest.raises(ValueError, match="Cannot resolve hostname"):
                validate_external_registry_url(
                    "https://registry.internal",
                    proxy_config=self._PROXY,
                    allowed_hosts=["10.0.0.0/8"],
                )
            mock_dns.assert_called_once()

    def test_proxy_route_still_blocks_metadata_hostname(self):
        with pytest.raises(SSRFBlockedError, match="not allowed"):
            validate_external_registry_url(
                "https://metadata.google.internal",
                proxy_config=self._PROXY,
            )

    def test_proxy_route_uses_dns_for_cidr_allowlisted_internal_hostname(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.1.5", 0))]
            validate_external_registry_url(
                "https://registry.internal",
                proxy_config=self._PROXY,
                allowed_hosts=["10.0.0.0/8"],
            )
            mock_dns.assert_called_once()

    def test_proxy_internal_hostname_rejected_when_resolved_ip_outside_cidr_allowlist(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("172.16.0.5", 0))]
            with pytest.raises(SSRFBlockedError, match="not allowed"):
                validate_external_registry_url(
                    "https://registry.internal",
                    proxy_config=self._PROXY,
                    allowed_hosts=["10.0.0.0/8"],
                )
            mock_dns.assert_called_once()

    def test_unknown_route_does_not_skip_dns_for_allowlisted_host(self):
        # Whitespace-only proxy URL yields UNKNOWN route; DNS must still run
        # even when the hostname is allowlisted (PROXY skip must not apply).
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            validate_external_registry_url(
                "https://registry.example.com",
                proxy_config={"https_proxy": "   "},
                allowed_hosts=["registry.example.com"],
            )
            mock_dns.assert_called_once()

    def test_proxy_does_not_bypass_scheme_check(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_external_registry_url(
                "ftp://registry.example.com",
                proxy_config=self._PROXY,
                allowed_hosts=["registry.example.com"],
            )

    def test_proxy_does_not_bypass_credential_check(self):
        with pytest.raises(ValueError, match="credentials"):
            validate_external_registry_url(
                "https://user:pass@registry.example.com",
                proxy_config=self._PROXY,
                allowed_hosts=["registry.example.com"],
            )

    def test_mixed_public_private_dns_answers_still_blocked_with_proxy(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),
                (2, 1, 6, "", ("10.0.0.1", 0)),
            ]
            with pytest.raises(SSRFBlockedError, match="private or reserved"):
                validate_external_registry_url(
                    "https://registry.example.com",
                    proxy_config=self._PROXY,
                )

    def test_validate_upstream_reference_allowlisted_proxy_skips_dns(self):
        with patch("util.security.ssrf._getaddrinfo") as mock_dns:
            mock_dns.side_effect = AssertionError("DNS should not be queried")
            validate_external_registry_reference(
                "registry.example.com/team/repository",
                proxy_config=self._PROXY,
                allowed_hosts=["registry.example.com"],
            )
