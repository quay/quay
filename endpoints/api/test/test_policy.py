import pytest

from data import database, model
from endpoints.api.policy import (
    OrgAutoPrunePolicies,
    OrgAutoPrunePolicy,
    UserAutoPrunePolicies,
    UserAutoPrunePolicy,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def test_get_org_policies(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(cl, OrgAutoPrunePolicies, "GET", {"orgname": "buynlarge"}).json
        assert len(response["policies"]) == 1
        assert response["policies"][0]["method"] == "creation_date"
        assert response["policies"][0]["value"] == "5d"


def test_create_org_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            OrgAutoPrunePolicies,
            "POST",
            {"orgname": "sellnsmall"},
            {"method": "creation_date", "value": "2w"},
            201,
        ).json
        assert response["uuid"] is not None
        assert (
            model.autoprune.get_namespace_autoprune_policy("sellnsmall", response["uuid"])
            is not None
        )
        org = model.organization.get_organization("sellnsmall")
        assert model.autoprune.namespace_has_autoprune_task(org.id)


def test_get_org_policy(initialized_db, app):
    policies = model.autoprune.get_namespace_autoprune_policies_by_orgname("buynlarge")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl, OrgAutoPrunePolicy, "GET", {"orgname": "buynlarge", "policy_uuid": policy_uuid}
        ).json
        assert response["method"] == "creation_date"
        assert response["value"] == "5d"


def test_update_org_policy(initialized_db, app):
    policies = model.autoprune.get_namespace_autoprune_policies_by_orgname("buynlarge")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrgAutoPrunePolicy,
            "PUT",
            {"orgname": "buynlarge", "policy_uuid": policy_uuid},
            {"method": "creation_date", "value": "2w"},
            expected_code=204,
        )

        # Make another request asserting it was updated
        get_response = conduct_api_call(
            cl, OrgAutoPrunePolicy, "GET", {"orgname": "buynlarge", "policy_uuid": policy_uuid}
        ).json
        assert get_response["method"] == "creation_date"
        assert get_response["value"] == "2w"


def test_delete_org_policy(initialized_db, app):
    policies = model.autoprune.get_namespace_autoprune_policies_by_orgname("buynlarge")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrgAutoPrunePolicy,
            "DELETE",
            {"orgname": "buynlarge", "policy_uuid": policy_uuid},
            expected_code=200,
        )
        conduct_api_call(
            cl,
            OrgAutoPrunePolicy,
            "GET",
            {"orgname": "buynlarge", "policy_uuid": policy_uuid},
            expected_code=404,
        )


def test_get_user_policies(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(cl, UserAutoPrunePolicies, "GET", {"orgname": "devtable"}).json
        assert len(response["policies"]) == 1
        assert response["policies"][0]["method"] == "number_of_tags"
        assert response["policies"][0]["value"] == 10


def test_create_user_policy(initialized_db, app):
    with client_with_identity("freshuser", app) as cl:
        response = conduct_api_call(
            cl,
            UserAutoPrunePolicies,
            "POST",
            {"orgname": "freshuser"},
            {"method": "creation_date", "value": "2w"},
            201,
        ).json
        assert response["uuid"] is not None
        assert (
            model.autoprune.get_namespace_autoprune_policy("freshuser", response["uuid"])
            is not None
        )
        org = model.user.get_user("freshuser")
        assert model.autoprune.namespace_has_autoprune_task(org.id)


def test_get_user_policy(initialized_db, app):
    policies = model.autoprune.get_namespace_autoprune_policies_by_orgname("devtable")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl, UserAutoPrunePolicy, "GET", {"orgname": "devtable", "policy_uuid": policy_uuid}
        ).json
        assert response["method"] == "number_of_tags"
        assert response["value"] == 10


def test_update_user_policy(initialized_db, app):
    policies = model.autoprune.get_namespace_autoprune_policies_by_orgname("devtable")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            UserAutoPrunePolicy,
            "PUT",
            {"orgname": "devtable", "policy_uuid": policy_uuid},
            {"method": "creation_date", "value": "2w"},
            204,
        )
        assert response is not None

        # Make another request asserting it was updated
        get_response = conduct_api_call(
            cl, UserAutoPrunePolicy, "GET", {"orgname": "devtable", "policy_uuid": policy_uuid}
        ).json
        assert get_response["method"] == "creation_date"
        assert get_response["value"] == "2w"


def test_delete_user_policy(initialized_db, app):
    policies = model.autoprune.get_namespace_autoprune_policies_by_orgname("devtable")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            UserAutoPrunePolicy,
            "DELETE",
            {"orgname": "devtable", "policy_uuid": policy_uuid},
            expected_code=200,
        )
        conduct_api_call(
            cl,
            UserAutoPrunePolicy,
            "GET",
            {"orgname": "devtable", "policy_uuid": policy_uuid},
            expected_code=404,
        )
