import logging
from base64 import b64encode

import cnr
from cnr.api.impl import registry as cnr_registry
from cnr.api.registry import _pull, repo_name
from cnr.exception import (
    ChannelNotFound,
    CnrException,
    Forbidden,
    InvalidParams,
    InvalidRelease,
    InvalidUsage,
    PackageAlreadyExists,
    PackageNotFound,
    PackageReleaseNotFound,
    UnableToLockResource,
    UnauthorizedAccess,
    Unsupported,
)
from flask import jsonify, request

from app import app, model_cache
from auth.auth_context import get_authenticated_user
from auth.credentials import validate_credentials
from auth.decorators import process_auth
from auth.permissions import CreateRepositoryPermission, ModifyRepositoryPermission
from data.logs_model import logs_model
from data.cache import cache_key
from endpoints.appr import appr_bp, require_app_repo_read, require_app_repo_write
from endpoints.appr.cnr_backend import Blob, Channel, Package, User
from endpoints.appr.decorators import disallow_for_image_repository
from endpoints.appr.models_cnr import model
from endpoints.decorators import anon_allowed, anon_protect, check_region_blacklisted
from util.names import REPOSITORY_NAME_REGEX, TAG_REGEX

logger = logging.getLogger(__name__)


@appr_bp.errorhandler(Unsupported)
@appr_bp.errorhandler(PackageAlreadyExists)
@appr_bp.errorhandler(InvalidRelease)
@appr_bp.errorhandler(Forbidden)
@appr_bp.errorhandler(UnableToLockResource)
@appr_bp.errorhandler(UnauthorizedAccess)
@appr_bp.errorhandler(PackageNotFound)
@appr_bp.errorhandler(PackageReleaseNotFound)
@appr_bp.errorhandler(CnrException)
@appr_bp.errorhandler(InvalidUsage)
@appr_bp.errorhandler(InvalidParams)
@appr_bp.errorhandler(ChannelNotFound)
def render_error(error):
    response = jsonify({"error": error.to_dict()})
    response.status_code = error.status_code
    return response


@appr_bp.route("/version")
@anon_allowed
def version():
    return jsonify({"cnr-api": cnr.__version__})


@appr_bp.route("/api/v1/users/login", methods=["POST"])
@anon_allowed
def login():
    values = request.get_json(force=True, silent=True) or {}
    username = values.get("user", {}).get("username")
    password = values.get("user", {}).get("password")
    if not username or not password:
        raise InvalidUsage("Missing username or password")

    result, _ = validate_credentials(username, password)
    if not result.auth_valid:
        raise UnauthorizedAccess(result.error_message)

    auth = b64encode(b"%s:%s" % (username.encode("ascii"), password.encode("ascii")))
    return jsonify({"token": "basic " + auth.decode("ascii")})


# @TODO: Redirect to S3 url
@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/blobs/sha256/<string:digest>",
    methods=["GET"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_read
@check_region_blacklisted(namespace_name_kwarg="namespace")
@anon_protect
def blobs(namespace, package_name, digest):
    reponame = repo_name(namespace, package_name)
    data = cnr_registry.pull_blob(reponame, digest, blob_class=Blob)
    json_format = request.args.get("format", None) == "json"
    return _pull(data, json_format=json_format)


@appr_bp.route("/api/v1/packages", methods=["GET"], strict_slashes=False)
@process_auth
@anon_protect
def list_packages():
    namespace = request.args.get("namespace", None)
    media_type = request.args.get("media_type", None)
    query = request.args.get("query", None)
    user = get_authenticated_user()
    username = None
    if user:
        username = user.username
    result_data = cnr_registry.list_packages(
        namespace, package_class=Package, search=query, media_type=media_type, username=username
    )
    return jsonify(result_data)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>/<string:media_type>",
    methods=["DELETE"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_write
@anon_protect
def delete_package(namespace, package_name, release, media_type):
    reponame = repo_name(namespace, package_name)
    result = cnr_registry.delete_package(reponame, release, media_type, package_class=Package)
    logs_model.log_action(
        "delete_tag",
        namespace,
        repository_name=package_name,
        metadata={"release": release, "mediatype": media_type},
    )
    return jsonify(result)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>/<string:media_type>",
    methods=["GET"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_read
@check_region_blacklisted(namespace_name_kwarg="namespace")
@anon_protect
def show_package(namespace, package_name, release, media_type):
    def _retrieve_package():
        reponame = repo_name(namespace, package_name)
        return cnr_registry.show_package(
            reponame, release, media_type, channel_class=Channel, package_class=Package
        )

    namespace_whitelist = app.config.get("APP_REGISTRY_SHOW_PACKAGE_CACHE_WHITELIST", [])
    if not namespace or namespace not in namespace_whitelist:
        return jsonify(_retrieve_package())

    show_package_cache_key = cache_key.for_appr_show_package(
        namespace, package_name, release, media_type, model_cache.cache_config
    )

    result = model_cache.retrieve(show_package_cache_key, _retrieve_package)
    return jsonify(result)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>",
    methods=["GET"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_read
@anon_protect
def show_package_releases(namespace, package_name):
    reponame = repo_name(namespace, package_name)
    media_type = request.args.get("media_type", None)
    result = cnr_registry.show_package_releases(
        reponame, media_type=media_type, package_class=Package
    )
    return jsonify(result)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>",
    methods=["GET"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_read
@anon_protect
def show_package_release_manifests(namespace, package_name, release):
    reponame = repo_name(namespace, package_name)
    result = cnr_registry.show_package_manifests(reponame, release, package_class=Package)
    return jsonify(result)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>/<string:media_type>/pull",
    methods=["GET"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_read
@check_region_blacklisted(namespace_name_kwarg="namespace")
@anon_protect
def pull(namespace, package_name, release, media_type):
    logger.debug("Pull of release %s of app repository %s/%s", release, namespace, package_name)
    reponame = repo_name(namespace, package_name)
    data = cnr_registry.pull(reponame, release, media_type, Package, blob_class=Blob)
    logs_model.log_action(
        "pull_repo",
        namespace,
        repository_name=package_name,
        metadata={"release": release, "mediatype": media_type},
    )
    json_format = request.args.get("format", None) == "json"
    return _pull(data, json_format)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>",
    methods=["POST"],
    strict_slashes=False,
)
@disallow_for_image_repository()
@process_auth
@anon_protect
def push(namespace, package_name):
    reponame = repo_name(namespace, package_name)

    if not REPOSITORY_NAME_REGEX.match(package_name):
        logger.debug("Found invalid repository name CNR push: %s", reponame)
        raise InvalidUsage("invalid repository name: %s" % reponame)

    values = request.get_json(force=True, silent=True) or {}
    private = values.get("visibility", "private")

    owner = get_authenticated_user()
    if not Package.exists(reponame):
        if not CreateRepositoryPermission(namespace).can():
            raise Forbidden(
                "Unauthorized access for: %s" % reponame,
                {"package": reponame, "scopes": ["create"]},
            )
        Package.create_repository(reponame, private, owner)
        logs_model.log_action("create_repo", namespace, repository_name=package_name)

    if not ModifyRepositoryPermission(namespace, package_name).can():
        raise Forbidden(
            "Unauthorized access for: %s" % reponame, {"package": reponame, "scopes": ["push"]}
        )

    if not "release" in values:
        raise InvalidUsage("Missing release")

    if not "media_type" in values:
        raise InvalidUsage("Missing media_type")

    if not "blob" in values:
        raise InvalidUsage("Missing blob")

    release_version = str(values["release"])
    media_type = values["media_type"]
    force = request.args.get("force", "false") == "true"

    blob = Blob(reponame, values["blob"])
    app_release = cnr_registry.push(
        reponame,
        release_version,
        media_type,
        blob,
        force,
        package_class=Package,
        user=owner,
        visibility=private,
    )
    logs_model.log_action(
        "push_repo", namespace, repository_name=package_name, metadata={"release": release_version}
    )
    return jsonify(app_release)


@appr_bp.route("/api/v1/packages/search", methods=["GET"], strict_slashes=False)
@process_auth
@anon_protect
def search_packages():
    query = request.args.get("q")
    user = get_authenticated_user()
    username = None
    if user:
        username = user.username

    search_results = cnr_registry.search(query, Package, username=username)
    return jsonify(search_results)


# CHANNELS
@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/channels",
    methods=["GET"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_read
@anon_protect
def list_channels(namespace, package_name):
    reponame = repo_name(namespace, package_name)
    return jsonify(cnr_registry.list_channels(reponame, channel_class=Channel))


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>",
    methods=["GET"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_read
@anon_protect
def show_channel(namespace, package_name, channel_name):
    reponame = repo_name(namespace, package_name)
    channel = cnr_registry.show_channel(reponame, channel_name, channel_class=Channel)
    return jsonify(channel)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>/<string:release>",
    methods=["POST"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_write
@anon_protect
def add_channel_release(namespace, package_name, channel_name, release):
    _check_channel_name(channel_name, release)
    reponame = repo_name(namespace, package_name)
    result = cnr_registry.add_channel_release(
        reponame, channel_name, release, channel_class=Channel, package_class=Package
    )
    logs_model.log_action(
        "create_tag",
        namespace,
        repository_name=package_name,
        metadata={"channel": channel_name, "release": release},
    )
    return jsonify(result)


def _check_channel_name(channel_name, release=None):
    if not TAG_REGEX.match(channel_name):
        logger.debug("Found invalid channel name CNR add channel release: %s", channel_name)
        raise InvalidUsage(
            "Found invalid channelname %s" % release, {"name": channel_name, "release": release}
        )

    if release is not None and not TAG_REGEX.match(release):
        logger.debug("Found invalid release name CNR add channel release: %s", release)
        raise InvalidUsage(
            "Found invalid channel release name %s" % release,
            {"name": channel_name, "release": release},
        )


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>/<string:release>",
    methods=["DELETE"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_write
@anon_protect
def delete_channel_release(namespace, package_name, channel_name, release):
    _check_channel_name(channel_name, release)
    reponame = repo_name(namespace, package_name)
    result = cnr_registry.delete_channel_release(
        reponame, channel_name, release, channel_class=Channel, package_class=Package
    )
    logs_model.log_action(
        "delete_tag",
        namespace,
        repository_name=package_name,
        metadata={"channel": channel_name, "release": release},
    )
    return jsonify(result)


@appr_bp.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>",
    methods=["DELETE"],
    strict_slashes=False,
)
@process_auth
@require_app_repo_write
@anon_protect
def delete_channel(namespace, package_name, channel_name):
    _check_channel_name(channel_name)
    reponame = repo_name(namespace, package_name)
    result = cnr_registry.delete_channel(reponame, channel_name, channel_class=Channel)
    logs_model.log_action(
        "delete_tag", namespace, repository_name=package_name, metadata={"channel": channel_name}
    )
    return jsonify(result)
