import logging

from functools import wraps

from flask import Blueprint, make_response, jsonify

import features

from app import app
from data.readreplica import ReadOnlyModeException
from endpoints.decorators import anon_protect, anon_allowed
from util.http import abort
from util.metrics.prometheus import timed_blueprint


logger = logging.getLogger(__name__)
v1_bp = timed_blueprint(Blueprint("v1", __name__))


# Note: This is *not* part of the Docker index spec. This is here for our own health check,
# since we have nginx handle the _ping below.
@v1_bp.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)


@v1_bp.route("/_ping")
@anon_allowed
def ping():
    # NOTE: any changes made here must also be reflected in the nginx config
    response = make_response("true", 200)
    response.headers["X-Docker-Registry-Version"] = "0.6.0"
    response.headers["X-Docker-Registry-Standalone"] = "0"
    return response


@v1_bp.app_errorhandler(ReadOnlyModeException)
def handle_readonly(ex):
    response = jsonify(
        {
            "message": "System is currently read-only. Pulls will succeed but all "
            + "write operations are currently suspended.",
            "is_readonly": True,
        }
    )
    response.status_code = 503
    return response


def check_v1_push_enabled(namespace_name_kwarg="namespace_name"):
    """
    Decorator which checks if V1 push is enabled for the current namespace.

    The first argument to the wrapped function must be the namespace name or there must be a kwarg
    with the name `namespace_name`.
    """

    def wrapper(wrapped):
        @wraps(wrapped)
        def decorated(*args, **kwargs):
            if namespace_name_kwarg in kwargs:
                namespace_name = kwargs[namespace_name_kwarg]
            else:
                namespace_name = args[0]

            if features.RESTRICTED_V1_PUSH:
                whitelist = app.config.get("V1_PUSH_WHITELIST") or []
                logger.debug("V1 push is restricted to whitelist: %s", whitelist)
                if namespace_name not in whitelist:
                    abort(
                        405,
                        message=(
                            "V1 push support has been deprecated. To enable for this "
                            + "namespace, please contact support."
                        ),
                    )

            return wrapped(*args, **kwargs)

        return decorated

    return wrapper


from endpoints.v1 import (
    index,
    registry,
    tag,
)
