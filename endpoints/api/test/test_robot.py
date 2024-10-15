import json
from unittest.mock import Mock

import pytest
import requests

from data import model
from endpoints.api import api
from endpoints.api.robot import (
    OrgRobot,
    OrgRobotFederation,
    OrgRobotList,
    UserRobot,
    UserRobotList,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *
from test.test_ldap import mock_ldap
from util.names import parse_robot_username


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
        None,
        {},
        {"description": "this is a description"},
        {"unstructured_metadata": {"foo": "bar"}},
        {"description": "this is a description", "unstructured_metadata": {"foo": "bar"}},
    ],
)
def test_create_robot_with_metadata(endpoint, body, app):
    with client_with_identity("devtable", app) as cl:
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
def test_retrieve_robot(endpoint, params, app):
    with client_with_identity("devtable", app) as cl:
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
def test_retrieve_robots(endpoint, params, bot_endpoint, include_token, limit, app):
    params["token"] = "true" if include_token else "false"

    if limit is not None:
        params["limit"] = limit

    with client_with_identity("devtable", app) as cl:
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
def test_retrieve_robots_token_permission(username, is_admin, with_permissions, app):
    with client_with_identity(username, app) as cl:
        params = {"orgname": "buynlarge", "token": "true"}
        if with_permissions:
            params["permissions"] = "true"

        result = conduct_api_call(cl, OrgRobotList, "GET", params, None)
        assert result.json["robots"]
        for robot in result.json["robots"]:
            assert (robot.get("token") is not None) == is_admin
            assert (robot.get("repositories") is not None) == (is_admin and with_permissions)


def test_duplicate_robot_creation(app):
    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(
            cl,
            UserRobot,
            "PUT",
            {"robot_shortname": "dtrobot"},
            expected_code=400,
        )
        assert resp.json["error_message"] == "Existing robot with name: devtable+dtrobot"

        resp = conduct_api_call(
            cl,
            OrgRobot,
            "PUT",
            {"orgname": "buynlarge", "robot_shortname": "coolrobot"},
            expected_code=400,
        )
        assert resp.json["error_message"] == "Existing robot with name: buynlarge+coolrobot"


def test_robot_federation_create(app):
    with client_with_identity("devtable", app) as cl:
        # Create the robot with the specified body.
        conduct_api_call(
            cl,
            OrgRobotFederation,
            "POST",
            {
                "orgname": "buynlarge",
                "robot_shortname": "coolrobot",
            },
            [{"issuer": "https://issuer1", "subject": "subject1"}],
            expected_code=200,
        )

        # Ensure the create succeeded.
        resp = conduct_api_call(
            cl,
            OrgRobotFederation,
            "GET",
            {
                "orgname": "buynlarge",
                "robot_shortname": "coolrobot",
            },
            expected_code=200,
        )

        assert len(resp.json) == 1
        assert resp.json[0].get("issuer") == "https://issuer1"
        assert resp.json[0].get("subject") == "subject1"

        resp = conduct_api_call(
            cl,
            OrgRobotFederation,
            "DELETE",
            {
                "orgname": "buynlarge",
                "robot_shortname": "coolrobot",
            },
            expected_code=204,
        )

        resp = conduct_api_call(
            cl,
            OrgRobotFederation,
            "GET",
            {
                "orgname": "buynlarge",
                "robot_shortname": "coolrobot",
            },
            expected_code=200,
        )

        assert len(resp.json) == 0


@pytest.mark.parametrize(
    "fed_config, raises_error, error_message",
    [
        (
            [{"issuer": "issuer1", "subject": "subject1"}],
            True,
            "Issuer must be a URL (http:// or https://)",
        ),
        ([{"issuer": "https://issuer1", "subject": "subject1"}], False, None),
        (
            [{"bad_key": "issuer1", "subject": "subject1"}],
            True,
            "Missing one or more required fields",
        ),
        (
            [{"issuer": "https://issuer1", "subject": "subject1"}, {}],
            True,
            "Missing one or more required fields",
        ),
        (
            [
                {"issuer": "https://issuer1", "subject": "subject1"},
                {"issuer": "https://issuer2", "subject": "subject1"},
                {"issuer": "https://issuer1", "subject": "subject1"},
            ],
            True,
            "Duplicate federation config entry",
        ),
    ],
)
def test_parse_federation_config(app, fed_config, raises_error, error_message):
    request = Mock(requests.Request)
    request.json = fed_config

    with app.app_context():
        if raises_error:
            with pytest.raises(Exception) as ex:
                parsed = OrgRobotFederation()._parse_federation_config(request)
            assert error_message in str(ex.value)
        else:
            parsed = OrgRobotFederation()._parse_federation_config(request)
