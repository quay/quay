import pytest

from data.model import immutability
from endpoints.api.immutability_policy import (
    OrgImmutabilityPolicies,
    OrgImmutabilityPolicy,
    RepositoryImmutabilityPolicies,
    RepositoryImmutabilityPolicy,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *  # noqa: F401, F403


class TestOrgImmutabilityPolicies:
    def test_list_empty(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            response = conduct_api_call(
                cl, OrgImmutabilityPolicies, "GET", {"orgname": "buynlarge"}
            ).json
            assert response["policies"] == []

    def test_create_and_list(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            # Create policy
            response = conduct_api_call(
                cl,
                OrgImmutabilityPolicies,
                "POST",
                {"orgname": "buynlarge"},
                {"tagPattern": "^v[0-9]+.*$"},
                201,
            ).json
            assert response["uuid"] is not None

            # List and verify
            response = conduct_api_call(
                cl, OrgImmutabilityPolicies, "GET", {"orgname": "buynlarge"}
            ).json
            assert len(response["policies"]) == 1
            assert response["policies"][0]["tagPattern"] == "^v[0-9]+.*$"

    def test_create_invalid_regex(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrgImmutabilityPolicies,
                "POST",
                {"orgname": "buynlarge"},
                {"tagPattern": "[invalid"},
                400,
            )

    def test_create_duplicate_policy(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            # Create first policy
            conduct_api_call(
                cl,
                OrgImmutabilityPolicies,
                "POST",
                {"orgname": "buynlarge"},
                {"tagPattern": "^v[0-9]+.*$"},
                201,
            )

            # Attempt to create duplicate - should return 400
            conduct_api_call(
                cl,
                OrgImmutabilityPolicies,
                "POST",
                {"orgname": "buynlarge"},
                {"tagPattern": "^v[0-9]+.*$"},
                400,
            )


class TestOrgImmutabilityPolicy:
    def test_get_update_delete(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            # Create
            created = conduct_api_call(
                cl,
                OrgImmutabilityPolicies,
                "POST",
                {"orgname": "buynlarge"},
                {"tagPattern": "^v1.*$"},
                201,
            ).json
            policy_uuid = created["uuid"]

            # Get
            response = conduct_api_call(
                cl,
                OrgImmutabilityPolicy,
                "GET",
                {"orgname": "buynlarge", "policy_uuid": policy_uuid},
            ).json
            assert response["tagPattern"] == "^v1.*$"

            # Update
            conduct_api_call(
                cl,
                OrgImmutabilityPolicy,
                "PUT",
                {"orgname": "buynlarge", "policy_uuid": policy_uuid},
                {"tagPattern": "^v2.*$"},
                204,
            )

            # Verify update
            response = conduct_api_call(
                cl,
                OrgImmutabilityPolicy,
                "GET",
                {"orgname": "buynlarge", "policy_uuid": policy_uuid},
            ).json
            assert response["tagPattern"] == "^v2.*$"

            # Delete
            conduct_api_call(
                cl,
                OrgImmutabilityPolicy,
                "DELETE",
                {"orgname": "buynlarge", "policy_uuid": policy_uuid},
                200,
            )

            # Verify deleted
            conduct_api_call(
                cl,
                OrgImmutabilityPolicy,
                "GET",
                {"orgname": "buynlarge", "policy_uuid": policy_uuid},
                expected_code=404,
            )


class TestRepositoryImmutabilityPolicies:
    def test_list_empty(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            response = conduct_api_call(
                cl,
                RepositoryImmutabilityPolicies,
                "GET",
                {"repository": "devtable/simple"},
            ).json
            assert response["policies"] == []

    def test_create_and_list(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            # Create policy
            response = conduct_api_call(
                cl,
                RepositoryImmutabilityPolicies,
                "POST",
                {"repository": "devtable/simple"},
                {"tagPattern": "^release-.*$"},
                201,
            ).json
            assert response["uuid"] is not None

            # List and verify
            response = conduct_api_call(
                cl,
                RepositoryImmutabilityPolicies,
                "GET",
                {"repository": "devtable/simple"},
            ).json
            assert len(response["policies"]) == 1
            assert response["policies"][0]["tagPattern"] == "^release-.*$"


class TestRepositoryImmutabilityPolicy:
    def test_crud(self, initialized_db, app):
        with client_with_identity("devtable", app) as cl:
            # Create
            created = conduct_api_call(
                cl,
                RepositoryImmutabilityPolicies,
                "POST",
                {"repository": "devtable/simple"},
                {"tagPattern": "^v1.*$"},
                201,
            ).json
            policy_uuid = created["uuid"]

            # Get
            response = conduct_api_call(
                cl,
                RepositoryImmutabilityPolicy,
                "GET",
                {"repository": "devtable/simple", "policy_uuid": policy_uuid},
            ).json
            assert response["tagPattern"] == "^v1.*$"

            # Update
            conduct_api_call(
                cl,
                RepositoryImmutabilityPolicy,
                "PUT",
                {"repository": "devtable/simple", "policy_uuid": policy_uuid},
                {"tagPattern": "^v2.*$", "tagPatternMatches": False},
                204,
            )

            # Delete
            conduct_api_call(
                cl,
                RepositoryImmutabilityPolicy,
                "DELETE",
                {"repository": "devtable/simple", "policy_uuid": policy_uuid},
                200,
            )
