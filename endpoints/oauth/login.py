import logging
import time
import recaptcha2

from collections import namedtuple
from flask import request, redirect, url_for, Blueprint, abort, session
from peewee import IntegrityError

import features

from app import app, analytics, get_app_url, oauth_login, authentication, url_scheme_and_hostname
from auth.auth_context import get_authenticated_user
from auth.decorators import require_session_login
from data import model
from data.users.shared import can_create_user
from endpoints.common import common_login
from endpoints.web import index, render_page_template_with_routedata
from endpoints.csrf import csrf_protect, OAUTH_CSRF_TOKEN_NAME, generate_csrf_token
from oauth.login import OAuthLoginException
from util.validation import generate_valid_usernames
from util.request import get_request_ip

logger = logging.getLogger(__name__)
client = app.config["HTTPCLIENT"]
oauthlogin = Blueprint("oauthlogin", __name__)

oauthlogin_csrf_protect = csrf_protect(
    OAUTH_CSRF_TOKEN_NAME, "state", all_methods=True, check_header=False
)


OAuthResult = namedtuple(
    "oauthresult",
    ["user_obj", "service_name", "error_message", "register_redirect", "requires_verification"],
)


def _oauthresult(
    user_obj=None,
    service_name=None,
    error_message=None,
    register_redirect=False,
    requires_verification=False,
):
    return OAuthResult(
        user_obj, service_name, error_message, register_redirect, requires_verification
    )


def _get_response(result):
    if result.error_message is not None:
        return _render_ologin_error(
            result.service_name, result.error_message, result.register_redirect
        )

    return _perform_login(result.user_obj, result.service_name)


def _conduct_oauth_login(
    auth_system, login_service, lid, lusername, lemail, metadata=None, captcha_verified=False
):
    """
    Conducts login from the result of an OAuth service's login flow and returns the status of the
    login, as well as the followup step.
    """
    service_id = login_service.service_id()
    service_name = login_service.service_name()

    # Check for an existing account *bound to this service*. If found, conduct login of that account
    # and redirect.
    user_obj = model.user.verify_federated_login(service_id, lid)
    if user_obj is not None:
        return _oauthresult(user_obj=user_obj, service_name=service_name)

    # If the login service has a bound field name, and we have a defined internal auth type that is
    # not the database, then search for an existing account with that matching field. This allows
    # users to setup SSO while also being backed by something like LDAP.
    bound_field_name = login_service.login_binding_field()
    if auth_system.federated_service is not None and bound_field_name is not None:
        # Perform lookup.
        logger.debug('Got oauth bind field name of "%s"', bound_field_name)
        lookup_value = None
        if bound_field_name == "sub":
            lookup_value = lid
        elif bound_field_name == "username":
            lookup_value = lusername
        elif bound_field_name == "email":
            lookup_value = lemail

        if lookup_value is None:
            logger.error("Missing lookup value for OAuth login")
            return _oauthresult(
                service_name=service_name, error_message="Configuration error in this provider"
            )

        (user_obj, err) = auth_system.link_user(lookup_value)
        if err is not None:
            logger.debug("%s %s not found: %s", bound_field_name, lookup_value, err)
            msg = "%s %s not found in backing auth system" % (bound_field_name, lookup_value)
            return _oauthresult(service_name=service_name, error_message=msg)

        # Found an existing user. Bind their internal auth account to this service as well.
        result = _attach_service(login_service, user_obj, lid, lusername)
        if result.error_message is not None:
            return result

        return _oauthresult(user_obj=user_obj, service_name=service_name)

    # Otherwise, we need to create a new user account.
    blacklisted_domains = app.config.get("BLACKLISTED_EMAIL_DOMAINS", [])
    if not can_create_user(lemail, blacklisted_domains=blacklisted_domains):
        error_message = "User creation is disabled. Please contact your administrator"
        return _oauthresult(service_name=service_name, error_message=error_message)

    if features.RECAPTCHA and not captcha_verified:
        return _oauthresult(service_name=service_name, requires_verification=True)

    # Try to create the user
    try:
        # Generate a valid username.
        new_username = None
        for valid in generate_valid_usernames(lusername):
            if model.user.get_user_or_org(valid):
                continue

            new_username = valid
            break

        requires_password = auth_system.requires_distinct_cli_password
        prompts = model.user.get_default_user_prompts(features)
        user_obj = model.user.create_federated_user(
            new_username,
            lemail,
            service_id,
            lid,
            set_password_notification=requires_password,
            metadata=metadata or {},
            confirm_username=features.USERNAME_CONFIRMATION,
            prompts=prompts,
            email_required=features.MAILING,
        )

        # Success, tell analytics
        analytics.track(user_obj.username, "register", {"service": service_name.lower()})
        return _oauthresult(user_obj=user_obj, service_name=service_name)

    except model.InvalidEmailAddressException:
        message = (
            "The e-mail address {0} is already associated "
            "with an existing {1} account. \n"
            "Please log in with your username and password and "
            "associate your {2} account to use it in the future."
        )
        message = message.format(lemail, app.config["REGISTRY_TITLE_SHORT"], service_name)
        return _oauthresult(
            service_name=service_name, error_message=message, register_redirect=True
        )

    except model.DataModelException as ex:
        return _oauthresult(service_name=service_name, error_message=str(ex))


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


def _attach_service(login_service, user_obj, lid, lusername):
    """
    Attaches the given user account to the given service, with the given service user ID and service
    username.
    """
    metadata = {
        "service_username": lusername,
    }

    try:
        model.user.attach_federated_login(
            user_obj, login_service.service_id(), lid, metadata=metadata
        )
        return _oauthresult(user_obj=user_obj)
    except IntegrityError:
        err = "%s account %s is already attached to a %s account" % (
            login_service.service_name(),
            lusername,
            app.config["REGISTRY_TITLE_SHORT"],
        )
        return _oauthresult(service_name=login_service.service_name(), error_message=err)


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

        # Conduct login.
        metadata = {
            "service_username": lusername,
        }

        # Conduct OAuth login.
        captcha_verified = (int(time.time()) - session.get("captcha_verified", 0)) <= 600
        session["captcha_verified"] = 0

        result = _conduct_oauth_login(
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
        result = _attach_service(login_service, user_obj, lid, lusername)
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
