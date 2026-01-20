# -*- coding: utf-8 -*-
"""
Organization mirroring utilities.

This package provides adapters for discovering repositories from various
source registries (Quay, Harbor, etc.) for organization-level mirroring.
"""

from typing import Dict, Optional

from data.database import SourceRegistryType
from util.orgmirror.exceptions import (
    HarborDiscoveryException,
    QuayDiscoveryException,
    RegistryDiscoveryException,
)
from util.orgmirror.harbor_adapter import HarborAdapter
from util.orgmirror.quay_adapter import QuayAdapter
from util.orgmirror.registry_adapter import RegistryAdapter


def get_registry_adapter(
    registry_type: SourceRegistryType,
    url: str,
    namespace: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    config: Optional[Dict] = None,
) -> RegistryAdapter:
    """
    Factory function to create the appropriate registry adapter.

    Args:
        registry_type: Type of source registry (SourceRegistryType enum)
        url: Base URL of the source registry
        namespace: Namespace/project/organization in the source registry
        username: Username for authentication (optional)
        password: Password for authentication (optional)
        config: Additional configuration (verify_tls, proxy, etc.)

    Returns:
        RegistryAdapter instance for the specified registry type

    Raises:
        ValueError: If the registry type is not supported
    """
    if registry_type == SourceRegistryType.QUAY:
        return QuayAdapter(url, namespace, username, password, config)
    elif registry_type == SourceRegistryType.HARBOR:
        return HarborAdapter(url, namespace, username, password, config)
    else:
        raise ValueError(f"Unsupported registry type: {registry_type}")


__all__ = [
    "get_registry_adapter",
    "RegistryAdapter",
    "QuayAdapter",
    "HarborAdapter",
    "RegistryDiscoveryException",
    "QuayDiscoveryException",
    "HarborDiscoveryException",
]
