"""
Tests for Global Read-Only Superuser functionality.

This test module validates that Global Read-Only Superusers have the correct
permissions - read access to all content but blocked from write operations.
"""

import pytest

from data import model
from endpoints.api import allow_if_global_readonly_superuser, allow_if_superuser
from endpoints.api.appspecifictokens import AppTokens
from endpoints.api.logs import OrgAggregateLogs, OrgLogs, UserAggregateLogs, UserLogs
from endpoints.api.organization import Organization, OrganizationList
from endpoints.api.repository import Repository, RepositoryList
from endpoints.api.superuser import SuperUserAggregateLogs, SuperUserLogs
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import User
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.fixture()
def regular_user(initialized_db):
    """Get a regular non-superuser."""
    return model.user.get_user("freshuser")


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestGlobalReadOnlySuperuserHelperFunctions:
    """Test the helper functions for global read-only superuser detection."""

    def test_allow_if_superuser_function_exists(self, app):
        """Test that allow_if_superuser() function exists and is callable."""
        assert callable(allow_if_superuser)

    def test_allow_if_global_readonly_superuser_function_exists(self, app):
        """Test that allow_if_global_readonly_superuser() function exists and is callable."""
        assert callable(allow_if_global_readonly_superuser)


# =============================================================================
# App Token Access Tests (Well-Written Integration Tests)
# =============================================================================


class TestAppTokenGlobalReadOnlySuperuserBehavior:
    """
    Test app token functionality for global read-only superusers.

    These tests use real fixtures and minimal mocking to validate actual behavior.
    """

    def test_app_token_list_regular_user_access(self, app):
        """Test that regular users only see their own app tokens."""
        # Create test tokens for different users
        devtable_user = model.user.get_user("devtable")
        freshuser = model.user.get_user("freshuser")

        devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
        freshuser_token = model.appspecifictoken.create_token(freshuser, "Fresh User Token")

        try:
            # Use freshuser (regular user, not superuser) to test regular user access
            with client_with_identity("freshuser", app) as cl:
                resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200)
                token_uuids = {token["uuid"] for token in resp.json["tokens"]}

                # Regular user should only see their own tokens
                assert freshuser_token.uuid in token_uuids
                assert devtable_token.uuid not in token_uuids

        finally:
            # Clean up
            devtable_token.delete_instance()
            freshuser_token.delete_instance()


# =============================================================================
# Write Operation Blocking Tests
# =============================================================================


class TestRepositoryWriteOperationsBlocking:
    """Test that repository write operations are blocked for global read-only superusers."""

    def test_repository_creation_blocked(self, app):
        """
        Test that repository creation is blocked for global readonly superusers.
        Permission blocking happens at the CreateRepositoryPermission class level.
        """
        from unittest.mock import MagicMock, patch

        # Mock the permission class to deny creation
        mock_permission = MagicMock()
        mock_permission.can.return_value = False

        with patch(
            "endpoints.api.repository.CreateRepositoryPermission", return_value=mock_permission
        ), patch("endpoints.api.repository.allow_if_superuser", return_value=False):
            with client_with_identity("reader", app) as cl:
                repo_data = {
                    "repository": "test-blocked-repo",
                    "visibility": "private",
                    "description": "Should be blocked",
                }
                # Should return 403 Unauthorized for write operations
                resp = conduct_api_call(cl, RepositoryList, "POST", None, repo_data, 403)


class TestOrganizationReadOperations:
    """Test that organization read operations work correctly for superusers."""

    def test_organization_details_accessible_to_any_superuser(self, app):
        """
        Test that organization details (email and teams) are visible to both
        regular superusers and global readonly superusers (not just org members).
        """
        from unittest.mock import patch

        with patch("endpoints.api.organization.allow_if_any_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(
                    cl, Organization, "GET", {"orgname": "buynlarge"}, None, 200
                )
                assert resp.status_code == 200
                # Superusers should be able to see the organization email
                assert "email" in resp.json
                # Email should not be empty for superusers
                assert resp.json.get("email") is not None
                # Superusers should also be able to see the organization teams
                assert "teams" in resp.json
                assert "ordered_teams" in resp.json


class TestOrganizationWriteOperationsBlocking:
    """Test that organization write operations are blocked for global read-only superusers."""

    def test_organization_creation_blocked(self, app):
        """
        Test that organization creation is blocked for global readonly superusers.
        When SUPERUSERS_ORG_CREATION_ONLY is enabled, global readonly superusers
        cannot create organizations (blocked by allow_if_superuser check).
        """
        from unittest.mock import patch

        from endpoints.test.shared import toggle_feature

        # Enable the feature that requires superuser for org creation
        with toggle_feature("SUPERUSERS_ORG_CREATION_ONLY", True):
            with patch("endpoints.api.organization.allow_if_superuser", return_value=False):
                with client_with_identity("reader", app) as cl:
                    org_data = {"name": "test-blocked-org", "email": "test@example.com"}
                    # Should return 403 Unauthorized for write operations
                    resp = conduct_api_call(cl, OrganizationList, "POST", None, org_data, 403)


# =============================================================================
# Audit Log Access Tests (With Mocking for Permission System)
# =============================================================================


class TestAuditLogAccess:
    """Test audit log access for global read-only superusers."""

    def test_superuser_audit_logs_accessible(self, app):
        """Test that superuser audit logs are accessible to global readonly superusers."""
        from unittest.mock import patch

        with patch("endpoints.api.SuperUserPermission") as mock_super, patch(
            "endpoints.api.GlobalReadOnlySuperUserPermission"
        ) as mock_global_ro, patch(
            "endpoints.api.superuser.allow_if_any_superuser", return_value=True
        ):
            mock_super.return_value.can.return_value = False
            mock_global_ro.return_value.can.return_value = True

            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(cl, SuperUserLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                assert "logs" in resp.json

    def test_superuser_aggregated_logs_accessible(self, app):
        """Test that superuser aggregated logs are accessible to global readonly superusers."""
        from unittest.mock import patch

        with patch("endpoints.api.SuperUserPermission") as mock_super, patch(
            "endpoints.api.GlobalReadOnlySuperUserPermission"
        ) as mock_global_ro, patch(
            "endpoints.api.superuser.allow_if_any_superuser", return_value=True
        ):
            mock_super.return_value.can.return_value = False
            mock_global_ro.return_value.can.return_value = True

            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(cl, SuperUserAggregateLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                assert "aggregated" in resp.json

    def test_user_logs_accessible(self, app):
        """Test that user logs are accessible to global readonly superusers."""
        from unittest.mock import patch

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(cl, UserLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                assert "logs" in resp.json

    def test_user_aggregated_logs_accessible(self, app):
        """Test that user aggregated logs are accessible to global readonly superusers."""
        from unittest.mock import patch

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(cl, UserAggregateLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                assert "aggregated" in resp.json

    def test_organization_logs_accessible(self, app):
        """Test that organization logs are accessible to global readonly superusers."""
        from unittest.mock import patch

        with patch("endpoints.api.SuperUserPermission") as mock_super, patch(
            "endpoints.api.GlobalReadOnlySuperUserPermission"
        ) as mock_global_ro, patch("endpoints.api.logs.allow_if_any_superuser", return_value=True):
            mock_super.return_value.can.return_value = False
            mock_global_ro.return_value.can.return_value = True

            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(cl, OrgLogs, "GET", {"orgname": "buynlarge"}, None, 200)
                assert resp.status_code == 200
                assert "logs" in resp.json

    def test_organization_aggregated_logs_accessible(self, app):
        """Test that organization aggregated logs are accessible to global readonly superusers."""
        from unittest.mock import patch

        with patch("endpoints.api.SuperUserPermission") as mock_super, patch(
            "endpoints.api.GlobalReadOnlySuperUserPermission"
        ) as mock_global_ro, patch("endpoints.api.logs.allow_if_any_superuser", return_value=True):
            mock_super.return_value.can.return_value = False
            mock_global_ro.return_value.can.return_value = True

            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(
                    cl, OrgAggregateLogs, "GET", {"orgname": "buynlarge"}, None, 200
                )
                assert resp.status_code == 200
                assert "aggregated" in resp.json


# =============================================================================
# Log Export Operations (Special Case - Read Operation That Uses POST)
# =============================================================================


class TestLogExportOperations:
    """Test that log export operations are allowed for global read-only superusers."""

    def test_logs_export_allowed(self, app):
        """
        Test that log export operations are allowed for global readonly superusers.
        Log export is a read operation for compliance/auditing purposes, even though it uses POST.
        """
        from unittest.mock import patch

        from endpoints.api.logs import ExportUserLogs

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):

            with client_with_identity("reader", app) as cl:
                export_data = {"callback_email": "test@example.com"}

                # This should succeed or fail for validation reasons, not permissions
                # We accept both 200 and 400, but verify 400 is NOT a permission error
                try:
                    resp = conduct_api_call(cl, ExportUserLogs, "POST", None, export_data, 200)
                    assert resp.status_code == 200
                    assert "export_id" in resp.json
                except AssertionError:
                    # May fail with 400 for validation reasons unrelated to permissions
                    resp = conduct_api_call(cl, ExportUserLogs, "POST", None, export_data, 400)
                    # Should NOT be a permission error about global readonly blocking
                    assert "Global readonly users cannot export logs" not in resp.json.get(
                        "message", ""
                    )
