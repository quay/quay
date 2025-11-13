"""
Tests for superuser functionality with and without FEATURE_SUPERUSERS_FULL_ACCESS.

This tests the fix for the bug where superuser panel endpoints return 403
when FEATURE_SUPERUSERS_FULL_ACCESS is disabled, even though they should
work with just FEATURE_SUPER_USERS enabled.
"""

import pytest

from endpoints.api.globalmessages import GlobalUserMessages
from endpoints.api.organization import Organization
from endpoints.api.repository import RepositoryList
from endpoints.api.superuser import (
    SuperUserAggregateLogs,
    SuperUserList,
    SuperUserLogs,
    SuperUserManagement,
    SuperUserOrganizationList,
)
from endpoints.api.team import OrganizationTeam
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


class TestSuperuserBasicAccessWithoutFullAccess:
    """
    Tests that basic superuser panel endpoints work with FEATURE_SUPER_USERS=true
    and FEATURE_SUPERUSERS_FULL_ACCESS=false.

    These are core superuser functions and should NOT require full access.
    """

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Disable SUPERUSERS_FULL_ACCESS for these tests."""
        import features

        # Ensure SUPER_USERS is enabled but FULL_ACCESS is disabled
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

    def test_superuser_can_list_users_without_full_access(self, app):
        """
        Test that superusers can access /v1/superuser/users/ without FULL_ACCESS.

        This is a core superuser panel function and should work with just
        FEATURE_SUPER_USERS enabled.
        """
        with client_with_identity("devtable", app) as cl:
            result = conduct_api_call(cl, SuperUserList, "GET", None, None, 200)
            assert result.json is not None
            assert "users" in result.json
            assert len(result.json["users"]) > 0

    def test_superuser_can_get_user_details_without_full_access(self, app):
        """
        Test that superusers can access /v1/superuser/users/<username> without FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            params = {"username": "randomuser"}
            result = conduct_api_call(cl, SuperUserManagement, "GET", params, None, 200)
            assert result.json is not None
            assert result.json["username"] == "randomuser"

    def test_superuser_can_list_organizations_without_full_access(self, app):
        """
        Test that superusers can access /v1/superuser/organizations/ without FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            result = conduct_api_call(cl, SuperUserOrganizationList, "GET", None, None, 200)
            assert result.json is not None
            assert "organizations" in result.json
            assert len(result.json["organizations"]) > 0

    def test_superuser_can_view_logs_without_full_access(self, app):
        """
        Test that superusers can access /v1/superuser/logs without FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            result = conduct_api_call(cl, SuperUserLogs, "GET", None, None, 200)
            assert result.json is not None
            assert "logs" in result.json

    def test_superuser_can_view_aggregate_logs_without_full_access(self, app):
        """
        Test that superusers can access /v1/superuser/aggregatelogs without FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            params = {"starttime": "01/01/2024 UTC", "endtime": "12/31/2024 UTC"}
            result = conduct_api_call(cl, SuperUserAggregateLogs, "GET", params, None, 200)
            assert result.json is not None
            assert "aggregated" in result.json

    def test_superuser_can_manage_global_messages_without_full_access(self, app):
        """
        Test that superusers can create/delete global messages without FULL_ACCESS.

        Managing global messages is a core superuser function.
        """
        with client_with_identity("devtable", app) as cl:
            # Create a global message
            body = {
                "message": {
                    "severity": "info",
                    "media_type": "text/plain",
                    "content": "Test message",
                }
            }
            result = conduct_api_call(cl, GlobalUserMessages, "POST", None, body, 201)
            assert result.status_code == 201


class TestSuperuserFullAccessRequired:
    """
    Tests that operations requiring FEATURE_SUPERUSERS_FULL_ACCESS are properly
    blocked when the feature is disabled.

    These operations bypass normal permission checks to access/modify resources
    owned by other users/organizations.
    """

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Disable SUPERUSERS_FULL_ACCESS for these tests."""
        import features
        from data import model

        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": False,
            }
        )

        # Create a test organization owned by randomuser (not devtable)
        # This is needed to test that devtable (superuser) cannot modify it without FULL_ACCESS
        randomuser = model.user.get_user("randomuser")
        try:
            model.organization.get_organization("testorg")
        except model.InvalidOrganizationException:
            model.organization.create_organization("testorg", "testorg@test.com", randomuser)

        yield
        # Note: We don't clean up the organization because it has foreign key constraints
        # and the test database is reset between test runs anyway

        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": True,
            }
        )

    def test_superuser_cannot_create_repo_in_other_namespace_without_full_access(self, app):
        """
        Test that superusers CANNOT create repos in other namespaces without FULL_ACCESS.

        This is a permission bypass operation that requires FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            # Try to create a repo in another user's namespace
            body = {
                "namespace": "randomuser",  # Not devtable's namespace
                "repository": "test-repo",
                "visibility": "private",
                "description": "test",
            }
            # Should be blocked without FULL_ACCESS
            conduct_api_call(cl, RepositoryList, "POST", None, body, 403)

    def test_superuser_cannot_modify_other_org_team_without_full_access(self, app):
        """
        Test that superusers CANNOT modify teams in other orgs without FULL_ACCESS.

        This is a permission bypass operation that requires FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            # Try to create a team in testorg (owned by randomuser, not devtable)
            params = {"orgname": "testorg", "teamname": "testteam"}
            body = {"role": "member"}
            # Should be blocked without FULL_ACCESS
            conduct_api_call(cl, OrganizationTeam, "PUT", params, body, 403)


class TestSuperuserFullAccessEnabled:
    """
    Tests that operations work correctly when FEATURE_SUPERUSERS_FULL_ACCESS is enabled.

    With full access, superusers can bypass permission checks.
    """

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Enable SUPERUSERS_FULL_ACCESS for these tests."""
        import features

        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": True,
            }
        )
        yield

    def test_superuser_can_view_other_org_details_with_full_access(self, app):
        """
        Test that superusers CAN view other organizations' details with FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            # Can view org that devtable doesn't own
            params = {"orgname": "buynlarge"}
            result = conduct_api_call(cl, Organization, "GET", params, None, 200)
            assert result.json is not None
            assert result.json["name"] == "buynlarge"

    def test_superuser_can_modify_other_org_team_with_full_access(self, app):
        """
        Test that superusers CAN modify teams in other orgs with FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            # Can create team in org that devtable doesn't own
            params = {"orgname": "buynlarge", "teamname": "testteam"}
            body = {"role": "member"}
            result = conduct_api_call(cl, OrganizationTeam, "PUT", params, body, 200)
            assert result.json is not None

    def test_superuser_can_create_repo_in_other_namespace_with_full_access(self, app):
        """
        Test that superusers CAN create repos in other namespaces with FULL_ACCESS.
        """
        with client_with_identity("devtable", app) as cl:
            # Can create repo in another user's namespace
            body = {
                "namespace": "randomuser",
                "repository": "test-repo-full-access",
                "visibility": "public",  # Use public to avoid license limit issues
                "description": "test with full access",
            }
            result = conduct_api_call(cl, RepositoryList, "POST", None, body, 201)
            assert result.json is not None
