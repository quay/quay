import pytest
import json

from data import model
from endpoints.api import api
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.robot import UserRobot, OrgRobot, UserRobotList, OrgRobotList
from endpoints.test.shared import client_with_identity
from util.names import parse_robot_username

from test.test_ldap import mock_ldap

from test.fixtures import *


@pytest.mark.parametrize(
    "endpoint",
    [
        UserRobot,
        OrgRobot,
    ],
)
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"description": "this is a description"},
        {"unstructured_metadata": {"foo": "bar"}},
        {"description": "this is a description", "unstructured_metadata": {"foo": "bar"}},
    ],
)
def test_create_robot_with_metadata(endpoint, body, client):
    with client_with_identity("devtable", client) as cl:
        # Create the robot with the specified body.
        conduct_api_call(
            cl,
            endpoint,
            "PUT",
            {"orgname": "buynlarge", "robot_shortname": "somebot"},
            body,
            expected_code=201,
        )

        # Ensure the create succeeded.
        resp = conduct_api_call(
            cl,
            endpoint,
            "GET",
            {
                "orgname": "buynlarge",
                "robot_shortname": "somebot",
            },
        )

        body = body or {}
        assert resp.json["description"] == (body.get("description") or "")
        assert resp.json["unstructured_metadata"] == (body.get("unstructured_metadata") or {})


@pytest.mark.parametrize(
    "endpoint, params",
    [
        (UserRobot, {"robot_shortname": "dtrobot"}),
        (OrgRobot, {"orgname": "buynlarge", "robot_shortname": "coolrobot"}),
    ],
)
def test_retrieve_robot(endpoint, params, app, client):
    with client_with_identity("devtable", client) as cl:
        result = conduct_api_call(cl, endpoint, "GET", params, None)
        assert result.json["token"] is not None


@pytest.mark.parametrize(
    "endpoint, params, bot_endpoint",
    [
        (UserRobotList, {}, UserRobot),
        (OrgRobotList, {"orgname": "buynlarge"}, OrgRobot),
    ],
)
@pytest.mark.parametrize(
    "include_token",
    [
        True,
        False,
    ],
)
@pytest.mark.parametrize(
    "limit",
    [
        None,
        1,
        5,
    ],
)
def test_retrieve_robots(endpoint, params, bot_endpoint, include_token, limit, app, client):
    params["token"] = "true" if include_token else "false"

    if limit is not None:
        params["limit"] = limit

    with client_with_identity("devtable", client) as cl:
        result = conduct_api_call(cl, endpoint, "GET", params, None)

        if limit is not None:
            assert len(result.json["robots"]) <= limit

        for robot in result.json["robots"]:
            assert (robot.get("token") is not None) == include_token
            if include_token:
                bot_params = dict(params)
                bot_params["robot_shortname"] = parse_robot_username(robot["name"])[1]
                result = conduct_api_call(cl, bot_endpoint, "GET", bot_params, None)
                assert robot.get("token") == result.json["token"]


@pytest.mark.parametrize(
    "username, is_admin",
    [
        ("devtable", True),
        ("reader", False),
    ],
)
@pytest.mark.parametrize(
    "with_permissions",
    [
        True,
        False,
    ],
)
def test_retrieve_robots_token_permission(username, is_admin, with_permissions, app, client):
    with client_with_identity(username, client) as cl:
        params = {"orgname": "buynlarge", "token": "true"}
        if with_permissions:
            params["permissions"] = "true"

        result = conduct_api_call(cl, OrgRobotList, "GET", params, None)
        assert result.json["robots"]
        for robot in result.json["robots"]:
            assert (robot.get("token") is not None) == is_admin
            assert (robot.get("repositories") is not None) == (is_admin and with_permissions)
