from unittest.mock import patch

import pytest

from data import model
from data.model import api_token
from endpoints.api.robot_application_tokens import (
    OrganizationRobotMintableScopes,
    OrganizationRobotToken,
    OrganizationRobotTokens,
    UserRobotMintableScopes,
    UserRobotToken,
    UserRobotTokens,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *

TOKEN_REQUEST = {"name": "CI robot token", "scope": "repo:read", "expiration": 3600}


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


def test_organization_robot_token_lifecycle(app):
    params = {"orgname": "buynlarge", "robot_shortname": "coolrobot"}

    with client_with_identity("devtable", app) as cl:
        created = conduct_api_call(
            cl, OrganizationRobotTokens, "POST", params, TOKEN_REQUEST, 200
        ).json
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
