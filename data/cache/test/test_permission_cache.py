"""
Tests for permission caching and revocation list functionality.
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from redis import RedisError

from data.cache.permission_cache import (
    add_repo_revocation,
    invalidate_org_permission,
    invalidate_repository_permission,
    is_repo_permission_revoked,
    revoke_and_invalidate_repo,
    revoke_and_invalidate_team_members,
    invalidate_user_team_grant,
    invalidate_user_team_removal,
    invalidate_bulk_team_member_removal,
    invalidate_org_member_removal,
)
from data.cache.revocation_list import PermissionRevocationList
from data.model import DataModelException


class TestPermissionRevocationList:
    """Tests for the PermissionRevocationList class."""

    def test_add_and_check_revocation(self):
        """Test adding a revocation and checking if it exists."""
        mock_redis = MagicMock()
        mock_redis.zscore.return_value = time.time()

        revocation_list = PermissionRevocationList(mock_redis)

        # Add a revocation
        revocation_list.add_repo_revocation(123, "myorg", "myrepo")

        # Verify Redis zadd was called
        assert mock_redis.zadd.called
        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == "permission_revocations"
        assert "repo:123:myorg:myrepo" in call_args[0][1]

    def test_is_revoked_returns_true_for_recent_revocation(self):
        """Test that is_revoked returns True for recently added revocations."""
        mock_redis = MagicMock()
        current_time = time.time()
        mock_redis.zscore.return_value = current_time - 60  # 1 minute ago

        revocation_list = PermissionRevocationList(mock_redis)

        # Check if revoked
        is_revoked = revocation_list.is_repo_revoked(123, "myorg", "myrepo")

        assert is_revoked is True
        mock_redis.zscore.assert_called_once_with(
            "permission_revocations", "repo:123:myorg:myrepo"
        )

    def test_is_revoked_returns_false_for_expired_revocation(self):
        """Test that is_revoked returns False for expired revocations."""
        mock_redis = MagicMock()
        current_time = time.time()
        # Set timestamp to 6 minutes ago (beyond 5 minute retention)
        mock_redis.zscore.return_value = current_time - 360

        revocation_list = PermissionRevocationList(mock_redis, retention_seconds=300)

        # Check if revoked
        is_revoked = revocation_list.is_repo_revoked(123, "myorg", "myrepo")

        assert is_revoked is False

    def test_is_revoked_returns_false_when_not_found(self):
        """Test that is_revoked returns False when entry doesn't exist."""
        mock_redis = MagicMock()
        mock_redis.zscore.return_value = None  # Entry not found

        revocation_list = PermissionRevocationList(mock_redis)

        is_revoked = revocation_list.is_repo_revoked(123, "myorg", "myrepo")

        assert is_revoked is False

    def test_is_revoked_fails_open_on_redis_error(self):
        """Test that is_revoked returns False (fail-open) on Redis errors."""
        mock_redis = MagicMock()
        mock_redis.zscore.side_effect = RedisError("Connection failed")

        revocation_list = PermissionRevocationList(mock_redis)

        is_revoked = revocation_list.is_repo_revoked(123, "myorg", "myrepo")

        # Should fail open for reads
        assert is_revoked is False

    def test_add_revocation_raises_on_redis_error(self):
        """Test that add_revocation raises exception on Redis errors (fail-closed for writes)."""
        mock_redis = MagicMock()
        mock_redis.zadd.side_effect = RedisError("Connection failed")

        revocation_list = PermissionRevocationList(mock_redis)

        with pytest.raises(RedisError):
            revocation_list.add_repo_revocation(123, "myorg", "myrepo")

    def test_cleanup_removes_old_entries(self):
        """Test that old entries are removed during add operation."""
        mock_redis = MagicMock()

        revocation_list = PermissionRevocationList(mock_redis, retention_seconds=300)
        revocation_list.add_repo_revocation(123, "myorg", "myrepo")

        # Verify cleanup was called
        assert mock_redis.zremrangebyscore.called
        call_args = mock_redis.zremrangebyscore.call_args[0]
        assert call_args[0] == "permission_revocations"
        assert call_args[1] == "-inf"
        # Cutoff should be approximately current_time - 300

    def test_no_redis_client(self):
        """Test graceful handling when Redis client is None."""
        revocation_list = PermissionRevocationList(None)

        # Should not raise errors
        revocation_list.add_repo_revocation(123, "myorg", "myrepo")
        is_revoked = revocation_list.is_repo_revoked(123, "myorg", "myrepo")

        assert is_revoked is False


class TestPermissionCacheInvalidation:
    """Tests for cache invalidation functions."""

    def test_invalidate_repository_permission(self):
        """Test invalidating repository permission cache."""
        mock_cache = MagicMock()
        mock_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}

        invalidate_repository_permission(
            user_id=123,
            repo_id=456,
            model_cache=mock_cache,
            namespace_name="myorg",
            repo_name="myrepo"
        )

        # Should invalidate both repo and org keys
        assert mock_cache.invalidate.call_count == 2

    def test_invalidate_repository_permission_no_cache(self):
        """Test that invalidation works when cache is None."""
        result = invalidate_repository_permission(
            user_id=123,
            repo_id=456,
            model_cache=None
        )

        assert result is True

    def test_invalidate_org_permission(self):
        """Test invalidating org-wide permission cache."""
        mock_cache = MagicMock()
        mock_cache.cache_config = {"user_org_provides_cache_ttl": "120s"}

        invalidate_org_permission(user_id=123, namespace_name="myorg", model_cache=mock_cache)

        mock_cache.invalidate.assert_called_once()

    def test_invalidate_handles_exceptions(self):
        """Test that invalidation handles exceptions gracefully."""
        mock_cache = MagicMock()
        mock_cache.invalidate.side_effect = Exception("Cache error")

        # Should not raise, just log warning
        result = invalidate_org_permission(
            user_id=123, namespace_name="myorg", model_cache=mock_cache
        )

        assert result is False


class TestRevocationHelpers:
    """Tests for revocation helper functions."""

    @patch('data.cache.permission_cache._get_revocation_list')
    def test_is_repo_permission_revoked(self, mock_get_rl):
        """Test checking if a repo permission is revoked."""
        mock_rl = MagicMock()
        mock_rl.is_repo_revoked.return_value = True
        mock_get_rl.return_value = mock_rl

        result = is_repo_permission_revoked(123, "myorg", "myrepo")

        assert result is True
        mock_rl.is_repo_revoked.assert_called_once_with(123, "myorg", "myrepo")

    @patch('data.cache.permission_cache._get_revocation_list')
    def test_is_repo_permission_revoked_no_rl(self, mock_get_rl):
        """Test graceful handling when revocation list is unavailable."""
        mock_get_rl.return_value = None

        result = is_repo_permission_revoked(123, "myorg", "myrepo")

        assert result is False

    @patch('data.cache.permission_cache._get_revocation_list')
    def test_add_repo_revocation(self, mock_get_rl):
        """Test adding a repo revocation."""
        mock_rl = MagicMock()
        mock_get_rl.return_value = mock_rl

        result = add_repo_revocation(123, "myorg", "myrepo")

        assert result is True
        mock_rl.add_repo_revocation.assert_called_once_with(123, "myorg", "myrepo")

    @patch('data.cache.permission_cache._get_revocation_list')
    def test_add_repo_revocation_handles_errors(self, mock_get_rl):
        """Test that add_repo_revocation handles errors gracefully."""
        mock_rl = MagicMock()
        mock_rl.add_repo_revocation.side_effect = Exception("Redis error")
        mock_get_rl.return_value = mock_rl

        result = add_repo_revocation(123, "myorg", "myrepo")

        assert result is False


class TestCompositeOperations:
    """Tests for composite revocation + invalidation operations."""

    @patch('data.cache.permission_cache._is_enabled')
    @patch('data.cache.permission_cache.add_repo_revocation')
    @patch('data.cache.permission_cache.invalidate_repository_permission')
    def test_revoke_and_invalidate_repo_success(
        self, mock_invalidate, mock_add_revoke, mock_is_enabled
    ):
        """Test successful revoke and invalidate operation."""
        mock_is_enabled.return_value = True
        mock_add_revoke.return_value = True
        mock_cache = MagicMock()

        revoke_and_invalidate_repo(
            user_id=123,
            repo_id=456,
            namespace_name="myorg",
            repo_name="myrepo",
            model_cache=mock_cache
        )

        mock_add_revoke.assert_called_once_with(123, "myorg", "myrepo")
        mock_invalidate.assert_called_once()

    @patch('data.cache.permission_cache._is_enabled')
    @patch('data.cache.permission_cache.add_repo_revocation')
    def test_revoke_and_invalidate_repo_fails_on_revocation_error(
        self, mock_add_revoke, mock_is_enabled
    ):
        """Test that operation fails if revocation fails."""
        mock_is_enabled.return_value = True
        mock_add_revoke.return_value = False  # Revocation failed
        mock_cache = MagicMock()

        with pytest.raises(DataModelException) as exc_info:
            revoke_and_invalidate_repo(
                user_id=123,
                repo_id=456,
                namespace_name="myorg",
                repo_name="myrepo",
                model_cache=mock_cache
            )

        assert "Permission revocation failed" in str(exc_info.value)

    @patch('data.cache.permission_cache._is_enabled')
    def test_revoke_and_invalidate_repo_disabled(self, mock_is_enabled):
        """Test that operation is skipped when feature is disabled."""
        mock_is_enabled.return_value = False
        mock_cache = MagicMock()

        # Should not raise, just return early
        revoke_and_invalidate_repo(
            user_id=123,
            repo_id=456,
            namespace_name="myorg",
            repo_name="myrepo",
            model_cache=mock_cache
        )

        # Cache should not be touched
        mock_cache.invalidate.assert_not_called()

    @patch('data.cache.permission_cache._is_enabled')
    @patch('data.model.organization.get_organization_team_members')
    @patch('data.cache.permission_cache.revoke_and_invalidate_repo')
    def test_revoke_and_invalidate_team_members(
        self, mock_revoke_repo, mock_get_members, mock_is_enabled
    ):
        """Test revoking permissions for all team members."""
        mock_is_enabled.return_value = True

        # Mock team members
        mock_member1 = MagicMock()
        mock_member1.id = 100
        mock_member2 = MagicMock()
        mock_member2.id = 200
        mock_get_members.return_value = [mock_member1, mock_member2]

        mock_cache = MagicMock()

        revoke_and_invalidate_team_members(
            team_id=10,
            repo_id=456,
            namespace_name="myorg",
            repo_name="myrepo",
            model_cache=mock_cache
        )

        # Should revoke for each member
        assert mock_revoke_repo.call_count == 2


class TestBulkOperations:
    """Tests for bulk invalidation operations."""

    @patch('data.cache.permission_cache._is_enabled')
    @patch('data.model.organization.get_organization_team_members')
    @patch('data.cache.permission_cache.invalidate_org_permission')
    @patch('data.model.permission.list_team_permissions')
    @patch('data.cache.permission_cache.invalidate_repository_permission')
    def test_invalidate_user_team_grant(
        self, mock_invalidate_repo, mock_list_perms, mock_invalidate_org,
        mock_get_members, mock_is_enabled
    ):
        """Test invalidating cache when user is granted team membership."""
        mock_is_enabled.return_value = True

        # Mock user and team
        mock_user = MagicMock()
        mock_user.id = 123

        mock_team = MagicMock()
        mock_team.organization.username = "myorg"

        # Mock team permissions
        mock_perm = MagicMock()
        mock_perm.repository.id = 456
        mock_perm.repository.name = "myrepo"
        mock_list_perms.return_value = [mock_perm]

        mock_cache = MagicMock()

        invalidate_user_team_grant(mock_user, mock_team, mock_cache)

        # Should invalidate org permission
        mock_invalidate_org.assert_called_once_with(123, "myorg", mock_cache)
        # Should invalidate repo permission for each team repo
        mock_invalidate_repo.assert_called_once()

    @patch('data.cache.permission_cache._is_enabled')
    @patch('data.model.permission.list_team_permissions')
    @patch('data.cache.permission_cache.add_repo_revocation')
    @patch('data.cache.permission_cache.invalidate_repository_permission')
    @patch('data.cache.permission_cache.invalidate_org_permission')
    def test_invalidate_user_team_removal(
        self, mock_invalidate_org, mock_invalidate_repo, mock_add_revoke,
        mock_list_perms, mock_is_enabled
    ):
        """Test invalidating cache when user is removed from team."""
        mock_is_enabled.return_value = True

        # Mock user and team
        mock_user = MagicMock()
        mock_user.id = 123

        mock_team = MagicMock()

        # Mock team permission
        mock_perm = MagicMock()
        mock_perm.repository.id = 456
        mock_perm.repository.name = "myrepo"
        mock_list_perms.return_value = [mock_perm]

        mock_cache = MagicMock()

        with patch('data.database.RepositoryPermission') as mock_rp:
            mock_rp.select.return_value.where.return_value.exists.return_value = False

            invalidate_user_team_removal(mock_user, mock_team, "myorg", mock_cache)

        # Should add revocation if no direct permission
        mock_add_revoke.assert_called_once_with(123, "myorg", "myrepo")

    @patch('data.cache.permission_cache._is_enabled')
    @patch('data.database.User')
    @patch('data.model.permission.list_team_permissions')
    @patch('data.cache.permission_cache.add_repo_revocation')
    @patch('data.cache.permission_cache.invalidate_org_permission')
    def test_invalidate_bulk_team_member_removal(
        self, mock_invalidate_org, mock_add_revoke, mock_list_perms,
        mock_user_model, mock_is_enabled
    ):
        """Test bulk invalidation when multiple team members are removed."""
        mock_is_enabled.return_value = True

        mock_team = MagicMock()
        mock_team.organization.username = "myorg"

        # Mock team permission
        mock_perm = MagicMock()
        mock_perm.repository.id = 456
        mock_perm.repository.name = "myrepo"
        mock_list_perms.return_value = [mock_perm]

        # Mock users
        mock_user1 = MagicMock()
        mock_user2 = MagicMock()
        mock_user_model.get_by_id.side_effect = [mock_user1, mock_user2]

        mock_cache = MagicMock()

        with patch('data.database.RepositoryPermission') as mock_rp:
            mock_rp.select.return_value.where.return_value.exists.return_value = False

            invalidate_bulk_team_member_removal(
                mock_team, [100, 200], mock_cache
            )

        # Should invalidate for each user
        assert mock_invalidate_org.call_count == 2


class TestFeatureFlagGating:
    """Tests for feature flag gating of caching operations."""

    @patch('data.cache.permission_cache._is_enabled')
    def test_operations_gated_when_disabled(self, mock_is_enabled):
        """Test that all operations are gated by FEATURE_PERMISSION_CACHE."""
        mock_is_enabled.return_value = False
        mock_cache = MagicMock()
        mock_user = MagicMock()
        mock_team = MagicMock()

        # All these should return early without doing anything
        revoke_and_invalidate_repo(123, 456, "org", "repo", mock_cache)
        revoke_and_invalidate_team_members(10, 456, "org", "repo", mock_cache)
        invalidate_user_team_grant(mock_user, mock_team, mock_cache)
        invalidate_user_team_removal(mock_user, mock_team, "org", mock_cache)
        invalidate_bulk_team_member_removal(mock_team, [100], mock_cache)

        # Cache should never be touched
        mock_cache.invalidate.assert_not_called()
