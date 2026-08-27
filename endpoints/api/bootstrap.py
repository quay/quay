import json
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

import jwt
from flask import Request, request

import features
from app import app
from auth.auth_context import get_validated_oauth_token
from data import model
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
    def __init__(self, error, description, status_code):
        super().__init__(
            ApiErrorType.invalid_token if status_code == 401 else ApiErrorType.unauthorized,
            status_code,
            description,
            {"error": error, "error_description": description},
        )


def _exchange_config():
    return app.config.get("KUBERNETES_SA_BOOTSTRAP_CONFIG") or {}


def _exchange_error(error, description, status_code):
    raise BootstrapExchangeError(error, description, status_code)


def _raise_invalid_bootstrap_token() -> None:
    raise InvalidToken(_INVALID_BOOTSTRAP_TOKEN_MESSAGE)


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_expired(token: OAuthAccessToken) -> bool:
    return token.expires_at <= _utcnow_naive()


def _is_local_bootstrap_renewal_request(req: Request) -> bool:
    return (
        req.headers.get(_QUAY_BOOTSTRAP_RENEWAL_LOCATION_HEADER)
        == _QUAY_BOOTSTRAP_RENEWAL_LOCATION_LOCAL
    )


@resource("/v1/bootstrap/exchange")
@show_if(features.KUBERNETES_SA_BOOTSTRAP)
class BootstrapTokenExchange(ApiResource):
    @anon_allowed
    @nickname("exchangeBootstrapToken")
    def post(self):
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
            claims = jwt.decode(raw, options={"verify_signature": False})
        except jwt.InvalidTokenError:
            _exchange_error(
                "invalid_token", "Kubernetes ServiceAccount token failed validation", 401
            )
        issuer = claims.get("iss")
        audience = _exchange_config().get("REQUIRED_AUDIENCE", "quay-bootstrap")
        if issuer not in {
            item.get("ISSUER") for item in _exchange_config().get("ISSUERS", [])
        } or audience not in (
            claims.get("aud") if isinstance(claims.get("aud"), list) else [claims.get("aud")]
        ):
            _exchange_error(
                "invalid_token", "Kubernetes ServiceAccount token failed validation", 401
            )
        subject = claims.get("sub")
        mapping = next(
            (
                item
                for item in _exchange_config().get("AUTHORIZED_SUBJECTS", [])
                if item.get("ISSUER") == issuer and item.get("SUBJECT") == subject
            ),
            None,
        )
        if mapping is None:
            _exchange_error("access_denied", "Kubernetes ServiceAccount is not authorized", 403)
        allowed = set(mapping.get("SCOPES", "").split())
        requested = set(values.get("scope", "").split()) or allowed
        if not requested.issubset(allowed):
            _exchange_error(
                "access_denied",
                "requested scope is not authorized for the Kubernetes ServiceAccount",
                403,
            )
        owner = model.user.get_user(app.config.get("BOOTSTRAP_TOKEN_OWNER"))
        if owner is None:
            _exchange_error("server_error", "bootstrap token owner does not exist", 500)
        application = model.oauth.get_singleton_bootstrap_application(owner)
        if application is None:
            application = model.oauth.create_bootstrap_application(
                model.oauth.get_bootstrap_app_name(), owner
            )
        record, token = create_bootstrap_oauth_api_token(
            application,
            owner,
            " ".join(sorted(requested)),
            expiration_seconds=min(
                app.config.get("BOOTSTRAP_TOKEN_MAX_TTL", 86400),
                app.config.get("BOOTSTRAP_TOKEN_EXPIRATION", 3600),
            ),
        )
        data = json.loads(record.data)
        data["subject"] = subject
        record.data = json.dumps(data)
        record.save()
        expires = app.config.get("BOOTSTRAP_TOKEN_EXPIRATION", 3600)
        return {
            "access_token": token,
            "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "token_type": "Bearer",
            "expires_in": expires,
            "scope": " ".join(sorted(requested)),
        }, 200


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
