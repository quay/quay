import pytest

from data import model
from data.model import vulnerabilitysuppression
from endpoints.api import api
from endpoints.api.organization import Organization, OrganizationCollaboratorList
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


def test_organization_vulnerability_suppression(client):
    with client_with_identity("devtable", client) as cl:
        suppressed_vulnerabilities = ["CVE-2019-1234"]

        org = model.organization.get_organization("buynlarge")
        suppression = vulnerabilitysuppression.create_vulnerability_suppression_for_org(
            org, suppressed_vulnerabilities
        )

        assert suppression.vulnerability_names == suppressed_vulnerabilities

        params = {
            "orgname": "buynlarge",
        }

        # check that we are getting the expected suppressed vulnerabilities
        result = conduct_api_call(cl, Organization, "GET", params, None, 200).json

        assert result["suppressed_vulnerabilities"] == suppressed_vulnerabilities

        # check that we can set new suppressed vulnerabilities

        new_vulnerability_suppression = ["CVE-2019-1234", "CVE-2019-5678"]
        params = {
            "orgname": "buynlarge",
        }

        body = {"suppressed_vulnerabilities": new_vulnerability_suppression}

        result = conduct_api_call(cl, Organization, "PUT", params, body, 200)

        assert result.status_code == 200
        assert result.json["suppressed_vulnerabilities"] == new_vulnerability_suppression
        assert (
            vulnerabilitysuppression.get_vulnerability_suppression_for_org(org)
            == new_vulnerability_suppression
        )

        # check that we can clear suppressed vulnerabilities by passing an empty list

        params = {
            "orgname": "buynlarge",
        }

        body = {"suppressed_vulnerabilities": []}

        result = conduct_api_call(cl, Organization, "PUT", params, body, 200)

        assert result.status_code == 200
        assert result.json["suppressed_vulnerabilities"] == []
        assert vulnerabilitysuppression.get_vulnerability_suppression_for_org(org) == []


@pytest.mark.parametrize(
    "suppressed_vulns",
    [
        (" CVE-2019-1234 ",),
        (" CVE-2019-1234",),
        ("CVE-2019-1234 ",),
        (" ",),
        ("",),
    ],
)
def test_organization_vulnerability_suppression_invalid(client, suppressed_vulns):
    with client_with_identity("devtable", client) as cl:
        params = {
            "orgname": "buynlarge",
        }

        body = {"suppressed_vulnerabilities": suppressed_vulns}

        result = conduct_api_call(cl, Organization, "PUT", params, body, 400)

        assert result.status_code == 400
