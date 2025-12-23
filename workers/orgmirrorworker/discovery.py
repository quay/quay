"""
Discovery client interface for organization mirror worker.

Routes to appropriate discovery client (Harbor, Quay) based on
external reference format.
"""

import logging

from data.fields import DecryptedValue
from util.repomirror.harbor_discovery import (
    HarborDiscoveryClient,
    is_harbor_registry,
    parse_harbor_external_reference,
)
from util.repomirror.quay_discovery import (
    QuayDiscoveryClient,
    is_quay_registry,
    parse_quay_external_reference,
)

logger = logging.getLogger(__name__)


def discover_repositories(mirror):
    """
    Discover repositories from external registry.

    Detects registry type from external_reference and routes to
    appropriate discovery client (Harbor, Quay, etc.).

    Args:
        mirror: OrgMirrorConfig instance with external_reference and credentials

    Returns:
        List of dicts with 'name' and 'external_reference' keys,
        or None if discovery failed

    Example:
        [
            {
                "name": "nginx",
                "external_reference": "harbor.example.com/library/nginx"
            },
            ...
        ]
    """
    external_ref = mirror.external_reference
    org_name = mirror.organization.username

    logger.info("Starting repository discovery for org %s from %s", org_name, external_ref)

    # Detect registry type and route to appropriate client
    # Check Quay first (more specific hostname-based detection)
    if is_quay_registry(external_ref):
        logger.info("Detected Quay registry: %s", external_ref)
        return _discover_from_quay(mirror)
    elif is_harbor_registry(external_ref):
        logger.info("Detected Harbor registry: %s", external_ref)
        return _discover_from_harbor(mirror)
    else:
        logger.warning(
            "Unknown registry type for %s. Supported: Harbor, Quay.",
            external_ref,
        )
        # Return empty list (not None, to avoid failing the sync)
        return []


def _discover_from_harbor(mirror):
    """
    Discover repositories from Harbor registry.

    Args:
        mirror: OrgMirrorConfig instance

    Returns:
        List of discovered repositories or None if failed
    """
    external_ref = mirror.external_reference
    org_name = mirror.organization.username

    # Parse Harbor reference
    parsed = parse_harbor_external_reference(external_ref)
    if not parsed:
        logger.error("Failed to parse Harbor external reference: %s", external_ref)
        return None

    harbor_url = parsed["harbor_url"]
    project_name = parsed["project_name"]

    logger.info(
        "Discovering repositories from Harbor project %s at %s",
        project_name,
        harbor_url,
    )

    # Extract credentials
    username = None
    password = None

    if mirror.external_registry_username:
        try:
            username_value = mirror.external_registry_username.decrypt()
            if isinstance(username_value, DecryptedValue):
                username = username_value.value
            else:
                username = username_value
        except Exception:
            logger.exception("Failed to decrypt external_registry_username")

    if mirror.external_registry_password:
        try:
            password_value = mirror.external_registry_password.decrypt()
            if isinstance(password_value, DecryptedValue):
                password = password_value.value
            else:
                password = password_value
        except Exception:
            logger.exception("Failed to decrypt external_registry_password")

    # Get registry configuration
    registry_config = mirror.external_registry_config or {}
    verify_tls = registry_config.get("verify_tls", True)
    proxy = registry_config.get("proxy")

    # Create Harbor client
    try:
        client = HarborDiscoveryClient(
            harbor_url=harbor_url,
            username=username,
            password=password,
            verify_tls=verify_tls,
            proxy=proxy,
            timeout=30,
            max_retries=3,
        )

        # Test connection first
        if not client.test_connection(project_name):
            logger.error(
                "Failed to connect to Harbor project %s at %s",
                project_name,
                harbor_url,
            )
            return None

        # Discover repositories
        repositories = client.discover_repositories(project_name)

        if repositories is None:
            logger.error("Failed to discover repositories from Harbor project %s", project_name)
            return None

        logger.info(
            "Successfully discovered %d repositories from Harbor project %s",
            len(repositories),
            project_name,
        )

        return repositories

    except Exception as e:
        logger.exception(
            "Unexpected error during Harbor discovery for org %s: %s", org_name, str(e)
        )
        return None


def _discover_from_quay(mirror):
    """
    Discover repositories from Quay registry.

    Args:
        mirror: OrgMirrorConfig instance

    Returns:
        List of discovered repositories or None if failed
    """
    external_ref = mirror.external_reference
    org_name = mirror.organization.username

    # Parse Quay reference
    parsed = parse_quay_external_reference(external_ref)
    if not parsed:
        logger.error("Failed to parse Quay external reference: %s", external_ref)
        return None

    quay_url = parsed["quay_url"]
    quay_org_name = parsed["org_name"]

    logger.info(
        "Discovering repositories from Quay organization %s at %s",
        quay_org_name,
        quay_url,
    )

    # Extract credentials
    token = None
    username = None
    password = None

    # Quay supports both OAuth tokens and robot accounts
    # Try token first, then fall back to username/password
    if mirror.external_registry_username:
        try:
            username_value = mirror.external_registry_username.decrypt()
            if isinstance(username_value, DecryptedValue):
                # Check if this is a token (robot tokens are long strings)
                # or a username (robot usernames are like "org+robotname")
                decrypted = username_value.value
                if "+" in decrypted:
                    # Likely a robot username
                    username = decrypted
                else:
                    # Likely a token
                    token = decrypted
            else:
                username_value_str = str(username_value)
                if "+" in username_value_str:
                    username = username_value_str
                else:
                    token = username_value_str
        except Exception:
            logger.exception("Failed to decrypt external_registry_username")

    if mirror.external_registry_password and username:
        # If we have username, get password for basic auth
        try:
            password_value = mirror.external_registry_password.decrypt()
            if isinstance(password_value, DecryptedValue):
                password = password_value.value
            else:
                password = password_value
        except Exception:
            logger.exception("Failed to decrypt external_registry_password")

    # Get registry configuration
    registry_config = mirror.external_registry_config or {}
    verify_tls = registry_config.get("verify_tls", True)
    proxy = registry_config.get("proxy")

    # Create Quay client
    try:
        client = QuayDiscoveryClient(
            quay_url=quay_url,
            token=token,
            username=username,
            password=password,
            verify_tls=verify_tls,
            proxy=proxy,
            timeout=30,
            max_retries=3,
        )

        # Test connection first
        if not client.test_connection(quay_org_name):
            logger.error(
                "Failed to connect to Quay organization %s at %s",
                quay_org_name,
                quay_url,
            )
            return None

        # Discover repositories
        repositories = client.discover_repositories(quay_org_name)

        if repositories is None:
            logger.error(
                "Failed to discover repositories from Quay organization %s",
                quay_org_name,
            )
            return None

        logger.info(
            "Successfully discovered %d repositories from Quay organization %s",
            len(repositories),
            quay_org_name,
        )

        return repositories

    except Exception as e:
        logger.exception("Unexpected error during Quay discovery for org %s: %s", org_name, str(e))
        return None
