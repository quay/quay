import os
import json
import logging

from datetime import timedelta, datetime

from cachetools.func import lru_cache
from flask import (
    abort,
    redirect,
    request,
    url_for,
    make_response,
    Response,
    render_template,
    Blueprint,
    jsonify,
    send_file,
    session,
)
from flask_login import current_user

import features

from app import (
    app,
    billing as stripe,
    build_logs,
    avatar,
    log_archive,
    config_provider,
    get_app_url,
    instance_keys,
    storage,
    authentication,
)
from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.basic import has_basic_auth
from auth.decorators import require_session_login, process_oauth, process_auth_or_cookie
from auth.permissions import (
    AdministerOrganizationPermission,
    ReadRepositoryPermission,
    SuperUserPermission,
    AdministerRepositoryPermission,
    ModifyRepositoryPermission,
    OrganizationMemberPermission,
)
from buildtrigger.basehandler import BuildTriggerHandler
from buildtrigger.bitbuckethandler import BitbucketBuildTrigger
from buildtrigger.customhandler import CustomBuildTrigger
from buildtrigger.triggerutil import TriggerProviderException
from data import model
from data.database import db, RepositoryTag, TagToRepositoryTag, random_string_generator, User
from endpoints.api.discovery import swagger_route_data
from endpoints.common import common_login, render_page_template
from endpoints.csrf import csrf_protect, generate_csrf_token, verify_csrf
from endpoints.decorators import (
    anon_protect,
    anon_allowed,
    route_show_if,
    parse_repository_name,
    param_required,
)
from health.healthcheck import get_healthchecker
from util.cache import no_cache
from util.headers import parse_basic_auth
from util.invoice import renderInvoiceToPdf
from util.useremails import send_email_changed
from util.registry.gzipinputstream import GzipInputStream
from util.request import get_request_ip
from _init import ROOT_DIR


PGP_KEY_MIMETYPE = "application/pgp-keys"


@lru_cache(maxsize=1)
def _get_route_data():
    return swagger_route_data(include_internal=True, compact=True)


def render_page_template_with_routedata(name, *args, **kwargs):
    return render_page_template(name, _get_route_data(), *args, **kwargs)


# Capture the unverified SSL errors.
logger = logging.getLogger(__name__)
logging.captureWarnings(True)

web = Blueprint("web", __name__)

STATUS_TAGS = app.config["STATUS_TAGS"]


@web.route("/", methods=["GET"], defaults={"path": ""})
@no_cache
def index(path, **kwargs):
    return render_page_template_with_routedata("index.html", **kwargs)


@web.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)


@web.route("/500", methods=["GET"])
def internal_error_display():
    return render_page_template_with_routedata("500.html")


@web.errorhandler(404)
@web.route("/404", methods=["GET"])
def not_found_error_display(e=None):
    resp = index("", error_code=404, error_info=dict(reason="notfound"))
    resp.status_code = 404
    return resp


@web.route("/opensearch.xml")
def opensearch():
    template = render_template(
        "opensearch.xml",
        baseurl=get_app_url(),
        registry_title=app.config.get("REGISTRY_TITLE", "Quay"),
    )
    resp = make_response(template)
    resp.headers["Content-Type"] = "application/xml"
    return resp


@web.route("/organization/<path:path>", methods=["GET"])
@web.route("/organization/<path:path>/", methods=["GET"])
@no_cache
def org_view(path):
    return index("")


@web.route("/user/<path:path>", methods=["GET"])
@web.route("/user/<path:path>/", methods=["GET"])
@no_cache
def user_view(path):
    return index("")


@web.route("/plans/")
@no_cache
@route_show_if(features.BILLING)
def plans():
    return index("")


@web.route("/search")
@no_cache
def search():
    return index("")


@web.route("/guide/")
@no_cache
def guide():
    return index("")


@web.route("/tour/")
@web.route("/tour/<path:path>")
@no_cache
def tour(path=""):
    return index("")


@web.route("/tutorial/")
@no_cache
def tutorial():
    return index("")


@web.route("/organizations/")
@web.route("/organizations/new/")
@no_cache
def organizations():
    return index("")


@web.route("/superuser/")
@no_cache
@route_show_if(features.SUPER_USERS)
def superuser():
    return index("")


@web.route("/setup/")
@no_cache
@route_show_if(features.SUPER_USERS)
def setup():
    return index("")


@web.route("/signin/")
@no_cache
def signin(redirect=None):
    return index("")


@web.route("/contact/")
@no_cache
def contact():
    return index("")


@web.route("/about/")
@no_cache
def about():
    return index("")


@web.route("/new/")
@no_cache
def new():
    return index("")


@web.route("/updateuser")
@no_cache
def updateuser():
    return index("")


@web.route("/confirminvite")
@no_cache
def confirm_invite():
    code = request.values["code"]
    return index("", code=code)


@web.route("/repository/", defaults={"path": ""})
@web.route("/repository/<path:path>", methods=["GET"])
@no_cache
def repository(path):
    return index("")


@web.route("/repository/<path:path>/trigger/<trigger>", methods=["GET"])
@no_cache
def buildtrigger(path, trigger):
    return index("")


@route_show_if(features.APP_REGISTRY)
@web.route("/application/", defaults={"path": ""})
@web.route("/application/<path:path>", methods=["GET"])
@no_cache
def application(path):
    return index("")


@web.route("/security/")
@no_cache
def security():
    return index("")


@web.route("/enterprise/")
@no_cache
@route_show_if(features.BILLING)
def enterprise():
    return redirect("/plans?tab=enterprise")


@web.route("/__exp/<expname>")
@no_cache
def exp(expname):
    return index("")


@web.route("/v1")
@web.route("/v1/")
@no_cache
def v1():
    return index("")


@web.route("/tos", methods=["GET"])
@no_cache
def tos():
    return index("")


@web.route("/privacy", methods=["GET"])
@no_cache
def privacy():
    return index("")


@web.route("/health", methods=["GET"])
@web.route("/health/instance", methods=["GET"])
@process_auth_or_cookie
@no_cache
def instance_health():
    checker = get_healthchecker(app, config_provider, instance_keys)
    (data, status_code) = checker.check_instance()
    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@web.route("/status", methods=["GET"])
@web.route("/health/endtoend", methods=["GET"])
@process_auth_or_cookie
@no_cache
def endtoend_health():
    checker = get_healthchecker(app, config_provider, instance_keys)
    (data, status_code) = checker.check_endtoend()
    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@web.route("/health/warning", methods=["GET"])
@process_auth_or_cookie
@no_cache
def warning_health():
    checker = get_healthchecker(app, config_provider, instance_keys)
    (data, status_code) = checker.check_warning()
    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@web.route("/health/dbrevision", methods=["GET"])
@route_show_if(features.BILLING)  # Since this is only used in production.
@process_auth_or_cookie
@no_cache
def dbrevision_health():
    # Find the revision from the database.
    result = db.execute_sql("select * from alembic_version limit 1").fetchone()
    db_revision = result[0]

    # Find the local revision from the file system.
    with open(os.path.join(ROOT_DIR, "ALEMBIC_HEAD"), "r") as f:
        local_revision = f.readline().split(" ")[0]

    data = {
        "db_revision": db_revision,
        "local_revision": local_revision,
    }

    status_code = 200 if db_revision == local_revision else 400

    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@web.route("/health/enabledebug/<secret>", methods=["GET"])
@no_cache
def enable_health_debug(secret):
    if not secret:
        abort(404)

    if not app.config.get("ENABLE_HEALTH_DEBUG_SECRET"):
        abort(404)

    if app.config.get("ENABLE_HEALTH_DEBUG_SECRET") != secret:
        abort(404)

    session["health_debug"] = True
    return make_response("Health check debug information enabled")


@web.route("/robots.txt", methods=["GET"])
def robots():
    robots_txt = make_response(render_template("robots.txt", baseurl=get_app_url()))
    robots_txt.headers["Content-Type"] = "text/plain"
    return robots_txt


@web.route("/buildlogs/<build_uuid>", methods=["GET"])
@route_show_if(features.BUILD_SUPPORT)
@process_auth_or_cookie
def buildlogs(build_uuid):
    found_build = model.build.get_repository_build(build_uuid)
    if not found_build:
        abort(403)

    repo = found_build.repository
    has_permission = ModifyRepositoryPermission(repo.namespace_user.username, repo.name).can()
    if features.READER_BUILD_LOGS and not has_permission:
        if ReadRepositoryPermission(
            repo.namespace_user.username, repo.name
        ).can() or model.repository.repository_is_public(repo.namespace_user.username, repo.name):
            has_permission = True

    if not has_permission:
        abort(403)

    # If the logs have been archived, just return a URL of the completed archive
    if found_build.logs_archived:
        return redirect(log_archive.get_file_url(found_build.uuid, get_request_ip()))

    _, logs = build_logs.get_log_entries(found_build.uuid, 0)
    response = jsonify({"logs": [log for log in logs]})

    response.headers["Content-Disposition"] = "attachment;filename=" + found_build.uuid + ".json"
    return response


@web.route("/exportedlogs/<file_id>", methods=["GET"])
def exportedlogs(file_id):
    # Only enable this endpoint if local storage is available.
    has_local_storage = False
    for storage_type, _ in list(app.config.get("DISTRIBUTED_STORAGE_CONFIG", {}).values()):
        if storage_type == "LocalStorage":
            has_local_storage = True
            break

    if not has_local_storage:
        abort(404)

    JSON_MIMETYPE = "application/json"
    exported_logs_storage_path = app.config.get(
        "EXPORT_ACTION_LOGS_STORAGE_PATH", "exportedactionlogs"
    )
    export_storage_path = os.path.join(exported_logs_storage_path, file_id)
    if not storage.exists(storage.preferred_locations, export_storage_path):
        abort(404)

    try:
        return send_file(
            storage.stream_read_file(storage.preferred_locations, export_storage_path),
            mimetype=JSON_MIMETYPE,
        )
    except IOError:
        logger.exception("Could not read exported logs")
        abort(403)


@web.route("/logarchive/<file_id>", methods=["GET"])
@route_show_if(features.BUILD_SUPPORT)
@process_auth_or_cookie
def logarchive(file_id):
    JSON_MIMETYPE = "application/json"
    try:
        found_build = model.build.get_repository_build(file_id)
    except model.InvalidRepositoryBuildException as ex:
        logger.exception(ex, extra={"build_uuid": file_id})
        abort(403)

    repo = found_build.repository
    has_permission = ModifyRepositoryPermission(repo.namespace_user.username, repo.name).can()
    if features.READER_BUILD_LOGS and not has_permission:
        if ReadRepositoryPermission(
            repo.namespace_user.username, repo.name
        ).can() or model.repository.repository_is_public(repo.namespace_user.username, repo.name):
            has_permission = True

    if not has_permission:
        abort(403)

    try:
        path = log_archive.get_file_id_path(file_id)
        data_stream = log_archive._storage.stream_read_file(log_archive._locations, path)
        return send_file(GzipInputStream(data_stream), mimetype=JSON_MIMETYPE)
    except IOError:
        logger.exception("Could not read archived logs")
        abort(403)


@web.route("/receipt", methods=["GET"])
@route_show_if(features.BILLING)
@require_session_login
def receipt():
    if not current_user.is_authenticated:
        abort(401)
        return

    invoice_id = request.args.get("id")
    if invoice_id:
        invoice = stripe.Invoice.retrieve(invoice_id)
        if invoice:
            user_or_org = model.user.get_user_or_org_by_customer_id(invoice.customer)

            if user_or_org:
                if user_or_org.organization:
                    admin_org = AdministerOrganizationPermission(user_or_org.username)
                    if not admin_org.can():
                        abort(404)
                        return
                else:
                    if not user_or_org.username == current_user.db_user().username:
                        abort(404)
                        return

            def format_date(timestamp):
                return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

            file_data = renderInvoiceToPdf(invoice, user_or_org)
            receipt_filename = "quay-receipt-%s.pdf" % (format_date(invoice.date))
            return Response(
                file_data,
                mimetype="application/pdf",
                headers={"Content-Disposition": "attachment;filename=" + receipt_filename},
            )
    abort(404)


@web.route("/authrepoemail", methods=["GET"])
@route_show_if(features.MAILING)
def confirm_repo_email():
    code = request.values["code"]
    record = None

    try:
        record = model.repository.confirm_email_authorization_for_repo(code)
    except model.DataModelException as ex:
        return index("", error_info=dict(reason="confirmerror", error_message=str(ex)))

    message = """
  Your E-mail address has been authorized to receive notifications for repository
  <a href="%s://%s/repository/%s/%s">%s/%s</a>.
  """ % (
        app.config["PREFERRED_URL_SCHEME"],
        app.config["SERVER_HOSTNAME"],
        record.repository.namespace_user.username,
        record.repository.name,
        record.repository.namespace_user.username,
        record.repository.name,
    )

    return render_page_template_with_routedata("message.html", message=message)


@web.route("/confirm", methods=["GET"])
@route_show_if(features.MAILING)
@anon_allowed
def confirm_email():
    code = request.values["code"]
    user = None
    new_email = None

    try:
        user, new_email, old_email = model.user.confirm_user_email(code)
    except model.DataModelException as ex:
        return index("", error_info=dict(reason="confirmerror", error_message=str(ex)))

    if new_email:
        send_email_changed(user.username, old_email, new_email)

    success, _ = common_login(user.uuid)
    if not success:
        return index(
            "", error_info=dict(reason="confirmerror", error_message="Could not perform login")
        )

    if model.user.has_user_prompts(user):
        return redirect(url_for("web.updateuser"))
    elif new_email:
        return redirect(url_for("web.user_view", path=user.username, tab="settings"))
    else:
        return redirect(url_for("web.index"))


@web.route("/recovery", methods=["GET"])
@route_show_if(features.MAILING)
@anon_allowed
def confirm_recovery():
    code = request.values["code"]
    user = model.user.validate_reset_code(code)

    if user is not None:
        success, _ = common_login(user.uuid)
        if not success:
            message = "Could not perform login."
            return render_page_template_with_routedata("message.html", message=message)

        return redirect(
            url_for("web.user_view", path=user.username, tab="settings", action="password")
        )
    else:
        message = "Invalid recovery code: This code is invalid or may have already been used."
        return render_page_template_with_routedata("message.html", message=message)


@web.route("/repository/<repopath:repository>/status", methods=["GET"])
@parse_repository_name()
@anon_protect
def build_status_badge(namespace_name, repo_name):
    token = request.args.get("token", None)
    repo = model.repository.get_repository(namespace_name, repo_name)
    if repo and repo.kind.name != "image":
        abort(404)

    is_public = model.repository.repository_is_public(namespace_name, repo_name)
    if not is_public:
        if not repo or token != repo.badge_token:
            abort(404)

    recent_build = model.build.get_recent_repository_build(namespace_name, repo_name)
    if recent_build and recent_build.phase == "complete":
        status_name = "ready"
    elif recent_build and recent_build.phase == "error":
        status_name = "failed"
    elif recent_build and recent_build.phase == "cancelled":
        status_name = "cancelled"
    elif recent_build and recent_build.phase != "complete":
        status_name = "building"
    else:
        status_name = "none"

    if request.headers.get("If-None-Match") == status_name:
        return Response(status=304)

    response = make_response(STATUS_TAGS[status_name])
    response.content_type = "image/svg+xml"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["ETag"] = status_name
    return response


class FlaskAuthorizationProvider(model.oauth.DatabaseAuthorizationProvider):
    def get_authorized_user(self):
        return get_authenticated_user()

    def _make_response(self, body="", headers=None, status_code=200):
        return make_response(body, status_code, headers)


@web.route("/oauth/authorizeapp", methods=["POST"])
@process_auth_or_cookie
def authorize_application():
    # Check for an authenticated user.
    if not get_authenticated_user():
        abort(401)
        return

    # If direct OAuth is not enabled or the user is not directly authed, verify CSRF.
    client_id = request.form.get("client_id", None)
    whitelist = app.config.get("DIRECT_OAUTH_CLIENTID_WHITELIST", [])
    if client_id not in whitelist or not has_basic_auth(get_authenticated_user().username):
        verify_csrf()

    provider = FlaskAuthorizationProvider()
    redirect_uri = request.form.get("redirect_uri", None)
    scope = request.form.get("scope", None)

    # Add the access token.
    return provider.get_token_response("token", client_id, redirect_uri, scope=scope)


@web.route(app.config["LOCAL_OAUTH_HANDLER"], methods=["GET"])
def oauth_local_handler():
    if not current_user.is_authenticated:
        abort(401)
        return

    if not request.args.get("scope"):
        return render_page_template_with_routedata("message.html", message="Authorization canceled")
    else:
        return render_page_template_with_routedata("generatedtoken.html")


@web.route("/oauth/denyapp", methods=["POST"])
@csrf_protect()
def deny_application():
    if not current_user.is_authenticated:
        abort(401)
        return

    provider = FlaskAuthorizationProvider()
    client_id = request.form.get("client_id", None)
    redirect_uri = request.form.get("redirect_uri", None)
    scope = request.form.get("scope", None)

    # Add the access token.
    return provider.get_auth_denied_response("token", client_id, redirect_uri, scope=scope)


@web.route("/oauth/authorize", methods=["GET"])
@no_cache
@param_required("client_id")
@param_required("redirect_uri")
@param_required("scope")
@process_auth_or_cookie
def request_authorization_code():
    provider = FlaskAuthorizationProvider()
    response_type = request.args.get("response_type", "code")
    client_id = request.args.get("client_id", None)
    redirect_uri = request.args.get("redirect_uri", None)
    scope = request.args.get("scope", None)

    if not current_user.is_authenticated or not provider.validate_has_scopes(
        client_id, current_user.db_user().username, scope
    ):
        if not provider.validate_redirect_uri(client_id, redirect_uri):
            current_app = provider.get_application_for_client_id(client_id)
            if not current_app:
                abort(404)

            return provider._make_redirect_error_response(
                current_app.redirect_uri, "redirect_uri_mismatch"
            )

        # Load the scope information.
        scope_info = scopes.get_scope_information(scope)
        if not scope_info:
            abort(404)
            return

        # Load the application information.
        oauth_app = provider.get_application_for_client_id(client_id)
        app_email = oauth_app.avatar_email or oauth_app.organization.email

        oauth_app_view = {
            "name": oauth_app.name,
            "description": oauth_app.description,
            "url": oauth_app.application_uri,
            "avatar": json.dumps(avatar.get_data(oauth_app.name, app_email, "app")),
            "organization": {
                "name": oauth_app.organization.username,
                "avatar": json.dumps(avatar.get_data_for_org(oauth_app.organization)),
            },
        }

        # Show the authorization page.
        has_dangerous_scopes = any([check_scope["dangerous"] for check_scope in scope_info])
        return render_page_template_with_routedata(
            "oauthorize.html",
            scopes=scope_info,
            has_dangerous_scopes=has_dangerous_scopes,
            application=oauth_app_view,
            enumerate=enumerate,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            csrf_token_val=generate_csrf_token(),
        )

    if response_type == "token":
        return provider.get_token_response(response_type, client_id, redirect_uri, scope=scope)
    else:
        return provider.get_authorization_code(response_type, client_id, redirect_uri, scope=scope)


@web.route("/oauth/access_token", methods=["POST"])
@no_cache
@param_required("grant_type", allow_body=True)
@param_required("client_id", allow_body=True)
@param_required("redirect_uri", allow_body=True)
@param_required("code", allow_body=True)
@param_required("scope", allow_body=True)
def exchange_code_for_token():
    grant_type = request.values.get("grant_type", None)
    client_id = request.values.get("client_id", None)
    client_secret = request.values.get("client_id", None)
    redirect_uri = request.values.get("redirect_uri", None)
    code = request.values.get("code", None)
    scope = request.values.get("scope", None)

    # Sometimes OAuth2 clients place the client id/secret in the Auth header.
    basic_header = parse_basic_auth(request.headers.get("Authorization"))
    if basic_header is not None:
        client_id = basic_header[0] or client_id
        client_secret = basic_header[1] or client_secret

    provider = FlaskAuthorizationProvider()
    return provider.get_token(grant_type, client_id, client_secret, redirect_uri, code, scope=scope)


@web.route("/bitbucket/setup/<repopath:repository>", methods=["GET"])
@require_session_login
@parse_repository_name()
@route_show_if(features.BITBUCKET_BUILD)
def attach_bitbucket_trigger(namespace_name, repo_name):
    permission = AdministerRepositoryPermission(namespace_name, repo_name)
    if permission.can():
        repo = model.repository.get_repository(namespace_name, repo_name)
        if not repo:
            msg = "Invalid repository: %s/%s" % (namespace_name, repo_name)
            abort(404, message=msg)
        elif repo.kind.name != "image":
            abort(501)

        trigger = model.build.create_build_trigger(
            repo, BitbucketBuildTrigger.service_name(), None, current_user.db_user()
        )

        try:
            oauth_info = BuildTriggerHandler.get_handler(trigger).get_oauth_url()
        except TriggerProviderException:
            trigger.delete_instance()
            logger.debug("Could not retrieve Bitbucket OAuth URL")
            abort(500)

        config = {"access_token": oauth_info["access_token"]}

        access_token_secret = oauth_info["access_token_secret"]
        model.build.update_build_trigger(trigger, config, auth_token=access_token_secret)

        return redirect(oauth_info["url"])

    abort(403)


@web.route("/customtrigger/setup/<repopath:repository>", methods=["GET"])
@require_session_login
@parse_repository_name()
def attach_custom_build_trigger(namespace_name, repo_name):
    permission = AdministerRepositoryPermission(namespace_name, repo_name)
    if permission.can():
        repo = model.repository.get_repository(namespace_name, repo_name)
        if not repo:
            msg = "Invalid repository: %s/%s" % (namespace_name, repo_name)
            abort(404, message=msg)
        elif repo.kind.name != "image":
            abort(501)

        trigger = model.build.create_build_trigger(
            repo, CustomBuildTrigger.service_name(), None, current_user.db_user()
        )

        repo_path = "%s/%s" % (namespace_name, repo_name)
        full_url = url_for("web.buildtrigger", path=repo_path, trigger=trigger.uuid)
        logger.debug("Redirecting to full url: %s", full_url)
        return redirect(full_url)

    abort(403)


@web.route("/<repopathredirect:repository>")
@web.route("/<repopathredirect:repository>/")
@no_cache
@process_oauth
@parse_repository_name(include_tag=True)
@anon_protect
def redirect_to_repository(namespace_name, repo_name, tag_name):
    # Always return 200 for ac-discovery, to ensure that rkt and other ACI-compliant clients can
    # find the metadata they need. Permissions will be checked in the registry API.
    if request.args.get("ac-discovery", 0) == 1:
        return index("")

    # Redirect to the repository page if the user can see the repository.
    is_public = model.repository.repository_is_public(namespace_name, repo_name)
    permission = ReadRepositoryPermission(namespace_name, repo_name)
    repo = model.repository.get_repository(namespace_name, repo_name)

    if repo and (permission.can() or is_public):
        repo_path = "/".join([namespace_name, repo_name])
        if repo.kind.name == "application":
            return redirect(url_for("web.application", path=repo_path))
        else:
            return redirect(url_for("web.repository", path=repo_path, tab="tags", tag=tag_name))

    namespace_exists = bool(model.user.get_user_or_org(namespace_name))
    namespace_permission = OrganizationMemberPermission(namespace_name).can()
    if get_authenticated_user() and get_authenticated_user().username == namespace_name:
        namespace_permission = True

    # Otherwise, we display an error for the user. Which error we display depends on permissions:
    # > If the namespace doesn't exist, 404.
    # > If the user is a member of the namespace:
    #   - If the repository doesn't exist, 404
    #   - If the repository does exist (no access), 403
    # > If the user is not a member of the namespace: 403
    error_info = {
        "reason": "notfound",
        "for_repo": True,
        "namespace_exists": namespace_exists,
        "namespace": namespace_name,
        "repo_name": repo_name,
    }

    if not namespace_exists or (namespace_permission and repo is None):
        resp = index("", error_code=404, error_info=json.dumps(error_info))
        resp.status_code = 404
        return resp
    else:
        resp = index("", error_code=403, error_info=json.dumps(error_info))
        resp.status_code = 403
        return resp


@web.route("/<namespace>")
@web.route("/<namespace>/")
@no_cache
@process_oauth
@anon_protect
def redirect_to_namespace(namespace):
    okay, _ = model.user.validate_username(namespace)
    if not okay:
        abort(404)

    user_or_org = model.user.get_user_or_org(namespace)
    if not user_or_org:
        abort(404)

    if user_or_org.organization:
        return redirect(url_for("web.org_view", path=namespace))
    else:
        return redirect(url_for("web.user_view", path=namespace))


def has_users():
    """
    Return false if no users in database yet
    """
    return bool(User.select().limit(1))


@web.route("/api/v1/user/initialize", methods=["POST"])
@route_show_if(features.USER_INITIALIZE)
def user_initialize():
    """
    Create initial user in an empty database
    """

    # Ensure that we are using database auth.
    if not features.USER_INITIALIZE:
        response = jsonify({"message": "Cannot initialize user, FEATURE_USER_INITIALIZE is False"})
        response.status_code = 400
        return response

    # Ensure that we are using database auth.
    if app.config["AUTHENTICATION_TYPE"] != "Database":
        response = jsonify({"message": "Cannot initialize user in a non-database auth system"})
        response.status_code = 400
        return response

    if has_users():
        response = jsonify({"message": "Cannot initialize user in a non-empty database"})
        response.status_code = 400
        return response

    user_data = request.get_json()
    try:
        prompts = model.user.get_default_user_prompts(features)
        new_user = model.user.create_user(
            user_data["username"],
            user_data["password"],
            user_data.get("email"),
            auto_verify=True,
            email_required=features.MAILING,
            is_possible_abuser=False,
            prompts=prompts,
        )
        success, headers = common_login(new_user.uuid)
        if not success:
            response = jsonify({"message": "Could not login. Failed to initialize user"})
            response.status_code = 403
            return response

        result = {
            "username": user_data["username"],
            "email": user_data.get("email"),
            "encrypted_password": authentication.encrypt_user_password(
                user_data["password"]
            ).decode("ascii"),
        }

        if user_data.get("access_token"):
            model.oauth.create_application(
                new_user,
                "automation",
                "",
                "",
                client_id=user_data["username"],
                description="Application token generated via /api/v1/user/initialize",
            )
            scope = "org:admin repo:admin repo:create repo:read repo:write super:user user:admin user:read"
            created, access_token = model.oauth.create_user_access_token(
                new_user, user_data["username"], scope
            )
            result["access_token"] = access_token

        return (result, 200, headers)
    except model.user.DataModelException as ex:
        response = jsonify({"message": "Failed to initialize user: " + str(ex)})
        response.status_code = 400
        return response
