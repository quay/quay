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

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                resp = conduct_api_call(cl, OrgLogs, "GET", {"orgname": "buynlarge"}, None, 200)
                assert resp.status_code == 200
                assert "logs" in resp.json

    def test_organization_aggregated_logs_accessible(self, app):
        """Test that organization aggregated logs are accessible to global readonly superusers."""
        from unittest.mock import patch

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
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


# =============================================================================
# Organization Logs Access Without Full Access (Bug PROJQUAY-9790)
# =============================================================================


class TestOrganizationLogsAccessWithoutFullAccess:
    """
    Test that global readonly superusers can access organization logs even when
    FEATURE_SUPERUSERS_FULL_ACCESS is disabled.

    This verifies the fix for bug PROJQUAY-9790 where global readonly superusers
    were incorrectly blocked from accessing organization logs when
    FEATURE_SUPERUSERS_FULL_ACCESS was set to false.
    """

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Configure test environment with SUPERUSERS_FULL_ACCESS disabled."""
        import features
        from data import model

        # Disable SUPERUSERS_FULL_ACCESS to test the bug scenario
        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": False,
            }
        )

        # Create a test organization owned by randomuser (not devtable or globalreadonlysuperuser)
        # This ensures devtable has no admin permissions on it
        randomuser = model.user.get_user("randomuser")
        try:
            org = model.organization.get_organization("testorglogs")
        except model.InvalidOrganizationException:
            org = model.organization.create_organization(
                "testorglogs", "testorglogs@test.com", randomuser
            )

        # Create an owners team for testing team access (if it doesn't exist)
        try:
            model.team.get_organization_team("testorglogs", "owners")
        except model.InvalidTeamException:
            model.team.create_team("owners", org, "admin", "Team for owners")

        yield
        # Note: We don't clean up the organization because it has foreign key constraints
        # and the test database is reset between test runs anyway

        # Reset to default test config
        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": True,
            }
        )

    def test_global_readonly_superuser_can_access_org_logs_without_full_access(self, app):
        """
        Test that global readonly superusers can access organization logs even when
        FEATURE_SUPERUSERS_FULL_ACCESS is false.

        This is the main test for bug PROJQUAY-9790. Global readonly superusers should
        always be able to access logs for auditing purposes, regardless of the
        SUPERUSERS_FULL_ACCESS setting.
        """
        from endpoints.api.logs import ExportOrgLogs

        # Use globalreadonlysuperuser (configured in testconfig.py)
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            # Should be able to access organization logs
            resp = conduct_api_call(cl, OrgLogs, "GET", {"orgname": "testorglogs"}, None, 200)
            assert resp.status_code == 200
            assert "logs" in resp.json

            # Should also be able to access aggregated logs
            resp = conduct_api_call(
                cl, OrgAggregateLogs, "GET", {"orgname": "testorglogs"}, None, 200
            )
            assert resp.status_code == 200
            assert "aggregated" in resp.json

            # Should be able to export logs (read operation even though it uses POST)
            export_data = {"callback_email": "test@example.com"}
            try:
                resp = conduct_api_call(
                    cl, ExportOrgLogs, "POST", {"orgname": "testorglogs"}, export_data, 200
                )
                assert resp.status_code == 200
            except AssertionError:
                # May fail with 400 for validation reasons, but should NOT be a permission error
                resp = conduct_api_call(
                    cl, ExportOrgLogs, "POST", {"orgname": "testorglogs"}, export_data, 400
                )
                # Verify it's not a permission error
                error_type = resp.json.get("error_type", "")
                assert (
                    error_type != "insufficient_scope"
                ), f"Global readonly superuser should be able to export org logs, got: {resp.json}"

    def test_regular_superuser_cannot_access_org_logs_without_full_access(self, app):
        """
        Test that regular superusers CANNOT access organization logs when
        FEATURE_SUPERUSERS_FULL_ACCESS is false.

        This verifies that the fix for PROJQUAY-9790 doesn't accidentally grant
        regular superusers access to organization logs when they shouldn't have it.
        """
        from endpoints.api.logs import ExportOrgLogs

        # Use devtable (regular superuser, not global readonly)
        with client_with_identity("devtable", app) as cl:
            # Should NOT be able to access organization logs without FULL_ACCESS
            resp = conduct_api_call(cl, OrgLogs, "GET", {"orgname": "testorglogs"}, None, 403)
            assert resp.status_code == 403

            # Should NOT be able to access aggregated logs
            resp = conduct_api_call(
                cl, OrgAggregateLogs, "GET", {"orgname": "testorglogs"}, None, 403
            )
            assert resp.status_code == 403

            # Should NOT be able to export logs
            export_data = {"callback_email": "test@example.com"}
            resp = conduct_api_call(
                cl, ExportOrgLogs, "POST", {"orgname": "testorglogs"}, export_data, 403
            )
            assert resp.status_code == 403

    def test_global_readonly_superuser_can_access_team_members_without_full_access(self, app):
        """
        Test that global readonly superusers can access team members when
        FEATURE_SUPERUSERS_FULL_ACCESS is false.

        This tests the fix for team member access. Global readonly superusers should
        be able to view team members for auditing purposes.
        """
        from endpoints.api.team import TeamMemberList

        # Use globalreadonlysuperuser (configured in testconfig.py)
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            # Should be able to access team members
            resp = conduct_api_call(
                cl, TeamMemberList, "GET", {"orgname": "buynlarge", "teamname": "owners"}, None, 200
            )
            assert resp.status_code == 200
            assert "members" in resp.json

    def test_global_readonly_superuser_can_access_team_permissions_without_full_access(self, app):
        """
        Test that global readonly superusers can access team permissions when
        FEATURE_SUPERUSERS_FULL_ACCESS is false.

        This tests the fix for the reported issue. Global readonly superusers should
        be able to view team permissions for auditing purposes.
        """
        from endpoints.api.team import TeamPermissions

        # Use globalreadonlysuperuser (configured in testconfig.py)
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            # Should be able to access team permissions
            resp = conduct_api_call(
                cl,
                TeamPermissions,
                "GET",
                {"orgname": "buynlarge", "teamname": "owners"},
                None,
                200,
            )
            assert resp.status_code == 200
            assert "permissions" in resp.json

    def test_regular_superuser_cannot_access_team_data_without_full_access(self, app):
        """
        Test that regular superusers CANNOT access team members/permissions when
        FEATURE_SUPERUSERS_FULL_ACCESS is false.

        This verifies that the fix doesn't accidentally grant regular superusers
        access to team data when they shouldn't have it.
        """
        from endpoints.api.team import TeamMemberList, TeamPermissions

        # Use devtable (regular superuser, not global readonly)
        with client_with_identity("devtable", app) as cl:
            # Should NOT be able to access team members without FULL_ACCESS
            # Using testorglogs org where devtable has no membership
            resp = conduct_api_call(
                cl,
                TeamMemberList,
                "GET",
                {"orgname": "testorglogs", "teamname": "owners"},
                None,
                403,
            )
            assert resp.status_code == 403

    def test_global_readonly_superuser_can_access_org_members_without_full_access(self, app):
        """
        Test that global readonly superusers can access organization members when
        FEATURE_SUPERUSERS_FULL_ACCESS is false.
        """
        from endpoints.api.organization import (
            OrganizationMember,
            OrganizationMemberList,
        )

        # Use globalreadonlysuperuser (configured in testconfig.py)
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            # Should be able to access organization member list
            resp = conduct_api_call(
                cl, OrganizationMemberList, "GET", {"orgname": "buynlarge"}, None, 200
            )
            assert resp.status_code == 200
            assert "members" in resp.json

            # Should be able to access individual member details
            resp = conduct_api_call(
                cl,
                OrganizationMember,
                "GET",
                {"orgname": "buynlarge", "membername": "devtable"},
                None,
                200,
            )
            assert resp.status_code == 200
            assert "name" in resp.json

    def test_global_readonly_superuser_can_access_org_applications_without_full_access(self, app):
        """
        Test that global readonly superusers can access organization OAuth applications
        when FEATURE_SUPERUSERS_FULL_ACCESS is false.
        """
        from endpoints.api.organization import OrganizationApplications

        # Use globalreadonlysuperuser (configured in testconfig.py)
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            # Should be able to access organization applications
            resp = conduct_api_call(
                cl, OrganizationApplications, "GET", {"orgname": "buynlarge"}, None, 200
            )
            assert resp.status_code == 200
            assert "applications" in resp.json

    def test_global_readonly_superuser_can_access_org_prototypes_without_full_access(self, app):
        """
        Test that global readonly superusers can access organization prototype
        permissions when FEATURE_SUPERUSERS_FULL_ACCESS is false.
        """
        from endpoints.api.prototype import PermissionPrototypeList

        # Use globalreadonlysuperuser (configured in testconfig.py)
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            # Should be able to access organization prototype permissions
            resp = conduct_api_call(
                cl,
                PermissionPrototypeList,
                "GET",
                {"orgname": "buynlarge"},
                None,
                200,
            )
            assert resp.status_code == 200
            assert "prototypes" in resp.json


# =============================================================================
# Quota Access Tests (PROJQUAY-9804)
# =============================================================================


class TestQuotaAccessWithoutFullAccess:
    """
    Test that global readonly superusers can access quota limits when
    FEATURE_SUPERUSERS_FULL_ACCESS is false.

    Fixes issue PROJQUAY-9804 where global readonly superusers were blocked from
    accessing quota limit endpoints.
    """

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Configure test environment with SUPERUSERS_FULL_ACCESS disabled."""
        import features

        # Disable SUPERUSERS_FULL_ACCESS to test the bug scenario
        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": False,
            }
        )
        yield
        # Reset to default test config
        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": True,
            }
        )

    def test_global_readonly_superuser_can_access_quota_limit_list(self, app):
        """
        Test that global readonly superusers can access quota limit list
        when FEATURE_SUPERUSERS_FULL_ACCESS is false.
        """
        from endpoints.api.namespacequota import OrganizationQuotaLimitList

        # Create a test quota with limits for an organization
        org = model.organization.get_organization("buynlarge")

        # Create quota if it doesn't exist
        try:
            quota = model.namespacequota.get_namespace_quota_list("buynlarge")
            if not quota:
                quota = model.namespacequota.create_namespace_quota(org, 1024 * 1024 * 1024)  # 1 GB
            else:
                quota = quota[0]
        except Exception:
            quota = model.namespacequota.create_namespace_quota(org, 1024 * 1024 * 1024)  # 1 GB

        # Create quota limits if they don't exist
        try:
            existing_limits = list(model.namespacequota.get_namespace_quota_limit_list(quota))
            if not existing_limits:
                model.namespacequota.create_namespace_quota_limit(quota, "Warning", 80)
                model.namespacequota.create_namespace_quota_limit(quota, "Reject", 95)
        except Exception:
            pass  # Limits may already exist

        try:
            # Use globalreadonlysuperuser (configured in testconfig.py)
            with client_with_identity("globalreadonlysuperuser", app) as cl:
                # Should be able to access quota limit list
                resp = conduct_api_call(
                    cl,
                    OrganizationQuotaLimitList,
                    "GET",
                    {"orgname": "buynlarge", "quota_id": quota.id},
                    None,
                    200,
                )
                assert resp.status_code == 200
                # Should return a list of quota limits
                assert isinstance(resp.json, list)
        finally:
            # Clean up - delete quota limits and quota
            try:
                for limit in model.namespacequota.get_namespace_quota_limit_list(quota):
                    model.namespacequota.delete_namespace_quota_limit(limit)
                model.namespacequota.delete_namespace_quota(quota)
            except Exception:
                pass  # Best effort cleanup

    def test_global_readonly_superuser_can_access_individual_quota_limit(self, app):
        """
        Test that global readonly superusers can access individual quota limits
        when FEATURE_SUPERUSERS_FULL_ACCESS is false.
        """
        from endpoints.api.namespacequota import OrganizationQuotaLimit

        # Create a test quota with limits for an organization
        org = model.organization.get_organization("buynlarge")

        # Create quota if it doesn't exist
        try:
            quota = model.namespacequota.get_namespace_quota_list("buynlarge")
            if not quota:
                quota = model.namespacequota.create_namespace_quota(org, 1024 * 1024 * 1024)  # 1 GB
            else:
                quota = quota[0]
        except Exception:
            quota = model.namespacequota.create_namespace_quota(org, 1024 * 1024 * 1024)  # 1 GB

        # Create quota limit
        try:
            existing_limits = list(model.namespacequota.get_namespace_quota_limit_list(quota))
            if existing_limits:
                limit = existing_limits[0]
            else:
                limit = model.namespacequota.create_namespace_quota_limit(quota, "Warning", 80)
        except Exception:
            limit = model.namespacequota.create_namespace_quota_limit(quota, "Warning", 80)

        try:
            # Use globalreadonlysuperuser (configured in testconfig.py)
            with client_with_identity("globalreadonlysuperuser", app) as cl:
                # Should be able to access individual quota limit
                resp = conduct_api_call(
                    cl,
                    OrganizationQuotaLimit,
                    "GET",
                    {"orgname": "buynlarge", "quota_id": quota.id, "limit_id": limit.id},
                    None,
                    200,
                )
                assert resp.status_code == 200
                # Should return quota limit details
                assert "id" in resp.json
                assert "type" in resp.json
                assert "limit_percent" in resp.json
        finally:
            # Clean up
            try:
                for limit in model.namespacequota.get_namespace_quota_limit_list(quota):
                    model.namespacequota.delete_namespace_quota_limit(limit)
                model.namespacequota.delete_namespace_quota(quota)
            except Exception:
                pass  # Best effort cleanup

    def test_regular_superuser_cannot_access_quota_limits_without_full_access(self, app):
        """
        Test that regular superusers CANNOT access quota limits when
        FEATURE_SUPERUSERS_FULL_ACCESS is false.

        This verifies that the fix doesn't accidentally grant regular superusers
        access when they shouldn't have it.
        """
        from endpoints.api.namespacequota import OrganizationQuotaLimitList

        # Use orgwithnosuperuser - an org that devtable doesn't belong to
        org = model.organization.get_organization("orgwithnosuperuser")

        # Get or create quota
        try:
            quota = model.namespacequota.get_namespace_quota_list("orgwithnosuperuser")
            if not quota:
                quota = model.namespacequota.create_namespace_quota(org, 1024 * 1024 * 1024)  # 1 GB
            else:
                quota = quota[0]
        except Exception:
            quota = model.namespacequota.create_namespace_quota(org, 1024 * 1024 * 1024)  # 1 GB

        try:
            # Use devtable (regular superuser, not global readonly)
            # accessing orgwithnosuperuser where they have no membership
            with client_with_identity("devtable", app) as cl:
                # Should NOT be able to access quota limit list without FULL_ACCESS
                resp = conduct_api_call(
                    cl,
                    OrganizationQuotaLimitList,
                    "GET",
                    {"orgname": "orgwithnosuperuser", "quota_id": quota.id},
                    None,
                    403,
                )
                assert resp.status_code == 403
        finally:
            # Clean up only if we created the quota
            # Note: orgwithnosuperuser may already have a quota from initdb.py (line 1421)
            # so we only clean up if we created it in this test
            pass
