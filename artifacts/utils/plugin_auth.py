import logging

from auth.decorators import authentication_count
from flask import abort, jsonify

logger = logging.getLogger(__name__)


def apply_auth_result(auth_result):
    if not auth_result:
        return abort(401, message=jsonify('Invalid username or password'))

    if auth_result.auth_valid:
        logger.debug("Found valid auth result: %s", auth_result.tuple())

        # Set the various pieces of the auth context.
        auth_result.apply_to_context()

        # Log the metric.
        authentication_count.labels(auth_result.kind, True).inc()

    # Otherwise, report the error.
    if auth_result.error_message is not None:
        # Log the failure.
        authentication_count.labels(auth_result.kind, False).inc()
        # Do we only need to abort for JWT based errors?
        abort(401, message=auth_result.error_message)

