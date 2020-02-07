import logging

from functools import wraps
from flask import request, session
from prometheus_client import Counter

from auth.basic import validate_basic_auth
from auth.oauth import validate_bearer_auth
from auth.cookie import validate_session_cookie
from auth.signedgrant import validate_signed_grant

from util.http import abort


logger = logging.getLogger(__name__)


authentication_count = Counter(
    "quay_authentication_attempts_total",
    "number of authentication attempts accross the registry and API",
    labelnames=["auth_kind", "success"],
)


def _auth_decorator(pass_result=False, handlers=None):
    """
    Builds an auth decorator that runs the given handlers and, if any return successfully, sets up
    the auth context.

    The wrapped function will be invoked *regardless of success or failure of the auth handler(s)*
    """

    def processor(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("authorization", "")
            result = None

            for handler in handlers:
                result = handler(auth_header)
                # If the handler was missing the necessary information, skip it and try the next one.
                if result.missing:
                    continue

                # Check for a valid result.
                if result.auth_valid:
                    logger.debug("Found valid auth result: %s", result.tuple())

                    # Set the various pieces of the auth context.
                    result.apply_to_context()

                    # Log the metric.
                    authentication_count.labels(result.kind, True).inc()
                    break

                # Otherwise, report the error.
                if result.error_message is not None:
                    # Log the failure.
                    authentication_count.labels(result.kind, False).inc()
                    break

            if pass_result:
                kwargs["auth_result"] = result

            return func(*args, **kwargs)

        return wrapper

    return processor


process_oauth = _auth_decorator(handlers=[validate_bearer_auth, validate_session_cookie])
process_auth = _auth_decorator(handlers=[validate_signed_grant, validate_basic_auth])
process_auth_or_cookie = _auth_decorator(handlers=[validate_basic_auth, validate_session_cookie])
process_basic_auth = _auth_decorator(handlers=[validate_basic_auth], pass_result=True)
process_basic_auth_no_pass = _auth_decorator(handlers=[validate_basic_auth])


def require_session_login(func):
    """
    Decorates a function and ensures that a valid session cookie exists or a 401 is raised.

    If a valid session cookie does exist, the authenticated user and identity are also set.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = validate_session_cookie()
        if result.has_nonrobot_user:
            result.apply_to_context()
            authentication_count.labels(result.kind, True).inc()
            return func(*args, **kwargs)
        elif not result.missing:
            authentication_count.labels(result.kind, False).inc()

        abort(401, message="Method requires login and no valid login could be loaded.")

    return wrapper


def extract_namespace_repo_from_session(func):
    """
    Extracts the namespace and repository name from the current session (which must exist) and
    passes them into the decorated function as the first and second arguments.

    If the session doesn't exist or does not contain these arugments, a 400 error is raised.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if "namespace" not in session or "repository" not in session:
            logger.error("Unable to load namespace or repository from session: %s", session)
            abort(400, message="Missing namespace in request")

        return func(session["namespace"], session["repository"], *args, **kwargs)

    return wrapper
