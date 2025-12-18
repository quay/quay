import logging
import os
import re
import time
from collections import namedtuple
from urllib.parse import urlencode, urlparse

from flask import Blueprint, abort, redirect, request, session, url_for

import features
from app import (
    analytics,
    app,
    authentication,
    get_app_url,
    oauth_login,
    url_scheme_and_hostname,
)
from auth.auth_context import get_authenticated_user
from auth.decorators import require_session_login
from data import model
from endpoints.common import common_login
from endpoints.csrf import OAUTH_CSRF_TOKEN_NAME, csrf_protect, generate_csrf_token
from endpoints.web import index, render_page_template_with_routedata
from oauth.login import ExportComplianceException, OAuthLoginException
from oauth.login_utils import _attach_service, _conduct_oauth_login
from util.request import get_request_ip

logger = logging.getLogger(__name__)
client = app.config["HTTPCLIENT"]
oauthlogin = Blueprint("oauthlogin", __name__)


def get_pkce_code_verifier(login_service):
    """
    Safely extract PKCE code verifier from session for the given login service.

    This function checks if PKCE is enabled for the login service, retrieves
    the verifier from the session, and performs defensive type checking.

    Args:
        login_service: The OAuth login service object

    Returns:
        str: The PKCE code verifier if present and valid, None otherwise
    """
    if not (hasattr(login_service, "pkce_enabled") and login_service.pkce_enabled()):
        return None

    session_key = f"_oauth_pkce_{login_service.service_id()}"
    data = session.pop(session_key, None)

    if isinstance(data, dict) and "verifier" in data:
        return data["verifier"]
    return None


oauthlogin_csrf_protect = csrf_protect(
    OAUTH_CSRF_TOKEN_NAME, "state", all_methods=True, check_header=False
)


def _get_response(result):
    if result.error_message is not None:
        return _render_ologin_error(
            result.service_name, result.error_message, result.register_redirect
        )

    return _perform_login(result.user_obj, result.service_name)


# OAuth error codes from RFC 6749 - safe to pass through
ALLOWED_OAUTH_ERRORS = {
    "invalid_request",
    "unauthorized_client",
    "access_denied",
    "unsupported_response_type",
    "invalid_scope",
    "server_error",
    "temporarily_unavailable",
}


def _sanitize_error_message(error_message):
    """
    Sanitize error message for safe use in URL redirects.

    React receives error messages via URL parameters (unlike Angular's
    server-side rendering). This function prevents injection attacks
    while preserving useful error information.

    Args:
        error_message: Untrusted error message from OAuth callback

    Returns:
        Sanitized error message safe for URL parameters
    """
    if not error_message:
        return "Could not load user data. The token may have expired"

    # Allow known OAuth error codes to pass through unchanged
    if error_message in ALLOWED_OAUTH_ERRORS:
        return error_message

    # For custom messages: allow only safe characters
    # Permits: letters, numbers, spaces, and common punctuation
    sanitized = re.sub(r"[^a-zA-Z0-9\s\.\-_@,\':()]", "", error_message)

    # Limit length to prevent abuse
    if len(sanitized) > 250:
        sanitized = sanitized[:250]

    # If sanitization removed everything, use default message
    if not sanitized.strip():
        return "Could not load user data. The token may have expired"

    return sanitized.strip()


def _render_ologin_error(service_name, error_message=None, register_redirect=False):
    """
    Returns a Flask response indicating an OAuth error.
    """

    user_creation = bool(
        features.USER_CREATION and features.DIRECT_LOGIN and not features.INVITE_ONLY_USER_CREATION
    )
    error_info = {
        "reason": "ologinerror",
        "service_name": service_name,
        "error_message": error_message or "Could not load user data. The token may have expired",
        "service_url": get_app_url(),
        "user_creation": user_creation,
        "register_redirect": register_redirect,
    }
    # Determine UI type: check user preference (cookie) first, then system default (config)
    should_use_react = False
    patternfly_cookie = request.cookies.get("patternfly", "")

    if patternfly_cookie in ["true", "react"]:
        should_use_react = True
    elif patternfly_cookie:
        should_use_react = False
    else:  # No cookie: use DEFAULT_UI
        should_use_react = app.config.get("DEFAULT_UI", "react").lower() == "react"

    if should_use_react:
        # React UI: redirect to dedicated OAuth error page
        params_dict = {
            "error": "oauth_error",
            "error_description": _sanitize_error_message(error_message),
            "provider": service_name,
        }

        if user_creation:
            params_dict["user_creation"] = "true"

        if register_redirect:
            params_dict["register_redirect"] = "true"

        # Determine if user is authenticated based on the request context
        # The attach/cli endpoints require authentication, callback does not
        authenticated_user = get_authenticated_user()

        if authenticated_user:
            params_dict["authenticated"] = "true"
            params_dict["username"] = authenticated_user.username

        params = urlencode(params_dict)

        # Use the Referer header to determine the correct origin to redirect to
        referer = request.headers.get("Referer")

        if referer:
            # Parse the origin from the referer
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            return redirect(f"{origin}/oauth-error?{params}")
        else:
            # Fallback to relative redirect
            return redirect(f"/oauth-error?{params}")

    # Angular UI: render error in template
    resp = index("", error_info=error_info)
    resp.status_code = 400
    return resp


def _render_export_compliance_error(service_name, sso_username, email, quay_username):
    """
    Returns a Flask response indicating an Export Compliance error.
    """

    error_info = {
        "reason": "exportcomplianceerror",
        "service_name": service_name,
        "sso_username": sso_username,
        "email": email,
        "quay_username": quay_username,
    }

    resp = index("", error_info=error_info)
    resp.status_code = 400
    return resp


def _perform_login(user_obj, service_name):
    """
    Attempts to login the given user, returning the Flask result of whether the login succeeded.
    """
    success, _ = common_login(user_obj.uuid)
    if success:
        if model.user.has_user_prompts(user_obj):
            return redirect(
                url_for(
                    "web.updateuser", _scheme=app.config["PREFERRED_URL_SCHEME"], _external=True
                )
            )
        else:
            return redirect(
                url_for("web.index", _scheme=app.config["PREFERRED_URL_SCHEME"], _external=True)
            )
    else:
        return _render_ologin_error(service_name, "Could not login. Account may be disabled")


def _register_service(login_service):
    """
    Registers the given login service, adding its callback and attach routes to the blueprint.
    """

    @oauthlogin_csrf_protect
    def callback_func():
        # Check for a callback error.
        error = request.values.get("error", None)
        if error:
            return _render_ologin_error(login_service.service_name(), error)

        # Exchange the OAuth code for login information.
        code = request.values.get("code")
        kwargs = {}
        verifier = get_pkce_code_verifier(login_service)
        if verifier:
            kwargs["code_verifier"] = verifier
        try:
            lid, lusername, lemail, additional_info = login_service.exchange_code_for_login(
                app.config, client, code, "", **kwargs
            )
        except OAuthLoginException as ole:
            logger.exception("Got login exception")
            return _render_ologin_error(login_service.service_name(), str(ole))
        except ExportComplianceException as ece:
            logger.exception("Export compliance exception", ece)
            return _render_export_compliance_error(
                login_service.service_name(), ece.sso_username, ece.email, ece.quay_username
            )

        # Conduct login.
        metadata = {
            "service_username": lusername,
        }

        # Conduct OAuth login.
        result = _conduct_oauth_login(
            app.config,
            analytics,
            authentication,
            login_service,
            lid,
            lusername,
            lemail,
            metadata=metadata,
            additional_login_info=additional_info,
        )

        return _get_response(result)

    @require_session_login
    @oauthlogin_csrf_protect
    def attach_func():
        # Check for a callback error.
        error = request.values.get("error", None)
        if error:
            return _render_ologin_error(login_service.service_name(), error)

        # Exchange the OAuth code for login information.
        code = request.values.get("code")
        kwargs = {}
        verifier = get_pkce_code_verifier(login_service)
        if verifier:
            kwargs["code_verifier"] = verifier
        try:
            lid, lusername, _, _ = login_service.exchange_code_for_login(
                app.config, client, code, "/attach", **kwargs
            )
        except OAuthLoginException as ole:
            return _render_ologin_error(login_service.service_name(), str(ole))

        # Conduct attach.
        user_obj = get_authenticated_user()
        result = _attach_service(app.config, login_service, user_obj, lid, lusername)
        if result.error_message is not None:
            return _get_response(result)

        return redirect(
            url_for(
                "web.user_view",
                _scheme=app.config["PREFERRED_URL_SCHEME"],
                _external=True,
                path=user_obj.username,
                tab="external",
            )
        )

    @require_session_login
    @oauthlogin_csrf_protect
    def cli_token_func():
        # Check for a callback error.
        error = request.values.get("error", None)
        if error:
            return _render_ologin_error(login_service.service_name(), error)

        # Exchange the OAuth code for the ID token.
        code = request.values.get("code")
        kwargs = {}
        verifier = get_pkce_code_verifier(login_service)
        if verifier:
            kwargs["code_verifier"] = verifier
        try:
            idtoken, _ = login_service.exchange_code_for_tokens(
                app.config, client, code, "/cli", **kwargs
            )
        except OAuthLoginException as ole:
            return _render_ologin_error(login_service.service_name(), str(ole))

        user_obj = get_authenticated_user()
        return redirect(
            url_for(
                "web.user_view",
                _scheme=app.config["PREFERRED_URL_SCHEME"],
                _external=True,
                path=user_obj.username,
                tab="settings",
                idtoken=idtoken,
            )
        )

    oauthlogin.add_url_rule(
        "/%s/callback" % login_service.service_id(),
        "%s_oauth_callback" % login_service.service_id(),
        callback_func,
        methods=["GET", "POST"],
    )

    oauthlogin.add_url_rule(
        "/%s/callback/attach" % login_service.service_id(),
        "%s_oauth_attach" % login_service.service_id(),
        attach_func,
        methods=["GET", "POST"],
    )

    oauthlogin.add_url_rule(
        "/%s/callback/cli" % login_service.service_id(),
        "%s_oauth_cli" % login_service.service_id(),
        cli_token_func,
        methods=["GET", "POST"],
    )


# Register the routes for each of the login services.
for current_service in oauth_login.services:
    _register_service(current_service)
