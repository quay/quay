import logging

from flask import Blueprint, request

from app import app, instance_keys
from auth.decorators import process_federated_auth
from data.model import InvalidRobotCredentialException, InvalidRobotException
from data.model.user import (
    TMP_ROBOT_TOKEN_VALIDITY_LIFETIME_S,
    generate_federated_robot_jwt_token,
    generate_temp_robot_jwt_token,
)
from util.security.federated_rate_limit import (
    TokenExchangeRateLimitExceeded,
    TokenExchangeRateLimitUnavailable,
    check_token_exchange_rate_limit,
)
from util.security.federated_robot_auth import (
    parse_federated_robot_resource,
    resolve_federation_scope,
    validate_federated_robot_subject_token,
)

logger = logging.getLogger(__name__)
federation_bp = Blueprint("federation", __name__)
sts_bp = Blueprint("sts_token_exchange", __name__)

TOKEN_EXCHANGE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:jwt"
ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
MAX_TOKEN_EXCHANGE_REQUEST_BYTES = 32 * 1024
MAX_SUBJECT_TOKEN_LENGTH = 24 * 1024


@federation_bp.route("/federation/robot/token")
@process_federated_auth
def auth_federated_robot_identity(auth_result):
    """
    Authenticates the request using the robot identity federation mechanism.
    and returns a robot temp token.
    """
    if auth_result.missing or auth_result.error_message:
        return {
            "error": auth_result.error_message if auth_result.error_message else "missing auth"
        }, 401

    robot = auth_result.context.robot
    assert robot

    # Preserve the original registry-only federation contract. Federated
    # Management API tokens are issued exclusively by the STS endpoint.
    return {"token": generate_temp_robot_jwt_token(instance_keys)}


def _oauth_error(error):
    return {"error": error}, 400


@sts_bp.route("/sts/token", methods=["POST"])
def exchange_federated_robot_subject_token():
    """Exchanges an external OIDC JWT for a short-lived federated robot JWT."""
    if request.mimetype != "application/x-www-form-urlencoded":
        return _oauth_error("invalid_request")
    if (
        request.content_length is not None
        and request.content_length > MAX_TOKEN_EXCHANGE_REQUEST_BYTES
    ):
        return _oauth_error("invalid_request")

    form = request.form
    required = ("grant_type", "subject_token", "subject_token_type", "resource")
    if any(not form.get(parameter) for parameter in required):
        return _oauth_error("invalid_request")
    if len(form["subject_token"]) > MAX_SUBJECT_TOKEN_LENGTH:
        return _oauth_error("invalid_request")

    if form["grant_type"] != TOKEN_EXCHANGE_GRANT_TYPE:
        return _oauth_error("unsupported_grant_type")
    if form["subject_token_type"] != JWT_TOKEN_TYPE:
        return _oauth_error("invalid_request")

    requested_token_type = form.get("requested_token_type")
    if requested_token_type and requested_token_type != ACCESS_TOKEN_TYPE:
        return _oauth_error("invalid_request")

    try:
        robot_username = parse_federated_robot_resource(form["resource"])
    except InvalidRobotCredentialException:
        return _oauth_error("invalid_target")

    try:
        check_token_exchange_rate_limit(
            app.config["USER_EVENTS_REDIS"],
            request.remote_addr,
            robot_username,
            app.config["FEDERATED_ROBOT_TOKEN_EXCHANGE_RATE_LIMIT"],
            app.config["FEDERATED_ROBOT_TOKEN_EXCHANGE_RATE_LIMIT_WINDOW_SECONDS"],
        )
    except TokenExchangeRateLimitExceeded as error:
        return {"error": "slow_down"}, 429, {"Retry-After": str(error.retry_after)}
    except TokenExchangeRateLimitUnavailable:
        return {"error": "temporarily_unavailable"}, 503

    try:
        robot, binding = validate_federated_robot_subject_token(
            robot_username, form["subject_token"]
        )
    except InvalidRobotException:
        return _oauth_error("invalid_target")
    except InvalidRobotCredentialException:
        return _oauth_error("invalid_grant")

    try:
        effective_scope = resolve_federation_scope(binding, form.get("scope"))
    except InvalidRobotCredentialException:
        return _oauth_error("invalid_grant")

    token = generate_federated_robot_jwt_token(instance_keys, robot, effective_scope, binding)
    return {
        "access_token": token,
        "issued_token_type": ACCESS_TOKEN_TYPE,
        "token_type": "Bearer",
        "expires_in": TMP_ROBOT_TOKEN_VALIDITY_LIFETIME_S,
        "scope": effective_scope,
    }
