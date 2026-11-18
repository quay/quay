# -*- coding: utf-8 -*-
# PROJQUAY-13785: the robot's last_accessed must move when it authenticates with a robot API
# token through the basic-credential path (what `podman login` and /v2/auth use).

from app import instance_keys
from auth.credential_consts import OAUTH_TOKEN_USERNAME
from auth.credentials import CredentialKind, validate_credentials
from data import model
from data.database import User
from data.model import api_token
from data.model.user import generate_federated_robot_jwt_token
from test.fixtures import *


def test_robot_api_token_as_basic_credential_updates_robot_last_accessed(app):
    # PROJQUAY-13785: podman login with the robot name and its API token goes through
    # validate_credentials; the robot's last_accessed must move like it does for the password.
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("token-basic-last-accessed", creator)
    _, secret = api_token.create_token_under_limit(robot, creator, "repo:write", 3600, "CI token")
    assert User.get(User.id == robot.id).last_accessed is None

    result, kind = validate_credentials(robot.username, secret)

    assert kind == CredentialKind.robot
    assert result.auth_valid
    assert User.get(User.id == robot.id).last_accessed is not None


def test_robot_password_as_basic_credential_updates_robot_last_accessed(app):
    # Control: the password path already records robot use.
    robot, password = model.user.create_robot(
        "password-last-accessed", model.user.get_user("devtable")
    )
    assert User.get(User.id == robot.id).last_accessed is None

    result, kind = validate_credentials(robot.username, password)

    assert kind == CredentialKind.robot
    assert result.auth_valid
    assert User.get(User.id == robot.id).last_accessed is not None


def _federated_jwt_for(robot):
    saved = model.user.create_robot_federation_config(
        robot,
        [
            {
                "issuer": "https://issuer.example",
                "subject": "system:serviceaccount:ci:builder",
                "audiences": ["quay"],
                "api_scopes": "repo:read",
            }
        ],
    )
    return generate_federated_robot_jwt_token(instance_keys, robot, "repo:read", saved[0])


def test_robot_api_token_as_oauthtoken_username_updates_robot_last_accessed(app):
    # The $oauthtoken username form goes through validate_oauth_token; success is final there.
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("token-oauthtoken-form", creator)
    _, secret = api_token.create_token_under_limit(robot, creator, "repo:read", 3600, "CI token")

    result, kind = validate_credentials(OAUTH_TOKEN_USERNAME, secret)

    assert kind == CredentialKind.oauth_token
    assert result.auth_valid
    assert User.get(User.id == robot.id).last_accessed is not None


def test_robot_api_token_presented_as_another_robot_marks_no_robot_used(app):
    # A rejected login must not count as robot use, for either robot involved.
    creator = model.user.get_user("devtable")
    owner_robot, _ = model.user.create_robot("token-owner", creator)
    other_robot, _ = model.user.create_robot("token-other", creator)
    _, secret = api_token.create_token_under_limit(
        owner_robot, creator, "repo:read", 3600, "CI token"
    )

    result, kind = validate_credentials(other_robot.username, secret)

    assert kind == CredentialKind.robot
    assert not result.auth_valid
    assert result.error_message == "API token subject does not match the supplied username"
    assert User.get(User.id == owner_robot.id).last_accessed is None
    assert User.get(User.id == other_robot.id).last_accessed is None


def test_federated_robot_jwt_as_oauthtoken_username_marks_no_robot_used(app):
    robot, _ = model.user.create_robot("jwt-oauthtoken-form", model.user.get_user("devtable"))
    jwt_token = _federated_jwt_for(robot)

    result, kind = validate_credentials(OAUTH_TOKEN_USERNAME, jwt_token)

    assert kind == CredentialKind.oauth_token
    assert not result.auth_valid
    assert result.error_message == "Quay-signed robot JWTs require the robot username"
    assert User.get(User.id == robot.id).last_accessed is None


def test_federated_robot_jwt_presented_as_another_robot_marks_no_robot_used(app):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("jwt-owner", creator)
    other_robot, _ = model.user.create_robot("jwt-other", creator)
    jwt_token = _federated_jwt_for(robot)

    result, kind = validate_credentials(other_robot.username, jwt_token)

    assert kind == CredentialKind.robot
    assert not result.auth_valid
    assert result.error_message == "JWT subject does not match the supplied username"
    assert User.get(User.id == robot.id).last_accessed is None
    assert User.get(User.id == other_robot.id).last_accessed is None


def test_federated_robot_jwt_as_its_robot_updates_robot_last_accessed(app):
    robot, _ = model.user.create_robot("jwt-basic", model.user.get_user("devtable"))
    jwt_token = _federated_jwt_for(robot)

    result, kind = validate_credentials(robot.username, jwt_token)

    assert kind == CredentialKind.robot
    assert result.auth_valid
    assert User.get(User.id == robot.id).last_accessed is not None
