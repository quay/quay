import base64
import datetime
from unittest.mock import patch

import pytest
import requests
from jwt import DecodeError

from auth.test.mock_oidc_server import generate_mock_oidc_token, mock_get, mock_request
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.model import InvalidRobotCredentialException, InvalidRobotException
from test.fixtures import *
from util.security.federated_robot_auth import (
    parse_federated_robot_resource,
    resolve_federation_scope,
    validate_federated_auth,
)


def test_parse_federated_robot_resource_requires_robot_urn():
    assert parse_federated_robot_resource("urn:quay:robot:devtable+ci") == "devtable+ci"
    with pytest.raises(InvalidRobotCredentialException, match="resource"):
        parse_federated_robot_resource("devtable+ci")


@pytest.mark.parametrize("resource", ["", "urn:quay:robot:", "urn:quay:user:devtable"])
def test_parse_federated_robot_resource_rejects_invalid_resource(resource):
    with pytest.raises(InvalidRobotCredentialException, match="resource"):
        parse_federated_robot_resource(resource)


def test_resolve_federation_scope_allows_only_binding_subset():
    binding = {"api_scopes": "repo:read repo:write"}
    assert resolve_federation_scope(binding, "repo:read") == "repo:read"
    assert resolve_federation_scope(binding, None) == "repo:read repo:write"
    with pytest.raises(InvalidRobotCredentialException, match="scope"):
        resolve_federation_scope(binding, "super:user")


def test_validate_federated_robot_auth_bad_header(app):
    header = "Basic bad-basic-auth-header"
    result = validate_federated_auth(header)
    assert result == ValidateResult(
        AuthKind.federated, missing=True, error_message="Could not parse basic auth header"
    )


def test_validate_federated_robot_auth_no_header(app):
    result = validate_federated_auth("")
    assert result == ValidateResult(
        AuthKind.federated, missing=True, error_message="No auth header"
    )


def test_validate_federated_robot_auth_invalid_robot_name(app):
    creds = base64.b64encode("nonrobotuser:password".encode("utf-8"))
    header = f"Basic {creds.decode('utf-8')}"
    result = validate_federated_auth(header)
    assert result == ValidateResult(AuthKind.federated, missing=True, error_message="Invalid robot")


def test_validate_federated_robot_auth_non_existing_robot(app):
    creds = base64.b64encode("someorg+somerobot:password".encode("utf-8"))
    header = f"Basic {creds.decode('utf-8')}"

    with pytest.raises(InvalidRobotException) as err:
        validate_federated_auth(header)

    assert "Could not find robot with specified username" in str(err)


def test_validate_federated_robot_auth_invalid_jwt(app):
    robot, password = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    creds = base64.b64encode(f"{robot.username}:{password}".encode("utf-8"))
    header = f"Basic {creds.decode('utf-8')}"
    with pytest.raises(DecodeError) as e:
        validate_federated_auth(header)


def test_validate_federated_robot_auth_no_fed_config(app):
    robot, password = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    token = generate_mock_oidc_token(subject=robot.username)
    creds = base64.b64encode(f"{robot.username}:{token}".encode("utf-8"))
    header = f"Basic {creds.decode('utf-8')}"
    with pytest.raises(InvalidRobotCredentialException) as e:
        result = validate_federated_auth(header)

    assert "Robot does not have federated login configured" in str(e)


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_validate_federated_robot_auth_expired_jwt(app):
    robot, password = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    fed_config = [
        {
            "issuer": "https://mock-oidc-server.com",
            "subject": robot.username,
        }
    ]

    iat = datetime.datetime.now() - datetime.timedelta(seconds=4000)

    model.user.create_robot_federation_config(robot, fed_config)
    token = generate_mock_oidc_token(subject=robot.username, issued_at=iat)
    creds = base64.b64encode(f"{robot.username}:{token}".encode("utf-8"))
    header = f"Basic {creds.decode('utf-8')}"

    with pytest.raises(InvalidRobotCredentialException) as e:
        validate_federated_auth(header)
        assert "Signature has expired" in str(e)


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_validate_federated_robot_auth_rejects_jwt_before_not_before(app):
    robot, _ = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    model.user.create_robot_federation_config(
        robot,
        [{"issuer": "https://mock-oidc-server.com", "subject": robot.username}],
    )
    token = generate_mock_oidc_token(
        subject=robot.username,
        not_before=datetime.datetime.now() + datetime.timedelta(minutes=5),
    )
    header = f"Basic {base64.b64encode(f'{robot.username}:{token}'.encode()).decode()}"

    with pytest.raises(InvalidRobotCredentialException, match="not yet valid"):
        validate_federated_auth(header)


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_validate_federated_robot_auth_valid_jwt(app):
    robot, password = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    fed_config = [
        {
            "issuer": "https://mock-oidc-server.com",
            "subject": robot.username,
        }
    ]
    model.user.create_robot_federation_config(robot, fed_config)

    token = generate_mock_oidc_token(subject=robot.username)
    creds = base64.b64encode(f"{robot.username}:{token}".encode("utf-8"))
    header = f"Basic {creds.decode('utf-8')}"

    result: ValidateResult = validate_federated_auth(header)
    assert result.error_message is None
    assert not result.missing
    assert result.kind == AuthKind.federated


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_validate_federated_robot_auth_validates_binding_audience(app):
    robot, _ = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    model.user.create_robot_federation_config(
        robot,
        [
            {
                "issuer": "https://mock-oidc-server.com",
                "subject": robot.username,
                "audiences": ["quay"],
            }
        ],
    )

    token = generate_mock_oidc_token(subject=robot.username, audience="quay")
    header = f"Basic {base64.b64encode(f'{robot.username}:{token}'.encode()).decode()}"

    result = validate_federated_auth(header)
    assert result.auth_valid


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_validate_federated_robot_auth_rejects_unconfigured_audience(app):
    robot, _ = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    model.user.create_robot_federation_config(
        robot,
        [
            {
                "issuer": "https://mock-oidc-server.com",
                "subject": robot.username,
                "audiences": ["quay"],
            }
        ],
    )

    token = generate_mock_oidc_token(subject=robot.username, audience="another-service")
    header = f"Basic {base64.b64encode(f'{robot.username}:{token}'.encode()).decode()}"

    with pytest.raises(InvalidRobotCredentialException, match="Token audience is not allowed"):
        validate_federated_auth(header)
