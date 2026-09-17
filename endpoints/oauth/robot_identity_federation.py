import logging

from flask import Blueprint, request

from app import instance_keys
from auth import scopes
from auth.decorators import process_basic_auth, process_federated_auth
from data import model
from data.database import RobotAccountToken
from data.model.api_token import normalize_scope, validate_api_scope_string
from data.model.user import generate_temp_robot_jwt_token, retrieve_robot_token

logger = logging.getLogger(__name__)
federation_bp = Blueprint("federation", __name__)


@federation_bp.route("/federation/robot/token")
@process_federated_auth
def auth_federated_robot_identity(auth_result):
    """
    Authenticates the request using the robot identity federation mechanism.
    and returns a robot temp token.
    """
    # robot is authenticated, return an expiring robot token
    if auth_result.missing or auth_result.error_message:
        return {
            "error": auth_result.error_message if auth_result.error_message else "missing auth"
        }, 401

    robot = auth_result.context.robot
    assert robot

    binding = getattr(auth_result.context, "federation_binding", None)
    allowed_scope = normalize_scope((binding or {}).get("api_scopes", ""))
    requested_scope = normalize_scope(request.args.get("scope", ""))
    if requested_scope:
        if not validate_api_scope_string(requested_scope) or not scopes.is_subset_string(
            allowed_scope, requested_scope
        ):
            return {"error": "Requested scope is not allowed for this federation binding"}, 400
        allowed_scope = requested_scope

    # API capability is opt-in: legacy bindings without api_scopes mint a
    # registry-only robot JWT.
    token = generate_temp_robot_jwt_token(instance_keys, allowed_scope, binding)
    return {"token": token}
