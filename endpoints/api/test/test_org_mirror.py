# -*- coding: utf-8 -*-
"""
Unit tests for organization-level mirror API endpoints.
"""

import logging
from datetime import datetime

import pytest

from data import model
from data.database import OrgMirrorConfig as OrgMirrorConfigModel
from endpoints.api import org_mirror
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *

logger = logging.getLogger(__name__)


def _cleanup_org_mirror_config(orgname):
    """Helper to clean up any existing org mirror config."""
    try:
        org = model.organization.get_organization(orgname)
        config = model.org_mirror.get_org_mirror_config(org)
        if config:
            config.delete_instance()
    except Exception as e:
        logger.exception("Failed to cleanup org mirror config for org '%s': %s", orgname, e)
        raise


class TestCreateOrgMirrorConfig:
    """Tests for POST /v1/organization/<orgname>/mirror endpoint."""

    def test_create_org_mirror_config_success(self, app):
        """
        Test successful creation of organization mirror configuration.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Verify the config was created
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config is not None
        assert config.external_registry_url == "https://harbor.example.com"
        assert config.external_namespace == "my-project"
        assert config.sync_interval == 3600
        assert config.is_enabled is True

        # Clean up
        config.delete_instance()

    def test_create_org_mirror_config_with_optional_fields(self, app):
        """
        Test creating org mirror config with all optional fields.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "quay",
                "external_registry_url": "https://quay.io",
                "external_namespace": "some-org",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "public",
                "sync_interval": 7200,
                "sync_start_date": "2025-06-15T12:00:00Z",
                "is_enabled": False,
                "external_registry_username": "myuser",
                "external_registry_password": "mypassword",
                "external_registry_config": {
                    "verify_tls": True,
                    "proxy": {
                        "https_proxy": "https://proxy.example.com",
                    },
                },
                "repository_filters": ["ubuntu*", "nginx"],
                "skopeo_timeout": 600,
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config is not None
        assert config.is_enabled is False
        assert config.repository_filters == ["ubuntu*", "nginx"]
        assert config.skopeo_timeout == 600
        assert config.visibility.name == "public"

        # Clean up
        config.delete_instance()

    def test_create_org_mirror_config_already_exists(self, app):
        """
        Test that creating a config when one already exists returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create initial config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Try to create another config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "quay",
                "external_registry_url": "https://quay.io",
                "external_namespace": "other-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "public",
                "sync_interval": 7200,
                "sync_start_date": "2025-02-01T00:00:00Z",
            }
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )
            assert "already exists" in resp.json.get("error_message", "")

        # Clean up
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        if config:
            config.delete_instance()

    def test_create_org_mirror_config_invalid_robot(self, app):
        """
        Test that creating config with invalid robot returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+nonexistent",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )
            assert "Invalid robot" in resp.json.get("error_message", "")

    def test_create_org_mirror_config_wrong_robot_namespace(self, app):
        """
        Test that creating config with robot from different org returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "devtable+dtrobot",  # Robot from different namespace
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )
            assert "belong to the organization" in resp.json.get("error_message", "")

    def test_create_org_mirror_config_invalid_registry_type(self, app):
        """
        Test that creating config with invalid registry type returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "invalid_registry",
                "external_registry_url": "https://example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            # Schema validation should catch this first
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400)

    def test_create_org_mirror_config_invalid_visibility(self, app):
        """
        Test that creating config with invalid visibility returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "invalid",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            # Schema validation should catch this first
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400)

    def test_create_org_mirror_config_sync_interval_too_small(self, app):
        """
        Test that creating config with sync_interval < 60 returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 30,  # Too small
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            # Schema validation should catch this first
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400)

    def test_create_org_mirror_config_invalid_date_format(self, app):
        """
        Test that creating config with invalid date format returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "January 1, 2025",  # Invalid format
            }
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )
            assert "sync_start_date" in resp.json.get("error_message", "")

    def test_create_org_mirror_config_org_not_found(self, app):
        """
        Test that creating config for non-existent org returns 404.
        """
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "nonexistentorg"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "nonexistentorg+robot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 404)

    def test_create_org_mirror_config_unauthorized(self, app):
        """
        Test that creating config without proper permissions returns 403.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("reader", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 403)

    def test_create_org_mirror_config_skopeo_timeout_out_of_range(self, app):
        """
        Test that creating config with skopeo_timeout out of range returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Test too small
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
                "skopeo_timeout": 10,  # Too small (min 30)
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400)

        # Test too large
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
                "skopeo_timeout": 5000,  # Too large (max 3600)
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400)


class TestDeleteOrgMirrorConfig:
    """Tests for DELETE /v1/organization/<orgname>/mirror endpoint."""

    def test_delete_org_mirror_config_success(self, app):
        """
        Test successful deletion of organization mirror configuration.
        """
        _cleanup_org_mirror_config("buynlarge")

        # First create a config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Verify it exists
        org = model.organization.get_organization("buynlarge")
        assert model.org_mirror.get_org_mirror_config(org) is not None

        # Delete it
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 204)

        # Verify it's gone
        assert model.org_mirror.get_org_mirror_config(org) is None

    def test_delete_org_mirror_config_not_found(self, app):
        """
        Test that deleting a non-existent config returns 404.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 404)

    def test_delete_org_mirror_config_org_not_found(self, app):
        """
        Test that deleting config for non-existent org returns 404.
        """
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "nonexistentorg"}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 404)

    def test_delete_org_mirror_config_unauthorized(self, app):
        """
        Test that deleting config without proper permissions returns 403.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create a config directly via data model to avoid identity persistence issues
        org = model.organization.get_organization("buynlarge")
        robot = model.user.lookup_robot("buynlarge+coolrobot")
        from data.database import SourceRegistryType, Visibility

        model.org_mirror.create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=Visibility.get(name="private"),
            sync_interval=3600,
            sync_start_date=datetime.now(),
            is_enabled=True,
        )

        # Verify config was created
        assert model.org_mirror.get_org_mirror_config(org) is not None

        # Try to delete as non-admin user (reader has member role, not admin)
        with client_with_identity("reader", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 403)

        # Verify config still exists
        assert model.org_mirror.get_org_mirror_config(org) is not None

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_delete_org_mirror_config_can_recreate_after_delete(self, app):
        """
        Test that after deleting a config, a new one can be created.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create first config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "project1",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Delete it
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 204)

        # Create a new config with different settings
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "quay",
                "external_registry_url": "https://quay.io",
                "external_namespace": "project2",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "public",
                "sync_interval": 7200,
                "sync_start_date": "2025-06-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Verify the new config has the updated settings
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config is not None
        assert config.external_registry_url == "https://quay.io"
        assert config.external_namespace == "project2"
        assert config.sync_interval == 7200

        # Clean up
        _cleanup_org_mirror_config("buynlarge")


class TestUpdateOrgMirrorConfig:
    """Tests for PUT /v1/organization/<orgname>/mirror endpoint."""

    def test_update_org_mirror_config_success(self, app):
        """
        Test successful update of organization mirror configuration.
        """
        _cleanup_org_mirror_config("buynlarge")

        # First create a config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Update the config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "sync_interval": 7200,
                "external_namespace": "updated-project",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 200)

        # Verify the update
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config is not None
        assert config.sync_interval == 7200
        assert config.external_namespace == "updated-project"
        # Original values should be unchanged
        assert config.external_registry_url == "https://harbor.example.com"

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_is_enabled(self, app):
        """
        Test updating is_enabled field.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Disable mirroring
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"is_enabled": False}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 200)

        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config.is_enabled is False

        # Re-enable mirroring
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"is_enabled": True}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 200)

        config = model.org_mirror.get_org_mirror_config(org)
        assert config.is_enabled is True

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_visibility(self, app):
        """
        Test updating visibility field.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config with private visibility
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Update to public visibility
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"visibility": "public"}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 200)

        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config.visibility.name == "public"

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_not_found(self, app):
        """
        Test that updating a non-existent config returns 404.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"sync_interval": 7200}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 404)

    def test_update_org_mirror_config_org_not_found(self, app):
        """
        Test that updating config for non-existent org returns 404.
        """
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "nonexistentorg"}
            request_body = {"sync_interval": 7200}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 404)

    def test_update_org_mirror_config_unauthorized(self, app):
        """
        Test that updating config without proper permissions returns 403.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create a config directly via data model to avoid identity persistence issues
        org = model.organization.get_organization("buynlarge")
        robot = model.user.lookup_robot("buynlarge+coolrobot")
        from data.database import SourceRegistryType, Visibility

        model.org_mirror.create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=Visibility.get(name="private"),
            sync_interval=3600,
            sync_start_date=datetime.now(),
            is_enabled=True,
        )

        # Try to update as non-admin (reader has member role, not admin)
        with client_with_identity("reader", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"sync_interval": 7200}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 403)

        # Verify config was not changed
        config = model.org_mirror.get_org_mirror_config(org)
        assert config.sync_interval == 3600

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_invalid_robot(self, app):
        """
        Test that updating with invalid robot returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Try to update with non-existent robot
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"robot_username": "buynlarge+nonexistent"}
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 400
            )
            assert "Invalid robot" in resp.json.get("error_message", "")

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_wrong_robot_namespace(self, app):
        """
        Test that updating with robot from different org returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Try to update with robot from different org
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"robot_username": "devtable+dtrobot"}
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 400
            )
            assert "belong to the organization" in resp.json.get("error_message", "")

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_sync_interval_too_small(self, app):
        """
        Test that updating with sync_interval < 60 returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Try to update with invalid sync_interval
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"sync_interval": 30}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 400)

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_invalid_visibility(self, app):
        """
        Test that updating with invalid visibility returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Try to update with invalid visibility
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"visibility": "invalid"}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 400)

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_invalid_date_format(self, app):
        """
        Test that updating with invalid date format returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Try to update with invalid date format
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"sync_start_date": "January 1, 2025"}
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 400
            )
            assert "sync_start_date" in resp.json.get("error_message", "")

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_skopeo_timeout_out_of_range(self, app):
        """
        Test that updating with skopeo_timeout out of range returns 400.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Test too small
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"skopeo_timeout": 10}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 400)

        # Test too large
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {"skopeo_timeout": 5000}
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 400)

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_multiple_fields(self, app):
        """
        Test updating multiple fields at once.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Update multiple fields
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "is_enabled": False,
                "external_registry_url": "https://updated-harbor.example.com",
                "external_namespace": "updated-project",
                "visibility": "public",
                "sync_interval": 7200,
                "sync_start_date": "2025-06-01T12:00:00Z",
                "repository_filters": ["ubuntu*", "nginx"],
                "skopeo_timeout": 600,
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 200)

        # Verify all updates
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config.is_enabled is False
        assert config.external_registry_url == "https://updated-harbor.example.com"
        assert config.external_namespace == "updated-project"
        assert config.visibility.name == "public"
        assert config.sync_interval == 7200
        assert config.repository_filters == ["ubuntu*", "nginx"]
        assert config.skopeo_timeout == 600

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_update_org_mirror_config_credentials(self, app):
        """
        Test updating credentials.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config without credentials
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Update with credentials
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_username": "newuser",
                "external_registry_password": "newpassword",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "PUT", params, request_body, 200)

        # Verify credentials were updated
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config.external_registry_username is not None
        assert config.external_registry_password is not None

        # Clean up
        _cleanup_org_mirror_config("buynlarge")


class TestVerifyOrgMirrorConnection:
    """Tests for POST /v1/organization/<orgname>/mirror/verify endpoint."""

    def test_verify_connection_success(self, app):
        """
        Test successful connection verification.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "quay",
                "external_registry_url": "https://quay.io",
                "external_namespace": "projectquay",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Verify connection (quay.io/projectquay is a public org that exists)
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            result = conduct_api_call(
                cl, org_mirror.OrgMirrorVerify, "POST", params, None, 200
            ).json
            assert result["success"] is True
            assert "successful" in result["message"].lower()

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_verify_connection_namespace_not_found(self, app):
        """
        Test verify connection with non-existent namespace.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config with a non-existent namespace
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "quay",
                "external_registry_url": "https://quay.io",
                "external_namespace": "this-namespace-definitely-does-not-exist-12345",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Verify connection should fail
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            result = conduct_api_call(
                cl, org_mirror.OrgMirrorVerify, "POST", params, None, 200
            ).json
            assert result["success"] is False
            assert "not found" in result["message"].lower()

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_verify_connection_no_config(self, app):
        """
        Test verify connection when no mirror config exists.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorVerify, "POST", params, None, 404)

    def test_verify_connection_org_not_found(self, app):
        """
        Test verify connection when organization doesn't exist.
        """
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "nonexistent-org-12345"}
            conduct_api_call(cl, org_mirror.OrgMirrorVerify, "POST", params, None, 404)

    def test_verify_connection_unauthorized(self, app):
        """
        Test verify connection without admin permission.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create a config directly via data model to avoid identity persistence issues
        org = model.organization.get_organization("buynlarge")
        robot = model.user.lookup_robot("buynlarge+coolrobot")
        from data.database import SourceRegistryType, Visibility

        model.org_mirror.create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.QUAY,
            external_registry_url="https://quay.io",
            external_namespace="projectquay",
            visibility=Visibility.get(name="private"),
            sync_interval=3600,
            sync_start_date=datetime.now(),
            is_enabled=True,
        )

        # Verify config was created
        assert model.org_mirror.get_org_mirror_config(org) is not None

        # Try to verify as non-admin user (reader has member role, not admin)
        with client_with_identity("reader", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorVerify, "POST", params, None, 403)

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_verify_connection_invalid_url(self, app):
        """
        Test verify connection with invalid/unreachable URL.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create config with invalid URL
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "quay",
                "external_registry_url": "https://invalid-registry-that-does-not-exist.example.com",
                "external_namespace": "someorg",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Verify connection should fail due to connection error
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            result = conduct_api_call(
                cl, org_mirror.OrgMirrorVerify, "POST", params, None, 200
            ).json
            assert result["success"] is False
            # Should contain connection error message
            assert "error" in result["message"].lower() or "connection" in result["message"].lower()

        # Clean up
        _cleanup_org_mirror_config("buynlarge")


class TestSyncNow:
    """Tests for POST /v1/organization/<orgname>/mirror/sync-now endpoint."""

    def test_sync_now_success(self, app):
        """
        Test triggering immediate sync successfully.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create a config first
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Trigger sync-now
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorSyncNow, "POST", params, None, 204)

        # Verify status changed to SYNC_NOW
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        from data.database import OrgMirrorStatus

        assert config.sync_status == OrgMirrorStatus.SYNC_NOW

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_sync_now_no_config(self, app):
        """
        Test sync-now returns 404 when no config exists.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorSyncNow, "POST", params, None, 404)

    def test_sync_now_fails_when_syncing(self, app):
        """
        Test sync-now returns error when already syncing.
        """
        from data.database import OrgMirrorStatus, SourceRegistryType, Visibility

        _cleanup_org_mirror_config("buynlarge")

        # Create a config in SYNCING state
        org = model.organization.get_organization("buynlarge")
        robot = model.user.lookup_robot("buynlarge+coolrobot")
        config = model.org_mirror.create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="project",
            visibility=Visibility.get(name="private"),
            sync_interval=3600,
            sync_start_date=datetime.now(),
            is_enabled=True,
        )
        config.sync_status = OrgMirrorStatus.SYNCING
        config.save()

        # Try to trigger sync-now - should fail
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorSyncNow, "POST", params, None, 400)

        # Clean up
        _cleanup_org_mirror_config("buynlarge")


class TestSyncCancel:
    """Tests for POST /v1/organization/<orgname>/mirror/sync-cancel endpoint."""

    def test_sync_cancel_success(self, app):
        """
        Test cancelling ongoing sync successfully.
        """
        from data.database import OrgMirrorStatus, SourceRegistryType, Visibility

        _cleanup_org_mirror_config("buynlarge")

        # Create a config in SYNCING state
        org = model.organization.get_organization("buynlarge")
        robot = model.user.lookup_robot("buynlarge+coolrobot")
        config = model.org_mirror.create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="project",
            visibility=Visibility.get(name="private"),
            sync_interval=3600,
            sync_start_date=datetime.now(),
            is_enabled=True,
        )
        config.sync_status = OrgMirrorStatus.SYNCING
        config.save()

        # Cancel sync
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorSyncCancel, "POST", params, None, 204)

        # Verify status changed to CANCEL
        config = model.org_mirror.get_org_mirror_config(org)
        assert config.sync_status == OrgMirrorStatus.CANCEL

        # Clean up
        _cleanup_org_mirror_config("buynlarge")

    def test_sync_cancel_no_config(self, app):
        """
        Test sync-cancel returns 404 when no config exists.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorSyncCancel, "POST", params, None, 404)

    def test_sync_cancel_fails_when_not_syncing(self, app):
        """
        Test sync-cancel returns error when not syncing.
        """
        _cleanup_org_mirror_config("buynlarge")

        # Create a config in NEVER_RUN state
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            request_body = {
                "external_registry_type": "harbor",
                "external_registry_url": "https://harbor.example.com",
                "external_namespace": "my-project",
                "robot_username": "buynlarge+coolrobot",
                "visibility": "private",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
            }
            conduct_api_call(cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201)

        # Try to cancel - should fail since not syncing
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(cl, org_mirror.OrgMirrorSyncCancel, "POST", params, None, 400)

        # Clean up
        _cleanup_org_mirror_config("buynlarge")
