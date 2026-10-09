import base64
import json
from unittest.mock import patch

import pytest
import requests

from app import instance_keys
from auth.credentials import CredentialKind, validate_credentials
from auth.oauth import validate_bearer_auth
from auth.test.mock_oidc_server import generate_mock_oidc_token, mock_get, mock_request
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.database import FederatedLogin
from data.model import config as model_config
from data.model.user import verify_robot_jwt_token
from endpoints.oauth.robot_identity_federation import (
    ACCESS_TOKEN_TYPE,
    JWT_TOKEN_TYPE,
    MAX_SUBJECT_TOKEN_LENGTH,
    TOKEN_EXCHANGE_GRANT_TYPE,
    auth_federated_robot_identity,
    federation_bp,
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


LEGACY_ISSUER = "https://mock-oidc-server.com"


@pytest.fixture()
def federation_app(app):
    app.register_blueprint(federation_bp, url_prefix="/oauth2")
    return app


def _store_legacy_federation_config(robot, bindings):
    """Write bindings in the pre-id JSON shape (no id, no version) straight into the row."""
    federated = FederatedLogin.get(FederatedLogin.user == robot)
    federated.metadata_json = json.dumps({"federation_config": bindings})
    federated.save()


def _legacy_federated_robot(subjects=None, api_scopes="repo:read repo:write"):
    """Robot whose stored federation JSON predates per-binding ids (no id, no version)."""
    robot, _ = model.user.create_robot("legacyfed", model.user.get_user("devtable"))
    _store_legacy_federation_config(
        robot,
        [
            {
                "issuer": LEGACY_ISSUER,
                "subject": subject,
                "audiences": ["quay"],
                "api_scopes": api_scopes,
            }
            for subject in (subjects or [robot.username])
        ],
    )
    return robot


def _exchange(client, robot, subject, scope="repo:read"):
    return client.post(
        "/sts/token",
        data={
            "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
            "subject_token": generate_mock_oidc_token(subject=subject, audience="quay"),
            "subject_token_type": JWT_TOKEN_TYPE,
            "resource": "urn:quay:robot:" + robot.username,
            "scope": scope,
        },
        content_type="application/x-www-form-urlencoded",
    )


def _basic_header(robot, token):
    creds = base64.b64encode(f"{robot.username}:{token}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {creds}"}


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_legacy_binding_without_id_exchanges_through_sts(sts_app):
    # PROJQUAY-13546: the exchange used to raise KeyError('id') while minting.
    robot = _legacy_federated_robot()

    with patch("endpoints.oauth.robot_identity_federation.log_action") as log_action:
        response = _exchange(sts_app.test_client(), robot, robot.username)

    assert response.status_code == 200
    expected = model.user.get_robot_federation_config(robot)[0]
    log_metadata = log_action.call_args.args[2]
    assert log_metadata["federation_binding_id"] == expected["id"]
    assert log_metadata["federation_binding_version"] == 1

    decoded = decode_bearer_token(
        response.json["access_token"], instance_keys, model_config.app_config
    )
    assert decoded["federation_binding_id"] == expected["id"]
    assert decoded["federation_binding_version"] == 1

    validated = validate_bearer_auth("Bearer " + response.json["access_token"])
    assert validated.auth_valid
    assert validated.context.federation_binding == expected

    # The API audit log carries the derived id instead of failing the request.
    from endpoints.api import log_action as api_log_action

    with sts_app.test_request_context("/api/v1/user/"):
        validated.apply_to_context()
        with patch("endpoints.api.logs_model") as logs_model:
            api_log_action("create_robot_federation", "devtable")
    audit = logs_model.log_action.call_args.kwargs["metadata"]
    assert audit["federation_binding_id"] == expected["id"]
    assert audit["federation_binding_version"] == 1


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_removed_legacy_binding_token_is_rejected_after_sts_exchange(sts_app):
    # PROJQUAY-13549: two legacy bindings stay independently revocable.
    subjects = ["system:serviceaccount:ci:builder-a", "system:serviceaccount:ci:builder-b"]
    robot = _legacy_federated_robot(subjects)
    client = sts_app.test_client()

    with patch("endpoints.oauth.robot_identity_federation.log_action"):
        exchange_a = _exchange(client, robot, subjects[0])
        exchange_b = _exchange(client, robot, subjects[1])
    assert exchange_a.status_code == 200
    assert exchange_b.status_code == 200
    token_a = exchange_a.json["access_token"]
    token_b = exchange_b.json["access_token"]

    bindings = model.user.get_robot_federation_config(robot)
    assert validate_bearer_auth("Bearer " + token_a).context.federation_binding == bindings[0]
    assert validate_bearer_auth("Bearer " + token_b).context.federation_binding == bindings[1]

    # Keeping only the second binding, as the UI posts it, removes the first by id.
    model.user.create_robot_federation_config(robot, [bindings[1]])

    revoked = validate_bearer_auth("Bearer " + token_a)
    assert not revoked.auth_valid
    assert revoked.error_message == "Federation binding is no longer valid"
    assert validate_bearer_auth("Bearer " + token_b).context.federation_binding == bindings[1]

    with patch("endpoints.oauth.robot_identity_federation.log_action"):
        assert _exchange(client, robot, subjects[0]).status_code == 400
        assert _exchange(client, robot, subjects[1]).status_code == 200


@patch.object(requests.Session, "request", mock_request)
@patch.object(requests.Session, "get", mock_get)
def test_legacy_binding_without_id_uses_legacy_endpoint(federation_app):
    # Guard for the PROJQUAY-13546 scenario: a legacy binding keeps getting a registry-only
    # token from the legacy endpoint, and another subject is denied with a controlled error.
    robot = _legacy_federated_robot()
    client = federation_app.test_client()
    token = generate_mock_oidc_token(subject=robot.username, audience="quay")

    for _ in range(2):
        response = client.get("/oauth2/federation/robot/token", headers=_basic_header(robot, token))
        assert response.status_code == 200
        decoded = decode_bearer_token(
            response.json["token"], instance_keys, model_config.app_config
        )
        assert decoded["sub"] == robot.username
        assert "api_scopes" not in decoded
        assert "federation_binding_id" not in decoded

    bad = generate_mock_oidc_token(subject="system:serviceaccount:other:sa", audience="quay")
    response = client.get("/oauth2/federation/robot/token", headers=_basic_header(robot, bad))
    assert response.status_code == 400
    assert response.json == {"message": "Token does not match robot"}
