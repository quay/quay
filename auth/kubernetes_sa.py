"""Validation of Kubernetes ServiceAccount JWTs for workload identity bootstrap."""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

import jwt
from authlib.jose import JsonWebKey
from jwt import InvalidTokenError

from oauth.oidc import JWT_CLOCK_SKEW_SECONDS

logger = logging.getLogger(__name__)

OIDC_WELL_KNOWN = ".well-known/openid-configuration"
_DEFAULT_CACHE_TTL_SECONDS = 3600

# Only RS256 is trusted for Kubernetes ServiceAccount JWTs. This is intentionally
# separate from the generic OIDC login allow-list, which may support other algorithms.
KUBERNETES_SA_ALLOWED_ALGORITHMS = ["RS256"]

_SUBJECT_PATTERN = re.compile(r"^system:serviceaccount:([^:\s]+):([^:\s]+)$")


class KubernetesSATokenValidationError(Exception):
    """Raised when a Kubernetes ServiceAccount credential cannot be trusted."""


@dataclass(frozen=True)
class ValidatedKubernetesSA:
    issuer: str
    subject: str
    claims: dict[str, Any]


@dataclass
class _CacheEntry:
    value: Any
    fetched_at: float


class _StaleTolerantCache:
    """Caches loader() results with a bounded grace period for refresh failures.

    A value is reused without calling loader() until `ttl_seconds` elapses. Past
    that, a refresh is attempted; if loader() raises, the previous value is reused
    for one additional `ttl_seconds` window (bounded staleness) before the entry is
    dropped entirely and callers must obtain a fresh value or fail. A successful
    refresh always replaces the previous value, even if it no longer contains what
    the caller is looking for -- there is no stale fallback once the issuer has
    authoritatively responded.
    """

    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, _CacheEntry] = {}

    def get(self, key: str, loader: Callable[[], Any], force: bool = False) -> tuple[Any, bool]:
        now = time.monotonic()
        entry = self._entries.get(key)

        if entry is not None and not force:
            age = now - entry.fetched_at
            if age <= self._ttl_seconds:
                return entry.value, False
            if age <= 2 * self._ttl_seconds:
                try:
                    value = loader()
                except Exception:
                    return entry.value, True
                self._entries[key] = _CacheEntry(value, now)
                return value, False
            # Past the bounded grace window: no more stale fallback is permitted.
            self._entries.pop(key, None)

        # Cold cache, forced refresh, or expired past the grace window: must succeed.
        value = loader()
        self._entries[key] = _CacheEntry(value, now)
        return value, False


class KubernetesSATokenValidator:
    """Validate Kubernetes ServiceAccount JWTs using OIDC discovery and JWKS.

    This performs local trust verification only -- it never sends the workload
    JWT to Kubernetes TokenReview/SAR. Mapping a verified identity to Quay
    authorization is out of scope.
    """

    def __init__(self, config: dict[str, Any], http_client):
        self._config = config
        self._http_client = http_client
        ttl = config.get("JWKS_CACHE_TTL_SECONDS", _DEFAULT_CACHE_TTL_SECONDS)
        self._metadata_cache = _StaleTolerantCache(ttl)
        self._jwks_cache = _StaleTolerantCache(ttl)

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
        return jwt.decode(
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
            raise KubernetesSATokenValidationError("Token is not a Kubernetes ServiceAccount token")
        match = _SUBJECT_PATTERN.match(subject)
        if not match:
            raise KubernetesSATokenValidationError("Token is not a Kubernetes ServiceAccount token")
        return match.group(1), match.group(2)

    def _verify_bound_claims(self, claims: dict[str, Any], namespace: str, name: str) -> None:
        bound = claims.get("kubernetes.io")
        if not isinstance(bound, dict):
            raise KubernetesSATokenValidationError(
                "Token is missing Kubernetes bound ServiceAccount claims"
            )
        if bound.get("namespace") != namespace:
            raise KubernetesSATokenValidationError("Token namespace claim does not match subject")

        service_account = bound.get("serviceaccount")
        if not isinstance(service_account, dict):
            raise KubernetesSATokenValidationError(
                "Token is missing Kubernetes bound ServiceAccount claims"
            )
        if service_account.get("name") != name:
            raise KubernetesSATokenValidationError(
                "Token ServiceAccount name claim does not match subject"
            )

        uid = service_account.get("uid")
        if not isinstance(uid, str) or not uid:
            raise KubernetesSATokenValidationError(
                "Token is missing a Kubernetes ServiceAccount UID claim"
            )

    def _issuer_config(self, token_issuer: str) -> dict[str, Any]:
        for issuer_config in self._config.get("ISSUERS", []):
            configured = issuer_config.get("ISSUER")
            if configured and configured.rstrip("/") == token_issuer.rstrip("/"):
                return issuer_config
        raise KubernetesSATokenValidationError("Token issuer is not trusted")

    def _get_key(self, issuer_config: dict[str, Any], kid: str):
        issuer = issuer_config["ISSUER"]

        keys_by_kid, stale = self._jwks_cache.get(issuer, lambda: self._fetch_jwks(issuer_config))
        if stale:
            logger.warning(
                "Kubernetes ServiceAccount JWKS refresh failed for issuer '%s'; using cached "
                "signing keys for the remainder of the bounded grace period",
                issuer,
            )
        if kid in keys_by_kid:
            return keys_by_kid[kid]

        # The kid may be unknown because Kubernetes rotated its signing key. Force an
        # immediate, uncached refresh -- there is no stale fallback for an unknown kid.
        logger.info(
            "Kubernetes ServiceAccount signing key '%s' not found for issuer '%s'; forcing refresh",
            kid,
            issuer,
        )
        keys_by_kid, _ = self._jwks_cache.get(
            issuer, lambda: self._fetch_jwks(issuer_config, force=True), force=True
        )
        if kid not in keys_by_kid:
            raise KubernetesSATokenValidationError("Token signing key was not found")
        return keys_by_kid[kid]

    def _fetch_jwks(self, issuer_config: dict[str, Any], force: bool = False) -> dict[str, Any]:
        metadata = self._metadata(issuer_config, force=force)
        jwks = self._get_json(metadata["jwks_uri"], issuer_config)

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

    def _metadata(self, issuer_config: dict[str, Any], force: bool = False) -> dict[str, Any]:
        issuer = issuer_config["ISSUER"]

        def load() -> dict[str, Any]:
            endpoint = issuer_config.get("DISCOVERY_ENDPOINT", issuer).rstrip("/") + "/"
            discovery_url = urljoin(endpoint, OIDC_WELL_KNOWN)
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

        metadata, stale = self._metadata_cache.get(issuer, load, force=force)
        if stale:
            logger.warning(
                "Kubernetes ServiceAccount OIDC discovery refresh failed for issuer '%s'; using "
                "cached metadata for the remainder of the bounded grace period",
                issuer,
            )
        return metadata

    def _get_json(self, url: str, issuer_config: dict[str, Any]) -> dict[str, Any]:
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
