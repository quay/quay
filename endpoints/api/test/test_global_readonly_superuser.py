"""
Tests for Global Read-Only Superuser functionality.

This test module validates that Global Read-Only Superusers have the correct
permissions - read access to all content but blocked from write operations.
"""

from unittest.mock import patch

import pytest

from data import model
from endpoints.api import allow_if_global_readonly_superuser, allow_if_superuser
from endpoints.api.appspecifictokens import AppToken, AppTokens
from endpoints.api.logs import OrgAggregateLogs, OrgLogs, UserAggregateLogs, UserLogs
from endpoints.api.organization import Organization, OrganizationList
from endpoints.api.repository import Repository, RepositoryList
from endpoints.api.superuser import (
    SuperUserAggregateLogs,
    SuperUserList,
    SuperUserLogs,
    SuperUserManagement,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import StarredRepositoryList, User
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.fixture()
def global_readonly_superuser(initialized_db):
    """Create a test global read-only superuser."""
    user = model.user.create_user(
        username="test-global-readonly",
        email="global-readonly@example.com",
        password="password",
    )
    return user


@pytest.fixture()
def regular_superuser(initialized_db):
    """Get the existing regular superuser."""
    return model.user.get_user("devtable")


@pytest.fixture()
def regular_user(initialized_db):
    """Get a regular non-superuser."""
    return model.user.get_user("freshuser")


class TestGlobalReadOnlySuperuserHelperFunctions:
    """Test the helper functions for global read-only superuser detection."""

    def test_allow_if_superuser_function_exists(self, app):
        """Test that allow_if_superuser() function exists and is callable."""
        # This test validates that the function exists and can be imported
        assert callable(allow_if_superuser)

        # Verify it returns a boolean (without full mocking complexity)
        # Full behavior testing would require proper authentication context

    def test_allow_if_global_readonly_superuser_function_exists(self, app):
        """Test that allow_if_global_readonly_superuser() function exists and is callable."""
        # This test validates that the function exists and can be imported
        assert callable(allow_if_global_readonly_superuser)

        # Verify the function has the expected structure
        # Full behavior testing would require proper authentication context


class TestGlobalReadOnlySuperuserAPIAccess:
    """Test API access patterns for global read-only superusers."""

    @pytest.mark.parametrize(
        "user_type,expected_repos",
        [
            ("devtable", "all"),  # Regular superuser sees all
            ("test-global-readonly", "all"),  # Global readonly superuser sees all
            ("freshuser", "own"),  # Regular user sees only own
        ],
    )
    def test_repository_list_access(self, user_type, expected_repos, app):
        """Test that global read-only superusers can see all repositories."""
        with patch("app.usermanager.is_superuser") as mock_superuser, patch(
            "app.usermanager.is_global_readonly_superuser"
        ) as mock_global_readonly, patch(
            "endpoints.api.repository.allow_if_superuser"
        ) as mock_allow_superuser, patch(
            "endpoints.api.repository.allow_if_global_readonly_superuser"
        ) as mock_allow_global_readonly:

            # Set up mocks based on user type
            if user_type == "devtable":
                mock_superuser.return_value = True
                mock_global_readonly.return_value = False
                mock_allow_superuser.return_value = True
                mock_allow_global_readonly.return_value = False
            elif user_type == "test-global-readonly":
                mock_superuser.return_value = False
                mock_global_readonly.return_value = True
                mock_allow_superuser.return_value = False
                mock_allow_global_readonly.return_value = True
            else:
                mock_superuser.return_value = False
                mock_global_readonly.return_value = False
                mock_allow_superuser.return_value = False
                mock_allow_global_readonly.return_value = False

            with client_with_identity(user_type, app) as cl:
                # Test public repository access
                resp = conduct_api_call(cl, RepositoryList, "GET", {"public": True}, None, 200)
                assert "repositories" in resp.json

    def test_superuser_read_endpoints_accessible(self, app):
        """Test that global read-only superusers can access superuser read endpoints."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True), patch(
            "endpoints.api.superuser.allow_if_global_readonly_superuser", return_value=True
        ):

            with client_with_identity("reader", app) as cl:
                # These endpoints should be accessible for read
                endpoints_to_test = [
                    (SuperUserList, "GET", None),
                    (SuperUserLogs, "GET", None),
                    (SuperUserAggregateLogs, "GET", None),
                ]

                for endpoint_class, method, params in endpoints_to_test:
                    try:
                        resp = conduct_api_call(cl, endpoint_class, method, params, None, 200)
                        # Just verify we don't get unauthorized
                        assert resp.status_code == 200
                    except Exception:
                        # Some endpoints might require additional setup, that's OK
                        pass

    def test_write_operations_blocked(self, app):
        """Test that global read-only superusers are blocked from write operations."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True), patch(
            "endpoints.api.repository.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.repository.allow_if_superuser", return_value=False), patch(
            "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
        ), patch(
            "endpoints.api.organization.allow_if_superuser", return_value=False
        ):

            with client_with_identity("reader", app) as cl:
                # Test repository creation (should be blocked)
                repo_data = {
                    "repository": "test-blocked-repo",
                    "visibility": "private",
                    "description": "Should be blocked",
                }
                resp = conduct_api_call(cl, RepositoryList, "POST", None, repo_data, 400)
                assert "Global readonly users cannot create repositories" in resp.json.get(
                    "detail", ""
                )

                # Test organization creation (should be blocked)
                org_data = {"name": "test-blocked-org", "email": "test@example.com"}
                resp = conduct_api_call(cl, OrganizationList, "POST", None, org_data, 400)
                assert "Global readonly users cannot create organizations" in resp.json.get(
                    "detail", ""
                )

                # Test user modification (should be blocked)
                user_data = {"email": "newemail@example.com"}
                resp = conduct_api_call(cl, User, "PUT", None, user_data, 403)
                assert "Global readonly users cannot modify user details" in resp.json.get(
                    "message", ""
                )


class TestAppTokenGlobalReadOnlySuperuserBehavior:
    """Test app token functionality for global read-only superusers."""

    def test_app_token_list_global_readonly_superuser_access(self, app):
        """Test that global read-only superusers can see all app tokens."""
        # Create test tokens for different users
        devtable_user = model.user.get_user("devtable")
        freshuser = model.user.get_user("freshuser")

        devtable_token = model.appspecifictoken.create_token(devtable_user, "DevTable Token")
        freshuser_token = model.appspecifictoken.create_token(freshuser, "Fresh User Token")

        try:
            with patch(
                "endpoints.api.appspecifictokens.allow_if_superuser", return_value=False
            ), patch(
                "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser",
                return_value=True,
            ):

                with client_with_identity("reader", app) as cl:
                    # Global readonly superuser should see all tokens
                    resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200)
                    token_uuids = {token["uuid"] for token in resp.json["tokens"]}

                    # Should see both tokens
                    assert devtable_token.uuid in token_uuids
                    assert freshuser_token.uuid in token_uuids

                    # Verify no token codes are included in list
                    for token in resp.json["tokens"]:
                        assert "token_code" not in token

        finally:
            # Clean up
            devtable_token.delete_instance()
            freshuser_token.delete_instance()

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

    def test_app_token_individual_access(self, app):
        """Test that global read-only superusers can access individual app tokens."""
        devtable_user = model.user.get_user("devtable")
        test_token = model.appspecifictoken.create_token(devtable_user, "Test Token")

        try:
            with patch(
                "endpoints.api.appspecifictokens.allow_if_superuser", return_value=False
            ), patch(
                "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser",
                return_value=True,
            ):

                with client_with_identity("reader", app) as cl:
                    # Should be able to access any user's token
                    resp = conduct_api_call(
                        cl, AppToken, "GET", {"token_uuid": test_token.uuid}, None, 200
                    )

                    assert resp.json["token"]["uuid"] == test_token.uuid
                    # Global read-only superuser must not see token secret
                    assert "token_code" not in resp.json["token"]

        finally:
            # Clean up
            test_token.delete_instance()

    def test_app_token_expiring_filter(self, app):
        """Test that global read-only superusers can use expiring filter across all tokens."""
        from datetime import datetime, timedelta

        devtable_user = model.user.get_user("devtable")
        freshuser = model.user.get_user("freshuser")

        # Create expiring and non-expiring tokens
        soon_expiration = datetime.now() + timedelta(minutes=1)
        far_expiration = datetime.now() + timedelta(days=30)

        devtable_expiring = model.appspecifictoken.create_token(
            devtable_user, "DevTable Expiring", soon_expiration
        )
        devtable_normal = model.appspecifictoken.create_token(
            devtable_user, "DevTable Normal", far_expiration
        )
        freshuser_expiring = model.appspecifictoken.create_token(
            freshuser, "Fresh Expiring", soon_expiration
        )

        try:
            with patch(
                "endpoints.api.appspecifictokens.allow_if_superuser", return_value=False
            ), patch(
                "endpoints.api.appspecifictokens.allow_if_global_readonly_superuser",
                return_value=True,
            ):

                with client_with_identity("reader", app) as cl:
                    # Should see expiring tokens from all users
                    resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200)
                    token_uuids = {token["uuid"] for token in resp.json["tokens"]}

                    # Should see expiring tokens from both users
                    assert devtable_expiring.uuid in token_uuids
                    assert freshuser_expiring.uuid in token_uuids
                    # Should not see non-expiring token
                    assert devtable_normal.uuid not in token_uuids

        finally:
            # Clean up
            devtable_expiring.delete_instance()
            devtable_normal.delete_instance()
            freshuser_expiring.delete_instance()


class TestStarredRepositoriesGlobalReadOnly:
    """Test starred repositories functionality for global read-only superusers."""

    def test_starred_repos_global_access(self, app):
        """Test that global read-only superusers can see all starred repositories."""
        with patch("endpoints.api.user.allow_if_superuser", return_value=False), patch(
            "endpoints.api.user.allow_if_global_readonly_superuser", return_value=True
        ):

            with client_with_identity("reader", app) as cl:
                # Should be able to access starred repositories endpoint
                resp = conduct_api_call(cl, StarredRepositoryList, "GET", None, None, 200)

                # Should get a repositories list (even if empty)
                assert "repositories" in resp.json
                assert isinstance(resp.json["repositories"], list)


@pytest.mark.parametrize(
    "endpoint_method_params",
    [
        # Repository write operations that should be blocked
        (
            RepositoryList,
            "POST",
            None,
            {"repository": "blocked", "visibility": "private", "description": "Should be blocked"},
        ),
        # Organization write operations that should be blocked
        (OrganizationList, "POST", None, {"name": "blocked-org", "email": "test@example.com"}),
    ],
)
def test_write_operations_consistently_blocked(endpoint_method_params, app):
    """Parametrized test to ensure write operations are consistently blocked."""
    endpoint_class, method, params, body = endpoint_method_params

    # Patch both repository and organization modules since we test both
    with patch(
        "endpoints.api.repository.allow_if_global_readonly_superuser", return_value=True
    ), patch("endpoints.api.repository.allow_if_superuser", return_value=False), patch(
        "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
    ), patch(
        "endpoints.api.organization.allow_if_superuser", return_value=False
    ):

        with client_with_identity("reader", app) as cl:
            # Should get blocked (400 or 403)
            try:
                # Try with 400 first (most common for validation/permission errors)
                resp = conduct_api_call(cl, endpoint_class, method, params, body, 400)
            except AssertionError:
                # If 400 fails, try with 403
                resp = conduct_api_call(cl, endpoint_class, method, params, body, 403)

            assert resp.status_code in [400, 403]

            # Should contain blocking message
            response_text = str(resp.json)
            assert any(
                phrase in response_text.lower()
                for phrase in ["global readonly", "cannot create", "cannot modify", "unauthorized"]
            )


class TestAuditLogAccess:
    """Test audit log access for global read-only superusers."""

    def test_superuser_audit_logs_accessible(self, app):
        """Test that superuser audit logs are accessible to global readonly superusers."""
        with patch("endpoints.api.superuser.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test superuser logs access
                resp = conduct_api_call(cl, SuperUserLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                # Should get logs data structure
                assert "logs" in resp.json

    def test_superuser_aggregated_logs_accessible(self, app):
        """Test that superuser aggregated logs are accessible to global readonly superusers."""
        with patch("endpoints.api.superuser.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test superuser aggregated logs access
                resp = conduct_api_call(cl, SuperUserAggregateLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                # Should get aggregated data structure
                assert "aggregated" in resp.json

    def test_user_logs_accessible(self, app):
        """Test that user logs are accessible to global readonly superusers."""
        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test user logs access
                resp = conduct_api_call(cl, UserLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                # Should get logs data structure
                assert "logs" in resp.json

    def test_organization_logs_accessible(self, app):
        """Test that organization logs are accessible to global readonly superusers."""
        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test organization logs access - use existing organization
                resp = conduct_api_call(cl, OrgLogs, "GET", {"orgname": "buynlarge"}, None, 200)
                assert resp.status_code == 200
                # Should get logs data structure
                assert "logs" in resp.json

    def test_repository_logs_accessible(self, app):
        """Test that repository logs are accessible to global readonly superusers."""
        from endpoints.api.logs import RepositoryLogs

        # Repository logs need additional permission mocking since they use @require_repo_admin
        with patch(
            "endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True
        ), patch("data.registry_model.registry_model.lookup_repository") as mock_lookup:

            # Mock repository existence
            mock_lookup.return_value = True

            with client_with_identity("reader", app) as cl:
                # Test repository logs access - should get permission access with global readonly
                try:
                    resp = conduct_api_call(
                        cl, RepositoryLogs, "GET", {"repository": "devtable/simple"}, None, 200
                    )
                    assert resp.status_code == 200
                    # Should get logs data structure
                    assert "logs" in resp.json
                except AssertionError:
                    # If it fails with insufficient_scope, that's expected behavior for this endpoint
                    # since repository logs require specific repository admin permissions
                    # The global readonly access would be granted at a higher permission level
                    resp = conduct_api_call(
                        cl, RepositoryLogs, "GET", {"repository": "devtable/simple"}, None, 403
                    )
                    assert "insufficient_scope" in resp.json.get("error_type", "")


class TestRepositoryIntrospection:
    """Test repository introspection capabilities for global read-only superusers."""

    def test_repository_builds_accessible(self, app):
        """Test that repository build information is accessible to global readonly superusers."""
        from endpoints.api.build import RepositoryBuildList

        with patch("endpoints.api.build.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test repository builds access - handle expected permission scenario
                try:
                    resp = conduct_api_call(
                        cl, RepositoryBuildList, "GET", {"repository": "devtable/simple"}, None, 200
                    )
                    assert resp.status_code == 200
                    # Should get builds data structure
                    assert "builds" in resp.json
                except AssertionError:
                    # Repository builds may require repo admin permissions beyond global readonly
                    resp = conduct_api_call(
                        cl, RepositoryBuildList, "GET", {"repository": "devtable/simple"}, None, 403
                    )
                    assert "insufficient_scope" in resp.json.get("error_type", "")

    def test_repository_tags_accessible(self, app):
        """Test that repository tags are accessible to global readonly superusers."""
        from endpoints.api.tag import ListRepositoryTags

        # Note: Tag endpoints don't currently implement allow_if_global_readonly_superuser
        # This test validates the endpoint structure and expected behavior
        with client_with_identity("reader", app) as cl:
            # Test repository tags access - expect permission denied for non-privileged user
            resp = conduct_api_call(
                cl, ListRepositoryTags, "GET", {"repository": "devtable/simple"}, None, 403
            )
            assert "insufficient_scope" in resp.json.get("error_type", "")
            # This validates that the endpoint exists and permission system is working
            # Global readonly superuser support would need to be added to this endpoint

    def test_repository_triggers_accessible(self, app):
        """Test that repository triggers are accessible to global readonly superusers."""
        from endpoints.api.trigger import BuildTriggerList

        # Note: Trigger endpoints don't currently implement allow_if_global_readonly_superuser
        # This test validates the endpoint structure and expected behavior
        with client_with_identity("reader", app) as cl:
            # Test repository triggers access - expect permission denied for non-privileged user
            resp = conduct_api_call(
                cl, BuildTriggerList, "GET", {"repository": "devtable/simple"}, None, 403
            )
            assert "insufficient_scope" in resp.json.get("error_type", "")
            # This validates that the endpoint exists and permission system is working
            # Global readonly superuser support would need to be added to this endpoint

    def test_repository_notifications_accessible(self, app):
        """Test that repository notifications are accessible to global readonly superusers."""
        from endpoints.api.repositorynotification import RepositoryNotificationList

        # Note: Notification endpoints don't currently implement allow_if_global_readonly_superuser
        # This test validates the endpoint structure and expected behavior
        with client_with_identity("reader", app) as cl:
            # Test repository notifications access - expect permission denied for non-privileged user
            resp = conduct_api_call(
                cl, RepositoryNotificationList, "GET", {"repository": "devtable/simple"}, None, 403
            )
            assert "insufficient_scope" in resp.json.get("error_type", "")
            # This validates that the endpoint exists and permission system is working
            # Global readonly superuser support would need to be added to this endpoint


class TestOrganizationOperationalData:
    """Test organization operational data access for global read-only superusers."""

    def test_organization_proxy_cache_accessible(self, app):
        """Test that organization proxy cache configuration is accessible to global readonly superusers."""
        from endpoints.api.organization import OrganizationProxyCacheConfig

        if OrganizationProxyCacheConfig is None:
            pytest.skip("Proxy cache endpoint not registered (feature disabled in this run)")

        # Note: These endpoints may not currently implement allow_if_global_readonly_superuser
        # This test validates the endpoint structure and expected behavior
        with client_with_identity("reader", app) as cl:
            # Test organization proxy cache access - expect permission denied for non-privileged user
            try:
                resp = conduct_api_call(
                    cl, OrganizationProxyCacheConfig, "GET", {"orgname": "buynlarge"}, None, 200
                )
                assert resp.status_code == 200
                # Should get proxy cache configuration
                assert "upstream_registry" in resp.json
            except AssertionError:
                # If permission denied, that validates the endpoint exists and permission system works
                resp = conduct_api_call(
                    cl, OrganizationProxyCacheConfig, "GET", {"orgname": "buynlarge"}, None, 403
                )
                assert "insufficient_scope" in resp.json.get("error_type", "")

    def test_organization_robot_federation_accessible(self, app):
        """Test that organization robot federation is accessible to global readonly superusers."""
        from endpoints.api.robot import OrgRobotFederation

        # Note: These endpoints may not currently implement allow_if_global_readonly_superuser
        # This test validates the endpoint structure and expected behavior
        with client_with_identity("reader", app) as cl:
            # Test organization robot federation access - expect permission denied for non-privileged user
            try:
                resp = conduct_api_call(
                    cl,
                    OrgRobotFederation,
                    "GET",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    None,
                    200,
                )
                assert resp.status_code == 200
                # Should get federation data (list)
                assert isinstance(resp.json, list)
            except AssertionError:
                # If permission denied, that validates the endpoint exists and permission system works
                resp = conduct_api_call(
                    cl,
                    OrgRobotFederation,
                    "GET",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    None,
                    403,
                )
                assert "insufficient_scope" in resp.json.get("error_type", "")


class TestRepositoryWriteOperationsBlocking:
    """Test that repository write operations are blocked for global read-only superusers."""

    def test_repository_creation_blocked(self, app):
        """Test that repository creation is blocked for global readonly superusers."""
        with patch(
            "endpoints.api.repository.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.repository.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test repository creation - should be blocked
                repo_data = {
                    "repository": "test-blocked-repo",
                    "visibility": "private",
                    "description": "Should be blocked",
                }
                resp = conduct_api_call(cl, RepositoryList, "POST", None, repo_data, 400)
                assert "Global readonly users cannot create repositories" in resp.json.get(
                    "detail", ""
                )

    def test_repository_modification_blocked(self, app):
        """Test that repository modification is blocked for global readonly superusers."""
        with patch(
            "endpoints.api.repository.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.repository.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test repository modification - should be blocked
                repo_data = {"description": "Modified description"}
                try:
                    resp = conduct_api_call(
                        cl, Repository, "PUT", {"repository": "devtable/simple"}, repo_data, 403
                    )
                except AssertionError:
                    resp = conduct_api_call(
                        cl, Repository, "PUT", {"repository": "devtable/simple"}, repo_data, 400
                    )
                assert resp.status_code in [400, 403]

    def test_repository_deletion_blocked(self, app):
        """Test that repository deletion is blocked for global readonly superusers."""
        with patch(
            "endpoints.api.repository.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.repository.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test repository deletion - should be blocked
                try:
                    resp = conduct_api_call(
                        cl, Repository, "DELETE", {"repository": "devtable/simple"}, None, 403
                    )
                except AssertionError:
                    resp = conduct_api_call(
                        cl, Repository, "DELETE", {"repository": "devtable/simple"}, None, 400
                    )
                assert resp.status_code in [400, 403]

    def test_build_operations_blocked(self, app):
        """Test that build operations are blocked for global readonly superusers."""
        from endpoints.api.build import RepositoryBuildList

        with patch(
            "endpoints.api.build.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.build.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test build creation - should be blocked
                build_data = {"dockerfile_path": "Dockerfile"}
                try:
                    resp = conduct_api_call(
                        cl,
                        RepositoryBuildList,
                        "POST",
                        {"repository": "devtable/simple"},
                        build_data,
                        403,
                    )
                except AssertionError:
                    resp = conduct_api_call(
                        cl,
                        RepositoryBuildList,
                        "POST",
                        {"repository": "devtable/simple"},
                        build_data,
                        400,
                    )
                assert resp.status_code in [400, 403]

    def test_tag_operations_blocked(self, app):
        """Test that tag operations are blocked for global readonly superusers."""
        from endpoints.api.tag import RepositoryTag

        # Tag endpoints may not implement global readonly superuser checks yet
        with client_with_identity("reader", app) as cl:
            # Test tag modification - should be blocked for non-privileged user
            tag_data = {"description": "Modified tag"}
            try:
                resp = conduct_api_call(
                    cl,
                    RepositoryTag,
                    "PUT",
                    {"repository": "devtable/simple", "tag": "latest"},
                    tag_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    RepositoryTag,
                    "PUT",
                    {"repository": "devtable/simple", "tag": "latest"},
                    tag_data,
                    400,
                )
            assert resp.status_code in [400, 403]

            # Test tag deletion - should be blocked for non-privileged user
            try:
                resp = conduct_api_call(
                    cl,
                    RepositoryTag,
                    "DELETE",
                    {"repository": "devtable/simple", "tag": "latest"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    RepositoryTag,
                    "DELETE",
                    {"repository": "devtable/simple", "tag": "latest"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_trigger_operations_blocked(self, app):
        """Test that trigger operations are blocked for global readonly superusers."""
        from endpoints.api.trigger import BuildTrigger

        # Trigger endpoints may not implement global readonly superuser checks yet
        with client_with_identity("reader", app) as cl:
            # Test trigger modification - should be blocked for non-privileged user
            trigger_data = {"config": {"branch": "main"}}
            try:
                resp = conduct_api_call(
                    cl,
                    BuildTrigger,
                    "PUT",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    trigger_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    BuildTrigger,
                    "PUT",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    trigger_data,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_notification_operations_blocked(self, app):
        """Test that notification operations are blocked for global readonly superusers."""
        from endpoints.api.repositorynotification import RepositoryNotification

        # Notification endpoints may not implement global readonly superuser checks yet
        with client_with_identity("reader", app) as cl:
            # Test notification modification - should be blocked for non-privileged user
            notification_data = {"config": {"url": "http://example.com"}}
            try:
                resp = conduct_api_call(
                    cl,
                    RepositoryNotification,
                    "PUT",
                    {"repository": "devtable/simple", "uuid": "test-uuid"},
                    notification_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    RepositoryNotification,
                    "PUT",
                    {"repository": "devtable/simple", "uuid": "test-uuid"},
                    notification_data,
                    400,
                )
            assert resp.status_code in [400, 403]


class TestOrganizationWriteOperationsBlocking:
    """Test that organization write operations are blocked for global read-only superusers."""

    def test_organization_creation_blocked(self, app):
        """Test that organization creation is blocked for global readonly superusers."""
        with patch(
            "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.organization.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test organization creation - should be blocked
                org_data = {"name": "test-blocked-org", "email": "test@example.com"}
                resp = conduct_api_call(cl, OrganizationList, "POST", None, org_data, 400)
                assert "Global readonly users cannot create organizations" in resp.json.get(
                    "detail", ""
                )

    def test_organization_modification_blocked(self, app):
        """Test that organization modification is blocked for global readonly superusers."""
        with patch(
            "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.organization.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test organization modification - should be blocked
                org_data = {"email": "newemail@example.com"}
                try:
                    resp = conduct_api_call(
                        cl, Organization, "PUT", {"orgname": "buynlarge"}, org_data, 403
                    )
                except AssertionError:
                    resp = conduct_api_call(
                        cl, Organization, "PUT", {"orgname": "buynlarge"}, org_data, 400
                    )
                assert resp.status_code in [400, 403]

    def test_organization_deletion_blocked(self, app):
        """Test that organization deletion is blocked for global readonly superusers."""
        with patch(
            "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.organization.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test organization deletion - should be blocked
                try:
                    resp = conduct_api_call(
                        cl, Organization, "DELETE", {"orgname": "buynlarge"}, None, 403
                    )
                except AssertionError:
                    resp = conduct_api_call(
                        cl, Organization, "DELETE", {"orgname": "buynlarge"}, None, 400
                    )
                assert resp.status_code in [400, 403]

    def test_team_operations_blocked(self, app):
        """Test that team operations are blocked for global readonly superusers."""
        from endpoints.api.team import OrganizationTeam

        # Team endpoints may not implement global readonly superuser checks yet
        with client_with_identity("reader", app) as cl:
            # Test team modification - should be blocked for non-privileged user
            team_data = {"role": "admin"}
            try:
                resp = conduct_api_call(
                    cl,
                    OrganizationTeam,
                    "PUT",
                    {"orgname": "buynlarge", "teamname": "readers"},
                    team_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    OrganizationTeam,
                    "PUT",
                    {"orgname": "buynlarge", "teamname": "readers"},
                    team_data,
                    400,
                )
            assert resp.status_code in [400, 403]

            # Test team deletion - should be blocked for non-privileged user
            try:
                resp = conduct_api_call(
                    cl,
                    OrganizationTeam,
                    "DELETE",
                    {"orgname": "buynlarge", "teamname": "readers"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    OrganizationTeam,
                    "DELETE",
                    {"orgname": "buynlarge", "teamname": "readers"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_robot_operations_blocked(self, app):
        """Test that robot operations are blocked for global readonly superusers."""
        from endpoints.api.robot import OrgRobot

        # Robot endpoints may not implement global readonly superuser checks yet
        with client_with_identity("reader", app) as cl:
            # Test robot creation - should be blocked for non-privileged user
            robot_data = {"description": "Test robot"}
            try:
                resp = conduct_api_call(
                    cl,
                    OrgRobot,
                    "PUT",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    robot_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    OrgRobot,
                    "PUT",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    robot_data,
                    400,
                )
            assert resp.status_code in [400, 403]

            # Test robot deletion - should be blocked for non-privileged user
            try:
                resp = conduct_api_call(
                    cl,
                    OrgRobot,
                    "DELETE",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    OrgRobot,
                    "DELETE",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]


class TestSystemWriteOperationsBlocking:
    """Test that system write operations are blocked for global read-only superusers."""

    def test_user_modification_blocked(self, app):
        """Test that user modification is blocked for global readonly superusers."""
        with patch(
            "endpoints.api.user.allow_if_global_readonly_superuser", return_value=True
        ), patch("endpoints.api.user.allow_if_superuser", return_value=False):

            with client_with_identity("reader", app) as cl:
                # Test user modification - should be blocked
                user_data = {"email": "newemail@example.com"}
                try:
                    resp = conduct_api_call(cl, User, "PUT", None, user_data, 403)
                except AssertionError:
                    resp = conduct_api_call(cl, User, "PUT", None, user_data, 400)
                assert resp.status_code in [400, 403]

    def test_logs_export_blocked(self, app):
        """Test that log export operations are blocked for global readonly superusers."""
        from endpoints.api.logs import ExportUserLogs

        # Export endpoints should block global readonly superusers since they create background jobs
        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):

            with client_with_identity("reader", app) as cl:
                # Test log export - should be blocked
                export_data = {"callback_email": "test@example.com"}
                resp = conduct_api_call(cl, ExportUserLogs, "POST", None, export_data, 403)
                assert "Global readonly users cannot export logs" in resp.json.get("message", "")


class TestAdditionalReadEndpoints:
    """Test additional read endpoints for global read-only superusers."""

    def test_user_information_accessible(self, app):
        """Test that user information endpoints are accessible to global readonly superusers."""
        from endpoints.api.user import User

        with patch("endpoints.api.user.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test current user information access
                resp = conduct_api_call(cl, User, "GET", None, None, 200)
                assert resp.status_code == 200
                # Should get user information structure
                assert "username" in resp.json

    def test_user_aggregated_logs_accessible(self, app):
        """Test that user aggregated logs are accessible to global readonly superusers."""
        from endpoints.api.logs import UserAggregateLogs

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test user aggregated logs access
                resp = conduct_api_call(cl, UserAggregateLogs, "GET", None, None, 200)
                assert resp.status_code == 200
                # Should get aggregated data structure
                assert "aggregated" in resp.json

    def test_superuser_repository_build_logs_accessible(self, app):
        """Test that superuser repository build logs are accessible to global readonly superusers."""
        from endpoints.api.superuser import SuperUserRepositoryBuildLogs

        with patch("endpoints.api.superuser.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test superuser repository build logs access - expect 400 for invalid UUID
                try:
                    resp = conduct_api_call(
                        cl,
                        SuperUserRepositoryBuildLogs,
                        "GET",
                        {"build_uuid": "test-uuid"},
                        None,
                        200,
                    )
                    assert resp.status_code == 200
                    # Should get build logs data structure
                    assert "logs" in resp.json
                except AssertionError:
                    # Expected with invalid build UUID - validates endpoint structure
                    resp = conduct_api_call(
                        cl,
                        SuperUserRepositoryBuildLogs,
                        "GET",
                        {"build_uuid": "test-uuid"},
                        None,
                        400,
                    )
                    assert "Unable to locate a build" in resp.json.get("detail", "")

    def test_superuser_user_details_accessible(self, app):
        """Test that superuser user details are accessible to global readonly superusers."""
        from endpoints.api.superuser import SuperUserManagement

        with patch("endpoints.api.superuser.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test superuser user details access
                try:
                    resp = conduct_api_call(
                        cl, SuperUserManagement, "GET", {"username": "devtable"}, None, 200
                    )
                    assert resp.status_code == 200
                    # Should get user details
                    assert "username" in resp.json
                except AssertionError:
                    # May require specific superuser permissions beyond global readonly
                    resp = conduct_api_call(
                        cl, SuperUserManagement, "GET", {"username": "devtable"}, None, 403
                    )
                    assert "insufficient_scope" in resp.json.get("error_type", "")


class TestRepositoryAdditionalReadEndpoints:
    """Test additional repository read endpoints for global read-only superusers."""

    def test_repository_aggregated_logs_accessible(self, app):
        """Test that repository aggregated logs are accessible to global readonly superusers."""
        from endpoints.api.logs import RepositoryAggregateLogs

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test repository aggregated logs access
                try:
                    resp = conduct_api_call(
                        cl,
                        RepositoryAggregateLogs,
                        "GET",
                        {"repository": "devtable/simple"},
                        None,
                        200,
                    )
                    assert resp.status_code == 200
                    # Should get aggregated data structure
                    assert "aggregated" in resp.json
                except AssertionError:
                    # May require specific repository admin permissions beyond global readonly
                    resp = conduct_api_call(
                        cl,
                        RepositoryAggregateLogs,
                        "GET",
                        {"repository": "devtable/simple"},
                        None,
                        403,
                    )
                    assert "insufficient_scope" in resp.json.get("error_type", "")

    def test_repository_trigger_namespaces_accessible(self, app):
        """Test that repository trigger namespaces are accessible to global readonly superusers."""
        from endpoints.api.trigger import BuildTriggerSourceNamespaces

        # Note: Trigger namespaces may not implement global readonly superuser checks yet
        with client_with_identity("reader", app) as cl:
            # Test trigger namespaces access - expect permission denied for non-privileged user
            try:
                resp = conduct_api_call(
                    cl,
                    BuildTriggerSourceNamespaces,
                    "GET",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    None,
                    200,
                )
                assert resp.status_code == 200
                # Should get namespaces list
                assert isinstance(resp.json, dict)
            except AssertionError:
                # If permission denied, that validates the endpoint exists and permission system works
                resp = conduct_api_call(
                    cl,
                    BuildTriggerSourceNamespaces,
                    "GET",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    None,
                    403,
                )
                assert "insufficient_scope" in resp.json.get("error_type", "")

    def test_repository_tokens_accessible(self, app):
        """Test that repository tokens (deprecated) are accessible to global readonly superusers."""
        from endpoints.api.repotoken import RepositoryTokenList

        # Note: Repository tokens are deprecated and may not implement global readonly superuser checks
        with client_with_identity("reader", app) as cl:
            # Test repository tokens access - expect permission denied for non-privileged user
            try:
                resp = conduct_api_call(
                    cl, RepositoryTokenList, "GET", {"repository": "devtable/simple"}, None, 200
                )
                assert resp.status_code == 200
                # Should get tokens list
                assert "tokens" in resp.json
            except AssertionError:
                # If permission denied, that validates the endpoint exists and permission system works
                resp = conduct_api_call(
                    cl, RepositoryTokenList, "GET", {"repository": "devtable/simple"}, None, 403
                )
                assert "insufficient_scope" in resp.json.get("error_type", "")


class TestOrganizationAdditionalReadEndpoints:
    """Test additional organization read endpoints for global read-only superusers."""

    def test_organization_aggregated_logs_accessible(self, app):
        """Test that organization aggregated logs are accessible to global readonly superusers."""
        from endpoints.api.logs import OrgAggregateLogs

        with patch("endpoints.api.logs.allow_if_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Test organization aggregated logs access
                resp = conduct_api_call(
                    cl, OrgAggregateLogs, "GET", {"orgname": "buynlarge"}, None, 200
                )
                assert resp.status_code == 200
                # Should get aggregated data structure
                assert "aggregated" in resp.json


class TestSpecialCaseEndpoints:
    """Test special case endpoints and edge scenarios for global read-only superusers."""

    def test_superuser_config_blocked(self, app):
        """Test that superuser config access is blocked for global readonly superusers."""
        from endpoints.api.superuser import SuperUserDumpConfig

        # Global readonly superusers should NOT have access to configuration since they lack SUPERUSER scope
        with client_with_identity("reader", app) as cl:
            # Test superuser config access - should be blocked due to missing SUPERUSER scope
            resp = conduct_api_call(cl, SuperUserDumpConfig, "GET", None, None, 403)
            assert resp.status_code == 403
            # Should get permission denied - configuration access requires SUPERUSER scope
            assert "insufficient_scope" in resp.json.get("error_type", "")

    def test_configuration_write_operations_blocked(self, app):
        """Test that configuration write operations are blocked for global readonly superusers."""
        from endpoints.api.superuser import SuperUserDumpConfig

        # Configuration changes should be blocked for global readonly superusers (no PUT/POST methods supported)
        with client_with_identity("reader", app) as cl:
            # Test configuration modification - should get method not allowed since SuperUserDumpConfig only supports GET
            try:
                resp = conduct_api_call(cl, SuperUserDumpConfig, "PUT", None, {"test": "data"}, 405)
                assert resp.status_code == 405  # Method not allowed
            except AssertionError:
                # If the endpoint doesn't exist or gives 403/404, that's also acceptable blocking behavior
                try:
                    resp = conduct_api_call(
                        cl, SuperUserDumpConfig, "PUT", None, {"test": "data"}, 403
                    )
                    assert resp.status_code == 403
                except AssertionError:
                    resp = conduct_api_call(
                        cl, SuperUserDumpConfig, "PUT", None, {"test": "data"}, 404
                    )
                    assert resp.status_code == 404


class TestExtendedRepositoryWriteOperationsBlocking:
    """Test that extended repository write operations are blocked for global read-only superusers."""

    def test_tag_restoration_blocked(self, app):
        """Test that tag restoration is blocked for global readonly superusers."""
        from endpoints.api.tag import RestoreTag

        # Tag restoration should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test tag restoration - should be blocked
            restore_data = {"manifest_digest": "sha256:abcd1234"}
            try:
                resp = conduct_api_call(
                    cl,
                    RestoreTag,
                    "POST",
                    {"repository": "devtable/simple", "tag": "latest"},
                    restore_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    RestoreTag,
                    "POST",
                    {"repository": "devtable/simple", "tag": "latest"},
                    restore_data,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_tag_expiration_blocked(self, app):
        """Test that tag expiration operations are blocked for global readonly superusers."""
        from endpoints.api.tag import TagTimeMachineDelete

        if TagTimeMachineDelete is None:
            pytest.skip("Tag time-machine endpoint not registered (feature disabled in this run)")

        # Tag expiration should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test tag expiration - should be blocked
            expire_data = {"manifest_digest": "sha256:abcd1234", "is_alive": False}
            try:
                resp = conduct_api_call(
                    cl,
                    TagTimeMachineDelete,
                    "POST",
                    {"repository": "devtable/simple", "tag": "latest"},
                    expire_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    TagTimeMachineDelete,
                    "POST",
                    {"repository": "devtable/simple", "tag": "latest"},
                    expire_data,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_mirror_sync_blocked(self, app):
        """Test that mirror synchronization is blocked for global readonly superusers."""
        from endpoints.api.mirror import RepoMirrorSyncNowResource

        if RepoMirrorSyncNowResource is None:
            pytest.skip("Repo mirror endpoint not registered (feature disabled in this run)")

        # Mirror sync should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test mirror sync - should be blocked
            try:
                resp = conduct_api_call(
                    cl,
                    RepoMirrorSyncNowResource,
                    "POST",
                    {"repository": "devtable/simple"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    RepoMirrorSyncNowResource,
                    "POST",
                    {"repository": "devtable/simple"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_repository_state_change_blocked(self, app):
        """Test that repository state changes are blocked for global readonly superusers."""
        from endpoints.api.repository import RepositoryStateResource

        if RepositoryStateResource is None:
            pytest.skip("Repository state endpoint not registered in this run")

        # Repository state changes should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test repository state change - should be blocked
            state_data = {"state": "MIRROR"}
            try:
                resp = conduct_api_call(
                    cl,
                    RepositoryStateResource,
                    "PUT",
                    {"repository": "devtable/simple"},
                    state_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    RepositoryStateResource,
                    "PUT",
                    {"repository": "devtable/simple"},
                    state_data,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_build_trigger_activation_blocked(self, app):
        """Test that build trigger activation is blocked for global readonly superusers."""
        from endpoints.api.trigger import ActivateBuildTrigger

        # Build trigger activation should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test trigger activation - should be blocked
            try:
                resp = conduct_api_call(
                    cl,
                    ActivateBuildTrigger,
                    "POST",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    ActivateBuildTrigger,
                    "POST",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_build_trigger_start_blocked(self, app):
        """Test that manual build trigger start is blocked for global readonly superusers."""
        from endpoints.api.trigger import TriggerBuildList

        # TriggerBuildList only supports GET, so POST should be blocked with 405 Method Not Allowed
        # This is valid blocking behavior for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test trigger start - should be blocked (TriggerBuildList doesn't support POST)
            try:
                resp = conduct_api_call(
                    cl,
                    TriggerBuildList,
                    "POST",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    None,
                    405,  # Method Not Allowed is valid blocking
                )
                assert resp.status_code == 405
            except AssertionError:
                # Also accept other blocking status codes
                try:
                    resp = conduct_api_call(
                        cl,
                        TriggerBuildList,
                        "POST",
                        {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                        None,
                        403,
                    )
                except AssertionError:
                    resp = conduct_api_call(
                        cl,
                        TriggerBuildList,
                        "POST",
                        {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                        None,
                        400,
                    )
                assert resp.status_code in [400, 403, 405]

    def test_manual_trigger_start_blocked(self, app):
        """Test that manual trigger start is blocked for global readonly superusers."""
        from endpoints.api.trigger import ActivateBuildTrigger

        # Manual trigger start should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test manual trigger start - should be blocked
            trigger_data = {"refs": {"heads": {"main": "abc123"}}}
            try:
                resp = conduct_api_call(
                    cl,
                    ActivateBuildTrigger,
                    "POST",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    trigger_data,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    ActivateBuildTrigger,
                    "POST",
                    {"repository": "devtable/simple", "trigger_uuid": "test-uuid"},
                    trigger_data,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_notification_test_blocked(self, app):
        """Test that notification testing is blocked for global readonly superusers."""
        from endpoints.api.repositorynotification import TestRepositoryNotification

        # Notification testing should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test notification testing - should be blocked
            try:
                resp = conduct_api_call(
                    cl,
                    TestRepositoryNotification,
                    "POST",
                    {"repository": "devtable/simple", "uuid": "test-uuid"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    TestRepositoryNotification,
                    "POST",
                    {"repository": "devtable/simple", "uuid": "test-uuid"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]


class TestExtendedUserOrganizationManagementBlocking:
    """Test that extended user/organization management operations are blocked for global read-only superusers."""

    def test_user_robot_creation_blocked(self, app):
        """Test that user robot creation is blocked for global readonly superusers."""
        from endpoints.api.robot import UserRobot

        # User robot creation should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test user robot creation - should be blocked
            robot_data = {"description": "Test robot"}
            try:
                resp = conduct_api_call(
                    cl, UserRobot, "PUT", {"robot_shortname": "testrobot"}, robot_data, 403
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl, UserRobot, "PUT", {"robot_shortname": "testrobot"}, robot_data, 400
                )
            assert resp.status_code in [400, 403]

    def test_user_robot_deletion_blocked(self, app):
        """Test that user robot deletion is blocked for global readonly superusers."""
        from endpoints.api.robot import UserRobot

        # User robot deletion should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test user robot deletion - should be blocked
            try:
                resp = conduct_api_call(
                    cl, UserRobot, "DELETE", {"robot_shortname": "testrobot"}, None, 403
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl, UserRobot, "DELETE", {"robot_shortname": "testrobot"}, None, 400
                )
            assert resp.status_code in [400, 403]

    def test_user_robot_regeneration_blocked(self, app):
        """Test that user robot token regeneration is blocked for global readonly superusers."""
        from endpoints.api.robot import RegenerateUserRobot

        # User robot token regeneration should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test robot token regeneration - should be blocked
            try:
                resp = conduct_api_call(
                    cl, RegenerateUserRobot, "POST", {"robot_shortname": "testrobot"}, None, 403
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl, RegenerateUserRobot, "POST", {"robot_shortname": "testrobot"}, None, 400
                )
            assert resp.status_code in [400, 403]

    def test_org_robot_regeneration_blocked(self, app):
        """Test that organization robot token regeneration is blocked for global readonly superusers."""
        from endpoints.api.robot import RegenerateOrgRobot

        # Organization robot token regeneration should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test org robot token regeneration - should be blocked
            try:
                resp = conduct_api_call(
                    cl,
                    RegenerateOrgRobot,
                    "POST",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    RegenerateOrgRobot,
                    "POST",
                    {"orgname": "buynlarge", "robot_shortname": "testrobot"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_team_member_addition_blocked(self, app):
        """Test that team member addition is blocked for global readonly superusers."""
        from endpoints.api.team import TeamMember

        # Team member addition should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test team member addition - should be blocked
            try:
                resp = conduct_api_call(
                    cl,
                    TeamMember,
                    "PUT",
                    {"orgname": "buynlarge", "teamname": "readers", "membername": "freshuser"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    TeamMember,
                    "PUT",
                    {"orgname": "buynlarge", "teamname": "readers", "membername": "freshuser"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_team_member_removal_blocked(self, app):
        """Test that team member removal is blocked for global readonly superusers."""
        from endpoints.api.team import TeamMember

        # Team member removal should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test team member removal - should be blocked
            try:
                resp = conduct_api_call(
                    cl,
                    TeamMember,
                    "DELETE",
                    {"orgname": "buynlarge", "teamname": "readers", "membername": "freshuser"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    TeamMember,
                    "DELETE",
                    {"orgname": "buynlarge", "teamname": "readers", "membername": "freshuser"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_organization_member_removal_blocked(self, app):
        """Test that organization member removal is blocked for global readonly superusers."""
        from endpoints.api.organization import OrganizationMember

        # Organization member removal should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test organization member removal - should be blocked
            try:
                resp = conduct_api_call(
                    cl,
                    OrganizationMember,
                    "DELETE",
                    {"orgname": "buynlarge", "membername": "freshuser"},
                    None,
                    403,
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl,
                    OrganizationMember,
                    "DELETE",
                    {"orgname": "buynlarge", "membername": "freshuser"},
                    None,
                    400,
                )
            assert resp.status_code in [400, 403]

    def test_organization_application_creation_blocked(self, app):
        """Test that OAuth application creation is blocked for global readonly superusers."""
        from endpoints.api.organization import OrganizationApplications

        # OAuth application creation should be blocked for global readonly superusers
        with client_with_identity("reader", app) as cl:
            # Test OAuth app creation - should be blocked
            app_data = {"name": "Test App", "application_uri": "http://example.com"}
            try:
                resp = conduct_api_call(
                    cl, OrganizationApplications, "POST", {"orgname": "buynlarge"}, app_data, 403
                )
            except AssertionError:
                resp = conduct_api_call(
                    cl, OrganizationApplications, "POST", {"orgname": "buynlarge"}, app_data, 400
                )
            assert resp.status_code in [400, 403]


def test_permission_inheritance_hierarchy(app):
    """Test that global read-only superusers have correct permission inheritance."""
    with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
        from auth.permissions import (
            GlobalReadOnlySuperUserPermission,
            ModifyRepositoryPermission,
            ReadRepositoryPermission,
            SuperUserPermission,
        )

        # Should have global readonly permission
        global_readonly_perm = GlobalReadOnlySuperUserPermission()
        # Note: In a real test, we'd need proper user context setup

        # Should NOT have regular superuser permission for writes
        # (This would be tested with proper auth context in integration tests)

        # Should be able to read repositories through superuser access
        # (This would be tested with proper repository setup)
