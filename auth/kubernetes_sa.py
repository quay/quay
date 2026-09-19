"""Validation of Kubernetes ServiceAccount JWTs for workload identity bootstrap."""

import hashlib
import logging
import re
import threading
import time
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import jwt
from authlib.jose import JsonWebKey
from jwt import InvalidTokenError

from data.cache.cache_key import CacheKey
from oauth.oidc import JWT_CLOCK_SKEW_SECONDS
from util.security.jwtutil import decode

logger = logging.getLogger(__name__)

OIDC_WELL_KNOWN = ".well-known/openid-configuration"

# Only RS256 is trusted for Kubernetes ServiceAccount JWTs. This is intentionally
# separate from the generic OIDC login allow-list, which may support other algorithms.
KUBERNETES_SA_ALLOWED_ALGORITHMS = ["RS256"]
JWKS_REFRESH_COOLDOWN_SECONDS = 60

_SUBJECT_PATTERN = re.compile(r"^system:serviceaccount:([^:\s]+):([^:\s]+)$")


class KubernetesSATokenValidationError(Exception):
    """Raised when a Kubernetes ServiceAccount credential cannot be trusted."""

    def __init__(self, message: str, category: str = "trust"):
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class ValidatedKubernetesSA:
    issuer: str
    subject: str
    claims: dict[str, Any]


class KubernetesSATokenValidator:
    """Validate Kubernetes ServiceAccount JWTs using OIDC discovery and JWKS.

    This performs local trust verification only -- it never sends the workload
    JWT to Kubernetes TokenReview/SAR. Mapping a verified identity to Quay
    authorization is out of scope.
    """

    _refresh_lock = threading.Lock()
    _last_refresh_attempt: weakref.WeakKeyDictionary[Any, dict[str, float]] = (
        weakref.WeakKeyDictionary()
    )

    def __init__(self, config: dict[str, Any], http_client, cache):
        self._config = config
        self._http_client = http_client
        self._cache = cache

    def validate(self, token: str) -> ValidatedKubernetesSA:
        try:
            unverified = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False, "verify_aud": False},
                algorithms=KUBERNETES_SA_ALLOWED_ALGORITHMS,
            )
            headers = jwt.get_unverified_header(token)
        except Exception as exc:
            raise KubernetesSATokenValidationError(
                "Malformed Kubernetes ServiceAccount token"
            ) from exc

        issuer = unverified.get("iss")
        kid = headers.get("kid")
        if not isinstance(issuer, str) or not issuer or not isinstance(kid, str) or not kid:
            raise KubernetesSATokenValidationError("Token is missing required issuer or key ID")

        issuer_config = self._issuer_config(issuer)

        try:
            key = self._get_key(issuer_config, kid)
        except KubernetesSATokenValidationError:
            raise
        except Exception as exc:
            raise KubernetesSATokenValidationError(
                "Kubernetes ServiceAccount signing keys are unavailable"
            ) from exc

        try:
            claims = self._decode(token, key, issuer)
        except InvalidTokenError as exc:
            raise KubernetesSATokenValidationError(
                "Kubernetes ServiceAccount token failed validation"
            ) from exc

        namespace, name = self._parse_subject(claims.get("sub"))
        self._verify_bound_claims(claims, namespace, name)

        return ValidatedKubernetesSA(
            issuer=issuer, subject=f"system:serviceaccount:{namespace}:{name}", claims=claims
        )

    def _decode(self, token: str, key: Any, issuer: str) -> dict[str, Any]:
        return decode(
            token,
            key,
            algorithms=KUBERNETES_SA_ALLOWED_ALGORITHMS,
            issuer=issuer,
            audience=self._config.get("REQUIRED_AUDIENCE", "quay-bootstrap"),
            leeway=JWT_CLOCK_SKEW_SECONDS,
            options={"require": ["iss", "sub", "iat", "exp", "aud"]},
        )

    def _parse_subject(self, subject: Any) -> tuple[str, str]:
        if not isinstance(subject, str):
            raise KubernetesSATokenValidationError(
                "Token is not a Kubernetes ServiceAccount token", category="identity"
            )
        match = _SUBJECT_PATTERN.match(subject)
        if not match:
            raise KubernetesSATokenValidationError(
                "Token is not a Kubernetes ServiceAccount token", category="identity"
            )
        return match.group(1), match.group(2)

    def _verify_bound_claims(self, claims: dict[str, Any], namespace: str, name: str) -> None:
        bound = claims.get("kubernetes.io")
        if not isinstance(bound, dict):
            raise KubernetesSATokenValidationError(
                "Token is missing Kubernetes bound ServiceAccount claims", category="identity"
            )
        if bound.get("namespace") != namespace:
            raise KubernetesSATokenValidationError(
                "Token namespace claim does not match subject", category="identity"
            )

        service_account = bound.get("serviceaccount")
        if not isinstance(service_account, dict):
            raise KubernetesSATokenValidationError(
                "Token is missing Kubernetes bound ServiceAccount claims", category="identity"
            )
        if service_account.get("name") != name:
            raise KubernetesSATokenValidationError(
                "Token ServiceAccount name claim does not match subject", category="identity"
            )

        uid = service_account.get("uid")
        if not isinstance(uid, str) or not uid:
            raise KubernetesSATokenValidationError(
                "Token is missing a Kubernetes ServiceAccount UID claim", category="identity"
            )

    def _issuer_config(self, token_issuer: str) -> dict[str, Any]:
        for issuer_config in self._config.get("ISSUERS", []):
            configured = issuer_config.get("ISSUER")
            if configured and configured.rstrip("/") == token_issuer.rstrip("/"):
                return issuer_config
        raise KubernetesSATokenValidationError("Token issuer is not trusted")

    def _get_key(self, issuer_config: dict[str, Any], kid: str):
        metadata = self._metadata(issuer_config)
        jwks_cache_key = self._jwks_cache_key(issuer_config, metadata["jwks_uri"])
        keys_by_kid = self._load_keys(issuer_config, metadata, jwks_cache_key)
        if kid not in keys_by_kid:
            keys_by_kid = self._refresh_keys(issuer_config, metadata, jwks_cache_key, keys_by_kid)
        if kid not in keys_by_kid:
            raise KubernetesSATokenValidationError("Token signing key was not found")
        return keys_by_kid[kid]

    def _refresh_keys(
        self,
        issuer_config: dict[str, Any],
        metadata: dict[str, Any],
        jwks_cache_key: CacheKey,
        current_keys: dict[str, Any],
    ) -> dict[str, Any]:
        """Refresh JWKS at most once per cooldown when an unknown key ID is seen."""
        now = time.monotonic()
        with self._refresh_lock:
            cache_attempts = self._last_refresh_attempt.setdefault(self._cache, {})
            previous_attempt = cache_attempts.get(jwks_cache_key.key)
            if (
                previous_attempt is not None
                and now - previous_attempt < JWKS_REFRESH_COOLDOWN_SECONDS
            ):
                return current_keys
            cache_attempts[jwks_cache_key.key] = now

        # Coordinate the cooldown across Quay workers when a shared model cache is
        # configured. The process-local guard above still bounds refreshes when the
        # deployment intentionally uses the no-op cache.
        refresh_marker = CacheKey(
            f"{jwks_cache_key.key}__refresh", f"{JWKS_REFRESH_COOLDOWN_SECONDS}s"
        )
        marker_added = self._cache.add(refresh_marker, True)
        if marker_added is False:
            return current_keys

        self._cache.invalidate(jwks_cache_key)
        return self._load_keys(issuer_config, metadata, jwks_cache_key)

    def _load_keys(
        self,
        issuer_config: dict[str, Any],
        metadata: dict[str, Any],
        jwks_cache_key: CacheKey,
    ) -> dict[str, Any]:
        jwks = self._cache.retrieve(
            jwks_cache_key,
            lambda: self._fetch_jwks(metadata, issuer_config),
        )

        keys_by_kid = {}
        for key_spec in jwks.get("keys", []):
            kid = key_spec.get("kid")
            if not isinstance(kid, str) or not kid:
                continue
            if key_spec.get("kty") != "RSA":
                continue
            if key_spec.get("use") not in (None, "sig"):
                continue
            if key_spec.get("alg") not in (None, "RS256"):
                continue
            try:
                keys_by_kid[kid] = JsonWebKey.import_key(key_spec).as_key()
            except Exception:
                logger.warning(
                    "Skipping unparseable Kubernetes ServiceAccount signing key '%s'", kid
                )
        return keys_by_kid

    def _fetch_jwks(
        self, metadata: dict[str, Any], issuer_config: dict[str, Any]
    ) -> dict[str, Any]:
        return self._get_json(metadata["jwks_uri"], issuer_config)

    def _metadata(self, issuer_config: dict[str, Any]) -> dict[str, Any]:
        cache_key = self._discovery_cache_key(issuer_config)
        return self._cache.retrieve(
            cache_key,
            lambda: self._fetch_metadata(issuer_config),
        )

    def _fetch_metadata(self, issuer_config: dict[str, Any]) -> dict[str, Any]:
        issuer = issuer_config["ISSUER"]
        endpoint = issuer_config.get("DISCOVERY_ENDPOINT", issuer).rstrip("/") + "/"
        discovery_url = urljoin(endpoint, OIDC_WELL_KNOWN)
        if urlsplit(discovery_url).scheme != "https":
            raise KubernetesSATokenValidationError("OIDC discovery endpoint must use https")
        metadata = self._get_json(discovery_url, issuer_config)

        discovered_issuer = metadata.get("issuer")
        if not discovered_issuer or discovered_issuer.rstrip("/") != issuer.rstrip("/"):
            raise KubernetesSATokenValidationError(
                "OIDC discovery issuer does not match configuration"
            )

        jwks_uri = metadata.get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri.startswith("https://"):
            raise KubernetesSATokenValidationError(
                "OIDC discovery did not provide a secure JWKS URI"
            )

        # Never trust a JWKS URI outside the origin we just fetched discovery from --
        # otherwise a compromised or misconfigured issuer could redirect Quay's mounted
        # ServiceAccount credential to an arbitrary host (SSRF / credential exfiltration).
        if _origin(jwks_uri) != _origin(discovery_url):
            raise KubernetesSATokenValidationError(
                "OIDC discovery returned a JWKS URI outside the trusted origin"
            )

        return metadata

    def _discovery_cache_key(self, issuer_config: dict[str, Any]) -> CacheKey:
        issuer = issuer_config["ISSUER"]
        endpoint = issuer_config.get("DISCOVERY_ENDPOINT", issuer)
        return self._cache_key("discovery", f"{issuer}\0{endpoint}")

    def _jwks_cache_key(self, issuer_config: dict[str, Any], jwks_uri: str) -> CacheKey:
        issuer = issuer_config["ISSUER"]
        return self._cache_key("jwks", f"{issuer}\0{jwks_uri}")

    def _cache_key(self, kind: str, identity: str) -> CacheKey:
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        ttl = self._config.get("JWKS_CACHE_TTL_SECONDS", 3600)
        return CacheKey(f"kubernetes_sa_oidc_{kind}__{digest}", f"{ttl}s")

    def _get_json(self, url: str, issuer_config: dict[str, Any]) -> dict[str, Any]:
        if urlsplit(url).scheme.lower() != "https":
            raise KubernetesSATokenValidationError("OIDC endpoint must use https")

        headers = {}
        token_path = issuer_config.get("BEARER_TOKEN_PATH")
        if token_path:
            headers["Authorization"] = f"Bearer {Path(token_path).read_text().strip()}"
        verify: bool | str = issuer_config.get("CA_CERT_PATH", True)

        try:
            response = self._http_client.get(
                url, headers=headers, timeout=5, verify=verify, allow_redirects=False
            )
        except KubernetesSATokenValidationError:
            raise
        except Exception as exc:
            raise KubernetesSATokenValidationError("OIDC request failed") from exc

        if response.status_code // 100 != 2:
            raise KubernetesSATokenValidationError("OIDC request failed")
        try:
            value = response.json()
        except ValueError as exc:
            raise KubernetesSATokenValidationError("OIDC response was not valid JSON") from exc
        if not isinstance(value, dict):
            raise KubernetesSATokenValidationError("OIDC response was not an object")
        return value


def _origin(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    return (parsed.scheme, parsed.netloc)
