import logging

from flask import Blueprint, request

from app import instance_keys
from auth.decorators import process_federated_auth
from auth.log import log_action
from data.model import InvalidRobotCredentialException, InvalidRobotException
from data.model.api_token import normalize_scope
from data.model.user import (
    TMP_ROBOT_TOKEN_VALIDITY_LIFETIME_S,
    generate_federated_robot_jwt_token,
    generate_temp_robot_jwt_token,
)
from util.names import parse_robot_username
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


def _log_exchange_result(result, requested_scope="", failure_reason=None, robot=None, binding=None):
    namespace = None
    metadata = {
        "result": result,
        "requested_scope": normalize_scope(requested_scope),
    }
    if failure_reason:
        metadata["failure_reason"] = failure_reason
    if robot is not None:
        namespace, robot_name = parse_robot_username(robot.username)
        metadata["robot"] = robot_name
    if binding is not None:
        metadata.update(
            {
                "subject": binding.get("subject"),
                "issuer": binding.get("issuer"),
                "federation_binding_id": binding.get("id"),
                "federation_binding_version": binding.get("version"),
            }
        )

    log_action("federated_robot_token_exchange", namespace, metadata)


def _oauth_error(error, failure_reason, requested_scope="", robot=None, binding=None):
    _log_exchange_result(
        "failure",
        requested_scope=requested_scope,
        failure_reason=failure_reason,
        robot=robot,
        binding=binding,
    )
    return {"error": error}, 400


@sts_bp.route("/sts/token", methods=["POST"])
def exchange_federated_robot_subject_token():
    """Exchanges an external OIDC JWT for a short-lived federated robot JWT."""
    if request.mimetype != "application/x-www-form-urlencoded":
        return _oauth_error("invalid_request", "unsupported_content_type")
    if (
        request.content_length is not None
        and request.content_length > MAX_TOKEN_EXCHANGE_REQUEST_BYTES
    ):
        return _oauth_error("invalid_request", "request_too_large")

    form = request.form
    required = ("grant_type", "subject_token", "subject_token_type", "resource")
    requested_scope = form.get("scope", "")
    if any(not form.get(parameter) for parameter in required):
        return _oauth_error("invalid_request", "missing_required_parameter", requested_scope)
    if len(form["subject_token"]) > MAX_SUBJECT_TOKEN_LENGTH:
        return _oauth_error("invalid_request", "subject_token_too_large", requested_scope)

    if form["grant_type"] != TOKEN_EXCHANGE_GRANT_TYPE:
        return _oauth_error("unsupported_grant_type", "unsupported_grant_type", requested_scope)
    if form["subject_token_type"] != JWT_TOKEN_TYPE:
        return _oauth_error("invalid_request", "unsupported_subject_token_type", requested_scope)

    requested_token_type = form.get("requested_token_type")
    if requested_token_type and requested_token_type != ACCESS_TOKEN_TYPE:
        return _oauth_error("invalid_request", "unsupported_requested_token_type", requested_scope)

    try:
        robot_username = parse_federated_robot_resource(form["resource"])
    except InvalidRobotCredentialException:
        return _oauth_error("invalid_target", "invalid_target", requested_scope)

    try:
        robot, binding = validate_federated_robot_subject_token(
            robot_username, form["subject_token"]
        )
    except InvalidRobotCredentialException:
        return _oauth_error("invalid_grant", "subject_token_rejected", requested_scope)
    except InvalidRobotException:
        return _oauth_error("invalid_target", "robot_not_found", requested_scope)

    try:
        effective_scope = resolve_federation_scope(binding, requested_scope)
    except InvalidRobotCredentialException:
        return _oauth_error(
            "invalid_grant",
            "scope_not_allowed",
            requested_scope,
            robot=robot,
            binding=binding,
        )

    token = generate_federated_robot_jwt_token(instance_keys, robot, effective_scope, binding)
    _log_exchange_result(
        "success",
        requested_scope=requested_scope,
        robot=robot,
        binding=binding,
    )
    return {
        "access_token": token,
        "issued_token_type": ACCESS_TOKEN_TYPE,
        "token_type": "Bearer",
        "expires_in": TMP_ROBOT_TOKEN_VALIDITY_LIFETIME_S,
        "scope": effective_scope,
    }
