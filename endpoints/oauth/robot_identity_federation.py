import logging

from flask import Blueprint

from app import instance_keys
from auth.decorators import process_basic_auth, process_federated_auth
from data import model
from data.database import RobotAccountToken
from data.model.user import generate_temp_robot_jwt_token, retrieve_robot_token
from util import request

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

    # generate a JWT based robot token instead of static
    token = generate_temp_robot_jwt_token(instance_keys)
    return {"token": token}
