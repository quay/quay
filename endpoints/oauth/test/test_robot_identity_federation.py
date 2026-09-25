from unittest.mock import patch

import pytest
import requests

from app import instance_keys
from auth.test.mock_oidc_server import generate_mock_oidc_token, mock_get, mock_request
from data import model
from data.model.user import verify_robot_jwt_token
from endpoints.oauth.robot_identity_federation import (
    ACCESS_TOKEN_TYPE,
    JWT_TOKEN_TYPE,
    TOKEN_EXCHANGE_GRANT_TYPE,
    sts_bp,
)
from test.fixtures import *


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
    assert response.json["token_type"] == "Bearer"
    assert response.json["issued_token_type"] == ACCESS_TOKEN_TYPE
    assert response.json["expires_in"] == 3600
    assert response.json["scope"] == "repo:read"
    verify_robot_jwt_token(robot.username, response.json["access_token"], instance_keys)


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


def test_sts_token_exchange_requires_form_encoding(sts_app):
    response = sts_app.test_client().post("/sts/token", json={})

    assert response.status_code == 400
    assert response.json == {"error": "invalid_request"}
