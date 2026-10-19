# -*- coding: utf-8 -*-
# PROJQUAY-13785: the robot's last_accessed must move when it authenticates with a robot API
# token through the basic-credential path (what `podman login` and /v2/auth use).

from auth.credentials import CredentialKind, validate_credentials
from data import model
from data.database import User
from data.model import api_token
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
