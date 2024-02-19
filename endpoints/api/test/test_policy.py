import json

import pytest

from data import database, model
from data.model.log import get_latest_logs_query, get_log_entry_kinds
from endpoints.api.policy import (
    OrgAutoPrunePolicies,
    OrgAutoPrunePolicy,
    RepositoryAutoPrunePolicies,
    RepositoryAutoPrunePolicy,
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

        # Check audit log was created
        logs = list(get_latest_logs_query(performer="devtable", namespace="sellnsmall"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["create_namespace_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["method"] == "creation_date"
        assert json.loads(log.metadata_json)["value"] == "2w"
        assert json.loads(log.metadata_json)["namespace"] == "sellnsmall"


def test_create_org_policy_already_existing(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            OrgAutoPrunePolicies,
            "POST",
            {"orgname": "buynlarge"},
            {"method": "creation_date", "value": "2w"},
            expected_code=400,
        ).json
        assert (
            response["error_message"]
            == "Policy for this namespace already exists, delete existing to create new policy"
        )


def test_create_org_policy_nonexistent_method(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            OrgAutoPrunePolicies,
            "POST",
            {"orgname": "sellnsmall"},
            {"method": "doesnotexist", "value": "2w"},
            expected_code=400,
        ).json
        assert response["error_message"] == "Invalid method provided"


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

        # Check audit log was created
        logs = list(get_latest_logs_query(performer="devtable", namespace="buynlarge"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["update_namespace_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["method"] == "creation_date"
        assert json.loads(log.metadata_json)["value"] == "2w"
        assert json.loads(log.metadata_json)["namespace"] == "buynlarge"


def test_update_org_policy_nonexistent_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrgAutoPrunePolicy,
            "PUT",
            {"orgname": "buynlarge", "policy_uuid": "doesnotexist"},
            {"method": "creation_date", "value": "2w"},
            expected_code=404,
        )


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

        # Check audit log was created
        logs = list(get_latest_logs_query(performer="devtable", namespace="buynlarge"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["delete_namespace_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["policy_uuid"] == policy_uuid
        assert json.loads(log.metadata_json)["namespace"] == "buynlarge"


def test_delete_org_policy_nonexistent_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrgAutoPrunePolicy,
            "DELETE",
            {"orgname": "buynlarge", "policy_uuid": "doesnotexist"},
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

        # Check audit log was created
        logs = list(get_latest_logs_query(performer="freshuser", namespace="freshuser"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["create_namespace_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["method"] == "creation_date"
        assert json.loads(log.metadata_json)["value"] == "2w"
        assert json.loads(log.metadata_json)["namespace"] == "freshuser"


def test_create_user_policy_already_existing(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            UserAutoPrunePolicies,
            "POST",
            {"orgname": "devtable"},
            {"method": "creation_date", "value": "2w"},
            expected_code=400,
        ).json
        assert (
            response["error_message"]
            == "Policy for this namespace already exists, delete existing to create new policy"
        )


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

        # Check audit log was created
        logs = list(get_latest_logs_query(performer="devtable", namespace="devtable"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["update_namespace_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["method"] == "creation_date"
        assert json.loads(log.metadata_json)["value"] == "2w"
        assert json.loads(log.metadata_json)["namespace"] == "devtable"


def test_update_user_policy_nonexistent_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            UserAutoPrunePolicy,
            "PUT",
            {"orgname": "devtable", "policy_uuid": "doesnotexist"},
            {"method": "creation_date", "value": "2w"},
            expected_code=404,
        )


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

        # Check audit log was created
        logs = list(get_latest_logs_query(performer="devtable", namespace="devtable"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["delete_namespace_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["policy_uuid"] == policy_uuid
        assert json.loads(log.metadata_json)["namespace"] == "devtable"


def test_delete_user_policy_nonexistent_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            UserAutoPrunePolicy,
            "DELETE",
            {"orgname": "devtable", "policy_uuid": "doesnotexist"},
            expected_code=404,
        )


def test_get_repo_policies(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        params = {"repository": "devtable/simple"}
        response = conduct_api_call(cl, RepositoryAutoPrunePolicies, "GET", params).json
        assert len(response["policies"]) == 1
        assert response["policies"][0]["method"] == "number_of_tags"
        assert response["policies"][0]["value"] == 10


def test_create_repo_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        params = {"repository": "testorgforautoprune/autoprunerepo"}
        response = conduct_api_call(
            cl,
            RepositoryAutoPrunePolicies,
            "POST",
            params,
            {"method": "creation_date", "value": "2w"},
            201,
        ).json
        assert response["uuid"] is not None
        assert (
            model.autoprune.get_repository_autoprune_policy_by_uuid(response["uuid"])
            is not None
        )
        org = model.organization.get_organization("testorgforautoprune")
        assert model.autoprune.namespace_has_autoprune_task(org.id)

        # Check audit log was created
        logs = list(get_latest_logs_query(namespace="testorgforautoprune"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["create_repository_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["method"] == "creation_date"
        assert json.loads(log.metadata_json)["value"] == "2w"
        assert json.loads(log.metadata_json)["namespace"] == "testorgforautoprune"


def test_create_repo_policy_already_existing(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        params = {"repository": "devtable/simple"}        
        response = conduct_api_call(
            cl,
            RepositoryAutoPrunePolicies,
            "POST",
            params,
            {"method": "creation_date", "value": "2w"},
            expected_code=400,
        ).json
        assert (
            response["error_message"]
            == "Policy for this repository already exists, delete existing to create new policy"
        )


def test_create_repo_policy_nonexistent_method(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        params = {"repository": "testorgforautoprune/autoprunerepo"}
        response = conduct_api_call(
            cl,
            RepositoryAutoPrunePolicies,
            "POST",
            params,
            {"method": "doesnotexist", "value": "2w"},
            expected_code=400,
        ).json
        assert response["error_message"] == "Invalid method provided"


def test_get_repo_policy(initialized_db, app):
    policies = model.autoprune.get_repository_autoprune_policies_by_repo_name("devtable","simple")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        params = {"repository": "devtable/simple", "policy_uuid": policy_uuid}
        response = conduct_api_call(
            cl, RepositoryAutoPrunePolicy, "GET", params
        ).json
        assert response["method"] == "number_of_tags"
        assert response["value"] == 10


def test_update_repo_policy(initialized_db, app):
    policies = model.autoprune.get_repository_autoprune_policies_by_repo_name("devtable","simple")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        params_for_update = {"repository": "devtable/simple", "policy_uuid": policy_uuid}
        conduct_api_call(
            cl,
            RepositoryAutoPrunePolicy,
            "PUT",
            params_for_update,
            {"method": "creation_date", "value": "2w"},
            expected_code=204,
        )

        # Make another request asserting it was updated
        params = {"repository": "devtable/simple", "policy_uuid": policy_uuid}
        get_response = conduct_api_call(
            cl, RepositoryAutoPrunePolicy, "GET", params
        ).json
        assert get_response["method"] == "creation_date"
        assert get_response["value"] == "2w"

        # Check audit log was created
        logs = list(get_latest_logs_query(namespace="devtable"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["update_repository_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["method"] == "creation_date"
        assert json.loads(log.metadata_json)["value"] == "2w"
        assert json.loads(log.metadata_json)["namespace"] == "devtable"


def test_update_repo_policy_nonexistent_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        params_for_update = {"repository": "devtable/simple", "policy_uuid": "doesnotexist"}
        conduct_api_call(
            cl,
            RepositoryAutoPrunePolicy,
            "PUT",
            params_for_update,
            {"method": "creation_date", "value": "2w"},
            expected_code=404,
        )


def test_delete_repo_policy(initialized_db, app):
    policies = model.autoprune.get_repository_autoprune_policies_by_repo_name("devtable","simple")
    assert len(policies) == 1
    policy_uuid = policies[0].uuid
    with client_with_identity("devtable", app) as cl:
        params_for_delete = {"repository": "devtable/simple", "policy_uuid": policy_uuid}
        conduct_api_call(
            cl,
            RepositoryAutoPrunePolicy,
            "DELETE",
            params_for_delete,
            expected_code=200,
        )
        params = {"repository": "devtable/simple", "policy_uuid": policy_uuid}
        conduct_api_call(
            cl,
            RepositoryAutoPrunePolicy,
            "GET",
            params,
            expected_code=404,
        )

        # Check audit log was created
        logs = list(get_latest_logs_query(namespace="devtable"))
        log_kinds = get_log_entry_kinds()
        log = None
        for l in logs:
            if l.kind == log_kinds["delete_repository_autoprune_policy"]:
                log = l
                break
        assert log is not None
        assert json.loads(log.metadata_json)["policy_uuid"] == policy_uuid
        assert json.loads(log.metadata_json)["namespace"] == "devtable"


def test_delete_repo_policy_nonexistent_policy(initialized_db, app):
    with client_with_identity("devtable", app) as cl:
        params_for_delete = {"repository": "testorgforautoprune/autoprunerepo", "policy_uuid": "doesnotexist"}
        conduct_api_call(
            cl,
            RepositoryAutoPrunePolicy,
            "DELETE",
            params_for_delete,
            expected_code=404,
        )
