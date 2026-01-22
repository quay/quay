# -*- coding: utf-8 -*-
"""
Abstract base class for source registry adapters used in organization mirroring.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3


class RegistryAdapter(ABC):
    """
    Abstract base class for source registry adapters.

    Each registry type (Quay, Harbor, etc.) implements this interface
    to provide repository discovery functionality.
    """

    def __init__(
        self,
        url: str,
        namespace: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        config: Optional[Dict] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """
        Initialize the registry adapter.

        Args:
            url: Base URL of the source registry
            namespace: Namespace/project/organization name in the source registry
            username: Username for authentication (optional)
            password: Password for authentication (optional)
            config: Additional configuration (verify_tls, proxy settings, etc.)
            max_retries: Maximum number of retries for transient failures
        """
        self.base_url = url.rstrip("/")
        self.namespace = namespace
        self.auth = (username, password) if username and password else None
        self._config = config or {}
        self.verify_tls = self._config.get("verify_tls", True)
        self.proxy = self._config.get("proxy", {})
        self.timeout = self._config.get("timeout", DEFAULT_TIMEOUT)
        self.max_retries = max_retries
        self.session = self._create_session()

    def _build_proxies(self) -> Dict:
        """Build proxies dict for requests library."""
        proxies = {}
        if self.proxy.get("http_proxy"):
            proxies["http"] = self.proxy["http_proxy"]
        if self.proxy.get("https_proxy"):
            proxies["https"] = self.proxy["https_proxy"]
        return proxies

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry strategy.

        Configures automatic retries with exponential backoff for transient
        failures (429 rate limiting, 5xx server errors).

        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,  # Exponential backoff: 1s, 2s, 4s, etc.
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,  # We handle status codes ourselves
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        if self.auth:
            session.auth = self.auth

        return session

    @abstractmethod
    def list_repositories(self) -> List[str]:
        """
        List all repository names in the namespace.

        Returns:
            List of repository names (without namespace prefix)
        """
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to the source registry.

        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
