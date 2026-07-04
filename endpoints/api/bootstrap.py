import logging
from datetime import UTC, datetime

from flask import request

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


class BootstrapTokenCleanupError(Exception):
    pass


def _raise_invalid_bootstrap_token() -> None:
    raise InvalidToken(_INVALID_BOOTSTRAP_TOKEN_MESSAGE)


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_expired(token: OAuthAccessToken) -> bool:
    return token.expires_at <= _utcnow_naive()


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

        if _is_expired(current_token):
            _raise_invalid_bootstrap_token()

        try:
            with db_transaction():
                lock_bootstrap_token_operation()

                current_token = validate_bootstrap_token(token_string, app.config)
                if current_token is None:
                    _raise_invalid_bootstrap_token()

                if _is_expired(current_token):
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
