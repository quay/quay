"""
Quay API client for discovering repositories in Quay organizations.

Supports Quay API v1 with authentication, pagination, TLS verification,
and proxy configuration.
"""

import logging
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class QuayDiscoveryException(Exception):
    """Exception raised when Quay discovery fails."""

    pass


class QuayDiscoveryClient:
    """
    Client for discovering repositories in Quay organizations.

    Supports Quay API v1 with pagination, authentication, TLS verification,
    and proxy configuration.
    """

    def __init__(
        self,
        quay_url,
        token=None,
        username=None,
        password=None,
        verify_tls=True,
        proxy=None,
        timeout=30,
        max_retries=3,
    ):
        """
        Initialize Quay discovery client.

        Args:
            quay_url: Base Quay URL (e.g., "https://quay.io" or "https://quay.example.com")
            token: OAuth token or robot account token
            username: Robot account username (alternative to token)
            password: Robot account password (alternative to token)
            verify_tls: Verify TLS certificates (default: True)
            proxy: HTTP proxy configuration dict with http/https keys
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.quay_url = quay_url.rstrip("/")
        self.token = token
        self.username = username
        self.password = password
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
            logger.debug("Quay client configured with token authentication")
        elif username and password:
            self.session.auth = (username, password)
            logger.debug("Quay client configured with basic authentication")
        else:
            logger.warning("Quay client configured without authentication")

        # Configure proxy
        if proxy:
            self.session.proxies = proxy
            logger.debug("Quay client configured with proxy: %s", proxy)

    def discover_repositories(self, org_name):
        """
        Discover all repositories in a Quay organization.

        Args:
            org_name: Quay organization name

        Returns:
            List of dicts with 'name' and 'external_reference' keys,
            or None if discovery failed

        Example:
            [
                {
                    "name": "myrepo",
                    "external_reference": "quay.io/myorg/myrepo"
                },
                ...
            ]
        """
        logger.info("Starting discovery for Quay organization: %s", org_name)

        repositories = []
        next_page = None

        try:
            while True:
                repos, next_page = self._list_repositories_page(org_name, next_page=next_page)

                if not repos:
                    # No more repositories
                    break

                repositories.extend(repos)

                logger.debug(
                    "Fetched page: %d repositories (total: %d)",
                    len(repos),
                    len(repositories),
                )

                # Check if more pages available
                if next_page is None:
                    # Last page
                    break

            logger.info(
                "Successfully discovered %d repositories in Quay organization %s",
                len(repositories),
                org_name,
            )

            return repositories

        except Exception as e:
            logger.exception(
                "Failed to discover repositories from Quay organization %s: %s",
                org_name,
                str(e),
            )
            return None

    def _list_repositories_page(self, org_name, next_page=None):
        """
        List a single page of repositories in a Quay organization.

        Args:
            org_name: Quay organization name
            next_page: Pagination token (optional)

        Returns:
            Tuple of (repositories, next_page_token)

        Raises:
            QuayDiscoveryException: API request failed
        """
        url = urljoin(self.quay_url, "/api/v1/repository")

        params = {
            "namespace": org_name,
            "public": "false",  # Include private repos
        }

        if next_page:
            params["next_page"] = next_page

        logger.debug(
            "Fetching Quay repositories from %s: namespace=%s, next_page=%s",
            url,
            org_name,
            next_page,
        )

        try:
            response = self.session.get(
                url, params=params, verify=self.verify_tls, timeout=self.timeout
            )

            response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise QuayDiscoveryException(f"Quay organization not found: {org_name}")
            elif e.response.status_code == 401:
                raise QuayDiscoveryException("Quay authentication failed")
            elif e.response.status_code == 403:
                raise QuayDiscoveryException(f"Access denied to Quay organization: {org_name}")
            else:
                raise QuayDiscoveryException(
                    f"Quay API request failed: {e.response.status_code} {e.response.reason}"
                )

        except requests.exceptions.SSLError as e:
            raise QuayDiscoveryException(f"TLS verification failed: {str(e)}")

        except requests.exceptions.ProxyError as e:
            raise QuayDiscoveryException(f"Proxy error: {str(e)}")

        except requests.exceptions.ConnectionError as e:
            raise QuayDiscoveryException(f"Connection error: {str(e)}")

        except requests.exceptions.Timeout as e:
            raise QuayDiscoveryException(f"Request timeout: {str(e)}")

        except requests.exceptions.RequestException as e:
            raise QuayDiscoveryException(f"Request failed: {str(e)}")

        # Parse response
        try:
            data = response.json()
        except ValueError as e:
            raise QuayDiscoveryException(f"Invalid JSON response: {str(e)}")

        if not isinstance(data, dict):
            raise QuayDiscoveryException(
                f"Unexpected response format: expected dict, got {type(data)}"
            )

        # Extract repositories from response
        repos_data = data.get("repositories", [])

        if not isinstance(repos_data, list):
            raise QuayDiscoveryException(
                f"Unexpected repositories format: expected list, got {type(repos_data)}"
            )

        # Parse repositories
        repositories = []
        for repo in repos_data:
            try:
                repo_name = repo["name"]
                namespace = repo["namespace"]

                # Build external reference for mirroring
                # Format: quay.io/namespace/repo
                # Extract hostname from quay_url
                hostname = (
                    self.quay_url.split("://")[1] if "://" in self.quay_url else self.quay_url
                )

                external_ref = f"{hostname}/{namespace}/{repo_name}"

                repositories.append(
                    {
                        "name": repo_name,
                        "external_reference": external_ref,
                    }
                )

            except (KeyError, IndexError) as e:
                logger.warning("Failed to parse repository from Quay response: %s", str(e))
                continue

        # Extract next page token
        next_page_token = data.get("next_page")

        return repositories, next_page_token

    def test_connection(self, org_name):
        """
        Test connection to Quay API.

        Args:
            org_name: Quay organization name to test

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._list_repositories_page(org_name)
            logger.info("Quay connection test successful for organization: %s", org_name)
            return True

        except Exception as e:
            logger.error("Quay connection test failed for organization %s: %s", org_name, str(e))
            return False


def parse_quay_external_reference(external_reference):
    """
    Parse Quay external reference into components.

    Args:
        external_reference: Quay reference (e.g., "quay.io/myorg/myrepo")

    Returns:
        Dict with 'quay_url', 'org_name', 'repo_name' or None if invalid

    Example:
        {
            "quay_url": "https://quay.io",
            "org_name": "myorg",
            "repo_name": "myrepo"
        }
    """
    try:
        # Split into parts
        parts = external_reference.split("/")

        if len(parts) < 2:
            logger.warning("Invalid Quay reference format: %s", external_reference)
            return None

        # Extract components
        hostname = parts[0]
        org_name = parts[1]
        repo_name = "/".join(parts[2:]) if len(parts) > 2 else None

        # Build Quay URL
        quay_url = f"https://{hostname}"

        return {
            "quay_url": quay_url,
            "org_name": org_name,
            "repo_name": repo_name,
        }

    except Exception as e:
        logger.exception("Failed to parse Quay external reference: %s", str(e))
        return None


def is_quay_registry(external_reference):
    """
    Detect if external reference is a Quay registry.

    Args:
        external_reference: External reference string

    Returns:
        True if appears to be Quay, False otherwise

    Note:
        This uses hostname-based detection to differentiate Quay from Harbor.
        Checks for "quay" in hostname or quay.io specifically.
    """
    try:
        if not external_reference:
            return False

        parts = external_reference.split("/")
        if len(parts) < 2:
            return False

        hostname = parts[0].lower()

        # Check for quay.io specifically
        if hostname == "quay.io":
            return True

        # Check if hostname contains "quay"
        if "quay" in hostname:
            return True

        return False

    except Exception:
        return False
