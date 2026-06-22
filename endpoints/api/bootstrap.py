import logging
from datetime import datetime
from ipaddress import ip_address

from flask import request

import features
from app import app
from auth.auth_context import get_validated_oauth_token
from data.logs_model import logs_model
from data.model import db_transaction
from data.model.oauth import (
    create_oauth_api_token,
    delete_other_bootstrap_tokens,
    delete_token_by_id,
    get_bootstrap_app_name,
    lock_bootstrap_token_operation,
    validate_bootstrap_token,
)
from endpoints.api import ApiResource, nickname, resource, show_if
from endpoints.exception import InvalidToken, Unauthorized
from util.bootstrap_token import write_bootstrap_token

logger = logging.getLogger(__name__)

_INVALID_BOOTSTRAP_TOKEN_MESSAGE = "Requires valid bootstrap bearer token"


def _raise_invalid_bootstrap_token():
    raise InvalidToken(_INVALID_BOOTSTRAP_TOKEN_MESSAGE)


def _is_expired(token):
    return token.expires_at <= datetime.utcnow()


def _is_loopback_remote_addr(remote_addr):
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


def _unproxied_remote_addr(req):
    proxy_fix_orig = req.environ.get("werkzeug.proxy_fix.orig") or {}
    return proxy_fix_orig.get("REMOTE_ADDR") or req.environ.get("REMOTE_ADDR")


def _is_unproxied_loopback_request(req):
    if (
        req.headers.get("X-Forwarded-For")
        or req.headers.get("X-Real-IP")
        or req.headers.get("Forwarded")
    ):
        return False

    return _is_loopback_remote_addr(_unproxied_remote_addr(req))


@resource("/v1/bootstrap/renew")
@show_if(features.PROGRAMMATIC_BOOTSTRAP)
class BootstrapTokenRenew(ApiResource):
    """Rotate the bootstrap token."""

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

        new_record = None
        try:
            with db_transaction():
                lock_bootstrap_token_operation()

                current_token = validate_bootstrap_token(token_string, app.config)
                if current_token is None:
                    _raise_invalid_bootstrap_token()

                if _is_expired(current_token) and not _is_unproxied_loopback_request(request):
                    _raise_invalid_bootstrap_token()

                scope = app.config["PROGRAMMATIC_TOKEN_SCOPE"]
                expiration = app.config["PROGRAMMATIC_TOKEN_EXPIRATION"]

                new_record, new_access_token = create_oauth_api_token(
                    application=current_token.application,
                    user=current_token.authorized_user,
                    scope=scope,
                    expiration_seconds=expiration,
                )

                write_bootstrap_token(app.config, new_access_token)
                delete_other_bootstrap_tokens(
                    current_token.application, keep_token_id=new_record.id
                )
        except OSError:
            if new_record is not None:
                delete_token_by_id(new_record.id)
            logger.exception("Bootstrap token renewal: failed to write token")
            return {"message": "Token rotation failed: could not write token"}, 500

        logs_model.log_action(
            "create_oauth_api_token",
            current_token.authorized_user.username,
            metadata={
                "auth_method": "token_renewal",
                "oauth_token_uuid": new_record.uuid,
                "scope": scope,
                "application_name": get_bootstrap_app_name(app.config),
            },
        )

        return {"status": "rotated"}, 200
