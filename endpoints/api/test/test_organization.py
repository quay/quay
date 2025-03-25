import pytest
from mock import patch

from app import app as realapp
from data import model
from endpoints.api import api
from endpoints.api.organization import (
    Organization,
    OrganizationCollaboratorList,
    OrganizationList,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue
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


def test_create_org_as_superuser_with_restricted_users_set(app):
    body = {
        "name": "buyandlarge",
        "email": "some@email.com",
    }

    # check if super users can create organizations regardles of restricted users set
    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl, OrganizationList, "POST", None, body=body, expected_code=201
            )

    # unset all super users temporarily
    superuser_list = realapp.config.get("SUPER_USERS")
    realapp.config["SUPER_USERS"] = []

    body = {
        "name": "buyandlargetimes2",
        "email": "some1@email.com",
    }

    # check if users who are not super users can create organizations when restricted users is set
    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl, OrganizationList, "POST", None, body=body, expected_code=403
            )

    # reset superuser list to previous value
    realapp.config["SUPER_USERS"] = superuser_list
