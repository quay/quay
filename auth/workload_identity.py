"""Authorization helpers for Kubernetes workload identity exchange."""

import re

_SCOPE_TOKEN = re.compile(r"^[\x21\x23-\x5b\x5d-\x7e]+$")


class WorkloadIdentityAuthorizationError(Exception):
    """Raised when a trusted workload identity is not authorized."""


def _normalize_issuer(issuer: str | None) -> str:
    return (issuer or "").rstrip("/")


def _scope_tokens(value: str | None) -> set[str]:
    """Parse an OAuth scope string and reject malformed scope-token input."""
    if value is None or not value:
        return set()
    tokens = value.split(" ")
    if any(
        not token
        or not _SCOPE_TOKEN.fullmatch(token)
        or any(character in token for character in "\\\"'")
        for token in tokens
    ):
        raise WorkloadIdentityAuthorizationError("scope contains invalid characters")
    return set(tokens)


def authorize_workload_identity_scope(
    authorized_subjects: list[dict], issuer: str, subject: str, requested_scope: str
) -> str:
    """Return the canonical scope allowed for an exact issuer and subject."""
    normalized = _normalize_issuer(issuer)
    mapping = next(
        (
            item
            for item in authorized_subjects
            if _normalize_issuer(item.get("ISSUER")) == normalized
            and item.get("SUBJECT") == subject
        ),
        None,
    )
    if mapping is None:
        raise WorkloadIdentityAuthorizationError("Kubernetes ServiceAccount is not authorized")
    allowed = _scope_tokens(mapping.get("SCOPES"))
    requested = _scope_tokens(requested_scope) if requested_scope else allowed
    if not allowed or not requested or not requested.issubset(allowed):
        raise WorkloadIdentityAuthorizationError(
            "requested scope is not authorized for the Kubernetes ServiceAccount"
        )
    return " ".join(sorted(requested))
