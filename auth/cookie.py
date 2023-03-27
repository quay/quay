import logging

from uuid import UUID
from flask_login import current_user

from auth.validateresult import AuthKind, ValidateResult

logger = logging.getLogger(__name__)


def validate_session_cookie(auth_header_unusued=None):
    """
    Attempts to load a user from a session cookie.
    """
    if current_user.is_anonymous:
        return ValidateResult(AuthKind.cookie, missing=True)

    try:
        # Attempt to parse the user uuid to make sure the cookie has the right value type
        UUID(current_user.get_id())
    except ValueError:
        logger.debug("Got non-UUID for session cookie user: %s", current_user.get_id())
        return ValidateResult(AuthKind.cookie, error_message="Invalid session cookie format")

    logger.debug("Loading user from cookie: %s", current_user.get_id())
    db_user = current_user.db_user()
    if db_user is None:
        return ValidateResult(AuthKind.cookie, error_message="Could not find matching user")

    # Don't allow disabled users to login.
    if not db_user.enabled:
        logger.debug("User %s in session cookie is disabled", db_user.username)
        return ValidateResult(AuthKind.cookie, error_message="User account is disabled")

    # Don't allow organizations to "login".
    if db_user.organization:
        logger.debug("User %s in session cookie is in-fact organization", db_user.username)
        return ValidateResult(AuthKind.cookie, error_message="Cannot login to organization")

    return ValidateResult(AuthKind.cookie, user=db_user)
