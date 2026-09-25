import json
import logging

from jwt import InvalidTokenError

import features
from app import app
from auth import scopes
from auth.basic import _parse_basic_auth_header
from auth.log import log_action
from auth.validateresult import AuthKind, ValidateResult
from data.database import FederatedLogin
from data.model import InvalidRobotCredentialException
from data.model.api_token import normalize_scope, validate_api_scope_string
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

    robot, binding = validate_federated_robot_subject_token(auth_username, federated_token)
    return ValidateResult(AuthKind.federated, robot=robot, federation_binding=binding)


def parse_federated_robot_resource(resource):
    """Returns the robot username encoded by a Quay federation resource URI."""
    prefix = "urn:quay:robot:"
    if not isinstance(resource, str) or not resource.startswith(prefix):
        raise InvalidRobotCredentialException("Invalid robot resource")

    robot_username = resource[len(prefix) :]
    if not robot_username or not parse_robot_username(robot_username):
        raise InvalidRobotCredentialException("Invalid robot resource")

    return robot_username


def validate_federated_robot_subject_token(robot_username, subject_token):
    """Validates an external subject token for the explicitly selected robot."""
    robot = lookup_robot(robot_username)
    result = verify_federated_robot_jwt_token(robot, subject_token)
    binding = result.context.federation_binding
    if not result.auth_valid or binding is None:
        raise InvalidRobotCredentialException("Token does not match robot")
    return robot, binding


def resolve_federation_scope(binding, requested_scope):
    """Returns the requested scope when it is a valid subset of the binding scope."""
    allowed_scope = normalize_scope(binding.get("api_scopes", ""))
    if allowed_scope and (
        not validate_api_scope_string(allowed_scope)
        or (
            scopes.SUPERUSER in scopes.scopes_from_scope_string(allowed_scope)
            and not features.SUPER_USERS
        )
    ):
        raise InvalidRobotCredentialException("Federation binding scope is not allowed")

    requested_scope = normalize_scope(requested_scope or "")
    if not requested_scope:
        return allowed_scope

    if not validate_api_scope_string(requested_scope) or not scopes.is_subset_string(
        allowed_scope, requested_scope
    ):
        raise InvalidRobotCredentialException("Requested scope is not allowed")
    return requested_scope


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

    issuer_bindings = [item for item in fed_config if item.get("issuer") == token_issuer]
    if not issuer_bindings:
        raise InvalidRobotCredentialException(
            f"issuer {token_issuer} not configured for this robot"
        )

    service_config = {
        "quayrobot": {
            "OIDC_SERVER": token_issuer,
            # Permit HTTP discovery only when Quay is explicitly running in debug mode.
            # Production federation remains HTTPS-only.
            "DEBUGGING": app.config.get("DEBUG", False),
        }
    }
    # The matching binding, including its audience policy, is selected after
    # signature and issuer validation based on the JWT subject.
    options = {"verify_aud": False, "verify_nbf": True}
    service = OIDCLoginService(service_config, "quayrobot", client=app.config["HTTPCLIENT"])

    try:
        decoded_token = service.decode_user_jwt(token, options=options)
    except InvalidTokenError as e:
        raise InvalidRobotCredentialException(f"Invalid token: {e}")

    assert decoded_token
    matches = [item for item in issuer_bindings if item.get("subject") == decoded_token.get("sub")]
    if len(matches) > 1:
        raise InvalidRobotCredentialException("Ambiguous federation binding for this robot")
    if not matches:
        raise InvalidRobotCredentialException("Token does not match robot")
    binding = matches[0]

    allowed_audiences = binding.get("audiences")
    if allowed_audiences:
        token_audience = decoded_token.get("aud", [])
        if isinstance(token_audience, str):
            token_audience = [token_audience]
        if not isinstance(token_audience, list) or not set(token_audience).intersection(
            allowed_audiences
        ):
            raise InvalidRobotCredentialException("Token audience is not allowed for this robot")
    else:
        logger.warning(
            "Federated robot '%s' authenticated without audience validation. "
            "Audience-less federation is deprecated and will be removed in a future release.",
            robot.username,
        )

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

    return ValidateResult(AuthKind.credentials, robot=robot, federation_binding=binding)
