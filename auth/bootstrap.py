"""
Bootstrap authentication module for programmatic token provisioning.

This module provides validate_bootstrap_auth(), a helper function called
explicitly by endpoints. It does NOT modify the existing auth chain.
"""

import logging
from base64 import b64decode

from flask import request
from jwt import InvalidTokenError

import features
from app import analytics, app, authentication, oauth_login, usermanager
from data import model
from oauth.login import OAuthLoginException
from oauth.login_utils import _conduct_oauth_login, get_sub_username_email_from_token
from oauth.oidc import OIDCLoginService, PublicKeyLoadException

logger = logging.getLogger(__name__)


class BootstrapAuthError(Exception):
    """Base exception for bootstrap auth failures."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BootstrapAuthResult:
    """Result of bootstrap authentication."""

    def __init__(self, user, auth_method):
        self.user = user
        self.auth_method = auth_method  # "Database", "LDAP", or "OIDC"


def validate_bootstrap_auth():
    """
    Validates bootstrap authentication from the current request.

    For Database/LDAP: parses Authorization: Basic header and validates
    credentials against the configured auth backend.

    For OIDC: parses Authorization: Bearer header and validates the JWT
    against the configured OIDC provider's JWKS. Superuser status is
    determined by the SUPER_USERS config list (same as Database/LDAP).

    Only superusers are authorized to use this endpoint.

    Returns:
        BootstrapAuthResult with the authenticated user and auth method.

    Raises:
        BootstrapAuthError with appropriate status_code:
            403 if FEATURE_PROGRAMMATIC_BOOTSTRAP is disabled.
            501 if AUTHENTICATION_TYPE is unsupported or OIDC config is missing.
            401 if credentials are invalid, missing, or user lacks permission.
    """
    if not features.PROGRAMMATIC_BOOTSTRAP:
        raise BootstrapAuthError("FEATURE_PROGRAMMATIC_BOOTSTRAP is not enabled", 403)

    auth_type = app.config.get("AUTHENTICATION_TYPE", "Database")

    if auth_type == "AppToken":
        raise BootstrapAuthError("Bootstrap authentication is not supported for AppToken", 501)

    scheme, credential = _parse_auth_header()

    if auth_type == "OIDC":
        if scheme != "bearer":
            raise BootstrapAuthError(
                "OIDC authentication requires Bearer token (Authorization: Bearer <jwt>)", 401
            )
        user = _validate_oidc_auth(credential)
        auth_method = "OIDC"
        is_su = usermanager.is_superuser(user.username)
    else:
        if scheme != "basic":
            raise BootstrapAuthError("Expected Basic authentication", 401)

        username, password = _parse_basic_auth_credential(credential)

        if auth_type == "Database":
            user = _validate_database_auth(username, password)
            auth_method = "Database"
        elif auth_type == "LDAP":
            user = _validate_ldap_auth(username, password)
            auth_method = "LDAP"
        else:
            raise BootstrapAuthError(
                "Bootstrap authentication is not supported for %s" % auth_type, 501
            )

        is_su = usermanager.is_superuser(user.username)

    if is_su:
        return BootstrapAuthResult(user=user, auth_method=auth_method)

    logger.warning("Bootstrap auth: user %s is not a superuser", user.username)
    raise BootstrapAuthError("Superuser access required", 401)


def _parse_auth_header():
    """
    Parse the Authorization header and return (scheme, credential).

    scheme is "basic" or "bearer" (lowercased).
    credential is the raw token string for Bearer, or the base64 blob for Basic.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise BootstrapAuthError("Missing Authorization header", 401)

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or not parts[1].strip():
        raise BootstrapAuthError("Invalid Authorization header", 401)

    scheme = parts[0].lower()
    if scheme not in ("basic", "bearer"):
        raise BootstrapAuthError("Unsupported Authorization scheme: %s" % parts[0], 401)

    return scheme, parts[1].strip()


def _parse_basic_auth_credential(credential):
    """Decode a base64 Basic Auth credential into (username, password)."""
    try:
        decoded = b64decode(credential).decode("utf-8")
        credentials = decoded.split(":", 1)
    except (TypeError, UnicodeDecodeError, ValueError):
        raise BootstrapAuthError("Invalid Authorization header encoding", 401)

    if len(credentials) != 2:
        raise BootstrapAuthError("Invalid credentials format", 401)

    return credentials[0], credentials[1]


def _validate_database_auth(username, password):
    """Validate credentials against the local database."""
    result = model.user.verify_user(username, password)
    if not result:
        logger.warning("Bootstrap auth: invalid Database credentials for %s", username)
        raise BootstrapAuthError("Invalid credentials", 401)
    if not result.enabled:
        raise BootstrapAuthError("User account is disabled", 401)
    return result


def _validate_ldap_auth(username, password):
    """
    Validate credentials via the existing LDAP search-then-bind flow.

    Uses authentication.verify_and_link_user() which handles:
    - LDAP search under LDAP_BASE_DN with LDAP_USER_FILTER
    - Bind with found DN + password
    - JIT provisioning of local Quay account via federated login path
    """
    (user, err_msg) = authentication.verify_and_link_user(username, password)
    if not user:
        logger.warning("Bootstrap auth: LDAP auth failed for %s: %s", username, err_msg)
        raise BootstrapAuthError("Invalid credentials", 401)
    if not user.enabled:
        raise BootstrapAuthError("User account is disabled", 401)
    return user


def _get_oidc_service():
    """
    Return the first OIDCLoginService from the OAuthLoginManager.

    Raises BootstrapAuthError(501) if none is configured.
    """
    for service in oauth_login.services:
        if isinstance(service, OIDCLoginService):
            return service
    raise BootstrapAuthError("No OIDC login service is configured", 501)


def _validate_oidc_auth(token):
    """
    Validate an OIDC JWT bearer token for bootstrap authentication.

    Follows the same pattern as auth/oauth.py:validate_sso_oauth_token():
    1. Decode and validate the JWT (signature, issuer, audience, expiration).
    2. Extract user identity from claims.
    3. JIT-provision a local Quay account via _conduct_oauth_login().

    Returns (user, decoded_jwt) on success.
    Raises BootstrapAuthError on any failure.
    """
    service = _get_oidc_service()

    try:
        decoded = service.decode_user_jwt(token)
    except InvalidTokenError as e:
        logger.warning("Bootstrap OIDC: invalid JWT: %s", e)
        raise BootstrapAuthError("Invalid OIDC token", 401)
    except PublicKeyLoadException as e:
        logger.warning("Bootstrap OIDC: could not load public key: %s", e)
        raise BootstrapAuthError("Could not validate OIDC token", 401)
    except ConnectionError as e:
        logger.warning("Bootstrap OIDC: could not connect to OIDC provider: %s", e)
        raise BootstrapAuthError("Could not connect to OIDC provider", 401)

    try:
        sub, lusername, lemail, additional_info = get_sub_username_email_from_token(
            decoded, None, service, False
        )
    except OAuthLoginException as e:
        logger.warning("Bootstrap OIDC: could not extract identity: %s", e)
        raise BootstrapAuthError("Could not extract identity from OIDC token", 401)

    try:
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
    except OAuthLoginException as e:
        logger.warning("Bootstrap OIDC: login failed: %s", e)
        raise BootstrapAuthError("OIDC login failed", 401)

    if login_result.error_message:
        logger.warning("Bootstrap OIDC: login failed: %s", login_result.error_message)
        raise BootstrapAuthError("OIDC login failed", 401)

    user = login_result.user_obj
    if not user:
        raise BootstrapAuthError("OIDC login did not return a user", 401)
    if not user.enabled:
        raise BootstrapAuthError("User account is disabled", 401)

    return user
