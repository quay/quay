"""
Various decorators for endpoint and API handlers.
"""

import os
import logging

from functools import wraps
from flask import abort, request, make_response

import features

from app import app, ip_resolver, model_cache
from auth.auth_context import get_authenticated_context, get_authenticated_user
from data.database import RepositoryState
from data.model.repository import get_repository, get_repository_state
from data.model.repo_mirror import get_mirroring_robot, get_mirror
from data.registry_model import registry_model
from data.readreplica import ReadOnlyModeException
from util.names import parse_namespace_repository, ImplicitLibraryNamespaceNotAllowed
from util.http import abort
from util.request import get_request_ip

logger = logging.getLogger(__name__)


def parse_repository_name(
    include_tag=False,
    ns_kwarg_name="namespace_name",
    repo_kwarg_name="repo_name",
    tag_kwarg_name="tag_name",
    incoming_repo_kwarg="repository",
):
    """
    Decorator which parses the repository name found in the incoming_repo_kwarg argument, and
    applies its pieces to the decorated function.
    """

    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                repo_name_components = parse_namespace_repository(
                    kwargs[incoming_repo_kwarg],
                    app.config["LIBRARY_NAMESPACE"],
                    include_tag=include_tag,
                    allow_library=features.LIBRARY_SUPPORT,
                )
            except ImplicitLibraryNamespaceNotAllowed:
                abort(400, message="A namespace must be specified explicitly")

            del kwargs[incoming_repo_kwarg]
            kwargs[ns_kwarg_name] = repo_name_components[0]
            kwargs[repo_kwarg_name] = repo_name_components[1]
            if include_tag:
                kwargs[tag_kwarg_name] = repo_name_components[2]
            return func(*args, **kwargs)

        return wrapper

    return inner


def param_required(param_name, allow_body=False):
    """
    Marks a route as requiring a parameter with the given name to exist in the request's arguments
    or (if allow_body=True) in its body values.

    If the parameter is not present, the request will fail with a 400.
    """

    def wrapper(wrapped):
        @wraps(wrapped)
        def decorated(*args, **kwargs):
            if param_name not in request.args:
                if not allow_body or param_name not in request.values:
                    abort(400, message="Required param: %s" % param_name)
            return wrapped(*args, **kwargs)

        return decorated

    return wrapper


def readonly_call_allowed(func):
    """
    Marks a method as allowing for invocation when the registry is in a read only state.

    Only necessary on non-GET methods.
    """
    func.__readonly_call_allowed = True
    return func


def anon_allowed(func):
    """
    Marks a method to allow anonymous access where it would otherwise be disallowed.
    """
    func.__anon_allowed = True
    return func


def anon_protect(func):
    """
    Marks a method as requiring some form of valid user auth before it can be executed.
    """
    func.__anon_protected = True
    return check_anon_protection(func)


def check_anon_protection(func):
    """
    Validates a method as requiring some form of valid user auth before it can be executed.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Skip if anonymous access is allowed.
        if features.ANONYMOUS_ACCESS or "__anon_allowed" in dir(func):
            return func(*args, **kwargs)

        # Check for validated context. If none exists, fail with a 401.
        if get_authenticated_context() and not get_authenticated_context().is_anonymous:
            return func(*args, **kwargs)

        abort(401, message="Anonymous access is not allowed")

    return wrapper


def check_readonly(func):
    """
    Validates that a non-GET method is not invoked when the registry is in read-only mode, unless
    explicitly marked as being allowed.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Skip if a GET method.
        if request.method == "GET":
            return func(*args, **kwargs)

        # Skip if not in read only mode.
        if app.config.get("REGISTRY_STATE", "normal") != "readonly":
            return func(*args, **kwargs)

        # Skip if readonly access is allowed.
        if hasattr(func, "__readonly_call_allowed"):
            return func(*args, **kwargs)

        raise ReadOnlyModeException()

    return wrapper


def route_show_if(value):
    """
    Adds/shows the decorated route if the given value is True.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not value:
                abort(404)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_xhr_from_browser(func):
    """
    Requires that API GET calls made from browsers are made via XHR, in order to prevent reflected
    text attacks.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if app.config.get("BROWSER_API_CALLS_XHR_ONLY", False):
            if request.method == "GET" and request.user_agent.browser:
                has_xhr_header = request.headers.get("X-Requested-With") == "XMLHttpRequest"
                if not has_xhr_header and not app.config.get("DEBUGGING") == True:
                    logger.warning(
                        "Disallowed possible RTA to URL %s with user agent %s",
                        request.path,
                        request.user_agent,
                    )
                    abort(
                        400,
                        message="API calls must be invoked with an X-Requested-With header "
                        + "if called from a browser",
                    )

        return func(*args, **kwargs)

    return wrapper


def check_region_blacklisted(error_class=None, namespace_name_kwarg=None):
    """
    Decorator which checks if the incoming request is from a region geo IP blocked for the current
    namespace.

    The first argument to the wrapped function must be the namespace name.
    """

    def wrapper(wrapped):
        @wraps(wrapped)
        def decorated(*args, **kwargs):
            if namespace_name_kwarg:
                namespace_name = kwargs[namespace_name_kwarg]
            else:
                namespace_name = args[0]

            region_blacklist = registry_model.get_cached_namespace_region_blacklist(
                model_cache, namespace_name
            )
            if region_blacklist:
                # Resolve the IP information and block if on the namespace's blacklist.
                remote_ip = get_request_ip()
                resolved_ip_info = ip_resolver.resolve_ip(remote_ip)
                logger.debug("Resolved IP information for IP %s: %s", remote_ip, resolved_ip_info)

                if (
                    resolved_ip_info
                    and resolved_ip_info.country_iso_code
                    and resolved_ip_info.country_iso_code in region_blacklist
                ):
                    if error_class:
                        raise error_class()

                    abort(403, "Pulls of this data have been restricted geographically")

            return wrapped(*args, **kwargs)

        return decorated

    return wrapper


def check_repository_state(f):
    @wraps(f)
    def wrapper(namespace_name, repo_name, *args, **kwargs):
        """
        Conditionally allow changes depending on the Repository's state.

        NORMAL    -> Pass READ_ONLY -> Block all POST/PUT/DELETE MIRROR    -> Same as READ_ONLY,
        except treat the Mirroring Robot User as Normal MARKED_FOR_DELETION -> Block everything as a
        404
        """
        user = get_authenticated_user()
        if user is None:
            # NOTE: Remaining auth checks will be handled by subsequent decorators.
            return f(namespace_name, repo_name, *args, **kwargs)

        repository = get_repository(namespace_name, repo_name)
        if not repository:
            return f(namespace_name, repo_name, *args, **kwargs)

        if repository.state == RepositoryState.MARKED_FOR_DELETION:
            abort(404)

        if repository.state == RepositoryState.READ_ONLY:
            abort(405, "%s/%s is in read-only mode." % (namespace_name, repo_name))

        if repository.state == RepositoryState.MIRROR:
            mirror = get_mirror(repository)
            robot = mirror.internal_robot if mirror is not None else None

            if mirror is None:
                abort(
                    500,
                    "Repository %s/%s is set as a mirror but the Mirror configuration is missing."
                    % (namespace_name, repo_name),
                )

            elif robot is None:
                abort(
                    400,
                    "Repository %s/%s is configured for mirroring but no robot is assigned."
                    % (namespace_name, repo_name),
                )

            elif user.id != robot.id:
                abort(
                    405,
                    "Repository %s/%s is a mirror. Mirrored repositories cannot be modified directly."
                    % (namespace_name, repo_name),
                )

            elif user.id == robot.id:
                pass  # User is designated robot for this mirror repo.

            else:
                msg = (
                    "An internal error has occurred while verifying repository %s/%s state. Please report "
                    "this to an administrator."
                ) % (namespace_name, repo_name)
                raise Exception(msg)

        return f(namespace_name, repo_name, *args, **kwargs)

    return wrapper
