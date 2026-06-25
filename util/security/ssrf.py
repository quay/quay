# -*- coding: utf-8 -*-
"""
SSRF prevention utilities for validating user-supplied URLs.
"""

import ipaddress
import logging
from socket import AF_UNSPEC, SOCK_STREAM
from socket import gaierror as _gaierror
from socket import getaddrinfo as _getaddrinfo
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SSRFBlockedError(ValueError):
    """Raised when a URL is rejected due to SSRF protection.

    Subclasses ValueError so existing defense-in-depth ``except ValueError``
    handlers (e.g. in the data-model layer) continue to work without
    modification.  The API layer catches this type explicitly to return a
    generic error message instead of leaking internal network topology.
    """


# Private and reserved IP networks that must never be accessed by user-controlled URLs.
# Based on OWASP SSRF Prevention Cheat Sheet and IANA Special-Purpose Address Registries.
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),  # "This host" (RFC 1122)
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),  # Shared Address Space / CGN (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback (RFC 1122)
    ipaddress.ip_network("169.254.0.0/16"),  # Link-Local / AWS metadata (RFC 3927)
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments (RFC 6890)
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1 (RFC 5737)
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),  # Benchmarking (RFC 2544)
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2 (RFC 5737)
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3 (RFC 5737)
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast (RFC 3171)
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved for future use (RFC 1112)
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("64:ff9b::/96"),  # NAT64 well-known prefix (RFC 6052)
    ipaddress.ip_network("100::/64"),  # Discard-Only (RFC 6666)
    ipaddress.ip_network("2001:db8::/32"),  # Documentation (RFC 3849)
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local (RFC 4193)
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local (RFC 4291)
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6 (RFC 4291)
]

# Hostnames that resolve to internal services and must be blocked regardless of DNS.
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",  # GCP metadata service
    "metadata.azure.internal",  # Azure Instance Metadata Service (IMDS)
    "metadata",  # Common cloud metadata alias
    "kubernetes.default.svc",  # Kubernetes API
    "kubernetes.default.svc.cluster.local",  # Kubernetes API (FQDN)
    "kubernetes.default",  # Kubernetes API
    "kubernetes",  # Kubernetes API
}

ALLOWED_SCHEMES = {"http", "https"}


def _is_ip_blocked(ip_str: str) -> bool:
    """
    Check if an IP address falls within any blocked network.

    Args:
        ip_str: IP address as string

    Returns:
        True if the IP is in a blocked network, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Unparseable IPs are treated as blocked

    return any(ip in network for network in BLOCKED_NETWORKS)


def _is_allowed(hostname: str, ip_str: Optional[str], allowed_hosts: List[str]) -> bool:
    """
    Check if a hostname or IP is in the configured allowlist.

    Each entry in allowed_hosts can be a hostname (matched case-insensitively)
    or a CIDR range (matched against the IP).

    Args:
        hostname: The hostname being validated
        ip_str: The resolved IP address (or None if not resolved yet)
        allowed_hosts: List of allowed hostnames or CIDR ranges

    Returns:
        True if the hostname or IP is explicitly allowed
    """
    hostname_lower = hostname.lower()

    for entry in allowed_hosts:
        # Try as CIDR range first
        try:
            network = ipaddress.ip_network(entry, strict=False)
            if ip_str:
                try:
                    if ipaddress.ip_address(ip_str) in network:
                        return True
                except ValueError:
                    pass
            # Also check if hostname itself is an IP in this network
            try:
                if ipaddress.ip_address(hostname) in network:
                    return True
            except ValueError:
                pass
            continue
        except ValueError:
            pass

        # Match as hostname (case-insensitive)
        if entry.lower() == hostname_lower:
            return True

    return False


def validate_external_registry_url(
    url: str,
    resolve_dns: bool = True,
    allowed_hosts: Optional[List[str]] = None,
) -> None:
    """
    Validate an external registry URL to prevent Server-Side Request Forgery (SSRF).

    Checks:
        1. URL is non-empty and well-formed
        2. Scheme is http or https only
        3. Hostname is present and not in the blocked list
        4. No userinfo (username:password) in the URL authority
        5. If hostname is an IP literal, it is not in a blocked network
        6. DNS resolution of hostname does not yield any blocked IPs (when resolve_dns=True)

    Hosts in the allowed_hosts list bypass the blocklist check (but not scheme/format checks).

    Args:
        url: The external registry URL to validate
        resolve_dns: Whether to resolve hostnames via DNS and check resulting IPs.
            Set to False for defense-in-depth layers where DNS resolution may not
            be appropriate (e.g., data model layer). The API layer and adapter
            constructor should always use True (the default).
        allowed_hosts: Optional list of hostnames or CIDR ranges that bypass the
            blocklist. Populated from the SSRF_ALLOWED_HOSTS config option.

    Raises:
        SSRFBlockedError: If the URL is blocked by SSRF protection (blocked
            hostname, private/reserved IP, or DNS resolving to a blocked IP).
            Subclass of ValueError.
        ValueError: If the URL fails a format/syntax check (bad scheme,
            embedded credentials, missing hostname, DNS resolution failure)
    """
    if not url or not isinstance(url, str):
        raise ValueError("External registry URL is required")

    url = url.strip()
    if not url:
        raise ValueError("External registry URL is required")

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")

    # Check scheme
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}': only HTTP and HTTPS are allowed")

    # Check for userinfo in URL (e.g., http://user:pass@host/)
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")

    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must include a hostname")

    _allowed_hosts = allowed_hosts or []

    # Check blocked hostnames (case-insensitive)
    hostname_lower = hostname.lower()
    blocked_by_name = (
        hostname_lower in BLOCKED_HOSTNAMES
        or hostname_lower.endswith(".internal")
        or hostname_lower.endswith(".local")
    )
    name_allowlisted = _is_allowed(hostname, None, _allowed_hosts)
    if blocked_by_name and not name_allowlisted and not resolve_dns:
        logger.warning("SSRF blocked: hostname '%s' is not allowed", hostname)
        raise SSRFBlockedError(f"Hostname '{hostname}' is not allowed")

    # Check if hostname is an IP address literal
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_ip_blocked(str(ip)):
            if not _is_allowed(hostname, str(ip), _allowed_hosts):
                logger.warning("SSRF blocked: IP literal '%s' is in a blocked network", hostname)
                raise SSRFBlockedError("URL points to a private or reserved IP address")
        # IP literal is allowed (public or allowlisted), no DNS resolution needed
        return
    except SSRFBlockedError:
        raise
    except ValueError:
        # Not an IP literal, continue with hostname validation
        pass

    if not resolve_dns:
        return

    # Resolve hostname and check all resulting IPs
    try:
        addr_infos = _getaddrinfo(hostname, None, AF_UNSPEC, SOCK_STREAM)
    except _gaierror:
        raise ValueError(f"Cannot resolve hostname '{hostname}'")

    if not addr_infos:
        raise ValueError(f"Cannot resolve hostname '{hostname}'")

    resolved_ips = [addr_info[4][0] for addr_info in addr_infos]

    # If the hostname was blocked by name but not allowlisted by hostname match,
    # check if any resolved IP matches a CIDR entry in the allowlist.
    # This allows CIDR-based allowlisting of .internal/.local hostnames.
    if blocked_by_name and not name_allowlisted:
        if not any(_is_allowed(hostname, ip, _allowed_hosts) for ip in resolved_ips):
            logger.warning("SSRF blocked: hostname '%s' is not allowed", hostname)
            raise SSRFBlockedError(f"Hostname '{hostname}' is not allowed")

    for ip_str in resolved_ips:
        if _is_ip_blocked(ip_str):
            if not _is_allowed(hostname, ip_str, _allowed_hosts):
                logger.warning(
                    "SSRF blocked: hostname '%s' resolves to private/reserved IP '%s'",
                    hostname,
                    ip_str,
                )
                raise SSRFBlockedError("URL resolves to a private or reserved IP address")
