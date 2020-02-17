import pytest

from data import model
from endpoints.api import api
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.organization import Organization, OrganizationCollaboratorList
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize(
    "expiration, expected_code", [(0, 200), (100, 400), (100000000000000000000, 400),]
)
def test_change_tag_expiration(expiration, expected_code, client):
    with client_with_identity("devtable", client) as cl:
        conduct_api_call(
            cl,
            Organization,
            "PUT",
            {"orgname": "buynlarge"},
            body={"tag_expiration_s": expiration},
            expected_code=expected_code,
        )


def test_get_organization_collaborators(client):
    params = {"orgname": "buynlarge"}

    with client_with_identity("devtable", client) as cl:
        resp = conduct_api_call(cl, OrganizationCollaboratorList, "GET", params)

    collaborator_names = [c["name"] for c in resp.json["collaborators"]]
    assert "outsideorg" in collaborator_names
    assert "devtable" not in collaborator_names
    assert "reader" not in collaborator_names

    for collaborator in resp.json["collaborators"]:
        if collaborator["name"] == "outsideorg":
            assert "orgrepo" in collaborator["repositories"]
            assert "anotherorgrepo" not in collaborator["repositories"]
