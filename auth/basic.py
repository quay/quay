import logging

from base64 import b64decode
from flask import request

from auth.credentials import validate_credentials
from auth.validateresult import ValidateResult, AuthKind

logger = logging.getLogger(__name__)


def has_basic_auth(username):
    """
    Returns true if a basic auth header exists with a username and password pair that validates
    against the internal authentication system.

    Returns True on full success and False on any failure (missing header, invalid header, invalid
    credentials, etc).
    """
    auth_header = request.headers.get("authorization", "")
    result = validate_basic_auth(auth_header)
    return result.has_nonrobot_user and result.context.user.username == username


def validate_basic_auth(auth_header):
    """
    Validates the specified basic auth header, returning whether its credentials point to a valid
    user or token.
    """
    if not auth_header:
        return ValidateResult(AuthKind.basic, missing=True)

    logger.debug("Attempt to process basic auth header")

    # Parse the basic auth header.
    assert isinstance(auth_header, str)
    credentials, err = _parse_basic_auth_header(auth_header)
    if err is not None:
        logger.debug("Got invalid basic auth header: %s", auth_header)
        return ValidateResult(AuthKind.basic, missing=True)

    auth_username, auth_password_or_token = credentials
    result, _ = validate_credentials(auth_username, auth_password_or_token)
    return result.with_kind(AuthKind.basic)


def _parse_basic_auth_header(auth):
    """
    Parses the given basic auth header, returning the credentials found inside.
    """
    normalized = [part.strip() for part in auth.split(" ") if part]
    if normalized[0].lower() != "basic" or len(normalized) != 2:
        return None, "Invalid basic auth header"

    try:
        credentials = [part.decode("utf-8") for part in b64decode(normalized[1]).split(b":", 1)]
    except (TypeError, UnicodeDecodeError, ValueError):
        logger.exception("Exception when parsing basic auth header: %s", auth)
        return None, "Could not parse basic auth header"

    if len(credentials) != 2:
        return None, "Unexpected number of credentials found in basic auth header"

    return credentials, None
