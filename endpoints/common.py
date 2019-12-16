import logging
import datetime
import os

from flask import make_response, render_template, request, session
from flask_login import login_user
from flask_principal import identity_changed

import endpoints.decorated  # Register the various exceptions via decorators.
import features

from app import app, oauth_apps, oauth_login, LoginWrappedDBUser, IS_KUBERNETES
from auth import scopes
from auth.permissions import QuayDeferredPermissionUser
from config import frontend_visible_config
from external_libraries import get_external_javascript, get_external_css
from endpoints.common_models_pre_oci import pre_oci_model as model
from endpoints.csrf import generate_csrf_token, QUAY_CSRF_UPDATED_HEADER_NAME
from util.config.provider.k8sprovider import QE_NAMESPACE
from util.secscan import PRIORITY_LEVELS
from util.timedeltastring import convert_to_timedelta
from _init import __version__


logger = logging.getLogger(__name__)


JS_BUNDLE_NAME = "bundle"


def common_login(user_uuid, permanent_session=True):
    """
    Performs login of the given user, with optional non-permanence on the session.

    Returns a tuple with (success, headers to set on success).
    """
    user = model.get_user(user_uuid)
    if user is None:
        return (False, None)

    if login_user(LoginWrappedDBUser(user_uuid)):
        logger.debug("Successfully signed in as user %s with uuid %s", user.username, user_uuid)
        new_identity = QuayDeferredPermissionUser.for_id(user_uuid)
        identity_changed.send(app, identity=new_identity)
        session["login_time"] = datetime.datetime.now()

        if permanent_session and features.PERMANENT_SESSIONS:
            session_timeout_str = app.config.get("SESSION_TIMEOUT", "31d")
            session.permanent = True
            session.permanent_session_lifetime = convert_to_timedelta(session_timeout_str)

        # Force a new CSRF token.
        headers = {}
        headers[QUAY_CSRF_UPDATED_HEADER_NAME] = generate_csrf_token(force=True)
        return (True, headers)

    logger.debug("User could not be logged in, inactive?")
    return (False, None)


def _list_files(path, extension, contains=""):
    """
    Returns a list of all the files with the given extension found under the given path.
    """

    def matches(f):
        return os.path.splitext(f)[1] == "." + extension and contains in os.path.splitext(f)[0]

    def join_path(dp, f):
        # Remove the static/ prefix. It is added in the template.
        return os.path.join(dp, f)[len("static/") :]

    filepath = os.path.join("static/", path)
    return [join_path(dp, f) for dp, _, files in os.walk(filepath) for f in files if matches(f)]


FONT_AWESOME_5 = "use.fontawesome.com/releases/v5.0.4/css/all.css"


def render_page_template(name, route_data=None, **kwargs):
    """
    Renders the page template with the given name as the response and returns its contents.
    """
    main_scripts = _list_files("build", "js", JS_BUNDLE_NAME)

    use_cdn = app.config.get("USE_CDN", True)
    if request.args.get("use_cdn") is not None:
        use_cdn = request.args.get("use_cdn") == "true"

    external_styles = get_external_css(local=not use_cdn, exclude=FONT_AWESOME_5)
    external_scripts = get_external_javascript(local=not use_cdn)

    # Add Stripe checkout if billing is enabled.
    if features.BILLING:
        external_scripts.append("//checkout.stripe.com/checkout.js")

    def get_external_login_config():
        login_config = []
        for login_service in oauth_login.services:
            login_config.append(
                {
                    "id": login_service.service_id(),
                    "title": login_service.service_name(),
                    "config": login_service.get_public_config(),
                    "icon": login_service.get_icon(),
                }
            )

        return login_config

    def get_oauth_config():
        oauth_config = {}
        for oauth_app in oauth_apps:
            oauth_config[oauth_app.key_name] = oauth_app.get_public_config()

        return oauth_config

    has_contact = len(app.config.get("CONTACT_INFO", [])) > 0
    contact_href = None
    if len(app.config.get("CONTACT_INFO", [])) == 1:
        contact_href = app.config["CONTACT_INFO"][0]

    version_number = ""
    if not features.BILLING:
        version_number = "Quay %s" % __version__

    scopes_set = {
        scope.scope: scope._asdict() for scope in list(scopes.app_scopes(app.config).values())
    }

    contents = render_template(
        name,
        registry_state=app.config.get("REGISTRY_STATE", "normal"),
        route_data=route_data,
        external_styles=external_styles,
        external_scripts=external_scripts,
        main_scripts=main_scripts,
        feature_set=features.get_features(),
        config_set=frontend_visible_config(app.config),
        oauth_set=get_oauth_config(),
        external_login_set=get_external_login_config(),
        scope_set=scopes_set,
        vuln_priority_set=PRIORITY_LEVELS,
        mixpanel_key=app.config.get("MIXPANEL_KEY", ""),
        munchkin_key=app.config.get("MARKETO_MUNCHKIN_ID", ""),
        recaptcha_key=app.config.get("RECAPTCHA_SITE_KEY", ""),
        google_tagmanager_key=app.config.get("GOOGLE_TAGMANAGER_KEY", ""),
        google_anaytics_key=app.config.get("GOOGLE_ANALYTICS_KEY", ""),
        sentry_public_dsn=app.config.get("SENTRY_PUBLIC_DSN", ""),
        is_debug=str(app.config.get("DEBUGGING", False)).lower(),
        aci_conversion=features.ACI_CONVERSION,
        has_billing=features.BILLING,
        onprem=not app.config.get("FEATURE_BILLING", False),
        contact_href=contact_href,
        has_contact=has_contact,
        hostname=app.config["SERVER_HOSTNAME"],
        preferred_scheme=app.config["PREFERRED_URL_SCHEME"],
        version_number=version_number,
        current_year=datetime.datetime.now().year,
        kubernetes_namespace=IS_KUBERNETES and QE_NAMESPACE,
        **kwargs,
    )

    resp = make_response(contents)
    resp.headers["X-FRAME-OPTIONS"] = "DENY"
    return resp
