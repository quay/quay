import logging
from datetime import datetime
from typing import Optional

from flask import request
from jwt import ExpiredSignatureError, InvalidTokenError

import features
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
)
from oauth.oidc import PublicKeyLoadException
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
    # K8s SA tokens lack typ:JWT header so is_jwt() returns False, but they
    # are structurally JWTs (three dot-separated base64 segments). Check
    # structure first to avoid calling validate_kubernetes_sa_token() on
    # app OAuth tokens (the common case for image pulls).
    if features.KUBERNETES_SA_AUTH and token.count(".") == 2:
        result = validate_kubernetes_sa_token(token)
        if result is not None:
            return result

    if is_jwt(token):
        return validate_sso_oauth_token(token)
    else:
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


def validate_kubernetes_sa_token(token: str) -> Optional[ValidateResult]:
    """
    Validate a Kubernetes ServiceAccount JWT token.

    Kubernetes SA tokens are validated via OIDC/JWKS, then mapped to robot accounts
    in the configured system organization. Permissions are granted through normal
    Quay mechanisms (org membership, team roles).

    Returns:
        ValidateResult on success, None if Kubernetes SA auth not configured or
        token issuer doesn't match
    """
    from data import model
    from data.model import user
    from oauth.oidc import PublicKeyLoadException
    from oauth.services.kubernetes_sa import (
        DEFAULT_KUBERNETES_OIDC_SERVER,
        KubernetesServiceAccountLoginService,
    )
    from util.security.jwtutil import InvalidTokenError

    kubernetes_config = app.config.get("KUBERNETES_SA_AUTH_CONFIG", {})
    if not kubernetes_config:
        logger.debug("FEATURE_KUBERNETES_SA_AUTH is enabled but no config provided")
        return None

    # Get configured OIDC server, falling back to default
    expected_oidc_server = kubernetes_config.get("OIDC_SERVER", DEFAULT_KUBERNETES_OIDC_SERVER)

    # Cache the service instance to reuse OIDC discovery and JWKS key caches
    if not hasattr(validate_kubernetes_sa_token, "_service"):
        validate_kubernetes_sa_token._service = KubernetesServiceAccountLoginService(app.config)  # type: ignore[attr-defined]
    kubernetes_service = validate_kubernetes_sa_token._service  # type: ignore[attr-defined]

    # Check if token issuer matches our configured Kubernetes OIDC server
    # This allows other JWT tokens to fall through to generic SSO handling
    try:
        issuer = get_jwt_issuer(token)
        if not issuer:
            return None

        # Normalize trailing slashes for comparison
        if issuer.rstrip("/") != expected_oidc_server.rstrip("/"):
            logger.debug(
                "Token issuer %s doesn't match Kubernetes OIDC server %s, skipping",
                issuer,
                expected_oidc_server,
            )
            return None
    except Exception:
        # If we can't decode issuer, let it fall through to other handlers
        return None

    try:
        # Validate the token
        decoded_token = kubernetes_service.validate_sa_token(token)

    except (InvalidTokenError, PublicKeyLoadException) as e:
        logger.warning(f"Kubernetes SA token validation failed: {e}")
        return ValidateResult(
            AuthKind.kubernetessa,
            error_message=f"Token validation failed: {e}",
        )
    except Exception as e:
        logger.warning(f"Kubernetes SA token validation error: {e}")
        return ValidateResult(
            AuthKind.kubernetessa,
            error_message=f"Token validation error: {e}",
        )

    # Extract subject (required claim)
    subject = decoded_token.get("sub")
    if not subject:
        logger.warning("Kubernetes SA token missing 'sub' claim")
        return ValidateResult(
            AuthKind.kubernetessa,
            error_message="Token missing subject claim",
        )

    # Parse and validate SA subject format
    parsed = kubernetes_service.parse_sa_subject(subject)
    if not parsed:
        logger.warning(f"Invalid Kubernetes SA subject format: {subject}")
        return ValidateResult(
            AuthKind.kubernetessa,
            error_message=f"Invalid ServiceAccount subject format: {subject}",
        )

    namespace, sa_name = parsed

    # Verify the subject is in the configured ALLOWED_SUBJECTS allowlist
    if not kubernetes_service.is_allowed_subject(subject):
        logger.warning(f"Kubernetes SA subject not in ALLOWED_SUBJECTS: {subject}")
        return ValidateResult(
            AuthKind.kubernetessa,
            error_message=f"ServiceAccount not authorized: {subject}",
        )

    # Look up the robot account
    robot_shortname = kubernetes_service.generate_robot_shortname(namespace, sa_name)
    system_org_name = kubernetes_service.system_org_name
    robot_username = f"{system_org_name}+{robot_shortname}"

    try:
        robot = user.lookup_robot(robot_username)
    except model.InvalidRobotException:
        # Robot doesn't exist - it should have been created at startup
        logger.error(
            f"Robot account {robot_username} not found. "
            f"Ensure ALLOWED_SUBJECTS is configured and Quay was restarted."
        )
        return ValidateResult(
            AuthKind.kubernetessa,
            error_message=f"Robot account not found: {robot_username}",
        )

    # Log successful authentication
    logger.debug(
        f"Kubernetes SA authenticated: {subject} -> {robot_username}",
        extra={
            "kubernetes_namespace": namespace,
            "kubernetes_sa_name": sa_name,
            "robot_username": robot_username,
        },
    )

    return ValidateResult(AuthKind.kubernetessa, robot=robot, sso_token=token)


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
