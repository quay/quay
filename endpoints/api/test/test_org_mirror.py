"""
Unit and integration tests for organization mirror API endpoints.

Tests CRUD operations, discovered repositories, and sync triggering.
"""

from datetime import datetime

import pytest

from data import model
from data.database import OrgMirrorRepoStatus, OrgMirrorStatus
from endpoints.api.org_mirror import (
    OrganizationMirrorRepositoriesResource,
    OrganizationMirrorResource,
    OrganizationMirrorSyncNowResource,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def _create_org_robot(orgname, robot_name):
    """Helper to create a robot account for an organization."""
    org = model.organization.get_organization(orgname)
    robot, _ = model.user.create_robot(robot_name, org)
    return robot


def _create_org_mirror(orgname, robot, **kwargs):
    """Helper to create an organization mirror configuration."""
    mirror_kwargs = {
        "is_enabled": True,
        "external_reference": "harbor.example.com/test-project",
        "sync_interval": 3600,
        "skopeo_timeout": 300,
        "external_registry_username": "testuser",
        "external_registry_password": "testpass",
        "external_registry_config": {"verify_tls": True},
    }
    mirror_kwargs.update(kwargs)

    mirror = model.org_mirror.create_org_mirror(
        org_name=orgname, internal_robot=robot, **mirror_kwargs
    )

    return mirror


# Test GET endpoint


def test_get_org_mirror_not_exists(app):
    """Test GET when org mirror doesn't exist."""
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorResource, "GET", params, None, 404)


def test_get_org_mirror_unauthorized(app):
    """Test GET without permission."""
    # Create mirror for buynlarge
    robot = _create_org_robot("buynlarge", "mirrorbot")
    _create_org_mirror("buynlarge", robot)

    # Try to access as devtable (not a member)
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorResource, "GET", params, None, 403)


def test_get_org_mirror_success(app):
    """Test successful GET of org mirror config."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror(
        "buynlarge",
        robot,
        external_reference="harbor.example.com/my-project",
        sync_interval=7200,
    )

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        resp = conduct_api_call(cl, OrganizationMirrorResource, "GET", params, None, 200)

        assert resp.json["external_reference"] == "harbor.example.com/my-project"
        assert resp.json["sync_interval"] == 7200
        assert resp.json["internal_robot"] == robot.username
        assert resp.json["sync_status"] == "NEVER_RUN"
        assert resp.json["is_enabled"] is True


# Test POST endpoint


def test_create_org_mirror_already_exists(app):
    """Test POST when mirror already exists."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    _create_org_mirror("buynlarge", robot)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "external_reference": "harbor.example.com/project",
            "sync_interval": 3600,
            "internal_robot": robot.username,
            "skopeo_timeout": 300,
        }
        conduct_api_call(cl, OrganizationMirrorResource, "POST", params, request_body, 400)


def test_create_org_mirror_invalid_robot(app):
    """Test POST with invalid robot account."""
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "external_reference": "harbor.example.com/project",
            "sync_interval": 3600,
            "internal_robot": "notarobot",
            "skopeo_timeout": 300,
        }
        conduct_api_call(cl, OrganizationMirrorResource, "POST", params, request_body, 400)


def test_create_org_mirror_wrong_org_robot(app):
    """Test POST with robot from different org."""
    robot = _create_org_robot("buynlarge", "mirrorbot")

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "sellnsmall"}  # Different org
        request_body = {
            "external_reference": "harbor.example.com/project",
            "sync_interval": 3600,
            "internal_robot": robot.username,  # buynlarge robot
            "skopeo_timeout": 300,
        }
        conduct_api_call(cl, OrganizationMirrorResource, "POST", params, request_body, 400)


def test_create_org_mirror_success(app):
    """Test successful creation of org mirror."""
    robot = _create_org_robot("buynlarge", "mirrorbot")

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "external_reference": "harbor.example.com/my-project",
            "sync_interval": 7200,
            "internal_robot": robot.username,
            "skopeo_timeout": 600,
            "external_registry_username": "myuser",
            "external_registry_password": "mypass",
            "external_registry_config": {"verify_tls": False},
            "is_enabled": True,
        }
        resp = conduct_api_call(cl, OrganizationMirrorResource, "POST", params, request_body, 201)

        assert resp.json["external_reference"] == "harbor.example.com/my-project"
        assert resp.json["sync_interval"] == 7200
        assert resp.json["internal_robot"] == robot.username
        assert resp.json["skopeo_timeout"] == 600
        assert resp.json["is_enabled"] is True
        assert resp.json["external_registry_config"]["verify_tls"] is False

    # Verify it was actually created
    mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    assert mirror is not None
    assert mirror.external_reference == "harbor.example.com/my-project"


def test_create_org_mirror_with_filtering_rule(app):
    """Test creating org mirror with repository filtering rule."""
    robot = _create_org_robot("buynlarge", "mirrorbot")

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "external_reference": "harbor.example.com/project",
            "sync_interval": 3600,
            "internal_robot": robot.username,
            "skopeo_timeout": 300,
            "root_rule": {
                "rule_type": "REPO_NAME_REGEX",
                "rule_value": {"pattern": "^prod-.*"},
            },
        }
        resp = conduct_api_call(cl, OrganizationMirrorResource, "POST", params, request_body, 201)

        assert resp.json["root_rule"] is not None
        assert resp.json["root_rule"]["rule_type"] == "REPO_NAME_REGEX"
        assert resp.json["root_rule"]["rule_value"]["pattern"] == "^prod-.*"


# Test PUT endpoint


def test_update_org_mirror_not_exists(app):
    """Test PUT when mirror doesn't exist."""
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {"sync_interval": 7200}
        conduct_api_call(cl, OrganizationMirrorResource, "PUT", params, request_body, 404)


def test_update_org_mirror_success(app):
    """Test successful update of org mirror."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot, sync_interval=3600)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "sync_interval": 7200,
            "is_enabled": False,
            "external_reference": "harbor.example.com/updated-project",
        }
        resp = conduct_api_call(cl, OrganizationMirrorResource, "PUT", params, request_body, 200)

        assert resp.json["sync_interval"] == 7200
        assert resp.json["is_enabled"] is False
        assert resp.json["external_reference"] == "harbor.example.com/updated-project"

    # Verify changes persisted
    updated_mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    assert updated_mirror.sync_interval == 7200
    assert updated_mirror.is_enabled is False


def test_update_org_mirror_change_robot(app):
    """Test updating the robot account."""
    robot1 = _create_org_robot("buynlarge", "mirrorbot1")
    robot2 = _create_org_robot("buynlarge", "mirrorbot2")

    mirror = _create_org_mirror("buynlarge", robot1)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {"internal_robot": robot2.username}
        resp = conduct_api_call(cl, OrganizationMirrorResource, "PUT", params, request_body, 200)

        assert resp.json["internal_robot"] == robot2.username

    # Verify change
    updated_mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    assert updated_mirror.internal_robot.username == robot2.username


def test_update_org_mirror_add_filtering_rule(app):
    """Test adding a filtering rule via update."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "root_rule": {
                "rule_type": "REPO_NAME_LIST",
                "rule_value": {"names": "repo1,repo2,repo3"},
            }
        }
        resp = conduct_api_call(cl, OrganizationMirrorResource, "PUT", params, request_body, 200)

        assert resp.json["root_rule"] is not None
        assert resp.json["root_rule"]["rule_type"] == "REPO_NAME_LIST"


def test_update_org_mirror_remove_filtering_rule(app):
    """Test removing a filtering rule via update."""
    from data.database import RepoMirrorRule, RepoMirrorRuleType

    robot = _create_org_robot("buynlarge", "mirrorbot")

    # Create rule
    rule = RepoMirrorRule.create(
        rule_type=RepoMirrorRuleType.REPO_NAME_REGEX,
        rule_value={"pattern": "^prod-.*"},
    )

    mirror = _create_org_mirror("buynlarge", robot, root_rule=rule)
    assert mirror.root_rule is not None

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {"root_rule": None}
        resp = conduct_api_call(cl, OrganizationMirrorResource, "PUT", params, request_body, 200)

        assert resp.json["root_rule"] is None

    # Verify removal
    updated_mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    assert updated_mirror.root_rule is None


# Test DELETE endpoint


def test_delete_org_mirror_not_exists(app):
    """Test DELETE when mirror doesn't exist."""
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorResource, "DELETE", params, None, 404)


def test_delete_org_mirror_success(app):
    """Test successful deletion of org mirror."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorResource, "DELETE", params, None, 204)

    # Verify deletion
    deleted_mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    assert deleted_mirror is None


# Test discovered repositories endpoint


def test_get_discovered_repos_mirror_not_exists(app):
    """Test GET discovered repos when mirror doesn't exist."""
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorRepositoriesResource, "GET", params, None, 404)


def test_get_discovered_repos_empty(app):
    """Test GET discovered repos when none exist."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        resp = conduct_api_call(
            cl, OrganizationMirrorRepositoriesResource, "GET", params, None, 200
        )

        assert resp.json["repositories"] == []


def test_get_discovered_repos_with_repos(app):
    """Test GET discovered repos with some repositories."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot)

    # Record some discovered repos
    discovered = [
        {"name": "repo1", "external_reference": "harbor.example.com/project/repo1"},
        {"name": "repo2", "external_reference": "harbor.example.com/project/repo2"},
    ]
    model.org_mirror.record_discovered_repos(mirror, discovered)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        resp = conduct_api_call(
            cl, OrganizationMirrorRepositoriesResource, "GET", params, None, 200
        )

        assert len(resp.json["repositories"]) == 2
        assert resp.json["repositories"][0]["repository_name"] == "repo1"
        assert resp.json["repositories"][0]["status"] == "PENDING"
        assert resp.json["repositories"][1]["repository_name"] == "repo2"


def test_get_discovered_repos_filtered_by_status(app):
    """Test GET discovered repos with status filter."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot)

    # Record repos and mark one as created
    discovered = [
        {"name": "repo1", "external_reference": "harbor.example.com/project/repo1"},
        {"name": "repo2", "external_reference": "harbor.example.com/project/repo2"},
    ]
    model.org_mirror.record_discovered_repos(mirror, discovered)

    # Mark repo1 as created
    repos_to_create = model.org_mirror.repos_to_create(mirror)
    repo1 = repos_to_create[0]
    created_repo = model.repository.create_repository(
        "buynlarge", "repo1", robot, description="Created by org mirror"
    )
    model.org_mirror.mark_repo_created(repo1, created_repo)

    # Get only PENDING repos
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        resp = conduct_api_call(
            cl,
            OrganizationMirrorRepositoriesResource,
            "GET",
            params,
            None,
            200,
            query_string="status=pending",
        )

        # Should only get repo2
        assert len(resp.json["repositories"]) == 1
        assert resp.json["repositories"][0]["repository_name"] == "repo2"
        assert resp.json["repositories"][0]["status"] == "PENDING"


# Test sync-now endpoint


def test_sync_now_mirror_not_exists(app):
    """Test POST sync-now when mirror doesn't exist."""
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorSyncNowResource, "POST", params, None, 404)


def test_sync_now_mirror_disabled(app):
    """Test POST sync-now when mirror is disabled."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot, is_enabled=False)

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorSyncNowResource, "POST", params, None, 400)


def test_sync_now_success(app):
    """Test successful trigger of immediate sync."""
    robot = _create_org_robot("buynlarge", "mirrorbot")
    mirror = _create_org_mirror("buynlarge", robot)

    assert mirror.sync_status == OrgMirrorStatus.NEVER_RUN

    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        resp = conduct_api_call(cl, OrganizationMirrorSyncNowResource, "POST", params, None, 200)

        assert resp.json["status"] == "sync_triggered"

    # Verify status changed to SYNC_NOW
    updated_mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    assert updated_mirror.sync_status == OrgMirrorStatus.SYNC_NOW


# Integration tests


def test_full_crud_cycle(app):
    """Integration test for full CRUD cycle."""
    robot = _create_org_robot("buynlarge", "mirrorbot")

    # CREATE
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "external_reference": "harbor.example.com/project",
            "sync_interval": 3600,
            "internal_robot": robot.username,
            "skopeo_timeout": 300,
        }
        create_resp = conduct_api_call(
            cl, OrganizationMirrorResource, "POST", params, request_body, 201
        )
        assert create_resp.json["external_reference"] == "harbor.example.com/project"

    # READ
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        get_resp = conduct_api_call(cl, OrganizationMirrorResource, "GET", params, None, 200)
        assert get_resp.json["external_reference"] == "harbor.example.com/project"
        assert get_resp.json["sync_interval"] == 3600

    # UPDATE
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {"sync_interval": 7200}
        update_resp = conduct_api_call(
            cl, OrganizationMirrorResource, "PUT", params, request_body, 200
        )
        assert update_resp.json["sync_interval"] == 7200

    # DELETE
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorResource, "DELETE", params, None, 204)

    # Verify deletion
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        conduct_api_call(cl, OrganizationMirrorResource, "GET", params, None, 404)


def test_full_workflow_with_discovered_repos(app):
    """Integration test for full workflow including discovered repositories."""
    robot = _create_org_robot("buynlarge", "mirrorbot")

    # Create mirror
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        request_body = {
            "external_reference": "harbor.example.com/project",
            "sync_interval": 3600,
            "internal_robot": robot.username,
            "skopeo_timeout": 300,
        }
        conduct_api_call(cl, OrganizationMirrorResource, "POST", params, request_body, 201)

    # Record discovered repos (simulate worker discovery)
    mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    discovered = [
        {"name": "api", "external_reference": "harbor.example.com/project/api"},
        {"name": "web", "external_reference": "harbor.example.com/project/web"},
    ]
    model.org_mirror.record_discovered_repos(mirror, discovered)

    # Get discovered repos
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        resp = conduct_api_call(
            cl, OrganizationMirrorRepositoriesResource, "GET", params, None, 200
        )
        assert len(resp.json["repositories"]) == 2

    # Trigger sync
    with client_with_identity("devtable", app) as cl:
        params = {"orgname": "buynlarge"}
        resp = conduct_api_call(cl, OrganizationMirrorSyncNowResource, "POST", params, None, 200)
        assert resp.json["status"] == "sync_triggered"

    # Verify sync status
    updated_mirror = model.org_mirror.get_org_mirror_config("buynlarge")
    assert updated_mirror.sync_status == OrgMirrorStatus.SYNC_NOW
