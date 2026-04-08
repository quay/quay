# -*- coding: utf-8 -*-
"""
Unit tests for SSRF prevention in util/security/ssrf.py.
"""

from unittest.mock import patch

import pytest

from util.security.ssrf import SSRFBlockedError, validate_external_registry_url


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
            "[::1]",  # Loopback
            "[fc00::1]",  # Unique local
            "[fd00::1]",  # Unique local
            "[fe80::1]",  # Link-local
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
