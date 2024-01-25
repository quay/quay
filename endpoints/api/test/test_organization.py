import pytest

from data import model
from endpoints.api import api
from endpoints.api.organization import (
    Organization,
    OrganizationApplications,
    OrganizationCollaboratorList,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize(
    "expiration, expected_code",
    [
        (0, 200),
        (100, 400),
        (100000000000000000000, 400),
    ],
)
def test_change_tag_expiration(expiration, expected_code, app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            Organization,
            "PUT",
            {"orgname": "buynlarge"},
            body={"tag_expiration_s": expiration},
            expected_code=expected_code,
        )


def test_get_organization_collaborators(app):
    params = {"orgname": "buynlarge"}

    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(cl, OrganizationCollaboratorList, "GET", params)

    collaborator_names = [c["name"] for c in resp.json["collaborators"]]
    assert "outsideorg" in collaborator_names
    assert "devtable" not in collaborator_names
    assert "reader" not in collaborator_names

    for collaborator in resp.json["collaborators"]:
        if collaborator["name"] == "outsideorg":
            assert "orgrepo" in collaborator["repositories"]
            assert "anotherorgrepo" not in collaborator["repositories"]


def test_create_oauth_application(app):
    payload = {"name": "test-app"}
    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(
            cl, OrganizationApplications, "POST", {"orgname": "buynlarge"}, payload, 200
        )

    assert resp.json["name"] == payload.get("name")


def test_create_local_oauth_application_without_scope(app):
    payload = {"name": "test-app", "local": True}
    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(
            cl, OrganizationApplications, "POST", {"orgname": "buynlarge"}, payload, 400
        )


def test_create_local_oauth_application_with_scope(app):
    payload = {"name": "test-app", "local": True, "scope": "org:admin"}
    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(
            cl, OrganizationApplications, "POST", {"orgname": "buynlarge"}, payload, 200
        )
    assert resp.json["access_token"] is not None
