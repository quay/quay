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

    body = {
        "name": "buyandlargetimes2",
        "email": "some1@email.com",
    }

    # check if users who are not super users can create organizations when restricted users is set
    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with patch("endpoints.api.organization.usermanager.is_superuser", return_value=False):
            with client_with_identity("devtable", app) as cl:
                conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=403)


def test_create_org_as_ldap_superuser_with_restricted_users_set(app):
    """
    Test that LDAP-detected superusers can create organizations
    even when not in the config SUPER_USERS list.
    """
    body = {
        "name": "ldapsuperuserorg",
        "email": "ldap@email.com",
    }

    # Remove user from config SUPER_USERS to simulate LDAP-only superuser
    superuser_list = realapp.config.get("SUPER_USERS")
    realapp.config["SUPER_USERS"] = []

    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        # Mock usermanager.is_superuser to return True (simulating LDAP detection)
        with patch("endpoints.api.organization.usermanager.is_superuser", return_value=True):
            with client_with_identity("devtable", app) as cl:
                conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=201)

    # Restore superuser list
    realapp.config["SUPER_USERS"] = superuser_list


@pytest.mark.parametrize(
    "is_superuser, is_restricted, expected_code",
    [
        # LDAP superuser + not restricted by LDAP -> allowed
        (True, False, 201),
        # LDAP superuser + restricted by LDAP -> allowed (superuser bypass)
        (True, True, 201),
        # Non-superuser + restricted -> forbidden
        (False, True, 403),
    ],
)
def test_create_org_ldap_restricted_user_no_whitelist(
    is_superuser, is_restricted, expected_code, app
):
    """
    Test org creation when FEATURE_RESTRICTED_USERS is enabled without
    RESTRICTED_USERS_WHITELIST (the LDAP-only restricted user path).
    Verifies LDAP superusers not matched by LDAP_RESTRICTED_USER_FILTER
    are not incorrectly blocked.
    """
    suffix = f"{str(is_superuser).lower()}{str(is_restricted).lower()}"
    body = {
        "name": f"ldaprestrictedorg{suffix}",
        "email": f"ldap{suffix}@email.com",
    }

    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with patch(
            "endpoints.api.organization.usermanager.is_superuser",
            return_value=is_superuser,
        ):
            with patch(
                "endpoints.api.organization.usermanager.is_restricted_user",
                return_value=is_restricted,
            ):
                with client_with_identity("devtable", app) as cl:
                    conduct_api_call(
                        cl, OrganizationList, "POST", None, body=body, expected_code=expected_code
                    )
