import logging
from datetime import UTC, datetime
from ipaddress import ip_address

from flask import Request, request

import features
from app import app
from auth.auth_context import get_validated_oauth_token
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
from endpoints.exception import InvalidToken, TokenRotationError, Unauthorized
from util.bootstrap_token import write_bootstrap_token

logger = logging.getLogger(__name__)

_INVALID_BOOTSTRAP_TOKEN_MESSAGE = "Requires valid bootstrap bearer token"
_QUAY_NGINX_ORIGINAL_REMOTE_ADDR_HEADER = "X-Quay-Original-Remote-Addr"


class BootstrapTokenCleanupError(Exception):
    pass


def _raise_invalid_bootstrap_token() -> None:
    raise InvalidToken(_INVALID_BOOTSTRAP_TOKEN_MESSAGE)


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_expired(token: OAuthAccessToken) -> bool:
    return token.expires_at <= _utcnow_naive()


def _is_loopback_remote_addr(remote_addr: str | None) -> bool:
    if not remote_addr:
        return False

    try:
        remote_ip = ip_address(remote_addr)
    except ValueError:
        return False

    if remote_ip.is_loopback:
        return True

    ipv4_mapped = getattr(remote_ip, "ipv4_mapped", None)
    return ipv4_mapped is not None and ipv4_mapped.is_loopback


def _unproxied_remote_addr(req: Request) -> str | None:
    proxy_fix_orig = req.environ.get("werkzeug.proxy_fix.orig") or {}
    return proxy_fix_orig.get("REMOTE_ADDR") or req.environ.get("REMOTE_ADDR")


def _has_forwarding_headers(req: Request) -> bool:
    return bool(
        req.headers.get("X-Forwarded-For")
        or req.headers.get("X-Real-IP")
        or req.headers.get("Forwarded")
    )


def _has_internal_or_unset_direct_peer(req: Request) -> bool:
    direct_peer = _unproxied_remote_addr(req)
    return not direct_peer or _is_loopback_remote_addr(direct_peer)


def _is_loopback_bootstrap_renewal_request(req: Request) -> bool:
    if _has_forwarding_headers(req):
        # Standard Quay deployments route /api/ requests through the bundled
        # nginx, which always adds X-Forwarded-For before proxying to gunicorn.
        # Do not trust request.remote_addr here: ProxyFix derives it from
        # X-Forwarded-For. Instead, trust only the original TCP peer address
        # overwritten by Quay's own nginx configuration, and require the direct
        # peer to be unset (Unix socket) or loopback (local TCP proxy).
        return _is_loopback_remote_addr(
            req.headers.get(_QUAY_NGINX_ORIGINAL_REMOTE_ADDR_HEADER)
        ) and _has_internal_or_unset_direct_peer(req)

    return _is_loopback_remote_addr(_unproxied_remote_addr(req))


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

        try:
            with db_transaction():
                lock_bootstrap_token_operation()

                current_token = validate_bootstrap_token(token_string, app.config)
                if current_token is None:
                    _raise_invalid_bootstrap_token()

                if _is_expired(current_token) and not _is_loopback_bootstrap_renewal_request(
                    request
                ):
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
