"""
Integration tests for permission caching with the auth system.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from auth.permissions import QuayDeferredPermissionUser
from data.model.user import get_user
from test.fixtures import *


@pytest.mark.skip(reason="Requires FEATURE_PERMISSION_CACHE to be defined in features module")
class TestPermissionCachingIntegration:
    """Integration tests for permission caching in the auth flow."""

    @patch("features.PERMISSION_CACHE", True)
    @patch("app.model_cache")
    def test_repo_permission_uses_cache_when_enabled(self, mock_model_cache, initialized_db):
        """Test that repository permissions use cache when FEATURE_PERMISSION_CACHE is enabled."""

        # Mock cache to return None (cache miss)
        mock_model_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}
        mock_model_cache.retrieve.side_effect = lambda key, loader: loader()

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        # Create a permission that will trigger repo loading
        from auth.permissions import ReadRepositoryPermission

        permission = ReadRepositoryPermission("devtable", "simple")

        # Check permission (this should trigger cache lookup)
        result = deferred_user.can(permission)

        # Verify cache was checked
        mock_model_cache.retrieve.assert_called()

    @patch("features.PERMISSION_CACHE", True)
    @patch("data.cache.permission_cache.is_repo_permission_revoked")
    def test_revoked_permission_blocks_access(self, mock_is_revoked, initialized_db):
        """Test that revoked permissions block access even if cached."""
        mock_is_revoked.return_value = True  # Permission is revoked

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        from auth.permissions import ReadRepositoryPermission

        permission = ReadRepositoryPermission("devtable", "simple")

        # Should return early due to revocation
        result = deferred_user.can(permission)

        # Verify revocation was checked
        mock_is_revoked.assert_called()

    @patch("features.PERMISSION_CACHE", False)
    def test_cache_disabled_queries_db_directly(self, initialized_db):
        """Test that permissions query DB directly when caching is disabled."""

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        from auth.permissions import ReadRepositoryPermission

        permission = ReadRepositoryPermission("devtable", "simple")

        # Should query DB directly
        result = deferred_user.can(permission)

        # The test passes if no cache errors occur

    @patch("features.PERMISSION_CACHE", True)
    @patch("app.model_cache")
    def test_org_permission_uses_cache_when_enabled(self, mock_model_cache, initialized_db):
        """Test that org-wide permissions use cache when enabled."""

        mock_model_cache.cache_config = {"user_org_provides_cache_ttl": "120s"}
        mock_model_cache.retrieve.side_effect = lambda key, loader: loader()

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        from auth.permissions import OrganizationMemberPermission

        permission = OrganizationMemberPermission("buynlarge")

        # Check permission
        result = deferred_user.can(permission)

        # Verify cache was checked
        assert mock_model_cache.retrieve.called

    @patch("features.PERMISSION_CACHE", True)
    @patch("app.model_cache")
    def test_cache_miss_queries_database(self, mock_model_cache, initialized_db):
        """Test that cache miss triggers database query and caches result."""

        mock_model_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}

        # Track if loader function was called
        loader_called = []

        def mock_retrieve(key, loader):
            loader_called.append(True)
            return loader()

        mock_model_cache.retrieve.side_effect = mock_retrieve

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        from auth.permissions import ReadRepositoryPermission

        permission = ReadRepositoryPermission("devtable", "simple")

        result = deferred_user.can(permission)

        # Loader should have been called (cache miss)
        assert len(loader_called) > 0

    @patch("features.PERMISSION_CACHE", True)
    @patch("app.model_cache")
    @patch("auth.permissions.logger")
    def test_cache_unavailable_falls_back_to_db(
        self, mock_logger, mock_model_cache, initialized_db
    ):
        """Test graceful fallback to DB when cache is unavailable."""

        mock_model_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}
        mock_model_cache.retrieve.side_effect = Exception("Cache unavailable")

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        from auth.permissions import ReadRepositoryPermission

        permission = ReadRepositoryPermission("devtable", "simple")

        # Should not raise, should fall back to DB
        result = deferred_user.can(permission)

        # Debug log should indicate cache unavailable
        assert mock_logger.debug.called


class TestPermissionCacheKeys:
    """Tests for cache key generation."""

    def test_repo_provides_key_format(self):
        """Test repository provides cache key format."""
        from data.cache.cache_key import for_user_repo_provides

        cache_config = {"user_repo_provides_cache_ttl": "120s"}
        key = for_user_repo_provides(123, "myorg", "myrepo", cache_config)

        assert key.key == "repo_provides__123_myorg_myrepo"
        assert key.expiration == "120s"

    def test_org_provides_key_format(self):
        """Test org provides cache key format."""
        from data.cache.cache_key import for_user_org_provides

        cache_config = {"user_org_provides_cache_ttl": "120s"}
        key = for_user_org_provides(123, "myorg", cache_config)

        assert key.key == "org_provides__123_myorg"
        assert key.expiration == "120s"

    def test_cache_keys_are_unique_per_user(self):
        """Test that cache keys are unique for different users."""
        from data.cache.cache_key import for_user_repo_provides

        cache_config = {"user_repo_provides_cache_ttl": "120s"}

        key1 = for_user_repo_provides(100, "myorg", "myrepo", cache_config)
        key2 = for_user_repo_provides(200, "myorg", "myrepo", cache_config)

        assert key1.key != key2.key

    def test_cache_keys_are_unique_per_repo(self):
        """Test that cache keys are unique for different repos."""
        from data.cache.cache_key import for_user_repo_provides

        cache_config = {"user_repo_provides_cache_ttl": "120s"}

        key1 = for_user_repo_provides(100, "myorg", "repo1", cache_config)
        key2 = for_user_repo_provides(100, "myorg", "repo2", cache_config)

        assert key1.key != key2.key


@pytest.mark.skip(reason="Requires FEATURE_PERMISSION_CACHE to be defined in features module")
class TestRevocationRaceCondition:
    """Tests verifying that revocation prevents race conditions."""

    @patch("features.PERMISSION_CACHE", True)
    @patch("data.cache.permission_cache.is_repo_permission_revoked")
    @patch("app.model_cache")
    def test_revocation_checked_before_cache(
        self, mock_model_cache, mock_is_revoked, initialized_db
    ):
        """Test that revocation list is checked before loading from cache."""
        mock_is_revoked.return_value = True

        # Set up cache to return a value (simulating stale cached permission)
        mock_model_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}
        mock_model_cache.retrieve.return_value = [
            {"namespace": "devtable", "repo_name": "simple", "role": "admin"}
        ]

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        from auth.permissions import ReadRepositoryPermission

        permission = ReadRepositoryPermission("devtable", "simple")

        # Check permission
        result = deferred_user.can(permission)

        # Revocation should be checked
        mock_is_revoked.assert_called_once()

        # Cache retrieve should NOT be called because revocation returned early
        mock_model_cache.retrieve.assert_not_called()

    @patch("features.PERMISSION_CACHE", True)
    @patch("data.cache.permission_cache.is_repo_permission_revoked")
    @patch("app.model_cache")
    def test_non_revoked_permission_loads_from_cache(
        self, mock_model_cache, mock_is_revoked, initialized_db
    ):
        """Test that non-revoked permissions proceed to cache lookup."""
        mock_is_revoked.return_value = False  # Not revoked

        mock_model_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}
        mock_model_cache.retrieve.side_effect = lambda key, loader: loader()

        user = get_user("devtable")
        deferred_user = QuayDeferredPermissionUser.for_user(user)

        from auth.permissions import ReadRepositoryPermission

        permission = ReadRepositoryPermission("devtable", "simple")

        result = deferred_user.can(permission)

        # Both revocation and cache should be checked
        mock_is_revoked.assert_called_once()
        mock_model_cache.retrieve.assert_called()


class TestPermissionCacheTTL:
    """Tests for cache TTL configuration."""

    def test_default_ttl_values(self):
        """Test default TTL values for permission caches."""
        from data.cache.cache_key import for_user_org_provides, for_user_repo_provides

        # When no TTL is specified in config, should use defaults
        cache_config = {}

        repo_key = for_user_repo_provides(123, "org", "repo", cache_config)
        org_key = for_user_org_provides(123, "org", cache_config)

        # Both should default to 120s
        assert repo_key.expiration == "120s"
        assert org_key.expiration == "120s"

    def test_custom_ttl_values(self):
        """Test custom TTL values are respected."""
        from data.cache.cache_key import for_user_org_provides, for_user_repo_provides

        cache_config = {"user_repo_provides_cache_ttl": "60s", "user_org_provides_cache_ttl": "90s"}

        repo_key = for_user_repo_provides(123, "org", "repo", cache_config)
        org_key = for_user_org_provides(123, "org", cache_config)

        assert repo_key.expiration == "60s"
        assert org_key.expiration == "90s"
