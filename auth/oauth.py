import logging

from datetime import datetime

from auth.scopes import scopes_from_scope_string
from auth.validateresult import AuthKind, ValidateResult
from data import model

logger = logging.getLogger(__name__)


def validate_bearer_auth(auth_header):
    """
    Validates an OAuth token found inside a basic auth `Bearer` token, returning whether it points
    to a valid OAuth token.
    """
    if not auth_header:
        return ValidateResult(AuthKind.oauth, missing=True)

    normalized = [part.strip() for part in auth_header.split(" ") if part]
    if normalized[0].lower() != "bearer" or len(normalized) != 2:
        logger.debug("Got invalid bearer token format: %s", auth_header)
        return ValidateResult(AuthKind.oauth, missing=True)

    (_, oauth_token) = normalized
    return validate_oauth_token(oauth_token)


def validate_oauth_token(token):
    """
    Validates the specified OAuth token, returning whether it points to a valid OAuth token.
    """
    validated = model.oauth.validate_access_token(token)
    if not validated:
        logger.warning("OAuth access token could not be validated: %s", token)
        return ValidateResult(
            AuthKind.oauth, error_message="OAuth access token could not be validated"
        )

    if validated.expires_at <= datetime.utcnow():
        logger.warning("OAuth access with an expired token: %s", token)
        return ValidateResult(AuthKind.oauth, error_message="OAuth access token has expired")

    # Don't allow disabled users to login.
    if not validated.authorized_user.enabled:
        return ValidateResult(
            AuthKind.oauth, error_message="Granter of the oauth access token is disabled"
        )

    # We have a valid token
    scope_set = scopes_from_scope_string(validated.scope)
    logger.debug("Successfully validated oauth access token with scope: %s", scope_set)
    return ValidateResult(AuthKind.oauth, oauthtoken=validated)
