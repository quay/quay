from unittest.mock import patch

from endpoints.api.robot import OrgRobotList
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *  # noqa: F401,F403


def test_org_robot_list_global_readonly_can_view_without_tokens(app):
    with patch("endpoints.api.robot.allow_if_superuser", return_value=False), patch(
        "endpoints.api.robot.allow_if_global_readonly_superuser", return_value=True
    ):
        with client_with_identity("reader", app) as cl:
            resp = conduct_api_call(
                cl, OrgRobotList, "GET", {"orgname": "devtable"}, None, 200
            ).json

            # Should include robots but not tokens in list view for global readonly
            assert "robots" in resp
            if resp["robots"]:
                assert "token" not in resp["robots"][0]
