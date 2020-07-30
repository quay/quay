import logging
import os
import base64
import hmac

from functools import wraps
from flask import session, request, Response

import features

from app import app
from auth.auth_context import get_validated_oauth_token
from util.http import abort


logger = logging.getLogger(__name__)

OAUTH_CSRF_TOKEN_NAME = "_oauth_csrf_token"
_QUAY_CSRF_TOKEN_NAME = "_csrf_token"
_QUAY_CSRF_HEADER_NAME = "X-CSRF-Token"

QUAY_CSRF_UPDATED_HEADER_NAME = "X-Next-CSRF-Token"


def generate_csrf_token(session_token_name=_QUAY_CSRF_TOKEN_NAME, force=False):
    """
    If not present in the session, generates a new CSRF token with the given name and places it into
    the session.

    Returns the generated token.
    """
    if session_token_name not in session or force:
        session[session_token_name] = base64.urlsafe_b64encode(os.urandom(48)).decode("utf-8")

    return session[session_token_name]


def verify_csrf(
    session_token_name=_QUAY_CSRF_TOKEN_NAME,
    request_token_name=_QUAY_CSRF_TOKEN_NAME,
    check_header=True,
):
    """
    Verifies that the CSRF token with the given name is found in the session and that the matching
    token is found in the request args or values.
    """
    token = str(session.get(session_token_name, ""))
    found_token = str(request.values.get(request_token_name, ""))
    if check_header and not found_token:
        found_token = str(request.headers.get(_QUAY_CSRF_HEADER_NAME, ""))

    if not token or not found_token or not hmac.compare_digest(token, found_token):
        msg = "CSRF Failure. Session token (%s) was %s and request token (%s) was %s"
        logger.error(msg, session_token_name, token, request_token_name, found_token)
        abort(403, message="CSRF token was invalid or missing.")


def csrf_protect(
    session_token_name=_QUAY_CSRF_TOKEN_NAME,
    request_token_name=_QUAY_CSRF_TOKEN_NAME,
    all_methods=False,
    check_header=True,
):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Verify the CSRF token.
            if get_validated_oauth_token() is None:
                if all_methods or (request.method != "GET" and request.method != "HEAD"):
                    verify_csrf(session_token_name, request_token_name, check_header)

            # Invoke the handler.
            resp = func(*args, **kwargs)
            return resp

        return wrapper

    return inner


app.jinja_env.globals["csrf_token"] = generate_csrf_token
