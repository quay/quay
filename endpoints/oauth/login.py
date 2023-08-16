import logging
import os
import time
from collections import namedtuple

import recaptcha2
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

oauthlogin_csrf_protect = csrf_protect(
    OAUTH_CSRF_TOKEN_NAME, "state", all_methods=True, check_header=False
)


def _get_response(result):
    if result.error_message is not None:
        return _render_ologin_error(
            result.service_name, result.error_message, result.register_redirect
        )

    return _perform_login(result.user_obj, result.service_name)


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
        try:
            lid, lusername, lemail = login_service.exchange_code_for_login(
                app.config, client, code, ""
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
        captcha_verified = (int(time.time()) - session.get("captcha_verified", 0)) <= 600
        session["captcha_verified"] = 0

        result = _conduct_oauth_login(
            app.config,
            analytics,
            authentication,
            login_service,
            lid,
            lusername,
            lemail,
            metadata=metadata,
            captcha_verified=captcha_verified,
        )
        if result.requires_verification:
            return render_page_template_with_routedata(
                "oauthcaptcha.html",
                recaptcha_site_key=app.config["RECAPTCHA_SITE_KEY"],
                callback_url=request.base_url,
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
        try:
            lid, lusername, _ = login_service.exchange_code_for_login(
                app.config, client, code, "/attach"
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

    def captcha_func():
        recaptcha_response = request.values.get("recaptcha_response", "")
        result = recaptcha2.verify(
            app.config["RECAPTCHA_SECRET_KEY"], recaptcha_response, get_request_ip()
        )

        if not result["success"]:
            abort(400)

        # Save that the captcha was verified.
        session["captcha_verified"] = int(time.time())

        # Redirect to the normal OAuth flow again, so that the user can now create an account.
        csrf_token = generate_csrf_token(OAUTH_CSRF_TOKEN_NAME)
        login_scopes = login_service.get_login_scopes()
        auth_url = login_service.get_auth_url(url_scheme_and_hostname, "", csrf_token, login_scopes)
        return redirect(auth_url)

    @require_session_login
    @oauthlogin_csrf_protect
    def cli_token_func():
        # Check for a callback error.
        error = request.values.get("error", None)
        if error:
            return _render_ologin_error(login_service.service_name(), error)

        # Exchange the OAuth code for the ID token.
        code = request.values.get("code")
        try:
            idtoken, _ = login_service.exchange_code_for_tokens(app.config, client, code, "/cli")
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
        "/%s/callback/captcha" % login_service.service_id(),
        "%s_oauth_captcha" % login_service.service_id(),
        captcha_func,
        methods=["POST"],
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
