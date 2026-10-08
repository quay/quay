from unittest.mock import patch

import pytest
import requests

from app import instance_keys
from auth.credentials import CredentialKind, validate_credentials
from auth.oauth import validate_bearer_auth
from auth.test.mock_oidc_server import generate_mock_oidc_token, mock_get, mock_request
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.model import config as model_config
from data.model.user import verify_robot_jwt_token
from endpoints.oauth.robot_identity_federation import (
    ACCESS_TOKEN_TYPE,
    JWT_TOKEN_TYPE,
    MAX_SUBJECT_TOKEN_LENGTH,
    TOKEN_EXCHANGE_GRANT_TYPE,
    auth_federated_robot_identity,
    sts_bp,
)
from test.fixtures import *
from util.security.registry_jwt import decode_bearer_token


@pytest.fixture()
def sts_app(app):
    app.register_blueprint(sts_bp)
    return app


def test_sts_token_route_is_registered(sts_app):
    routes = {(rule.rule, frozenset(rule.methods)) for rule in sts_app.url_map.iter_rules()}
    assert ("/sts/token", frozenset({"POST", "OPTIONS"})) in routes


def _federated_robot(scopes="repo:read repo:write"):
    robot, _ = model.user.create_robot("federated", model.user.get_user("devtable"))
    model.user.create_robot_federation_config(
        robot,
        [
            {
                "issuer": "https://mock-oidc-server.com",
                "subject": robot.username,
                "audiences": ["quay"],
                "api_scopes": scopes,
            }
        ],
    )
    return robot


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_sts_token_exchange_returns_quay_robot_jwt(sts_app):
    robot = _federated_robot()
    with patch("endpoints.oauth.robot_identity_federation.log_action") as log_action:
        response = sts_app.test_client().post(
            "/sts/token",
            data={
                "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
                "subject_token": generate_mock_oidc_token(subject=robot.username, audience="quay"),
                "subject_token_type": JWT_TOKEN_TYPE,
                "resource": "urn:quay:robot:" + robot.username,
                "scope": "repo:read",
            },
            content_type="application/x-www-form-urlencoded",
        )

    assert response.status_code == 200
    log_action.assert_called_once()
    log_metadata = log_action.call_args.args[2]
    assert log_metadata["result"] == "success"
    assert log_metadata["requested_scope"] == "repo:read"
    assert response.json["token_type"] == "Bearer"
    assert response.json["issued_token_type"] == ACCESS_TOKEN_TYPE
    assert response.json["expires_in"] == 3600
    assert response.json["scope"] == "repo:read"
    verify_robot_jwt_token(robot.username, response.json["access_token"], instance_keys)
    validated = validate_bearer_auth("Bearer " + response.json["access_token"])
    binding = model.user.get_robot_federation_config(robot)[0]
    assert validated.context.federation_binding == binding

    with patch("features.ROBOT_API_TOKEN_EXCHANGE", False):
        still_valid = validate_bearer_auth("Bearer " + response.json["access_token"])
    assert still_valid.auth_valid

    with patch("features.ROBOT_API_TOKENS", False):
        disabled = validate_bearer_auth("Bearer " + response.json["access_token"])
    assert not disabled.auth_valid
    assert disabled.error_message == "API token is invalid, revoked or expired"

    basic_result, credential_kind = validate_credentials(
        robot.username, response.json["access_token"]
    )
    assert credential_kind == CredentialKind.robot
    assert basic_result.auth_valid
    assert basic_result.context.federation_binding == binding

    changed_binding = dict(binding, api_scopes="repo:write")
    model.user.create_robot_federation_config(robot, [changed_binding])
    revoked_result, _ = validate_credentials(robot.username, response.json["access_token"])
    assert not revoked_result.auth_valid
    assert revoked_result.error_message == "Federation binding is no longer valid"


def test_legacy_federation_endpoint_issues_registry_only_token(app):
    robot = _federated_robot()
    binding = model.user.get_robot_federation_config(robot)[0]
    auth_result = ValidateResult(AuthKind.federated, robot=robot, federation_binding=binding)

    with app.test_request_context("/oauth2/federation/robot/token?scope=repo:read"):
        auth_result.apply_to_context()
        response = auth_federated_robot_identity.__wrapped__(auth_result)

    decoded = decode_bearer_token(response["token"], instance_keys, model_config.app_config)
    assert decoded["sub"] == robot.username
    assert "api_scopes" not in decoded
    assert "federation_binding_id" not in decoded


@pytest.mark.parametrize(
    "form,error",
    [
        ({}, "invalid_request"),
        (
            {
                "grant_type": "authorization_code",
                "subject_token": "token",
                "subject_token_type": JWT_TOKEN_TYPE,
                "resource": "urn:quay:robot:devtable+robot",
            },
            "unsupported_grant_type",
        ),
        (
            {
                "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
                "subject_token": "token",
                "subject_token_type": "access_token",
                "resource": "urn:quay:robot:devtable+robot",
            },
            "invalid_request",
        ),
        (
            {
                "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
                "subject_token": "token",
                "subject_token_type": JWT_TOKEN_TYPE,
                "resource": "not-a-resource",
            },
            "invalid_target",
        ),
    ],
)
def test_sts_token_exchange_rejects_invalid_requests(sts_app, form, error):
    response = sts_app.test_client().post(
        "/sts/token", data=form, content_type="application/x-www-form-urlencoded"
    )

    assert response.status_code == 400
    assert response.json == {"error": error}


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_sts_token_exchange_rejects_scope_outside_binding(sts_app):
    robot = _federated_robot(scopes="repo:read")
    with patch("endpoints.oauth.robot_identity_federation.log_action") as log_action:
        response = sts_app.test_client().post(
            "/sts/token",
            data={
                "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
                "subject_token": generate_mock_oidc_token(subject=robot.username, audience="quay"),
                "subject_token_type": JWT_TOKEN_TYPE,
                "resource": "urn:quay:robot:" + robot.username,
                "scope": "repo:write",
            },
            content_type="application/x-www-form-urlencoded",
        )

    assert response.status_code == 400
    assert response.json == {"error": "invalid_grant"}
    log_action.assert_called_once()
    metadata = log_action.call_args.args[2]
    assert metadata["result"] == "failure"
    assert metadata["failure_reason"] == "scope_not_allowed"
    assert metadata["requested_scope"] == "repo:write"
    assert metadata["subject"] == robot.username


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_sts_token_exchange_rejects_binding_without_api_scope(sts_app):
    robot = _federated_robot(scopes="")
    response = sts_app.test_client().post(
        "/sts/token",
        data={
            "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
            "subject_token": generate_mock_oidc_token(subject=robot.username, audience="quay"),
            "subject_token_type": JWT_TOKEN_TYPE,
            "resource": "urn:quay:robot:" + robot.username,
        },
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 400
    assert response.json == {"error": "invalid_grant"}


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_sts_token_exchange_rejects_audience_outside_binding(sts_app):
    robot = _federated_robot()
    response = sts_app.test_client().post(
        "/sts/token",
        data={
            "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
            "subject_token": generate_mock_oidc_token(
                subject=robot.username, audience="other-audience"
            ),
            "subject_token_type": JWT_TOKEN_TYPE,
            "resource": "urn:quay:robot:" + robot.username,
            "scope": "repo:read",
        },
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 400
    assert response.json == {"error": "invalid_grant"}


def test_sts_token_exchange_rejects_oversized_subject_token(sts_app):
    response = sts_app.test_client().post(
        "/sts/token",
        data={
            "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
            "subject_token": "x" * (MAX_SUBJECT_TOKEN_LENGTH + 1),
            "subject_token_type": JWT_TOKEN_TYPE,
            "resource": "urn:quay:robot:devtable+robot",
        },
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 400
    assert response.json == {"error": "invalid_request"}


def test_sts_token_exchange_requires_form_encoding(sts_app):
    response = sts_app.test_client().post("/sts/token", json={})

    assert response.status_code == 400
    assert response.json == {"error": "invalid_request"}
