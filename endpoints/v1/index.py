import json
import logging
import urllib.parse

from functools import wraps

from flask import request, make_response, jsonify, session

import features
from app import userevents, storage, docker_v2_signing_key
from auth.auth_context import get_authenticated_context, get_authenticated_user
from auth.credentials import validate_credentials, CredentialKind
from auth.decorators import process_auth
from auth.permissions import (
    ModifyRepositoryPermission,
    UserAdminPermission,
    ReadRepositoryPermission,
    CreateRepositoryPermission,
    repository_read_grant,
    repository_write_grant,
)
from auth.signedgrant import generate_signed_token
from data import model
from data.registry_model import registry_model
from data.registry_model.manifestbuilder import create_manifest_builder, lookup_manifest_builder
from endpoints.decorators import (
    anon_protect,
    anon_allowed,
    parse_repository_name,
    check_repository_state,
    check_readonly,
)
from endpoints.metrics import image_pulls, image_pushes
from endpoints.v1 import v1_bp, check_v1_push_enabled
from notifications import spawn_notification
from util.audit import track_and_log
from util.http import abort
from util.names import REPOSITORY_NAME_REGEX

logger = logging.getLogger(__name__)


class GrantType(object):
    READ_REPOSITORY = "read"
    WRITE_REPOSITORY = "write"


def ensure_namespace_enabled(f):
    @wraps(f)
    def wrapper(namespace_name, repo_name, *args, **kwargs):
        namespace = model.user.get_namespace_user(namespace_name)
        is_namespace_enabled = namespace is not None and namespace.enabled
        if not is_namespace_enabled:
            abort(400, message="Namespace is disabled. Please contact your system administrator.")

        return f(namespace_name, repo_name, *args, **kwargs)

    return wrapper


def generate_headers(scope=GrantType.READ_REPOSITORY, add_grant_for_status=None):
    def decorator_method(f):
        @wraps(f)
        def wrapper(namespace_name, repo_name, *args, **kwargs):
            response = f(namespace_name, repo_name, *args, **kwargs)

            # Setting session namespace and repository
            session["namespace"] = namespace_name
            session["repository"] = repo_name

            # We run our index and registry on the same hosts for now
            registry_server = urllib.parse.urlparse(request.url).netloc
            response.headers["X-Docker-Endpoints"] = registry_server

            has_token_request = request.headers.get("X-Docker-Token", "")
            force_grant = add_grant_for_status == response.status_code

            if has_token_request or force_grant:
                grants = []

                if scope == GrantType.READ_REPOSITORY:
                    if force_grant or ReadRepositoryPermission(namespace_name, repo_name).can():
                        grants.append(repository_read_grant(namespace_name, repo_name))
                elif scope == GrantType.WRITE_REPOSITORY:
                    if force_grant or ModifyRepositoryPermission(namespace_name, repo_name).can():
                        grants.append(repository_write_grant(namespace_name, repo_name))

                # Generate a signed token for the user (if any) and the grants (if any)
                if grants or get_authenticated_user():
                    user_context = get_authenticated_user() and get_authenticated_user().username
                    signature = generate_signed_token(grants, user_context)
                    response.headers["WWW-Authenticate"] = signature
                    response.headers["X-Docker-Token"] = signature

            return response

        return wrapper

    return decorator_method


@v1_bp.route("/users", methods=["POST"])
@v1_bp.route("/users/", methods=["POST"])
@anon_allowed
@check_readonly
def create_user():
    user_data = request.get_json()
    if not user_data or not "username" in user_data:
        abort(400, "Missing username")

    username = user_data["username"]
    password = user_data.get("password", "")

    # UGH! we have to use this response when the login actually worked, in order
    # to get the CLI to try again with a get, and then tell us login succeeded.
    success = make_response('"Username or email already exists"', 400)
    result, kind = validate_credentials(username, password)
    if not result.auth_valid:
        if kind == CredentialKind.token:
            abort(400, "Invalid access token.", issue="invalid-access-token")

        if kind == CredentialKind.robot:
            abort(400, "Invalid robot account or password.", issue="robot-login-failure")

        if kind == CredentialKind.oauth_token:
            abort(400, "Invalid oauth access token.", issue="invalid-oauth-access-token")

        if kind == CredentialKind.user:
            # Mark that the login failed.
            event = userevents.get_event(username)
            event.publish_event_data("docker-cli", {"action": "loginfailure"})
            abort(400, result.error_message, issue="login-failure")

        # Default case: Just fail.
        abort(400, result.error_message, issue="login-failure")

    if result.has_nonrobot_user:
        # Mark that the user was logged in.
        event = userevents.get_event(username)
        event.publish_event_data("docker-cli", {"action": "login"})

    return success


@v1_bp.route("/users", methods=["GET"])
@v1_bp.route("/users/", methods=["GET"])
@process_auth
@anon_allowed
def get_user():
    context = get_authenticated_context()
    if not context or context.is_anonymous:
        abort(404)

    return jsonify(
        {
            "username": context.credential_username,
            "email": None,
        }
    )


@v1_bp.route("/users/<username>/", methods=["PUT"])
@process_auth
@anon_allowed
@check_readonly
def update_user(username):
    permission = UserAdminPermission(username)
    if permission.can():
        update_request = request.get_json()

        if "password" in update_request:
            logger.debug("Updating user password")
            model.user.change_password(get_authenticated_user(), update_request["password"])

        return jsonify(
            {
                "username": get_authenticated_user().username,
                "email": get_authenticated_user().email,
            }
        )

    abort(403)


@v1_bp.route("/repositories/<v1createrepopath:repository>/", methods=["PUT"])
@process_auth
@parse_repository_name()
@check_v1_push_enabled()
@ensure_namespace_enabled
@check_repository_state
@generate_headers(scope=GrantType.WRITE_REPOSITORY, add_grant_for_status=201)
@anon_allowed
@check_readonly
def create_repository(namespace_name, repo_name):
    # Verify that the repository name is valid.
    if not REPOSITORY_NAME_REGEX.match(repo_name):
        abort(400, message="Invalid repository name. Repository names cannot contain slashes.")

    logger.debug("Looking up repository %s/%s", namespace_name, repo_name)
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None and get_authenticated_user() is None:
        logger.debug(
            "Attempt to create repository %s/%s without user auth", namespace_name, repo_name
        )
        abort(
            401,
            message='Cannot create a repository as a guest. Please login via "docker login" first.',
            issue="no-login",
        )
    elif repository_ref:
        modify_perm = ModifyRepositoryPermission(namespace_name, repo_name)
        if not modify_perm.can():
            abort(
                403,
                message="You do not have permission to modify repository %(namespace)s/%(repository)s",
                issue="no-repo-write-permission",
                namespace=namespace_name,
                repository=repo_name,
            )
        elif repository_ref.kind != "image":
            msg = (
                "This repository is for managing %s resources and not container images."
                % repository_ref.kind
            )
            abort(405, message=msg, namespace=namespace_name)
    else:
        create_perm = CreateRepositoryPermission(namespace_name)
        if not create_perm.can():
            logger.warning(
                "Attempt to create a new repo %s/%s with insufficient perms",
                namespace_name,
                repo_name,
            )
            msg = 'You do not have permission to create repositories in namespace "%(namespace)s"'
            abort(403, message=msg, issue="no-create-permission", namespace=namespace_name)

        # Attempt to create the new repository.
        logger.debug(
            "Creating repository %s/%s with owner: %s",
            namespace_name,
            repo_name,
            get_authenticated_user().username,
        )

        repository_ref = model.repository.create_repository(
            namespace_name, repo_name, get_authenticated_user()
        )

    if get_authenticated_user():
        user_event_data = {
            "action": "push_start",
            "repository": repo_name,
            "namespace": namespace_name,
        }

        event = userevents.get_event(get_authenticated_user().username)
        event.publish_event_data("docker-cli", user_event_data)

    # Start a new builder for the repository and save its ID in the session.
    assert repository_ref
    builder = create_manifest_builder(repository_ref, storage, docker_v2_signing_key)
    logger.debug("Started repo push with manifest builder %s", builder)
    if builder is None:
        abort(404, message="Unknown repository", issue="unknown-repo")

    session["manifest_builder"] = builder.builder_id
    return make_response("Created", 201)


@v1_bp.route("/repositories/<repopath:repository>/images", methods=["PUT"])
@process_auth
@parse_repository_name()
@check_v1_push_enabled()
@ensure_namespace_enabled
@check_repository_state
@generate_headers(scope=GrantType.WRITE_REPOSITORY)
@anon_allowed
@check_readonly
def update_images(namespace_name, repo_name):
    permission = ModifyRepositoryPermission(namespace_name, repo_name)
    if permission.can():
        logger.debug("Looking up repository")
        repository_ref = registry_model.lookup_repository(
            namespace_name, repo_name, kind_filter="image"
        )
        if repository_ref is None:
            # Make sure the repo actually exists.
            image_pushes.labels("v1", 404, "").inc()
            abort(404, message="Unknown repository", issue="unknown-repo")

        builder = lookup_manifest_builder(
            repository_ref, session.get("manifest_builder"), storage, docker_v2_signing_key
        )
        if builder is None:
            image_pushes.labels("v1", 400, "").inc()
            abort(400)

        # Generate a job for each notification that has been added to this repo
        logger.debug("Adding notifications for repository")
        event_data = {
            "updated_tags": [tag.name for tag in builder.committed_tags],
        }

        builder.done()

        track_and_log("push_repo", repository_ref)
        spawn_notification(repository_ref, "repo_push", event_data)
        image_pushes.labels("v1", 204, "").inc()
        return make_response("Updated", 204)

    image_pushes.labels("v1", 403, "").inc()
    abort(403)


@v1_bp.route("/repositories/<repopath:repository>/images", methods=["GET"])
@process_auth
@parse_repository_name()
@ensure_namespace_enabled
@generate_headers(scope=GrantType.READ_REPOSITORY)
@anon_protect
def get_repository_images(namespace_name, repo_name):
    repository_ref = registry_model.lookup_repository(
        namespace_name, repo_name, kind_filter="image"
    )

    permission = ReadRepositoryPermission(namespace_name, repo_name)
    if permission.can() or (repository_ref and repository_ref.is_public):
        # We can't rely on permissions to tell us if a repo exists anymore
        if repository_ref is None:
            image_pulls.labels("v1", "tag", 404).inc()
            abort(404, message="Unknown repository", issue="unknown-repo")

        logger.debug("Building repository image response")
        resp = make_response(json.dumps([]), 200)
        resp.mimetype = "application/json"

        track_and_log(
            "pull_repo", repository_ref, analytics_name="pull_repo_100x", analytics_sample=0.01
        )
        image_pulls.labels("v1", "tag", 200).inc()
        return resp

    image_pulls.labels("v1", "tag", 403).inc()
    abort(403)


@v1_bp.route("/repositories/<repopath:repository>/images", methods=["DELETE"])
@process_auth
@parse_repository_name()
@check_v1_push_enabled()
@ensure_namespace_enabled
@check_repository_state
@generate_headers(scope=GrantType.WRITE_REPOSITORY)
@anon_allowed
@check_readonly
def delete_repository_images(namespace_name, repo_name):
    abort(501, "Not Implemented", issue="not-implemented")


@v1_bp.route("/repositories/<repopath:repository>/auth", methods=["PUT"])
@parse_repository_name()
@check_v1_push_enabled()
@ensure_namespace_enabled
@check_repository_state
@anon_allowed
@check_readonly
def put_repository_auth(namespace_name, repo_name):
    abort(501, "Not Implemented", issue="not-implemented")


@v1_bp.route("/search", methods=["GET"])
@process_auth
@anon_protect
def get_search():
    query = request.args.get("q") or ""

    try:
        limit = min(100, max(1, int(request.args.get("n", 25))))
    except ValueError:
        limit = 25

    try:
        page = max(0, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    username = None
    user = get_authenticated_user()
    if user is not None:
        username = user.username

    data = _conduct_repo_search(username, query, limit, page)
    resp = make_response(json.dumps(data), 200)
    resp.mimetype = "application/json"
    return resp


def _conduct_repo_search(username, query, limit=25, page=1):
    """
    Finds matching repositories.
    """
    # Note that we put a maximum limit of five pages here, because this API should only really ever
    # be used by the Docker CLI, and it doesn't even paginate.
    page = min(page, 5)
    offset = (page - 1) * limit

    if query:
        matching_repos = model.repository.get_filtered_matching_repositories(
            query, filter_username=username, offset=offset, limit=limit + 1
        )
    else:
        matching_repos = []

    results = []
    for repo in matching_repos[0:limit]:
        results.append(
            {
                "name": repo.namespace_user.username + "/" + repo.name,
                "description": repo.description,
                "is_public": model.repository.is_repository_public(repo),
                "href": "/repository/" + repo.namespace_user.username + "/" + repo.name,
            }
        )

    # Defined: https://docs.docker.com/v1.6/reference/api/registry_api/
    return {
        "query": query,
        "num_results": len(results),
        "num_pages": page + 1 if len(matching_repos) > limit else page,
        "page": page,
        "page_size": limit,
        "results": results,
    }
