import logging
import os.path

from functools import wraps
from urllib.parse import urlparse
from urllib.parse import urlencode

from flask import Blueprint, make_response, url_for, request, jsonify
from semantic_version import Spec

import features

from app import app, get_app_url
from auth.auth_context import get_authenticated_context
from auth.permissions import (
    ReadRepositoryPermission,
    ModifyRepositoryPermission,
    AdministerRepositoryPermission,
)
from auth.registry_jwt_auth import process_registry_jwt_auth, get_auth_headers
from data.registry_model import registry_model
from data.readreplica import ReadOnlyModeException
from endpoints.decorators import anon_protect, anon_allowed, route_show_if
from endpoints.v2.errors import (
    V2RegistryException,
    Unauthorized,
    Unsupported,
    NameUnknown,
    ReadOnlyMode,
)
from util.http import abort
from util.metrics.prometheus import timed_blueprint
from util.registry.dockerver import docker_version
from util.pagination import encrypt_page_token, decrypt_page_token


logger = logging.getLogger(__name__)
v2_bp = timed_blueprint(Blueprint("v2", __name__))


@v2_bp.app_errorhandler(V2RegistryException)
def handle_registry_v2_exception(error):
    response = jsonify({"errors": [error.as_dict()]})

    response.status_code = error.http_status_code
    if response.status_code == 401:
        response.headers.extend(get_auth_headers(repository=error.repository, scopes=error.scopes))
    logger.debug("sending response: %s", response.get_data())
    return response


@v2_bp.app_errorhandler(ReadOnlyModeException)
def handle_readonly(ex):
    error = ReadOnlyMode()
    response = jsonify({"errors": [error.as_dict()]})
    response.status_code = error.http_status_code
    logger.debug("sending response: %s", response.get_data())
    return response


_MAX_RESULTS_PER_PAGE = app.config.get("V2_PAGINATION_SIZE", 100)


def paginate(
    start_id_kwarg_name="start_id",
    limit_kwarg_name="limit",
    callback_kwarg_name="pagination_callback",
):
    """
    Decorates a handler adding a parsed pagination token and a callback to encode a response token.
    """

    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                requested_limit = int(request.args.get("n", _MAX_RESULTS_PER_PAGE))
            except ValueError:
                requested_limit = 0

            limit = max(min(requested_limit, _MAX_RESULTS_PER_PAGE), 1)
            next_page_token = request.args.get("next_page", request.args.get("last", None))

            # Decrypt the next page token, if any.
            start_id = None
            page_info = decrypt_page_token(next_page_token)
            if page_info is not None:
                start_id = page_info.get("start_id", None)

            def callback(results, response):
                if len(results) <= limit:
                    return

                next_page_token = encrypt_page_token({"start_id": max([obj.id for obj in results])})

                link_url = os.path.join(
                    get_app_url(), url_for(request.endpoint, **request.view_args)
                )
                link_param = urlencode({"n": limit, "next_page": next_page_token})
                link = '<%s?%s>; rel="next"' % (link_url, link_param)
                response.headers["Link"] = link

            kwargs[limit_kwarg_name] = limit
            kwargs[start_id_kwarg_name] = start_id
            kwargs[callback_kwarg_name] = callback
            return func(*args, **kwargs)

        return wrapped

    return wrapper


def _require_repo_permission(permission_class, scopes=None, allow_public=False):
    def wrapper(func):
        @wraps(func)
        def wrapped(namespace_name, repo_name, *args, **kwargs):
            logger.debug(
                "Checking permission %s for repo: %s/%s",
                permission_class,
                namespace_name,
                repo_name,
            )

            permission = permission_class(namespace_name, repo_name)
            if permission.can():
                return func(namespace_name, repo_name, *args, **kwargs)

            repository = namespace_name + "/" + repo_name
            if allow_public:
                repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
                if repository_ref is None or not repository_ref.is_public:
                    raise Unauthorized(repository=repository, scopes=scopes)

                if repository_ref.kind != "image":
                    msg = (
                        "This repository is for managing %s and not container images."
                        % repository_ref.kind
                    )
                    raise Unsupported(detail=msg)

                if repository_ref.is_public:
                    if not features.ANONYMOUS_ACCESS:
                        raise Unauthorized(repository=repository, scopes=scopes)

                    return func(namespace_name, repo_name, *args, **kwargs)

            raise Unauthorized(repository=repository, scopes=scopes)

        return wrapped

    return wrapper


require_repo_read = _require_repo_permission(
    ReadRepositoryPermission, scopes=["pull"], allow_public=True
)
require_repo_write = _require_repo_permission(ModifyRepositoryPermission, scopes=["pull", "push"])
require_repo_admin = _require_repo_permission(
    AdministerRepositoryPermission, scopes=["pull", "push"]
)


def get_input_stream(flask_request):
    if flask_request.headers.get("transfer-encoding") == "chunked":
        return flask_request.environ["wsgi.input"]
    return flask_request.stream


@v2_bp.route("/")
@route_show_if(features.ADVERTISE_V2)
@process_registry_jwt_auth()
@anon_allowed
def v2_support_enabled():
    docker_ver = docker_version(request.user_agent.string)

    # Check if our version is one of the blacklisted versions, if we can't
    # identify the version (None) we will fail open and assume that it is
    # newer and therefore should not be blacklisted.
    if docker_ver is not None and Spec(app.config["BLACKLIST_V2_SPEC"]).match(docker_ver):
        abort(404)

    response = make_response("true", 200)

    if get_authenticated_context() is None:
        response = make_response("true", 401)

    response.headers.extend(get_auth_headers())
    return response


from endpoints.v2 import (
    blob,
    catalog,
    manifest,
    tag,
    v2auth,
)
