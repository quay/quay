# -*- coding: utf-8 -*-
"""
Quay registry adapter for organization mirroring.

Implements repository discovery using Quay's API v1.
"""

import logging
from typing import Dict, List, Optional, Tuple

from requests.exceptions import (
    ConnectionError,
    HTTPError,
    ProxyError,
    RequestException,
    SSLError,
    Timeout,
)

from util.orgmirror.exceptions import QuayDiscoveryException
from util.orgmirror.registry_adapter import DEFAULT_MAX_RETRIES, RegistryAdapter

logger = logging.getLogger(__name__)


class QuayAdapter(RegistryAdapter):
    """
    Adapter for discovering repositories from a source Quay registry.

    Uses Quay's API v1 to list repositories in a namespace (organization).

    API Details:
        Endpoint: GET /api/v1/repository?namespace=<namespace>
        Authentication: Basic auth or Bearer token
        Response: {"repositories": [...], "next_page": "token"}
        Pagination: Uses next_page token until null/missing
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
        super().__init__(url, namespace, username, password, config, max_retries)

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
                )

                # Handle HTTP errors with specific messages
                if response.status_code == 404:
                    raise QuayDiscoveryException(
                        f"Namespace '{self.namespace}' not found on Quay registry"
                    )
                elif response.status_code == 401:
                    raise QuayDiscoveryException(
                        "Authentication failed: invalid credentials"
                    )
                elif response.status_code == 403:
                    raise QuayDiscoveryException(
                        f"Access forbidden to namespace '{self.namespace}'"
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
            raise QuayDiscoveryException(
                "Failed to connect through proxy", cause=e
            )
        except ConnectionError as e:
            raise QuayDiscoveryException(
                f"Failed to connect to Quay registry at {self.base_url}", cause=e
            )
        except Timeout as e:
            raise QuayDiscoveryException(
                f"Connection to {self.base_url} timed out", cause=e
            )
        except RequestException as e:
            raise QuayDiscoveryException(
                "Unexpected error during repository discovery", cause=e
            )

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
