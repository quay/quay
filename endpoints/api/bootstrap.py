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
from data.database import OAuthAccessToken
from data.model import db_transaction
from data.model.oauth import (
    create_bootstrap_oauth_api_token,
    delete_bootstrap_tokens,
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


def _exchange_expiration_seconds():
    """Return the configured token lifetime bounded by the exchange maximum."""
    return min(
        _exchange_config().get("BOOTSTRAP_TOKEN_MAX_TTL", 86400),
        app.config.get("BOOTSTRAP_TOKEN_EXPIRATION", 3600),
    )


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


def _exchange_bootstrap_token():
    values = request.form
    required = ("grant_type", "subject_token", "subject_token_type")
    if (
        any(not values.get(key) for key in required)
        or values.get("grant_type") != "urn:ietf:params:oauth:grant-type:token-exchange"
        or values.get("subject_token_type") != "urn:ietf:params:oauth:token-type:jwt"
    ):
        _exchange_error("invalid_request", "invalid token exchange request", 400)
    try:
        validated = KubernetesSATokenValidator(
            _exchange_config(), app.config["HTTPCLIENT"], model_cache
        ).validate(values["subject_token"])
    except KubernetesSATokenValidationError:
        _exchange_error("invalid_token", "Kubernetes ServiceAccount token failed validation", 401)
    _exchange_error("server_error", "workload identity authorization is not available", 503)


@resource("/v1/bootstrap/exchange")
@show_if(features.KUBERNETES_SA_BOOTSTRAP)
class BootstrapTokenExchange(ApiResource):
    @anon_allowed
    @nickname("exchangeBootstrapToken")
    def post(self):
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
