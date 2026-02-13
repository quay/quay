# -*- coding: utf-8 -*-
"""
Harbor registry adapter for organization mirroring.

Implements repository discovery using Harbor's API v2.0.
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

from util.orgmirror.exceptions import HarborDiscoveryException
from util.orgmirror.registry_adapter import DEFAULT_MAX_RETRIES, RegistryAdapter

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100


class HarborAdapter(RegistryAdapter):
    """
    Adapter for discovering repositories from a source Harbor registry.

    Uses Harbor's API v2.0 to list repositories in a project.

    API Details:
        Endpoint: GET /api/v2.0/projects/{project_name}/repositories
        Pagination: page=1, page_size=100
        Response: [{"name": "project/repo-name", ...}]
        Note: Strip {project}/ prefix from name
    """

    def __init__(
        self,
        url: str,
        namespace: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        config: Optional[Dict] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        allowed_hosts: Optional[List[str]] = None,
    ):
        super().__init__(url, namespace, username, password, config, max_retries, allowed_hosts)
        self.page_size = self._config.get("page_size", DEFAULT_PAGE_SIZE)

    def list_repositories(self) -> List[str]:
        """
        Fetch all repository names from the Harbor project.

        Returns:
            List of repository names (without project prefix)

        Raises:
            HarborDiscoveryException: On network, authentication, or API errors
        """
        repos = []
        page = 1

        try:
            while True:
                url = f"{self.base_url}/api/v2.0/projects/{self.namespace}/repositories"
                params = {"page": page, "page_size": self.page_size}

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
                    raise HarborDiscoveryException(
                        f"Project '{self.namespace}' not found on Harbor registry"
                    )
                elif response.status_code == 401:
                    raise HarborDiscoveryException("Authentication failed: invalid credentials")
                elif response.status_code == 403:
                    raise HarborDiscoveryException(
                        f"Access forbidden to project '{self.namespace}'"
                    )

                try:
                    response.raise_for_status()
                except HTTPError as e:
                    raise HarborDiscoveryException(
                        f"Harbor API returned error: {response.status_code}", cause=e
                    )

                data = response.json()

                if not data:  # Empty page means we're done
                    break

                for repo in data:
                    # Harbor returns "project/repo-name", strip project prefix
                    full_name = repo["name"]
                    if "/" in full_name:
                        name = full_name.split("/", 1)[1]
                    else:
                        name = full_name
                    repos.append(name)

                if len(data) < self.page_size:
                    break
                page += 1

        except HarborDiscoveryException:
            raise
        except SSLError as e:
            raise HarborDiscoveryException(
                f"SSL certificate verification failed for {self.base_url}", cause=e
            )
        except ProxyError as e:
            raise HarborDiscoveryException("Failed to connect through proxy", cause=e)
        except ConnectionError as e:
            raise HarborDiscoveryException(
                f"Failed to connect to Harbor registry at {self.base_url}", cause=e
            )
        except Timeout as e:
            raise HarborDiscoveryException(f"Connection to {self.base_url} timed out", cause=e)
        except RequestException as e:
            raise HarborDiscoveryException("Unexpected error during repository discovery", cause=e)

        logger.info(
            "Discovered %d repositories from Harbor project %s",
            len(repos),
            self.namespace,
        )
        return repos

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to the source Harbor registry.

        Attempts to fetch the project info to verify connectivity
        and authentication.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Try to fetch project info
            url = f"{self.base_url}/api/v2.0/projects/{self.namespace}"
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
            elif response.status_code == 403:
                return False, "Access forbidden - check permissions"
            elif response.status_code == 404:
                return False, f"Project '{self.namespace}' not found"
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
