import json
import logging

from jwt import InvalidTokenError

from app import app
from auth.basic import _parse_basic_auth_header
from auth.log import log_action
from auth.validateresult import AuthKind, ValidateResult
from data.database import FederatedLogin
from data.model import InvalidRobotCredentialException
from data.model.user import lookup_robot
from oauth.login_utils import get_jwt_issuer
from oauth.oidc import OIDCLoginService
from util.names import parse_robot_username

logger = logging.getLogger(__name__)


def validate_federated_auth(auth_header):
    """
    Validates the specified federated auth header, returning whether its credentials point to a valid
    user or token.
    """
    if not auth_header:
        return ValidateResult(AuthKind.federated, missing=True, error_message="No auth header")

    logger.debug("Attempt to process federated auth header")

    # Parse the federated auth header.
    assert isinstance(auth_header, str)
    credentials, err = _parse_basic_auth_header(auth_header)
    if err is not None:
        logger.debug("Got invalid federated auth header: %s", auth_header)
        return ValidateResult(AuthKind.federated, missing=True, error_message=err)

    auth_username, federated_token = credentials

    is_robot = parse_robot_username(auth_username)
    if not is_robot:
        logger.debug(
            f"Federated auth is only supported for robots. got invalid federated auth header: {auth_header}"
        )
        return ValidateResult(AuthKind.federated, missing=True, error_message="Invalid robot")

    # find out if the robot is federated
    # get the issuer from the DB config
    # validate the token
    robot = lookup_robot(auth_username)
    assert robot.robot

    result = verify_federated_robot_jwt_token(robot, federated_token)
    return result.with_kind(AuthKind.federated)


def verify_federated_robot_jwt_token(robot, token):
    # The token is a JWT token from the external OIDC provider
    # We always have an entry in the federatedlogin table for each robot account
    federated_robot = FederatedLogin.select().where(FederatedLogin.user == robot).get()
    assert federated_robot

    try:
        metadata = json.loads(federated_robot.metadata_json)
    except Exception as e:
        logger.debug("Error parsing federated login metadata: %s", e)
        raise InvalidRobotCredentialException("Robot does not have federated login configured")

    # check if robot has federated login config
    token_issuer = get_jwt_issuer(token)
    if not token_issuer:
        raise InvalidRobotCredentialException("Token does not contain issuer")

    fed_config = metadata.get("federation_config", [])
    if not fed_config:
        raise InvalidRobotCredentialException("Robot does not have federated login configured")

    matched_subs = []
    for item in fed_config:
        if item.get("issuer") == token_issuer:
            matched_subs.append(item.get("subject"))

    if not matched_subs:
        raise InvalidRobotCredentialException(
            f"issuer {token_issuer} not configured for this robot"
        )

    # verify the token
    service_config = {"quayrobot": {"OIDC_SERVER": token_issuer}}
    service = OIDCLoginService(service_config, "quayrobot", client=app.config["HTTPCLIENT"])

    # throws an exception if we cannot decode/verify the token
    options = {"verify_aud": False, "verify_nbf": False}
    try:
        decoded_token = service.decode_user_jwt(token, options=options)
    except InvalidTokenError as e:
        raise InvalidRobotCredentialException(f"Invalid token: {e}")

    assert decoded_token
    # check if the token is for the robot

    if decoded_token.get("sub") not in matched_subs:
        raise InvalidRobotCredentialException("Token does not match robot")

    namespace, robot_name = parse_robot_username(robot.username)

    log_action(
        "federated_robot_token_exchange",
        namespace,
        {
            "subject": decoded_token.get("sub"),
            "issuer": decoded_token.get("iss"),
            "robot": robot_name,
        },
    )

    return ValidateResult(AuthKind.credentials, robot=robot)
