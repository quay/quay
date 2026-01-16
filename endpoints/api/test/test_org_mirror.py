# -*- coding: utf-8 -*-
"""
Unit tests for organization-level mirror API endpoints.
"""

from datetime import datetime

import pytest

from data import model
from data.database import OrgMirrorConfig as OrgMirrorConfigModel
from endpoints.api import org_mirror
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def _cleanup_org_mirror_config(orgname):
    """Helper to clean up any existing org mirror config."""
    try:
        org = model.organization.get_organization(orgname)
        config = model.org_mirror.get_org_mirror_config(org)
        if config:
            config.delete_instance()
    except Exception:
        pass


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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201
            )

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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201
            )

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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201
            )

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
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )

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
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )

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
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )

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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 404
            )

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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 403
            )

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
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )

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
            resp = conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 400
            )


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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201
            )

        # Verify it exists
        org = model.organization.get_organization("buynlarge")
        assert model.org_mirror.get_org_mirror_config(org) is not None

        # Delete it
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 204
            )

        # Verify it's gone
        assert model.org_mirror.get_org_mirror_config(org) is None

    def test_delete_org_mirror_config_not_found(self, app):
        """
        Test that deleting a non-existent config returns 404.
        """
        _cleanup_org_mirror_config("buynlarge")

        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 404
            )

    def test_delete_org_mirror_config_org_not_found(self, app):
        """
        Test that deleting config for non-existent org returns 404.
        """
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "nonexistentorg"}
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 404
            )

    def test_delete_org_mirror_config_unauthorized(self, app):
        """
        Test that deleting config without proper permissions returns 403.
        """
        _cleanup_org_mirror_config("buynlarge")

        # First create a config as admin
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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201
            )

        # Try to delete as non-admin user
        with client_with_identity("reader", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 403
            )

        # Verify config still exists
        org = model.organization.get_organization("buynlarge")
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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201
            )

        # Delete it
        with client_with_identity("devtable", app) as cl:
            params = {"orgname": "buynlarge"}
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "DELETE", params, None, 204
            )

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
            conduct_api_call(
                cl, org_mirror.OrgMirrorConfig, "POST", params, request_body, 201
            )

        # Verify the new config has the updated settings
        org = model.organization.get_organization("buynlarge")
        config = model.org_mirror.get_org_mirror_config(org)
        assert config is not None
        assert config.external_registry_url == "https://quay.io"
        assert config.external_namespace == "project2"
        assert config.sync_interval == 7200

        # Clean up
        _cleanup_org_mirror_config("buynlarge")
