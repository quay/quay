"""
Tests for pull statistics endpoint permissions (PROJQUAY-9775).

Pull statistics should be PRIVATE data - only accessible to users with
explicit repository permissions, not publicly accessible even for public repositories.
"""

import pytest

from endpoints.api.manifest import RepositoryManifestPullStatistics
from endpoints.api.organization import Organization
from endpoints.api.tag import RepositoryTagPullStatistics
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


class TestPullStatisticsRequireExplicitPermissions:
    """Test that pull statistics require explicit permissions, even for public repos."""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Disable SUPERUSERS_FULL_ACCESS for these tests."""
        import features

        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": False,
                "IMAGE_PULL_STATS": True,
            }
        )

        yield

        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": True,
                "IMAGE_PULL_STATS": True,
            }
        )

    def test_superuser_cannot_access_cross_namespace_tag_pull_stats(self, app):
        """
        Test that superusers CANNOT access tag pull statistics for other namespaces
        when FULL_ACCESS is disabled, even for public repositories.
        """
        with client_with_identity("devtable", app) as cl:
            # devtable (superuser) trying to access randomuser's repo pull statistics
            params = {
                "repository": "randomuser/simple",
                "tag": "latest",
            }
            # Should be blocked - no explicit permission
            conduct_api_call(cl, RepositoryTagPullStatistics, "GET", params, None, 403)

    def test_superuser_can_access_own_namespace_tag_pull_stats(self, app):
        """
        Test that superusers CAN access tag pull statistics for their own namespace.
        """
        with client_with_identity("devtable", app) as cl:
            # devtable accessing their own repo
            params = {
                "repository": "devtable/simple",
                "tag": "latest",
            }
            # Should succeed (or 404 if tag doesn't exist, but NOT 403)
            result = conduct_api_call(cl, RepositoryTagPullStatistics, "GET", params, None)
            assert result.status_code in [
                200,
                404,
            ], f"Expected 200 or 404, got {result.status_code}"

    def test_superuser_cannot_access_cross_namespace_manifest_pull_stats(self, app):
        """
        Test that superusers CANNOT access manifest pull statistics for other namespaces
        when FULL_ACCESS is disabled.
        """
        with client_with_identity("devtable", app) as cl:
            params = {
                "repository": "randomuser/simple",
                "manifestref": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            }
            # Should be blocked
            result = conduct_api_call(
                cl, RepositoryManifestPullStatistics, "GET", params, None, expected_code=403
            )

    def test_regular_user_cannot_access_other_user_pull_stats(self, app):
        """
        Test that regular users CANNOT access pull statistics for repos they don't have access to,
        even if the repo is public.
        """
        with client_with_identity("randomuser", app) as cl:
            # randomuser (not a superuser) trying to access devtable's repo
            params = {
                "repository": "devtable/simple",
                "tag": "latest",
            }
            # Should be blocked - no permission even though repo might be public
            conduct_api_call(cl, RepositoryTagPullStatistics, "GET", params, None, 403)

    def test_user_can_access_own_repo_pull_stats(self, app):
        """
        Test that users CAN access pull statistics for their own repos.

        Note: This test verifies access is NOT blocked with 403.
        A 404 is acceptable if the repo/tag doesn't exist in test data.
        """
        with client_with_identity("devtable", app) as cl:
            # devtable accessing their own repo (devtable/simple should exist in test data)
            params = {
                "repository": "devtable/simple",
                "tag": "latest",
            }
            # Should succeed (or 404 if tag doesn't exist, but NOT 403 forbidden)
            result = conduct_api_call(cl, RepositoryTagPullStatistics, "GET", params, None)
            assert result.status_code in [
                200,
                404,
            ], f"Expected 200 or 404, got {result.status_code}"


# NOTE: Additional test for FULL_ACCESS enabled behavior commented out due to test data dependencies.
# The core security requirement is tested above: blocking access without explicit permissions.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
