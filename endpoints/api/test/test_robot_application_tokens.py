from unittest.mock import patch

import pytest

import features
from data import model
from data.model import api_token
from data.model import config as model_config
from endpoints.api.discovery import swagger_route_data
from endpoints.api.robot_application_tokens import (
    NEW_ROBOT_TOKEN_SCHEMA,
    OrganizationRobotMintableScopes,
    OrganizationRobotToken,
    OrganizationRobotTokens,
    UserRobotMintableScopes,
    UserRobotToken,
    UserRobotTokens,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, toggle_feature
from test.fixtures import *

TOKEN_REQUEST = {"name": "CI robot token", "scope": "repo:read", "expiration": 3600}


ROBOT_TOKEN_OPERATIONS = {
    "/api/v1/user/robots/{robot_shortname}/mintable-scopes": {
        "get": "listUserRobotMintableScopes",
    },
    "/api/v1/user/robots/{robot_shortname}/tokens": {
        "get": "listUserRobotTokens",
        "post": "createUserRobotToken",
    },
    "/api/v1/user/robots/{robot_shortname}/tokens/{token_uuid}": {
        "delete": "deleteUserRobotToken",
    },
    "/api/v1/organization/{orgname}/robots/{robot_shortname}/mintable-scopes": {
        "get": "listOrganizationRobotMintableScopes",
    },
    "/api/v1/organization/{orgname}/robots/{robot_shortname}/tokens": {
        "get": "listOrganizationRobotTokens",
        "post": "createOrganizationRobotToken",
    },
    "/api/v1/organization/{orgname}/robots/{robot_shortname}/tokens/{token_uuid}": {
        "delete": "deleteOrganizationRobotToken",
    },
}


def test_robot_api_token_routes_are_registered(app):
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/user/robots/<robot_shortname>/tokens" in routes
    assert "/api/v1/organization/<orgname>/robots/<robot_shortname>/tokens" in routes


def test_robot_api_token_operations_are_in_discovery():
    assert features.ROBOT_API_TOKENS

    swagger = swagger_route_data()
    operations = {
        path: {method: swagger["paths"][path][method]["operationId"] for method in methods}
        for path, methods in ROBOT_TOKEN_OPERATIONS.items()
    }

    assert operations == ROBOT_TOKEN_OPERATIONS

    operation_ids = [
        operation_id for methods in operations.values() for operation_id in methods.values()
    ]
    assert len(operation_ids) == len(set(operation_ids)) == 8

    for path in (
        "/api/v1/user/robots/{robot_shortname}/tokens",
        "/api/v1/organization/{orgname}/robots/{robot_shortname}/tokens",
    ):
        body = next(
            parameter
            for parameter in swagger["paths"][path]["post"]["parameters"]
            if parameter["in"] == "body"
        )
        assert body["schema"] == {"$ref": "#/definitions/NewRobotToken"}

    assert swagger["definitions"]["NewRobotToken"] == NEW_ROBOT_TOKEN_SCHEMA


def test_organization_robot_mintable_scopes(app):
    params = {"orgname": "buynlarge", "robot_shortname": "coolrobot"}

    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl, OrganizationRobotMintableScopes, "GET", params, None, 200
        ).json

    assert response["scopes"] == [
        "repo:read",
        "repo:write",
        "repo:admin",
        "repo:create",
        "user:read",
        "org:admin",
        "super:user",
        "user:admin",
    ]


def test_user_robot_mintable_scopes(app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl, UserRobotMintableScopes, "GET", {"robot_shortname": "dtrobot"}, None, 200
        ).json

    assert response["scopes"] == [
        "repo:read",
        "repo:write",
        "repo:admin",
        "repo:create",
        "user:read",
        "org:admin",
        "super:user",
        "user:admin",
    ]


def test_mintable_scopes_exclude_scopes_the_creator_cannot_mint(app):
    params = {"orgname": "buynlarge", "robot_shortname": "coolrobot"}
    with patch(
        "endpoints.api.robot_application_tokens._can_mint_scope",
        side_effect=lambda _namespace, scope, _creator: scope != "super:user",
    ):
        with client_with_identity("devtable", app) as cl:
            response = conduct_api_call(
                cl, OrganizationRobotMintableScopes, "GET", params, None, 200
            ).json

    assert "repo:read" in response["scopes"]
    assert "super:user" not in response["scopes"]


@pytest.mark.parametrize(
    "resource,method,params",
    [
        (UserRobotMintableScopes, "GET", {"robot_shortname": "missing"}),
        (UserRobotTokens, "GET", {"robot_shortname": "missing"}),
        (
            OrganizationRobotTokens,
            "GET",
            {"orgname": "buynlarge", "robot_shortname": "missing"},
        ),
    ],
)
def test_missing_robot_returns_not_found(app, resource, method, params):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(cl, resource, method, params, None, 404)


@pytest.mark.parametrize(
    "resource,params",
    [
        (UserRobotTokens, {"robot_shortname": "dtrobot"}),
        (OrganizationRobotTokens, {"orgname": "buynlarge", "robot_shortname": "coolrobot"}),
    ],
)
def test_robot_token_listing_supports_pagination(app, resource, params):
    creator = model.user.get_user("devtable")
    token_one, _ = api_token.create_token_under_limit(
        creator, creator, "repo:read", 3600, "First token"
    )
    token_two, _ = api_token.create_token_under_limit(
        creator, creator, "repo:write", 3600, "Second token"
    )

    with patch("endpoints.api.robot_application_tokens.api_token_model.list_tokens") as list_tokens:
        list_tokens.side_effect = [([token_two], {"id": token_one.id}), ([token_one], None)]
        with client_with_identity("devtable", app) as cl:
            first_page = conduct_api_call(cl, resource, "GET", params, None, 200).json
            second_page = conduct_api_call(
                cl,
                resource,
                "GET",
                {**params, "next_page": first_page["next_page"]},
                None,
                200,
            ).json

    assert [token["uuid"] for token in first_page["tokens"]] == [token_two.uuid]
    assert [token["uuid"] for token in second_page["tokens"]] == [token_one.uuid]
    assert "next_page" not in second_page


@pytest.mark.parametrize(
    "request_body,expected_message",
    [
        (
            {"name": "   ", "scope": "repo:read", "expiration": 3600},
            "'name' cannot be empty",
        ),
        (
            {"name": "CI robot token", "scope": "direct_user_login", "expiration": 3600},
            "Invalid scope",
        ),
    ],
)
def test_organization_robot_token_rejects_invalid_requests(app, request_body, expected_message):
    params = {"orgname": "buynlarge", "robot_shortname": "coolrobot"}

    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl, OrganizationRobotTokens, "POST", params, request_body, 400
        ).json

    assert expected_message in response["message"]


def test_revoke_missing_robot_token_returns_not_found(app):
    params = {
        "orgname": "buynlarge",
        "robot_shortname": "coolrobot",
        "token_uuid": "missing-token",
    }

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(cl, OrganizationRobotToken, "DELETE", params, None, 404)


def test_organization_robot_token_lifecycle(app):
    params = {"orgname": "buynlarge", "robot_shortname": "coolrobot"}

    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(cl, OrganizationRobotTokens, "POST", params, TOKEN_REQUEST, 200)
        assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        created = response.json
        assert created["token"].startswith(api_token.API_TOKEN_PREFIX)
        assert created["name"] == TOKEN_REQUEST["name"]
        assert created["scope"] == TOKEN_REQUEST["scope"]

        listed = conduct_api_call(cl, OrganizationRobotTokens, "GET", params, None, 200).json
        listed_token = next(token for token in listed["tokens"] if token["uuid"] == created["uuid"])
        assert "token" not in listed_token

        conduct_api_call(
            cl,
            OrganizationRobotToken,
            "DELETE",
            {**params, "token_uuid": created["uuid"]},
            None,
            204,
        )


def test_user_robot_token_lifecycle(app):
    params = {"robot_shortname": "dtrobot"}

    with client_with_identity("devtable", app) as cl:
        created = conduct_api_call(cl, UserRobotTokens, "POST", params, TOKEN_REQUEST, 200).json
        assert created["token"].startswith(api_token.API_TOKEN_PREFIX)

        listed = conduct_api_call(cl, UserRobotTokens, "GET", params, None, 200).json
        assert any(token["uuid"] == created["uuid"] for token in listed["tokens"])

        conduct_api_call(
            cl,
            UserRobotToken,
            "DELETE",
            {**params, "token_uuid": created["uuid"]},
            None,
            204,
        )


def test_robot_api_token_bearer_reads_permitted_repository(app):
    robot = model.user.lookup_robot("buynlarge+coolrobot")
    creator = model.user.get_user("devtable")
    _, secret = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "Repository read token"
    )
    model.permission.set_user_repo_permission(robot.username, "buynlarge", "orgrepo", "read")

    with app.test_client() as cl:
        response = cl.get(
            "/api/v1/repository/buynlarge/orgrepo",
            headers={"Authorization": "Bearer " + secret},
        )

    assert response.status_code == 200
    assert response.json["name"] == "orgrepo"
    assert response.json["namespace"] == "buynlarge"


@pytest.mark.parametrize(
    "robot_shortname, whitelist, expected_status",
    [
        ("policyendpointdenied", [], 401),
        (
            "policyendpointnonmatching",
            lambda robot: [robot.username + "-suffix"],
            401,
        ),
        ("policyendpointallowed", lambda robot: [robot.username], 200),
    ],
)
def test_robot_api_token_bearer_respects_robot_access_policy_at_repository_endpoint(
    app, robot_shortname, whitelist, expected_status
):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot(robot_shortname, creator)
    repository = model.repository.create_repository(
        creator.username, robot_shortname, creator, visibility="private"
    )
    _, secret = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "Repository read token"
    )
    model.permission.set_user_repo_permission(
        robot.username, creator.username, repository.name, "read"
    )
    endpoint = "/api/v1/repository/{}/{}".format(creator.username, repository.name)
    whitelist = whitelist(robot) if callable(whitelist) else whitelist

    with app.test_client() as cl:
        assert cl.get(endpoint).status_code == 401

    with patch.dict(
        model_config.app_config,
        {"ROBOTS_DISALLOW": True, "ROBOTS_WHITELIST": whitelist},
    ):
        with app.test_client() as cl:
            response = cl.get(endpoint, headers={"Authorization": "Bearer " + secret})

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json["name"] == repository.name
        assert response.json["namespace"] == creator.username


@pytest.mark.parametrize(
    "resource, params, robot_username",
    [
        (UserRobotTokens, {"robot_shortname": "dtrobot"}, "devtable+dtrobot"),
        (
            OrganizationRobotTokens,
            {"orgname": "buynlarge", "robot_shortname": "coolrobot"},
            "buynlarge+coolrobot",
        ),
    ],
)
@pytest.mark.parametrize(
    "whitelist, expected_code",
    [
        ([], 403),
        (lambda robot: [robot.username], 200),
        (lambda robot: [robot.username + "-suffix"], 403),
    ],
)
def test_robot_token_creation_respects_robot_access_policy(
    app, resource, params, robot_username, whitelist, expected_code
):
    robot = model.user.lookup_robot(robot_username)
    token_count_before = api_token.count_active_tokens(robot)
    whitelist = whitelist(robot) if callable(whitelist) else whitelist

    with patch.dict(
        model_config.app_config,
        {"ROBOTS_DISALLOW": True, "ROBOTS_WHITELIST": whitelist},
    ):
        with client_with_identity("devtable", app) as cl:
            response = conduct_api_call(cl, resource, "POST", params, TOKEN_REQUEST, expected_code)

    if expected_code == 200:
        assert response.json["token"].startswith(api_token.API_TOKEN_PREFIX)
    assert api_token.count_active_tokens(robot) == token_count_before + (expected_code == 200)


ORG_TOKEN_ROBOT_PARAMS = {"orgname": "robottokenorg", "robot_shortname": "tokenbot"}
TOKEN_VIEW_FIELDS = {
    "uuid",
    "name",
    "scope",
    "expires_at",
    "created",
    "created_by",
    "last_accessed",
}


def _org_robot_with_two_tokens():
    # freshuser owns the organization; devtable is a superuser who is not a member of it.
    owner = model.user.get_user("freshuser")
    org = model.organization.create_organization(
        "robottokenorg", "robottokenorg@devtable.com", owner
    )
    robot, _ = model.user.create_robot("tokenbot", org)
    tokens = [
        api_token.create_token_under_limit(robot, owner, "repo:read", 3600, name)[0]
        for name in ("First token", "Second token")
    ]
    return robot, tokens


@pytest.mark.parametrize(
    "username, full_access, expected_codes",
    [
        ("freshuser", True, (200, 200, 200, 204)),
        ("devtable", True, (200, 200, 200, 204)),
        ("devtable", False, (403, 403, 403, 403)),
        ("globalreadonlysuperuser", True, (200, 200, 403, 403)),
        ("reader", True, (403, 403, 403, 403)),
    ],
)
def test_organization_robot_token_endpoint_access(app, username, full_access, expected_codes):
    _, tokens = _org_robot_with_two_tokens()
    calls = [
        (OrganizationRobotTokens, "GET", ORG_TOKEN_ROBOT_PARAMS, None),
        (OrganizationRobotMintableScopes, "GET", ORG_TOKEN_ROBOT_PARAMS, None),
        (OrganizationRobotTokens, "POST", ORG_TOKEN_ROBOT_PARAMS, TOKEN_REQUEST),
        (
            OrganizationRobotToken,
            "DELETE",
            {**ORG_TOKEN_ROBOT_PARAMS, "token_uuid": tokens[0].uuid},
            None,
        ),
    ]

    with toggle_feature("SUPERUSERS_FULL_ACCESS", full_access):
        with client_with_identity(username, app) as cl:
            for (resource, method, params, body), expected_code in zip(calls, expected_codes):
                conduct_api_call(cl, resource, method, params, body, expected_code)


def test_global_readonly_superuser_lists_organization_robot_tokens_without_secrets(app):
    _, tokens = _org_robot_with_two_tokens()

    with client_with_identity("globalreadonlysuperuser", app) as cl:
        listed = conduct_api_call(
            cl, OrganizationRobotTokens, "GET", ORG_TOKEN_ROBOT_PARAMS, None, 200
        ).json

    assert {token["uuid"] for token in listed["tokens"]} == {token.uuid for token in tokens}
    assert all(set(token) == TOKEN_VIEW_FIELDS for token in listed["tokens"])


def test_global_readonly_superuser_has_no_mintable_scopes(app):
    _org_robot_with_two_tokens()

    with client_with_identity("globalreadonlysuperuser", app) as cl:
        response = conduct_api_call(
            cl, OrganizationRobotMintableScopes, "GET", ORG_TOKEN_ROBOT_PARAMS, None, 200
        ).json

    assert response["scopes"] == []


def test_global_readonly_superuser_cannot_create_or_revoke_organization_robot_tokens(app):
    robot, tokens = _org_robot_with_two_tokens()

    with client_with_identity("globalreadonlysuperuser", app) as cl:
        conduct_api_call(
            cl, OrganizationRobotTokens, "POST", ORG_TOKEN_ROBOT_PARAMS, TOKEN_REQUEST, 403
        )
        for token in tokens:
            conduct_api_call(
                cl,
                OrganizationRobotToken,
                "DELETE",
                {**ORG_TOKEN_ROBOT_PARAMS, "token_uuid": token.uuid},
                None,
                403,
            )

    remaining, _ = api_token.list_tokens(robot)
    assert {token.uuid for token in remaining} == {token.uuid for token in tokens}
