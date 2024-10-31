import logging
from enum import Enum

from flask import request
from jwt import InvalidTokenError

import features
from app import app, authentication, instance_keys
from auth.credential_consts import (
    ACCESS_TOKEN_USERNAME,
    APP_SPECIFIC_TOKEN_USERNAME,
    OAUTH_TOKEN_USERNAME,
)
from auth.log import log_action
from auth.oauth import validate_oauth_token
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.database import User
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

            error_message = "Invalid token"

            if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
                log_action(
                    "login_failure",
                    None,
                    {
                        "type": "v2auth",
                        "kind": "app_specific_token",
                        "useragent": request.user_agent.string,
                        "message": error_message,
                    },
                )

            return (
                ValidateResult(AuthKind.credentials, error_message=error_message),
                CredentialKind.app_specific_token,
            )

        if not token.user.enabled:
            logger.debug("Tried to use an app specific token for a disabled user: %s", token.uuid)

            error_message = "This user has been disabled. Please contact your administrator."

            if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
                log_action(
                    "login_failure",
                    token.user.username,
                    {
                        "type": "v2auth",
                        "kind": "app_specific_token",
                        "app_specific_token_title": token.title,
                        "username": token.user.username,
                        "useragent": request.user_agent.string,
                        "message": error_message,
                    },
                    performer=token.user,
                )

            return (
                ValidateResult(
                    AuthKind.credentials,
                    error_message=error_message,
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
            robot = model.user.verify_robot(auth_username, auth_password_or_token, instance_keys)
            assert robot
            logger.debug("Successfully validated credentials for robot %s", auth_username)
            return ValidateResult(AuthKind.credentials, robot=robot), CredentialKind.robot
        except model.DeactivatedRobotOwnerException as dre:
            robot_owner, robot_name = parse_robot_username(auth_username)

            logger.debug(
                "Tried to use the robot %s for a disabled user: %s", robot_name, robot_owner
            )

            if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
                try:
                    performer = model.user.lookup_robot(auth_username)
                except User.DoesNotExist:
                    performer = None

                log_action(
                    "login_failure",
                    robot_owner,
                    {
                        "type": "v2auth",
                        "kind": "robot",
                        "robot": auth_username,
                        "username": robot_owner,
                        "useragent": request.user_agent.string,
                        "message": str(dre),
                    },
                    performer=performer,
                )

            return (
                ValidateResult(AuthKind.credentials, error_message=str(dre)),
                CredentialKind.robot,
            )
        except (model.InvalidRobotCredentialException, InvalidTokenError) as ire:
            logger.debug("Failed to validate credentials for robot %s: %s", auth_username, ire)

            if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
                robot_owner, _ = parse_robot_username(auth_username)

                try:
                    performer = model.user.lookup_robot(auth_username)
                except User.DoesNotExist:
                    performer = None

                log_action(
                    "login_failure",
                    robot_owner,
                    {
                        "type": "v2auth",
                        "kind": "robot",
                        "robot": auth_username,
                        "username": robot_owner,
                        "useragent": request.user_agent.string,
                        "message": str(ire),
                    },
                    performer=performer,
                )

            return (
                ValidateResult(AuthKind.credentials, error_message=str(ire)),
                CredentialKind.robot,
            )
        except model.InvalidRobotException as ire:
            if isinstance(ire, model.InvalidRobotException):
                logger.debug("Failed to validate credentials for robot %s: %s", auth_username, ire)
            elif isinstance(ire, model.InvalidRobotOwnerException):
                logger.debug(
                    "Tried to use the robot %s for a non-existing user: %s", auth_username, ire
                )

            if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
                robot_owner, _ = parse_robot_username(auth_username)

                # need to get the owner here in case it wasn't found due to a non-existing user
                owner = model.user.get_nonrobot_user(robot_owner)

                log_action(
                    "login_failure",
                    owner.username if owner else None,
                    {
                        "type": "v2auth",
                        "kind": "robot",
                        "robot": auth_username,
                        "username": robot_owner,
                        "useragent": request.user_agent.string,
                        "message": str(ire),
                    },
                )

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

        if app.config.get("ACTION_LOG_AUDIT_LOGIN_FAILURES"):
            log_action(
                "login_failure",
                None,
                {
                    "type": "v2auth",
                    "kind": "user",
                    "username": auth_username,
                    "useragent": request.user_agent.string,
                    "message": err,
                },
            )

        return ValidateResult(AuthKind.credentials, error_message=err), CredentialKind.user
