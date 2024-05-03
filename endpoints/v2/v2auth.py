import logging
import re
from collections import namedtuple

from cachetools.func import lru_cache
from flask import jsonify, request, g

import features
from app import app, instance_keys, userevents, usermanager
from auth.auth_context import get_authenticated_context, get_authenticated_user
from auth.decorators import process_basic_auth
from auth.permissions import (
    AdministerRepositoryPermission,
    CreateRepositoryPermission,
    ModifyRepositoryPermission,
    OrganizationMemberPermission,
    ReadRepositoryPermission,
)
from data import model
from data.database import RepositoryState
from data.model.repo_mirror import get_mirroring_robot
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from endpoints.api import log_action
from endpoints.decorators import anon_protect
from endpoints.v2 import v2_bp
from endpoints.v2.errors import (
    InvalidLogin,
    InvalidRequest,
    NameInvalid,
    NamespaceDisabled,
    Unauthorized,
    Unsupported,
)
from util.cache import no_cache
from util.names import (
    REPOSITORY_NAME_EXTENDED_REGEX,
    REPOSITORY_NAME_REGEX,
    parse_namespace_repository,
    parse_robot_username,
)
from util.request import get_request_ip
from util.security.registry_jwt import (
    DISABLED_TUF_ROOT,
    QUAY_TUF_ROOT,
    SIGNER_TUF_ROOT,
    build_context_and_subject,
    generate_bearer_token,
)

logger = logging.getLogger(__name__)

TOKEN_VALIDITY_LIFETIME_S = 60 * 60  # 1 hour
SCOPE_REGEX_TEMPLATE = r"^repository:((?:{}\/)?((?:[\.a-zA-Z0-9_\-]+\/)*[\.a-zA-Z0-9_\-]+)):((?:push|pull|\*)(?:,(?:push|pull|\*))*)$"

scopeResult = namedtuple(
    "scopeResult", ["actions", "namespace", "repository", "registry_and_repo", "tuf_root"]
)


@v2_bp.route("/auth")
@process_basic_auth
@no_cache
@anon_protect
def registry_auth_token(auth_result):
    """
    This endpoint will generate a JWT conforming to the Docker Registry v2 Auth Spec:

    https://docs.docker.com/registry/spec/auth/token/
    """
    audience_param = request.args.get("service")
    logger.debug("Request audience: %s", audience_param)

    scope_params = request.args.getlist("scope") or []
    logger.debug("Scope request: %s", scope_params)

    auth_header = request.headers.get("authorization", "")
    auth_credentials_sent = bool(auth_header)

    logger.info(f'🔴 🔴 🔴 🔴 auth_credentials_sent {auth_credentials_sent}, audience_param {audience_param}, '
                f'scope_params {scope_params}')
    token = generate_registry_jwt(auth_result, auth_credentials_sent, audience_param, scope_params)

    return jsonify({"token": token})


def generate_registry_jwt(auth_result, auth_credentials_sent, audience_param, scope_params):
    # Load the auth context and verify that we've directly received credentials.
    has_valid_auth_context = False
    if get_authenticated_context():
        has_valid_auth_context = not get_authenticated_context().is_anonymous

    logger.info(f'🥐🥐🥐🥐🥐 has_valid_auth_context {has_valid_auth_context}')
    if auth_credentials_sent and not has_valid_auth_context:
        # The auth credentials sent for the user are invalid.
        raise InvalidLogin(auth_result.error_message)

    if not has_valid_auth_context and len(scope_params) == 0:
        # In this case, we are doing an auth flow, and it's not an anonymous pull.
        logger.debug("No user and no token sent for empty scope list")
        raise Unauthorized()

    # Build the access list for the authenticated context.
    access = []
    scope_results = []
    for scope_param in scope_params:
        scope_result = _authorize_or_downscope_request(scope_param, has_valid_auth_context)
        if scope_result is None:
            continue

        scope_results.append(scope_result)
        access.append(
            {
                "type": "repository",
                "name": scope_result.registry_and_repo,
                "actions": scope_result.actions,
            }
        )

    # Issue user events.
    user_event_data = {
        "action": "login",
    }

    # Set the user event data for when authed.
    if len(scope_results) > 0:
        if "push" in scope_results[0].actions:
            user_action = "push_start"
        elif "pull" in scope_results[0].actions:
            user_action = "pull_start"
        else:
            user_action = "login"

        user_event_data = {
            "action": user_action,
            "namespace": scope_results[0].namespace,
            "repository": scope_results[0].repository,
        }

    # determine if this is solely a login event
    # need to use scope_params here since scope_results could be empty in case of lack of permissions
    is_login_event = user_event_data["action"] == "login" and len(scope_params) == 0

    # Send the user event.
    user = get_authenticated_user()
    if user is not None:
        if is_login_event and app.config.get("ACTION_LOG_AUDIT_LOGINS"):
            metadata = {}
            context = get_authenticated_context()

            if context.appspecifictoken is not None:
                metadata["kind"] = "app_specific_token"
                metadata["app_specific_token_title"] = context.appspecifictoken.title

            if context.robot is not None:
                metadata["kind"] = "robot"
                metadata["robot"] = context.robot.username

            if context.user is not None:
                metadata["kind"] = "user"

            metadata["type"] = "v2auth"
            metadata["useragent"] = request.user_agent.string

            log_action(
                "login_success",
                user.username if not user.robot else parse_robot_username(user.username)[0],
                metadata=metadata,
            )
        event = userevents.get_event(user.username)
        event.publish_event_data("docker-cli", user_event_data)

    # Build the signed JWT.
    tuf_roots = {
        "%s/%s" % (scope_result.namespace, scope_result.repository): scope_result.tuf_root
        for scope_result in scope_results
    }
    context, subject = build_context_and_subject(get_authenticated_context(), tuf_roots=tuf_roots)
    token = generate_bearer_token(
        audience_param, subject, context, access, TOKEN_VALIDITY_LIFETIME_S, instance_keys
    )
    return token


@lru_cache(maxsize=1)
def _get_scope_regex():
    hostname = re.escape(app.config["SERVER_HOSTNAME"])
    scope_regex_string = SCOPE_REGEX_TEMPLATE.format(hostname)
    return re.compile(scope_regex_string)


def _get_tuf_root(repository_ref, namespace, reponame):
    if not features.SIGNING or repository_ref is None or not repository_ref.trust_enabled:
        return DISABLED_TUF_ROOT

    # Users with write access to a repository will see signer-rooted TUF metadata
    if ModifyRepositoryPermission(namespace, reponame).can():
        return SIGNER_TUF_ROOT
    return QUAY_TUF_ROOT


def validate_repository_name(namespace, reponame, namespace_and_repo):
    # Ensure that we are never creating an invalid repository.
    if features.EXTENDED_REPOSITORY_NAMES:
        if not REPOSITORY_NAME_EXTENDED_REGEX.match(reponame):
            logger.debug("Found invalid repository name in auth flow: %s", reponame)
            raise NameInvalid(message="Invalid repository name: %s" % namespace_and_repo)
    else:
        if not REPOSITORY_NAME_REGEX.match(reponame):
            logger.debug("Found invalid repository name in auth flow: %s", reponame)
            if len(namespace_and_repo.split("/")) > 1:
                msg = "Nested repositories are not supported. Found: %s" % namespace_and_repo
                raise NameInvalid(message=msg)

            raise NameInvalid(message="Invalid repository name: %s" % namespace_and_repo)


def ensure_namespace_enabled(namespace):
    # Ensure the namespace is enabled.
    if registry_model.is_existing_disabled_namespace(namespace):
        msg = "Namespace %s has been disabled. Please contact a system administrator." % namespace
        raise NamespaceDisabled(message=msg)


def validate_repository_state(repository_ref):
    if not repository_ref:
        return

    # if repository_ref is not None and repository_ref.kind != "image":
    #     raise Unsupported(message="Cannot push/pull non-image repository")

    # Ensure the repository is not marked for deletion.
    if repository_ref is not None and repository_ref.state == RepositoryState.MARKED_FOR_DELETION:
        raise Unsupported(message="Unknown repository")


def validate_user_can_create_new_repo(namespace, reponame):
    pass


def ensure_repository_exists(user, namespace, reponame):
    repository_ref = registry_model.lookup_repository(namespace, reponame)
    namespace_ref = model.user.get_namespace_user(namespace)

    if not namespace_ref and not app.config.get("CREATE_NAMESPACE_ON_PUSH", False):
        raise Unsupported(message="Unknown namespace")

    if not repository_ref and features.RESTRICTED_USERS and usermanager.is_restricted_user(user.username):
        raise Unsupported(message="Restricted users cannot create repositories")

    if not repository_ref and not CreateRepositoryPermission(namespace).can():
        raise Unsupported(message="No permission to create repository")

    # if repository_ref is not None and repository_ref.kind != "image":
    #     raise Unsupported(message="Cannot administer non-image repository")

    try:
        if not namespace_ref and app.config.get("CREATE_NAMESPACE_ON_PUSH", False):
            model.organization.create_organization(
                namespace,
                ("+" + namespace + "@").join(user.email.split("@")),
                user,
                email_required=features.MAILING,
            )

        if not repository_ref:
            visibility = "private" if app.config.get("CREATE_PRIVATE_REPO_ON_PUSH", True) else "public"
            found = model.repository.get_or_create_repository(namespace, reponame, get_authenticated_user(),
                                                              visibility=visibility)

            repository_ref = RepositoryReference.for_repo_obj(found)

    except model.DataModelException as ex:
        logger.exception("Failed to create repository %s/%s", namespace, reponame)
        raise Unsupported(message="Cannot create repository")

    return repository_ref


def _authorize_or_downscope_request(scope_param, has_valid_auth_context):
    # TODO: The complexity of this function is difficult to follow and maintain. Refactor/Cleanup.
    logger.info(f'🟣🟣🟣🟣scope_param {scope_param}, has_valid_auth_context {has_valid_auth_context}')
    if len(scope_param) == 0:
        if not has_valid_auth_context:
            # In this case, we are doing an auth flow, and it's not an anonymous pull.
            logger.debug("No user and no token sent for empty scope list")
            raise Unauthorized()

        return None

    match = _get_scope_regex().match(scope_param)
    if match is None:
        logger.debug("Match: %s", match)
        logger.debug("len: %s", len(scope_param))
        logger.warning("Unable to decode repository and actions: %s", scope_param)
        raise InvalidRequest("Unable to decode repository and actions: %s" % scope_param)

    logger.debug("Match: %s", match.groups())

    registry_and_repo = match.group(1)
    namespace_and_repo = match.group(2)
    requested_actions = match.group(3).split(",")

    lib_namespace = app.config["LIBRARY_NAMESPACE"]
    namespace, reponame = parse_namespace_repository(namespace_and_repo, lib_namespace)
    logger.info(f'🟣🟣🟣🟣 namespace {namespace}, reponame {reponame}, registry_and_repo {registry_and_repo}')

    validate_repository_name(namespace, reponame, namespace_and_repo)
    ensure_namespace_enabled(namespace)

    repository_ref = registry_model.lookup_repository(namespace, reponame)
    validate_repository_state(repository_ref)

    repo_is_public = repository_ref is not None and repository_ref.is_public
    final_actions = []

    if "push" in requested_actions:
        # Check if there is a valid user or token, as otherwise the repository cannot be
        # accessed.
        if has_valid_auth_context:
            user = get_authenticated_user()
            logger.info(
                f'🟣🟣🟣🟣 user {user} can create repo {CreateRepositoryPermission(namespace).can()} identity {g.identity}')

            # Lookup the repository. If it exists, make sure the entity has modify
            # permission. Otherwise, make sure the entity has create permission.

            repository_ref = ensure_repository_exists(user, namespace, reponame)
            if not ModifyRepositoryPermission(namespace, reponame).can():
                raise Unsupported(message="No permission to modify repository")

            # Check for different repository states.
            if repository_ref.state == RepositoryState.NORMAL:
                # In NORMAL mode, if the user has permission, then they can push.
                final_actions.append("push")
            elif repository_ref.state == RepositoryState.MIRROR:
                # In MIRROR mode, only the mirroring robot can push.
                mirror = model.repo_mirror.get_mirror(repository_ref.id)
                robot = mirror.internal_robot if mirror is not None else None
                if robot is not None and user is not None and robot == user:
                    assert robot.robot
                    final_actions.append("push")
                else:
                    logger.debug(
                        "Repository %s/%s push requested for non-mirror robot %s: %s",
                        namespace,
                        reponame,
                        robot,
                        user,
                    )
            elif repository_ref.state == RepositoryState.READ_ONLY:
                # No pushing allowed in read-only state.
                pass
            else:
                logger.warning(
                    "Unknown state for repository %s: %s",
                    repository_ref,
                    repository_ref.state,
                )

    if "pull" in requested_actions:
        user = None
        if (features.PROXY_CACHE or features.SUPER_USERS) and has_valid_auth_context:
            user = get_authenticated_user()

        can_pullthru = False
        if features.PROXY_CACHE and model.proxy_cache.has_proxy_cache_config(namespace):
            can_pullthru = OrganizationMemberPermission(namespace).can() and user is not None

        global_readonly_superuser = False
        if features.SUPER_USERS and user is not None:
            global_readonly_superuser = usermanager.is_global_readonly_superuser(user.username)

        if (
                ReadRepositoryPermission(namespace, reponame).can()
                or can_pullthru
                or repo_is_public
                or global_readonly_superuser
        ):
            final_actions.append("pull")
        else:
            logger.debug("No permission to pull repository %s/%s", namespace, reponame)

    if "*" in requested_actions:
        # Grant * user is admin
        user = get_authenticated_user()
        repository_ref = ensure_repository_exists(user, namespace, reponame)
        if AdministerRepositoryPermission(namespace, reponame).can():
            if repository_ref.state in (RepositoryState.MIRROR, RepositoryState.READ_ONLY):
                logger.debug("No permission to administer repository %s/%s", namespace, reponame)
            else:
                assert repository_ref.state == RepositoryState.NORMAL
                final_actions.append("*")
        else:
            logger.debug("No permission to administer repository %s/%s", namespace, reponame)

    # Final sanity checks.
    if "push" in final_actions:
        assert repository_ref.state != RepositoryState.READ_ONLY

    if "*" in final_actions:
        assert repository_ref.state == RepositoryState.NORMAL

    return scopeResult(
        actions=final_actions,
        namespace=namespace,
        repository=reponame,
        registry_and_repo=registry_and_repo,
        tuf_root=_get_tuf_root(repository_ref, namespace, reponame),
    )
