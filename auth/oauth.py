import logging
from datetime import datetime

from jwt import ExpiredSignatureError

from app import oauth_login, authentication, app, analytics
from auth.scopes import scopes_from_scope_string
from auth.validateresult import AuthKind, ValidateResult
from data import model
from oauth.login import OAuthLoginException
from oauth.login_utils import is_jwt, get_sub_username_email_from_token, _conduct_oauth_login, get_jwt_issuer

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
    if is_jwt(token):
        return validate_sso_oauth_token(token)
    else:
        return validate_app_oauth_token(token)


def validate_sso_oauth_token(token):
    issuer = get_jwt_issuer(token)
    service = oauth_login.get_service_by_issuer(issuer)
    if not service:
        return ValidateResult(
            AuthKind.ssojwt, error_message=f"Issuer {issuer} not configured"
        )

    try:
        # for client side oauth, the audience will be the client side oauth client
        decoded_id_token = service.decode_user_jwt(token, options={'verify_aud': False, 'verify_nbf': False})
        sub, lusername, lemail = get_sub_username_email_from_token(decoded_id_token, None, service.config, False)

        login_result = _conduct_oauth_login(app=app,
                                            analytics=analytics,
                                            auth_system=authentication,
                                            login_service=service,
                                            lid=sub,
                                            lusername=lusername,
                                            lemail=lemail,
                                            captcha_verified=True)
        if login_result.error_message:
            logger.error(f"Error logging in {login_result.error_message}")
            return ValidateResult(AuthKind.ssojwt, error_message=login_result.error_message)

        return ValidateResult(AuthKind.ssojwt, user=login_result.user_obj)

    except (OAuthLoginException, ExpiredSignatureError) as ole:
        logger.exception("Got login exception")
        return ValidateResult(
            AuthKind.ssojwt, error_message=str(ole)
        )


def validate_app_oauth_token(token):
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
