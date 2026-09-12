import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from flask import Request, request

import features
from app import app, model_cache
from auth.auth_context import get_validated_oauth_token
from auth.kubernetes_sa import (
    KubernetesSATokenValidationError,
    KubernetesSATokenValidator,
)
from auth.workload_identity import (
    WorkloadIdentityAuthorizationError,
    authorize_workload_identity_scope,
)
from data import model
from data.database import OAuthAccessToken
from data.model import db_transaction
from data.model.oauth import (
    create_bootstrap_application,
    create_bootstrap_oauth_api_token,
    create_workload_identity_oauth_token,
    delete_bootstrap_tokens,
    get_canonical_automatic_bootstrap_application,
    lock_bootstrap_token_operation,
    validate_bootstrap_token,
)
from endpoints.api import ApiResource, nickname, resource, show_if
from endpoints.decorators import anon_allowed
from endpoints.exception import (
    ApiErrorType,
    ApiException,
    InvalidToken,
    TokenRotationError,
    Unauthorized,
)
from util.bootstrap_token import write_bootstrap_token

logger = logging.getLogger(__name__)

_INVALID_BOOTSTRAP_TOKEN_MESSAGE = "Requires valid bootstrap bearer token"
_QUAY_BOOTSTRAP_RENEWAL_LOCATION_HEADER = "X-Quay-Bootstrap-Renewal-Location"
_QUAY_BOOTSTRAP_RENEWAL_LOCATION_LOCAL = "local"


class BootstrapTokenCleanupError(Exception):
    pass


class BootstrapExchangeError(ApiException):
    """Represent an OAuth token-exchange error as a Quay API problem."""

    _ERROR_TYPES = {
        "invalid_request": ApiErrorType.invalid_request,
        "invalid_token": ApiErrorType.invalid_token,
        "access_denied": ApiErrorType.unauthorized,
        "server_error": ApiErrorType.server_error,
    }

    def __init__(self, error, description, status_code):
        super().__init__(
            self._ERROR_TYPES[error],
            status_code,
            description,
            {"error": error, "error_description": description},
        )


def _exchange_config():
    """Return the configured Kubernetes ServiceAccount exchange settings."""
    return app.config.get("KUBERNETES_SA_BOOTSTRAP_CONFIG") or {}


def _exchange_error(error, description, status_code):
    """Raise a structured OAuth token-exchange error."""
    raise BootstrapExchangeError(error, description, status_code)


def _exchange_response(payload):
    """Return a successful token-exchange response that cannot be cached."""
    return payload, 200, {"Cache-Control": "no-store", "Pragma": "no-cache"}


def _normalize_exchange_issuer(issuer):
    """Normalize an issuer for comparison with configured authorization mappings."""
    return (issuer or "").rstrip("/")


def _exchange_expiration_seconds(validated=None):
    """Return the configured lifetime bounded by the verified JWT lifetime."""
    if validated is None:
        return min(
            _exchange_config().get("BOOTSTRAP_TOKEN_MAX_TTL", 86400),
            app.config.get("BOOTSTRAP_TOKEN_EXPIRATION", 3600),
        )
    try:
        remaining = int(float(validated.claims["exp"]) - datetime.now(UTC).timestamp())
    except (KeyError, TypeError, ValueError, OverflowError):
        _exchange_error(
            "invalid_token", "Kubernetes ServiceAccount token has invalid expiration", 401
        )
    if remaining <= 0:
        _exchange_error("invalid_token", "Kubernetes ServiceAccount token has expired", 401)
    return min(
        _exchange_config().get("BOOTSTRAP_TOKEN_MAX_TTL", 86400),
        app.config.get("BOOTSTRAP_TOKEN_EXPIRATION", 3600),
        remaining,
    )


class WorkloadScopeAuthorizationError(WorkloadIdentityAuthorizationError):
    """Backward-compatible alias for the endpoint authorization error."""


def authorize_workload_scope(authorized_subjects, issuer, subject, requested_scope):
    """Return the effective scope authorized for an exact issuer and subject."""
    return authorize_workload_identity_scope(authorized_subjects, issuer, subject, requested_scope)


def _raise_invalid_bootstrap_token() -> None:
    """Raise the standard invalid bootstrap-token error."""
    raise InvalidToken(_INVALID_BOOTSTRAP_TOKEN_MESSAGE)


def _utcnow_naive() -> datetime:
    """Return the current UTC time without timezone information."""
    return datetime.now(UTC).replace(tzinfo=None)


def _is_expired(token: OAuthAccessToken) -> bool:
    """Return whether a bootstrap token has expired."""
    return token.expires_at <= _utcnow_naive()


def _is_local_bootstrap_renewal_request(req: Request) -> bool:
    """Return whether a request is an internal local renewal request."""
    return (
        req.headers.get(_QUAY_BOOTSTRAP_RENEWAL_LOCATION_HEADER)
        == _QUAY_BOOTSTRAP_RENEWAL_LOCATION_LOCAL
    )


def _mint_authorized_exchange(validated, effective_scope):
    owner = model.user.get_user(app.config.get("BOOTSTRAP_TOKEN_OWNER"))
    if owner is None:
        _exchange_error("server_error", "bootstrap token owner does not exist", 500)
    expiration_seconds = _exchange_expiration_seconds(validated)
    with db_transaction():
        lock_bootstrap_token_operation()
        application = get_canonical_automatic_bootstrap_application(owner)
        if application is None:
            application = create_bootstrap_application(model.oauth.get_bootstrap_app_name(), owner)
        _, token = create_workload_identity_oauth_token(
            application,
            owner,
            effective_scope,
            validated.issuer,
            validated.subject,
            expiration_seconds=expiration_seconds,
        )
    return _exchange_response(
        {
            "access_token": token,
            "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "token_type": "Bearer",
            "expires_in": expiration_seconds,
            "scope": effective_scope,
        }
    )


def _authorize_validated_exchange(validated, requested_scope):
    try:
        effective_scope = authorize_workload_identity_scope(
            _exchange_config().get("AUTHORIZED_SUBJECTS", []),
            validated.issuer,
            validated.subject,
            requested_scope,
        )
    except WorkloadIdentityAuthorizationError as exc:
        _exchange_error("access_denied", str(exc), 403)
    return _mint_authorized_exchange(validated, effective_scope)


def _exchange_bootstrap_token():
    """Validate an exchange request and mint its bounded bootstrap token."""
    values = request.form
    required = ("grant_type", "subject_token", "subject_token_type")
    if (
        any(not values.get(key) for key in required)
        or values.get("grant_type") != "urn:ietf:params:oauth:grant-type:token-exchange"
        or values.get("subject_token_type") != "urn:ietf:params:oauth:token-type:jwt"
    ):
        _exchange_error("invalid_request", "invalid token exchange request", 400)
    raw = values["subject_token"]
    try:
        validated = KubernetesSATokenValidator(
            _exchange_config(), app.config["HTTPCLIENT"], model_cache
        ).validate(raw)
    except KubernetesSATokenValidationError:
        _exchange_error("invalid_token", "Kubernetes ServiceAccount token failed validation", 401)
    return _authorize_validated_exchange(validated, values.get("scope", ""))


@resource("/v1/bootstrap/exchange")
@show_if(features.KUBERNETES_SA_BOOTSTRAP)
class BootstrapTokenExchange(ApiResource):
    @anon_allowed
    @nickname("exchangeBootstrapToken")
    def post(self):
        """Exchange a Kubernetes ServiceAccount JWT for a scoped token."""
        return _exchange_bootstrap_token()


@resource("/v1/bootstrap/renew")
@show_if(features.PROGRAMMATIC_BOOTSTRAP)
class BootstrapTokenRenew(ApiResource):
    """Rotate the bootstrap token."""

    @anon_allowed
    @nickname("renewBootstrapToken")
    def post(self):
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            _raise_invalid_bootstrap_token()

        token_string = parts[1].strip()
        if not token_string:
            _raise_invalid_bootstrap_token()

        current_token = validate_bootstrap_token(token_string, app.config)
        if current_token is None:
            if get_validated_oauth_token() is not None:
                raise Unauthorized()

            _raise_invalid_bootstrap_token()

        if _is_expired(current_token) and not _is_local_bootstrap_renewal_request(request):
            _raise_invalid_bootstrap_token()

        try:
            with db_transaction():
                lock_bootstrap_token_operation()

                current_token = validate_bootstrap_token(token_string, app.config)
                if current_token is None:
                    _raise_invalid_bootstrap_token()

                if _is_expired(current_token) and not _is_local_bootstrap_renewal_request(request):
                    _raise_invalid_bootstrap_token()

                scope = app.config["BOOTSTRAP_TOKEN_SCOPE"]
                expiration = app.config["BOOTSTRAP_TOKEN_EXPIRATION"]

                new_record, new_access_token = create_bootstrap_oauth_api_token(
                    current_token.application,
                    current_token.authorized_user,
                    scope,
                    expiration_seconds=expiration,
                )

                try:
                    delete_bootstrap_tokens(current_token.application, keep_token_id=new_record.id)
                except Exception as exc:
                    raise BootstrapTokenCleanupError() from exc

                write_bootstrap_token(app.config, new_access_token)
        except BootstrapTokenCleanupError:
            logger.exception("Bootstrap token renewal failed while deleting stale tokens")
            raise TokenRotationError("Token rotation failed: could not clean up tokens")
        except OSError:
            logger.exception("Bootstrap token renewal failed while writing token")
            raise TokenRotationError("Token rotation failed: could not write token")

        return {"status": "rotated"}, 200
