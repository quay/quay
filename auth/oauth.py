import logging
from datetime import datetime

from flask import request
from jwt import ExpiredSignatureError, InvalidTokenError

from app import analytics, app, authentication, oauth_login
from auth.log import log_action
from auth.scopes import scopes_from_scope_string
from auth.validateresult import AuthKind, ValidateResult
from data import model
from oauth.login import OAuthLoginException
from oauth.login_utils import (
    _conduct_oauth_login,
    get_jwt_issuer,
    get_sub_username_email_from_token,
    sync_oidc_groups,
)
from oauth.oidc import PublicKeyLoadException
from oauth.services.openshift import OpenShiftOAuthService
from util.security.jwtutil import is_jwt

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
        # Try OpenShift opaque token validation first
        result = validate_openshift_opaque_token(token)
        if result is not None and not result.error_message:
            return result

        # Fall back to app OAuth token
        return validate_app_oauth_token(token)


def validate_sso_oauth_token(token):
    issuer = get_jwt_issuer(token)
    if not issuer:
        return ValidateResult(AuthKind.ssojwt, error_message="Token does not contain issuer")

    try:
        service = oauth_login.get_service_by_issuer(issuer)
        if not service:
            return ValidateResult(AuthKind.ssojwt, error_message=f"Issuer {issuer} not configured")
    except ConnectionError as e:
        logger.exception(e)
        return ValidateResult(AuthKind.ssojwt, error_message="Unable to connect to auth server")

    try:
        # for client side oauth, the audience will be the client side oauth client
        options = {"verify_aud": False, "verify_nbf": False}
        if app.config.get("TESTING", False):
            options["verify_signature"] = False

        decoded_id_token = service.decode_user_jwt(token, options=options)
        sub, lusername, lemail, additional_info = get_sub_username_email_from_token(
            decoded_id_token, None, service, False
        )

        login_result = _conduct_oauth_login(
            config=app.config,
            analytics=analytics,
            auth_system=authentication,
            login_service=service,
            lid=sub,
            lusername=lusername,
            lemail=lemail,
            captcha_verified=True,
        )
        if login_result.error_message:
            logger.error(f"Error logging in {login_result.error_message}")
            return ValidateResult(AuthKind.ssojwt, error_message=login_result.error_message)

        return ValidateResult(AuthKind.ssojwt, user=login_result.user_obj, sso_token=token)

    except (
        OAuthLoginException,
        ExpiredSignatureError,
        InvalidTokenError,
        PublicKeyLoadException,
    ) as ole:
        logger.exception(ole)
        return ValidateResult(AuthKind.ssojwt, error_message=str(ole))


def validate_openshift_opaque_token(token):
    """
    Validate an opaque (non-JWT) OpenShift access token.

    OpenShift can issue opaque access tokens that aren't JWTs. We validate
    these by calling the OpenShift User API - if it succeeds, the token is valid.

    Returns:
        ValidateResult on success, None if no OpenShift service configured
    """
    # Find OpenShift OAuth service
    openshift_service = None
    for service in oauth_login.services:
        if isinstance(service, OpenShiftOAuthService):
            openshift_service = service
            break

    if openshift_service is None:
        return None

    try:
        # Validate token by calling OpenShift User API
        user_info = openshift_service.validate_opaque_token(openshift_service._http_client, token)

        if not user_info or not user_info.get("sub"):
            return ValidateResult(
                AuthKind.ssojwt,
                error_message="Could not extract user info from OpenShift token",
            )

        # Conduct OAuth login with extracted info
        login_result = _conduct_oauth_login(
            config=app.config,
            analytics=analytics,
            auth_system=authentication,
            login_service=openshift_service,
            lid=user_info["sub"],
            lusername=user_info.get("preferred_username", user_info["sub"]),
            lemail=user_info.get("email"),
            captcha_verified=True,
            additional_login_info={"groups": user_info.get("groups", [])},
        )

        if login_result.error_message:
            logger.error(f"OpenShift login failed: {login_result.error_message}")
            return ValidateResult(AuthKind.ssojwt, error_message=login_result.error_message)

        # Sync groups to teams
        if user_info.get("groups"):
            sync_oidc_groups(
                {"groups": user_info["groups"]},
                login_result.user_obj,
                authentication,
                openshift_service,
                app.config,
            )

        return ValidateResult(AuthKind.ssojwt, user=login_result.user_obj, sso_token=token)

    except Exception as e:
        logger.debug(f"OpenShift opaque token validation failed: {e}")
        return None


def validate_app_oauth_token(token):
    """
    Validates the specified OAuth token, returning whether it points to a valid OAuth token.
    """
    validated = model.oauth.validate_access_token(token)
    if not validated:
        logger.warning("OAuth access token could not be validated: %s", token)

        error_message = "OAuth access token could not be validated"

        if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
            log_action(
                "login_failure",
                None,
                {
                    "type": "quayauth",
                    "kind": "oauth",
                    "useragent": request.user_agent.string,
                    "message": error_message,
                },
            )

        return ValidateResult(AuthKind.oauth, error_message=error_message)

    if validated.expires_at <= datetime.utcnow():
        logger.warning("OAuth access with an expired token: %s", token)

        error_message = "OAuth access token has expired"

        if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
            log_action(
                "login_failure",
                validated.application.organization.username,
                {
                    "type": "quayauth",
                    "kind": "oauth",
                    "token": validated.token_name,
                    "application_name": validated.application.name,
                    "oauth_token_id": validated.id,
                    "oauth_token_application_id": validated.application.client_id,
                    "oauth_token_application": validated.application.name,
                    "username": validated.authorized_user.username,
                    "useragent": request.user_agent.string,
                    "message": error_message,
                },
                performer=validated,
            )

        return ValidateResult(AuthKind.oauth, error_message=error_message)

    # Don't allow disabled users to login.
    if not validated.authorized_user.enabled:
        error_message = "Granter of the oauth access token is disabled"

        if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
            log_action(
                "login_failure",
                validated.application.organization.username,
                {
                    "type": "quayauth",
                    "kind": "oauth",
                    "token": validated.token_name,
                    "application_name": validated.application.name,
                    "username": validated.authorized_user.username,
                    "useragent": request.user_agent.string,
                    "message": error_message,
                },
                performer=validated.authorized_user,
            )

        return ValidateResult(
            AuthKind.oauth,
            error_message=error_message,
        )

    # We have a valid token
    scope_set = scopes_from_scope_string(validated.scope)
    logger.debug("Successfully validated oauth access token with scope: %s", scope_set)
    return ValidateResult(AuthKind.oauth, oauthtoken=validated)
