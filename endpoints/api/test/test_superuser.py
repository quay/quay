import pytest

from endpoints.api.superuser import SuperUserList, SuperUserManagement
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


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


def test_change_install_user(client):
    with client_with_identity("devtable", client) as cl:
        params = {"username": "randomuser"}
        body = {"email": "new_email123@test.com"}
        result = conduct_api_call(cl, SuperUserManagement, "PUT", params, body, 200).json

        assert result["email"] == body["email"]
