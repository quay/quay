import pytest

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.permission import RepositoryUserPermission
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize(
    "repository, username, expected_code",
    [
        pytest.param("devtable/simple", "public", 200, id="valid user under user"),
        pytest.param("devtable/simple", "devtable+dtrobot", 200, id="valid robot under user"),
        pytest.param("devtable/simple", "buynlarge+coolrobot", 400, id="invalid robot under user"),
        pytest.param("buynlarge/orgrepo", "devtable", 200, id="valid user under org"),
        pytest.param("buynlarge/orgrepo", "devtable+dtrobot", 400, id="invalid robot under org"),
        pytest.param("buynlarge/orgrepo", "buynlarge+coolrobot", 200, id="valid robot under org"),
    ],
)
def test_robot_permission(repository, username, expected_code, client):
    with client_with_identity("devtable", client) as cl:
        conduct_api_call(
            cl,
            RepositoryUserPermission,
            "PUT",
            {"repository": repository, "username": username},
            body={
                "role": "read",
            },
            expected_code=expected_code,
        )
