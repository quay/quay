# -*- coding: utf-8 -*-
"""
Quay registry adapter for organization mirroring.

Implements repository discovery using Quay's API v1.
"""

import logging
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    ProxyError,
    RequestException,
    SSLError,
    Timeout,
)
from requests.packages.urllib3.util.retry import Retry

from util.orgmirror.exceptions import QuayDiscoveryException
from util.orgmirror.registry_adapter import DEFAULT_MAX_RETRIES, RegistryAdapter

logger = logging.getLogger(__name__)


class QuayAdapter(RegistryAdapter):
    """
    Adapter for discovering repositories from a source Quay registry.

    Uses Quay's API v1 to list repositories in a namespace (organization).

    API Details:
        Endpoint: GET /api/v1/repository?namespace=<namespace>
        Authentication: Bearer token (API token required)
        Response: {"repositories": [...], "next_page": "token"}
        Pagination: Uses next_page token until null/missing

    Note:
        Quay's API v1 does not support basic authentication. An API token
        must be provided via the `token` parameter or the `password` field.
        The username field is ignored for Quay authentication.
    """

    def __init__(
        self,
        url: str,
        namespace: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        config: Optional[Dict] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        token: Optional[str] = None,
        allowed_hosts: Optional[List[str]] = None,
    ):
        # Store token before calling super().__init__ since _create_session uses it
        # Token can be passed explicitly or via password field (common pattern)
        self._api_token = token or password
        super().__init__(url, namespace, username, password, config, max_retries, allowed_hosts)

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with Bearer token authentication.

        Overrides base class to use Bearer token instead of basic auth,
        as Quay's API v1 requires token authentication.

        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Use Bearer token authentication for Quay API
        if self._api_token:
            session.headers["Authorization"] = f"Bearer {self._api_token}"

        return session

    def list_repositories(self) -> List[str]:
        """
        Fetch all repository names from the source Quay namespace.

        Returns:
            List of repository names (without namespace prefix)

        Raises:
            QuayDiscoveryException: On network, authentication, or API errors
        """
        repos: List[str] = []
        next_page: Optional[str] = None

        try:
            while True:
                url = f"{self.base_url}/api/v1/repository"
                params: Dict[str, str] = {"namespace": self.namespace, "public": "true"}
                if next_page:
                    params["next_page"] = next_page

                logger.debug("Fetching repositories from %s with params %s", url, params)

                response = self.session.get(
                    url,
                    params=params,
                    verify=self.verify_tls,
                    proxies=self._build_proxies(),
                    timeout=self.timeout,
                    allow_redirects=False,
                )

                # Handle HTTP errors with specific messages
                if response.status_code == 404:
                    raise QuayDiscoveryException(
                        f"Namespace '{self.namespace}' not found on Quay registry"
                    )
                elif response.status_code == 401:
                    raise QuayDiscoveryException("Authentication failed: invalid credentials")
                elif response.status_code == 403:
                    raise QuayDiscoveryException(
                        f"Access forbidden to namespace '{self.namespace}'"
                    )
                elif 300 <= response.status_code < 400:
                    raise QuayDiscoveryException(
                        f"Registry returned redirect ({response.status_code})"
                    )

                try:
                    response.raise_for_status()
                except HTTPError as e:
                    raise QuayDiscoveryException(
                        f"Quay API returned error: {response.status_code}", cause=e
                    )

                data = response.json()

                for repo in data.get("repositories", []):
                    # Quay returns "name" without namespace prefix
                    repos.append(repo["name"])

                next_page = data.get("next_page")
                if not next_page:
                    break

        except QuayDiscoveryException:
            raise
        except SSLError as e:
            raise QuayDiscoveryException(
                f"SSL certificate verification failed for {self.base_url}", cause=e
            )
        except ProxyError as e:
            raise QuayDiscoveryException("Failed to connect through proxy", cause=e)
        except ConnectionError as e:
            raise QuayDiscoveryException(
                f"Failed to connect to Quay registry at {self.base_url}", cause=e
            )
        except Timeout as e:
            raise QuayDiscoveryException(f"Connection to {self.base_url} timed out", cause=e)
        except RequestException as e:
            raise QuayDiscoveryException("Unexpected error during repository discovery", cause=e)

        logger.info(
            "Discovered %d repositories from Quay namespace %s",
            len(repos),
            self.namespace,
        )
        return repos

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to the source Quay registry.

        Attempts to fetch the organization info to verify connectivity
        and authentication.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Try to fetch organization info
            url = f"{self.base_url}/api/v1/organization/{self.namespace}"
            response = self.session.get(
                url,
                verify=self.verify_tls,
                proxies=self._build_proxies(),
                timeout=10,
                allow_redirects=False,
            )

            if response.status_code == 200:
                return True, "Connection successful"
            elif response.status_code == 401:
                return False, "Authentication failed"
            elif response.status_code == 404:
                return False, f"Namespace '{self.namespace}' not found"
            else:
                return False, f"Unexpected response: {response.status_code}"

        except Timeout:
            return False, "Connection timed out"
        except SSLError as e:
            return False, f"SSL error: {e}"
        except ConnectionError as e:
            return False, f"Connection error: {e}"
        except RequestException as e:
            return False, str(e)
