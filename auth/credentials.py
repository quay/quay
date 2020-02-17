import logging

from enum import Enum

import features

from app import authentication
from auth.oauth import validate_oauth_token
from auth.validateresult import ValidateResult, AuthKind
from auth.credential_consts import (
    ACCESS_TOKEN_USERNAME,
    OAUTH_TOKEN_USERNAME,
    APP_SPECIFIC_TOKEN_USERNAME,
)
from data import model
from util.names import parse_robot_username

logger = logging.getLogger(__name__)


class CredentialKind(Enum):
    user = "user"
    robot = "robot"
    token = ACCESS_TOKEN_USERNAME
    oauth_token = OAUTH_TOKEN_USERNAME
    app_specific_token = APP_SPECIFIC_TOKEN_USERNAME


def validate_credentials(auth_username, auth_password_or_token):
    """
    Validates a pair of auth username and password/token credentials.
    """
    # Check for access tokens.
    if auth_username == ACCESS_TOKEN_USERNAME:
        logger.debug("Found credentials for access token")
        try:
            token = model.token.load_token_data(auth_password_or_token)
            logger.debug("Successfully validated credentials for access token %s", token.id)
            return ValidateResult(AuthKind.credentials, token=token), CredentialKind.token
        except model.DataModelException:
            logger.warning(
                "Failed to validate credentials for access token %s", auth_password_or_token
            )
            return (
                ValidateResult(AuthKind.credentials, error_message="Invalid access token"),
                CredentialKind.token,
            )

    # Check for App Specific tokens.
    if features.APP_SPECIFIC_TOKENS and auth_username == APP_SPECIFIC_TOKEN_USERNAME:
        logger.debug("Found credentials for app specific auth token")
        token = model.appspecifictoken.access_valid_token(auth_password_or_token)
        if token is None:
            logger.debug(
                "Failed to validate credentials for app specific token: %s", auth_password_or_token
            )
            return (
                ValidateResult(AuthKind.credentials, error_message="Invalid token"),
                CredentialKind.app_specific_token,
            )

        if not token.user.enabled:
            logger.debug("Tried to use an app specific token for a disabled user: %s", token.uuid)
            return (
                ValidateResult(
                    AuthKind.credentials,
                    error_message="This user has been disabled. Please contact your administrator.",
                ),
                CredentialKind.app_specific_token,
            )

        logger.debug("Successfully validated credentials for app specific token %s", token.id)
        return (
            ValidateResult(AuthKind.credentials, appspecifictoken=token),
            CredentialKind.app_specific_token,
        )

    # Check for OAuth tokens.
    if auth_username == OAUTH_TOKEN_USERNAME:
        return validate_oauth_token(auth_password_or_token), CredentialKind.oauth_token

    # Check for robots and users.
    is_robot = parse_robot_username(auth_username)
    if is_robot:
        logger.debug("Found credentials header for robot %s", auth_username)
        try:
            robot = model.user.verify_robot(auth_username, auth_password_or_token)
            logger.debug("Successfully validated credentials for robot %s", auth_username)
            return ValidateResult(AuthKind.credentials, robot=robot), CredentialKind.robot
        except model.InvalidRobotException as ire:
            logger.warning("Failed to validate credentials for robot %s: %s", auth_username, ire)
            return (
                ValidateResult(AuthKind.credentials, error_message=str(ire)),
                CredentialKind.robot,
            )

    # Otherwise, treat as a standard user.
    (authenticated, err) = authentication.verify_and_link_user(
        auth_username, auth_password_or_token, basic_auth=True
    )
    if authenticated:
        logger.debug("Successfully validated credentials for user %s", authenticated.username)
        return ValidateResult(AuthKind.credentials, user=authenticated), CredentialKind.user
    else:
        logger.warning("Failed to validate credentials for user %s: %s", auth_username, err)
        return ValidateResult(AuthKind.credentials, error_message=err), CredentialKind.user
