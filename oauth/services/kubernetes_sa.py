"""
Kubernetes ServiceAccount OIDC authentication service for Quay.

Enables Kubernetes ServiceAccount tokens to authenticate to Quay using OIDC
federation. SA tokens map to robot accounts owned by a configurable system
organization. Authenticated SAs matching the configured superuser subject
receive dynamic superuser privileges.
"""

import logging
import os
import re
from typing import Any, Optional

from oauth.oidc import (
    ALLOWED_ALGORITHMS,
    JWT_CLOCK_SKEW_SECONDS,
    OIDCLoginService,
    PublicKeyLoadException,
)
from util.security.jwtutil import InvalidTokenError, decode

logger = logging.getLogger(__name__)

# Standard Kubernetes ServiceAccount CA certificate path
SERVICE_ACCOUNT_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

# Kubernetes SA subject format: system:serviceaccount:<namespace>:<name>
KUBERNETES_SA_SUBJECT_PATTERN = re.compile(
    r"^system:serviceaccount:(?P<namespace>[^:]+):(?P<name>[^:]+)$"
)

# Default system org for Kubernetes SA robot accounts
DEFAULT_SYSTEM_ORG_NAME = "quay-system"

# Default Kubernetes API server OIDC endpoint (in-cluster)
# Can be overridden via KUBERNETES_SA_AUTH_CONFIG.OIDC_SERVER
DEFAULT_KUBERNETES_OIDC_SERVER = "https://kubernetes.default.svc"

# Default expected audience for Kubernetes SA tokens
# Operators must create tokens with this audience: kubectl create token <sa> --audience=quay
DEFAULT_EXPECTED_AUDIENCE = "quay"


class KubernetesServiceAccountLoginService(OIDCLoginService):
    """
    Kubernetes ServiceAccount OIDC authentication service.

    Validates Kubernetes SA JWT tokens using OIDC/JWKS and maps them to robot
    accounts in a dedicated system organization.

    Unlike standard OIDC login services, this service:
    - Does not participate in OAuth authorization flows
    - Validates bearer tokens directly from Kubernetes pods
    - Validates audience claim against configurable value (default: "quay")
    - Maps SA subjects to robot accounts deterministically

    Operators must create tokens with the expected audience:
        kubectl create token <sa-name> --audience=quay
    """

    def __init__(
        self,
        config: dict[str, Any],
        key_name: str = "KUBERNETES_SA_AUTH_CONFIG",
        client: Any = None,
    ) -> None:
        """
        Initialize the Kubernetes SA login service.

        Args:
            config: Application configuration dict containing KUBERNETES_SA_AUTH_CONFIG
            key_name: Configuration key name (default: KUBERNETES_SA_AUTH_CONFIG)
            client: Optional HTTP client for testing
        """
        kubernetes_config: dict[str, Any] = config.get(key_name, {})

        # Get OIDC server from config, falling back to default
        oidc_server = kubernetes_config.get("OIDC_SERVER", DEFAULT_KUBERNETES_OIDC_SERVER)

        # Build OIDC-compatible config from Kubernetes SA config
        oidc_config: dict[str, Any] = {
            key_name: {
                "OIDC_SERVER": oidc_server,
                "SERVICE_NAME": kubernetes_config.get("SERVICE_NAME", "Kubernetes"),
                # CLIENT_ID is used for audience validation - defaults to server hostname
                "CLIENT_ID": config.get("SERVER_HOSTNAME", ""),
                "CLIENT_SECRET": "",  # Not used for SA token validation
                "DEBUGGING": kubernetes_config.get("DEBUGGING", False),
            },
            "HTTPCLIENT": config.get("HTTPCLIENT"),
            "TESTING": config.get("TESTING", False),
            "FEATURE_MAILING": False,
        }

        super().__init__(oidc_config, key_name, client)

        # Store Kubernetes-specific config
        self._kubernetes_config: dict[str, Any] = kubernetes_config
        self._oidc_server: str = oidc_server
        self._system_org_name: str = kubernetes_config.get(
            "SYSTEM_ORG_NAME", DEFAULT_SYSTEM_ORG_NAME
        )
        self._superuser_subjects: list[str] = kubernetes_config.get("SUPERUSER_SUBJECTS") or []
        self._verify_tls: bool = kubernetes_config.get("VERIFY_TLS", True)
        self._ca_bundle: str = kubernetes_config.get("CA_BUNDLE", SERVICE_ACCOUNT_CA_PATH)
        self._expected_audience: str = kubernetes_config.get(
            "EXPECTED_AUDIENCE", DEFAULT_EXPECTED_AUDIENCE
        )

    def service_id(self) -> str:
        return "kubernetes_sa"

    def service_name(self) -> str:
        return self._kubernetes_config.get("SERVICE_NAME", "Kubernetes")

    @property
    def oidc_server(self) -> str:
        """The Kubernetes OIDC server URL for token validation."""
        return self._oidc_server

    @property
    def system_org_name(self) -> str:
        """Name of the organization that owns Kubernetes SA robot accounts."""
        return self._system_org_name

    @property
    def superuser_subjects(self) -> list[str]:
        """List of SA subjects configured as superusers."""
        return self._superuser_subjects

    @property
    def expected_audience(self) -> str:
        """Expected audience claim for K8s SA tokens. Defaults to 'quay'."""
        return self._expected_audience

    def is_superuser_subject(self, subject: str) -> bool:
        """Check if the given SA subject is configured as a superuser."""
        return subject in self._superuser_subjects

    def parse_sa_subject(self, subject: str) -> Optional[tuple[str, str]]:
        """
        Parse a Kubernetes SA subject into namespace and name.

        Args:
            subject: SA subject (e.g., "system:serviceaccount:quay:quay-operator")

        Returns:
            Tuple of (namespace, sa_name) or None if invalid format
        """
        match = KUBERNETES_SA_SUBJECT_PATTERN.match(subject)
        if not match:
            return None
        return match.group("namespace"), match.group("name")

    def generate_robot_shortname(self, namespace: str, sa_name: str) -> str:
        """
        Generate a deterministic robot shortname from Kubernetes SA identity.

        Robot format: kube_<namespace>_<sa_name>
        Characters are sanitized to be valid robot names (lowercase alphanumeric + underscore).

        Args:
            namespace: Kubernetes namespace
            sa_name: ServiceAccount name

        Returns:
            Sanitized robot shortname
        """
        # Sanitize: replace invalid chars with underscore, lowercase
        safe_ns = re.sub(r"[^a-z0-9]", "_", namespace.lower())
        safe_name = re.sub(r"[^a-z0-9]", "_", sa_name.lower())
        return f"kube_{safe_ns}_{safe_name}"

    def get_ssl_verification(self) -> str | bool:
        """
        Get SSL verification setting for Kubernetes API calls.

        Returns:
            False if TLS verification disabled, path to CA bundle if configured,
            or True to use system CA certificates.
        """
        if not self._verify_tls:
            return False

        if self._ca_bundle and os.path.exists(self._ca_bundle):
            return self._ca_bundle

        return True

    def get_jwks_auth_headers(self) -> dict[str, str] | None:
        """
        Get auth headers for JWKS endpoint requests.

        Kubernetes OIDC JWKS endpoints may require authentication. We use
        the pod's ServiceAccount token to authenticate.

        Returns:
            Dict with Authorization header, or None if token unavailable.
        """
        token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        if os.path.exists(token_path):
            try:
                with open(token_path) as f:
                    token = f.read().strip()
                return {"Authorization": f"Bearer {token}"}
            except Exception as e:
                logger.warning(f"Failed to read SA token for JWKS auth: {e}")
        return None

    def _load_oidc_config_via_discovery(self, is_debugging: bool) -> dict[str, Any]:
        """
        Override to use custom TLS verification for Kubernetes API server.

        Kubernetes clusters may use self-signed certificates, so we use
        the configured CA bundle for verification.
        """
        import json
        from posixpath import join

        from oauth.oidc import OIDC_WELLKNOWN, DiscoveryFailureException

        oidc_server = self.config["OIDC_SERVER"]
        if not oidc_server.startswith("https://") and not is_debugging:
            raise DiscoveryFailureException("OIDC server must be accessed over SSL")

        ssl_verify = self.get_ssl_verification()
        auth_headers = self.get_jwks_auth_headers() or {}

        discovery_url = join(oidc_server, OIDC_WELLKNOWN)
        try:
            discovery = self._http_client.get(
                discovery_url, timeout=5, verify=ssl_verify, headers=auth_headers
            )
        except Exception as e:
            logger.exception("Failed to connect to Kubernetes OIDC server: %s", e)
            raise DiscoveryFailureException(f"Failed to connect to Kubernetes OIDC server: {e}")

        if discovery.status_code // 100 != 2:
            logger.debug(
                "Got %s response for OIDC discovery: %s",
                discovery.status_code,
                discovery.text,
            )
            raise DiscoveryFailureException(
                f"Could not load OIDC discovery information: {discovery.status_code}"
            )

        try:
            return json.loads(discovery.text)
        except ValueError:
            logger.exception("Could not parse OIDC discovery for url: %s", discovery_url)
            raise DiscoveryFailureException("Could not parse OIDC discovery information")

    def validate_sa_token(self, token: str) -> dict[str, Any]:
        """
        Validate a Kubernetes ServiceAccount JWT token.

        This method validates the token signature using JWKS from the Kubernetes
        API server. Audience validation is always enabled - operators must create
        tokens with the expected audience (default: "quay").

        Token creation example:
            kubectl create token <sa-name> --audience=quay

        Args:
            token: The JWT token from Kubernetes SA

        Returns:
            Decoded token claims

        Raises:
            InvalidTokenError: If token validation fails (including audience mismatch)
            PublicKeyLoadException: If JWKS cannot be loaded
        """
        options = {
            "verify_aud": True,  # Always validate - bound tokens always have aud
            "verify_nbf": False,  # Some Kubernetes tokens lack nbf claim
        }

        return self.decode_user_jwt(token, options=options, audience=self._expected_audience)

    def get_issuer(self) -> Optional[str]:
        """
        Get the expected token issuer.

        For Kubernetes, this is typically the API server URL or a custom
        issuer configured at the cluster level.
        """
        return self._issuer
