import logging
import json

from flask import request, make_response, current_app
from werkzeug.exceptions import HTTPException

from app import analytics
from auth.auth_context import get_authenticated_context

logger = logging.getLogger(__name__)


DEFAULT_MESSAGE = {}
DEFAULT_MESSAGE[400] = "Invalid Request"
DEFAULT_MESSAGE[401] = "Unauthorized"
DEFAULT_MESSAGE[403] = "Permission Denied"
DEFAULT_MESSAGE[404] = "Not Found"
DEFAULT_MESSAGE[409] = "Conflict"
DEFAULT_MESSAGE[501] = "Not Implemented"


def _abort(status_code, data_object, description, headers):
    # Add CORS headers to all errors
    options_resp = current_app.make_default_options_response()
    headers["Access-Control-Allow-Origin"] = "*"
    headers["Access-Control-Allow-Methods"] = options_resp.headers["allow"]
    headers["Access-Control-Max-Age"] = str(21600)
    headers["Access-Control-Allow-Headers"] = ["Authorization", "Content-Type"]

    resp = make_response(json.dumps(data_object), status_code, headers)

    # Report the abort to the user.
    # Raising HTTPException as workaround for https://github.com/pallets/werkzeug/issues/1098
    new_exception = HTTPException(response=resp, description=description)
    new_exception.code = status_code
    raise new_exception


def exact_abort(status_code, message=None):
    data = {}

    if message is not None:
        data["error"] = message

    _abort(status_code, data, message or None, {})


def abort(status_code, message=None, issue=None, headers=None, **kwargs):
    message = str(message) % kwargs if message else DEFAULT_MESSAGE.get(status_code, "")

    params = dict(request.view_args or {})
    params.update(kwargs)

    params["url"] = request.url
    params["status_code"] = status_code
    params["message"] = message

    # Add the user information.
    auth_context = get_authenticated_context()
    if auth_context is not None:
        message = "%s (authorized: %s)" % (message, auth_context.description)

    # Log the abort.
    logger.error("Error %s: %s; Arguments: %s" % (status_code, message, params))

    # Create the final response data and message.
    data = {}
    data["error"] = message

    if headers is None:
        headers = {}

    _abort(status_code, data, message, headers)
