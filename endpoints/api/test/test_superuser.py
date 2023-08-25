from test.fixtures import *

import pytest

from data.database import DeletedNamespace, User
from endpoints.api.superuser import (
    SuperUserList,
    SuperUserManagement,
    SuperUserOrganizationList,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity


@pytest.mark.parametrize(
    "disabled",
    [
        (True),
        (False),
    ],
)
def test_list_all_users(disabled, client):
    with client_with_identity("devtable", client) as cl:
        params = {"disabled": disabled}
        result = conduct_api_call(cl, SuperUserList, "GET", params, None, 200).json
        assert len(result["users"])
        for user in result["users"]:
            if not disabled:
                assert user["enabled"]


def test_list_all_orgs(client):
    with client_with_identity("devtable", client) as cl:
        result = conduct_api_call(cl, SuperUserOrganizationList, "GET", None, None, 200).json
        assert len(result["organizations"]) == 5


def test_paginate_orgs(client):
    with client_with_identity("devtable", client) as cl:
        params = {"limit": 3}
        firstResult = conduct_api_call(cl, SuperUserOrganizationList, "GET", params, None, 200).json
        assert len(firstResult["organizations"]) == 3
        assert firstResult["next_page"] is not None
        params["next_page"] = firstResult["next_page"]
        secondResult = conduct_api_call(
            cl, SuperUserOrganizationList, "GET", params, None, 200
        ).json
        assert len(secondResult["organizations"]) == 2
        assert secondResult.get("next_page", None) is None


def test_paginate_test_list_all_users(client):
    with client_with_identity("devtable", client) as cl:
        params = {"limit": 6}
        firstResult = conduct_api_call(cl, SuperUserList, "GET", params, None, 200).json
        assert len(firstResult["users"]) == 6
        assert firstResult["next_page"] is not None
        params["next_page"] = firstResult["next_page"]
        secondResult = conduct_api_call(cl, SuperUserList, "GET", params, None, 200).json
        assert len(secondResult["users"]) == 4
        assert secondResult.get("next_page", None) is None


def test_change_install_user(client):
    with client_with_identity("devtable", client) as cl:
        params = {"username": "randomuser"}
        body = {"email": "new_email123@test.com"}
        result = conduct_api_call(cl, SuperUserManagement, "PUT", params, body, 200).json

        assert result["email"] == body["email"]
