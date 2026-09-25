import logging

from flask import Blueprint, request

from app import instance_keys
from auth.decorators import process_federated_auth
from data.model import InvalidRobotCredentialException, InvalidRobotException
from data.model.user import (
    TMP_ROBOT_TOKEN_VALIDITY_LIFETIME_S,
    generate_federated_robot_jwt_token,
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

    try:
        allowed_scope = resolve_federation_scope(
            auth_result.context.federation_binding, request.args.get("scope")
        )
    except InvalidRobotCredentialException:
        return {"error": "Requested scope is not allowed for this federation binding"}, 400

    token = generate_federated_robot_jwt_token(
        instance_keys, robot, allowed_scope, auth_result.context.federation_binding
    )
    return {"token": token}


def _oauth_error(error):
    return {"error": error}, 400


@sts_bp.route("/sts/token", methods=["POST"])
def exchange_federated_robot_subject_token():
    """Exchanges an external OIDC JWT for a short-lived federated robot JWT."""
    if request.mimetype != "application/x-www-form-urlencoded":
        return _oauth_error("invalid_request")

    form = request.form
    required = ("grant_type", "subject_token", "subject_token_type", "resource")
    if any(not form.get(parameter) for parameter in required):
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
