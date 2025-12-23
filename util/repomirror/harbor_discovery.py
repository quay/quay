"""
Harbor API client for discovering repositories in Harbor projects.

Supports Harbor API v2.0 with authentication, pagination, TLS verification,
and proxy configuration.
"""

import logging
import time
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HarborDiscoveryException(Exception):
    """Exception raised when Harbor discovery fails."""

    pass


class HarborDiscoveryClient:
    """
    Client for discovering repositories in Harbor projects.

    Supports Harbor API v2.0 with pagination, authentication, TLS verification,
    and proxy configuration.
    """

    def __init__(
        self,
        harbor_url,
        username=None,
        password=None,
        token=None,
        verify_tls=True,
        proxy=None,
        timeout=30,
        max_retries=3,
    ):
        """
        Initialize Harbor discovery client.

        Args:
            harbor_url: Base Harbor URL (e.g., "https://harbor.example.com")
            username: Harbor username (basic auth)
            password: Harbor password (basic auth)
            token: Harbor API token (alternative to username/password)
            verify_tls: Verify TLS certificates (default: True)
            proxy: HTTP proxy configuration dict with http/https keys
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.harbor_url = harbor_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.verify_tls = verify_tls
        self.proxy = proxy
        self.timeout = timeout
        self.max_retries = max_retries

        # Create session with retry strategy
        self.session = requests.Session()

        # Configure retry strategy for transient failures
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configure authentication
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            logger.debug("Harbor client configured with token authentication")
        elif username and password:
            self.session.auth = (username, password)
            logger.debug("Harbor client configured with basic authentication")
        else:
            logger.warning("Harbor client configured without authentication")

        # Configure proxy
        if proxy:
            self.session.proxies = proxy
            logger.debug("Harbor client configured with proxy: %s", proxy)

    def discover_repositories(self, project_name):
        """
        Discover all repositories in a Harbor project.

        Args:
            project_name: Harbor project name

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
        logger.info("Starting discovery for Harbor project: %s", project_name)

        repositories = []
        page = 1
        page_size = 100

        try:
            while True:
                repos = self._list_repositories_page(project_name, page=page, page_size=page_size)

                if not repos:
                    # No more repositories
                    break

                repositories.extend(repos)

                logger.debug(
                    "Fetched page %d: %d repositories (total: %d)",
                    page,
                    len(repos),
                    len(repositories),
                )

                # Check if more pages available
                if len(repos) < page_size:
                    # Last page
                    break

                page += 1

            logger.info(
                "Successfully discovered %d repositories in Harbor project %s",
                len(repositories),
                project_name,
            )

            return repositories

        except Exception as e:
            logger.exception(
                "Failed to discover repositories from Harbor project %s: %s",
                project_name,
                str(e),
            )
            return None

    def _list_repositories_page(self, project_name, page=1, page_size=100):
        """
        List a single page of repositories in a Harbor project.

        Args:
            project_name: Harbor project name
            page: Page number (1-indexed, default: 1)
            page_size: Number of results per page (default: 100)

        Returns:
            List of dicts with 'name' and 'external_reference'

        Raises:
            HarborDiscoveryException: API request failed
        """
        url = urljoin(self.harbor_url, f"/api/v2.0/projects/{project_name}/repositories")

        params = {
            "page": page,
            "page_size": page_size,
        }

        logger.debug(
            "Fetching Harbor repositories from %s: page=%d, page_size=%d",
            url,
            page,
            page_size,
        )

        try:
            response = self.session.get(
                url, params=params, verify=self.verify_tls, timeout=self.timeout
            )

            response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise HarborDiscoveryException(f"Harbor project not found: {project_name}")
            elif e.response.status_code == 401:
                raise HarborDiscoveryException("Harbor authentication failed")
            elif e.response.status_code == 403:
                raise HarborDiscoveryException(f"Access denied to Harbor project: {project_name}")
            else:
                raise HarborDiscoveryException(
                    f"Harbor API request failed: {e.response.status_code} {e.response.reason}"
                )

        except requests.exceptions.SSLError as e:
            raise HarborDiscoveryException(f"TLS verification failed: {str(e)}")

        except requests.exceptions.ProxyError as e:
            raise HarborDiscoveryException(f"Proxy error: {str(e)}")

        except requests.exceptions.ConnectionError as e:
            raise HarborDiscoveryException(f"Connection error: {str(e)}")

        except requests.exceptions.Timeout as e:
            raise HarborDiscoveryException(f"Request timeout: {str(e)}")

        except requests.exceptions.RequestException as e:
            raise HarborDiscoveryException(f"Request failed: {str(e)}")

        # Parse response
        try:
            repos_data = response.json()
        except ValueError as e:
            raise HarborDiscoveryException(f"Invalid JSON response: {str(e)}")

        if not isinstance(repos_data, list):
            raise HarborDiscoveryException(
                f"Unexpected response format: expected list, got {type(repos_data)}"
            )

        # Parse repositories
        repositories = []
        for repo in repos_data:
            try:
                # Harbor returns full path like "library/nginx"
                repo_full_name = repo["name"]

                # Extract repo name (without project prefix)
                if "/" in repo_full_name:
                    repo_name = repo_full_name.split("/", 1)[1]
                else:
                    repo_name = repo_full_name

                # Build external reference for mirroring
                # Format: harbor.example.com/project/repo
                # Extract hostname from harbor_url
                hostname = (
                    self.harbor_url.split("://")[1] if "://" in self.harbor_url else self.harbor_url
                )

                external_ref = f"{hostname}/{repo_full_name}"

                repositories.append(
                    {
                        "name": repo_name,
                        "external_reference": external_ref,
                    }
                )

            except (KeyError, IndexError) as e:
                logger.warning("Failed to parse repository from Harbor response: %s", str(e))
                continue

        return repositories

    def test_connection(self, project_name):
        """
        Test connection to Harbor API.

        Args:
            project_name: Harbor project name to test

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._list_repositories_page(project_name, page=1, page_size=1)
            logger.info("Harbor connection test successful for project: %s", project_name)
            return True

        except Exception as e:
            logger.error("Harbor connection test failed for project %s: %s", project_name, str(e))
            return False


def parse_harbor_external_reference(external_reference):
    """
    Parse Harbor external reference into components.

    Args:
        external_reference: Harbor reference (e.g., "harbor.example.com/library/nginx")

    Returns:
        Dict with 'harbor_url', 'project_name', 'repo_name' or None if invalid

    Example:
        {
            "harbor_url": "https://harbor.example.com",
            "project_name": "library",
            "repo_name": "nginx"
        }
    """
    try:
        # Split into parts
        parts = external_reference.split("/")

        if len(parts) < 2:
            logger.warning("Invalid Harbor reference format: %s", external_reference)
            return None

        # Extract components
        hostname = parts[0]
        project_name = parts[1]
        repo_name = "/".join(parts[2:]) if len(parts) > 2 else None

        # Build Harbor URL
        harbor_url = f"https://{hostname}"

        return {
            "harbor_url": harbor_url,
            "project_name": project_name,
            "repo_name": repo_name,
        }

    except Exception as e:
        logger.exception("Failed to parse Harbor external reference: %s", str(e))
        return None


def is_harbor_registry(external_reference):
    """
    Detect if external reference is a Harbor registry.

    Args:
        external_reference: External reference string

    Returns:
        True if appears to be Harbor, False otherwise

    Note:
        This uses hostname-based detection to differentiate Harbor from other registries.
        Checks for "harbor" in hostname. For ambiguous cases without "harbor" in the
        hostname, returns True as a fallback (Harbor-first strategy) unless the hostname
        contains "quay".
    """
    try:
        if not external_reference:
            return False

        parts = external_reference.split("/")
        if len(parts) < 2:
            return False

        hostname = parts[0].lower()

        # Check for quay specifically - not Harbor
        if "quay" in hostname or hostname == "quay.io":
            return False

        # Check if hostname contains "harbor"
        if "harbor" in hostname:
            return True

        # For other hostnames with 2+ path components, assume Harbor
        # (Harbor-first strategy for backward compatibility)
        return True

    except Exception:
        return False
