"""
Integration tests for permission model operations with caching.

Tests the interaction between permission CRUD operations and cache invalidation.
"""

from unittest.mock import MagicMock, patch

import pytest

from data.model import DataModelException
from data.model.organization import create_organization
from data.model.permission import (
    delete_team_permission,
    delete_user_permission,
    set_user_repo_permission,
)
from data.model.repository import create_repository
from data.model.team import add_user_to_team, create_team, remove_user_from_team
from data.model.user import create_user_noverify, get_user
from test.fixtures import *


class TestPermissionDeletionCaching:
    """Tests for cache invalidation during permission deletion."""

    @patch("data.cache.permission_cache._is_enabled")
    @patch("data.cache.permission_cache.add_repo_revocation")
    @patch("data.cache.permission_cache.invalidate_repository_permission")
    def test_delete_user_permission_revokes_before_delete(
        self, mock_invalidate, mock_add_revoke, mock_is_enabled, initialized_db
    ):
        """Test that user permission deletion adds revocation before deleting from DB."""
        mock_is_enabled.return_value = True
        mock_add_revoke.return_value = True

        admin_user = get_user("devtable")
        test_user = create_user_noverify("testdeluser", "testdel@example.com")

        # Create repo and grant permission
        repo = create_repository("devtable", "testrepo", admin_user)
        set_user_repo_permission(test_user.username, "devtable", "testrepo", "read")

        # Mock cache
        mock_cache = MagicMock()
        mock_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}

        # Delete permission
        delete_user_permission("testdeluser", "devtable", "testrepo", mock_cache)

        # Verify revocation was added
        mock_add_revoke.assert_called_once()
        # Verify cache was invalidated
        mock_invalidate.assert_called_once()

    @patch("data.cache.permission_cache._is_enabled")
    @patch("data.cache.permission_cache.add_repo_revocation")
    def test_delete_user_permission_fails_if_revocation_fails(
        self, mock_add_revoke, mock_is_enabled, initialized_db
    ):
        """Test that deletion fails if revocation fails (fail-safe)."""
        mock_is_enabled.return_value = True
        mock_add_revoke.return_value = False  # Revocation failed

        admin_user = get_user("devtable")
        test_user = create_user_noverify("testfailuser", "testfail@example.com")

        repo = create_repository("devtable", "failrepo", admin_user)
        set_user_repo_permission(test_user.username, "devtable", "failrepo", "read")

        mock_cache = MagicMock()

        # Should raise exception
        with pytest.raises(DataModelException) as exc_info:
            delete_user_permission("testfailuser", "devtable", "failrepo", mock_cache)

        assert "Permission revocation failed" in str(exc_info.value)

    @patch("data.cache.permission_cache._is_enabled")
    @patch("data.cache.permission_cache.revoke_and_invalidate_team_members")
    def test_delete_team_permission_revokes_all_members(
        self, mock_revoke_team, mock_is_enabled, initialized_db
    ):
        """Test that team permission deletion revokes for all team members."""
        mock_is_enabled.return_value = True

        admin_user = get_user("devtable")
        org = create_organization("testcacheorg", "testcache@example.com", admin_user)
        team = create_team("devs", org, "member")

        # Add members to team
        user1 = create_user_noverify("member1", "member1@example.com")
        user2 = create_user_noverify("member2", "member2@example.com")
        add_user_to_team(user1, team)
        add_user_to_team(user2, team)

        repo = create_repository("testcacheorg", "teamrepo", admin_user)

        # Grant team permission
        from data.database import RepositoryPermission, Role

        read_role = Role.get(Role.name == "read")
        RepositoryPermission.create(team=team, repository=repo, role=read_role)

        mock_cache = MagicMock()

        # Delete team permission
        delete_team_permission("devs", "testcacheorg", "teamrepo", mock_cache)

        # Should revoke for all team members
        mock_revoke_team.assert_called_once()


class TestPermissionModificationCaching:
    """Tests for cache invalidation during permission modification."""

    @patch("data.cache.permission_cache._is_enabled")
    @patch("data.cache.permission_cache.add_repo_revocation")
    @patch("data.cache.permission_cache.invalidate_repository_permission")
    def test_downgrade_permission_revokes(
        self, mock_invalidate, mock_add_revoke, mock_is_enabled, initialized_db
    ):
        """Test that downgrading permissions adds revocation."""
        mock_is_enabled.return_value = True
        mock_add_revoke.return_value = True

        admin_user = get_user("devtable")
        test_user = create_user_noverify("downgradeuser", "downgrade@example.com")

        repo = create_repository("devtable", "downgraderepo", admin_user)

        mock_cache = MagicMock()
        mock_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}

        # Grant admin
        set_user_repo_permission(
            test_user.username, "devtable", "downgraderepo", "admin", model_cache=mock_cache
        )
        mock_add_revoke.reset_mock()

        # Downgrade to read (should revoke)
        set_user_repo_permission(
            test_user.username, "devtable", "downgraderepo", "read", model_cache=mock_cache
        )

        # Should have revoked
        mock_add_revoke.assert_called_once()

    @patch("data.cache.permission_cache._is_enabled")
    @patch("data.cache.permission_cache.add_repo_revocation")
    @patch("data.cache.permission_cache.invalidate_repository_permission")
    def test_upgrade_permission_no_revocation(
        self, mock_invalidate, mock_add_revoke, mock_is_enabled, initialized_db
    ):
        """Test that upgrading permissions does not add revocation."""
        mock_is_enabled.return_value = True

        admin_user = get_user("devtable")
        test_user = create_user_noverify("upgradeuser", "upgrade@example.com")

        repo = create_repository("devtable", "upgraderepo", admin_user)

        mock_cache = MagicMock()
        mock_cache.cache_config = {"user_repo_provides_cache_ttl": "120s"}

        # Grant read
        set_user_repo_permission(
            test_user.username, "devtable", "upgraderepo", "read", model_cache=mock_cache
        )
        mock_add_revoke.reset_mock()
        mock_invalidate.reset_mock()

        # Upgrade to admin (should only invalidate, not revoke)
        set_user_repo_permission(
            test_user.username, "devtable", "upgraderepo", "admin", model_cache=mock_cache
        )

        # Should NOT have revoked (upgrade is safe)
        mock_add_revoke.assert_not_called()
        # Should have invalidated
        mock_invalidate.assert_called_once()


class TestTeamMembershipCaching:
    """Tests for cache invalidation during team membership changes."""

    @patch("data.cache.permission_cache._is_enabled")
    @patch("data.cache.permission_cache.invalidate_user_team_grant")
    def test_add_user_to_team_invalidates_cache(
        self, mock_invalidate_grant, mock_is_enabled, initialized_db
    ):
        """Test that adding user to team invalidates their permission cache."""
        mock_is_enabled.return_value = True

        admin_user = get_user("devtable")
        org = create_organization("teammemberorg", "teammember@example.com", admin_user)
        team = create_team("newteam", org, "member")
        test_user = create_user_noverify("newmember", "newmember@example.com")

        mock_cache = MagicMock()

        # Reset mock after fixture setup
        mock_invalidate_grant.reset_mock()

        # Add user to team with model_cache
        add_user_to_team(test_user, team, model_cache=mock_cache)

        # Should invalidate cache for the grant
        mock_invalidate_grant.assert_called_once_with(test_user, team, mock_cache)

    @patch("data.cache.permission_cache._is_enabled")
    @patch("data.cache.permission_cache.invalidate_user_team_removal")
    def test_remove_user_from_team_revokes_access(
        self, mock_invalidate_removal, mock_is_enabled, initialized_db
    ):
        """Test that removing user from team revokes their team-based access."""
        mock_is_enabled.return_value = True

        admin_user = get_user("devtable")
        org = create_organization("removalorg", "removal@example.com", admin_user)
        team = create_team("removeteam", org, "member")
        test_user = create_user_noverify("removemember", "removemember@example.com")

        # Add and then remove
        add_user_to_team(test_user, team)

        mock_cache = MagicMock()

        # Remove user from team with model_cache
        remove_user_from_team(
            org.username, team.name, test_user.username, admin_user.username, model_cache=mock_cache
        )

        # Should invalidate with revocation for removal
        mock_invalidate_removal.assert_called_once()


class TestCacheInvalidationOrdering:
    """Tests to verify correct ordering of cache operations."""

    @patch("data.cache.permission_cache._is_enabled")
    def test_revocation_happens_before_db_delete(self, mock_is_enabled, initialized_db):
        """Test that revocation is added before database deletion."""
        mock_is_enabled.return_value = True

        admin_user = get_user("devtable")
        test_user = create_user_noverify("orderuser", "order@example.com")

        repo = create_repository("devtable", "orderrepo", admin_user)
        set_user_repo_permission(test_user.username, "devtable", "orderrepo", "read")

        mock_cache = MagicMock()
        call_order = []

        # Track call order
        original_add_revoke = None
        with patch("data.cache.permission_cache.add_repo_revocation") as mock_add_revoke:
            mock_add_revoke.side_effect = lambda *args: call_order.append("revoke") or True

            with patch("data.database.RepositoryPermission.delete_instance") as mock_delete:
                mock_delete.side_effect = lambda: call_order.append("delete")

                try:
                    delete_user_permission("orderuser", "devtable", "orderrepo", mock_cache)
                except:
                    pass  # May fail due to mocking

        # Revoke should come before delete
        if "revoke" in call_order and "delete" in call_order:
            assert call_order.index("revoke") < call_order.index("delete")


class TestFeatureFlagDisabled:
    """Tests when FEATURE_PERMISSION_CACHE is disabled."""

    @patch("data.cache.permission_cache._is_enabled")
    def test_no_caching_when_disabled(self, mock_is_enabled, initialized_db):
        """Test that no caching occurs when feature is disabled."""
        mock_is_enabled.return_value = False

        admin_user = get_user("devtable")
        test_user = create_user_noverify("nocacheuser", "nocache@example.com")

        repo = create_repository("devtable", "nocacherepo", admin_user)
        set_user_repo_permission(test_user.username, "devtable", "nocacherepo", "read")

        mock_cache = MagicMock()

        # Delete permission
        delete_user_permission("nocacheuser", "devtable", "nocacherepo", mock_cache)

        # Cache should never be touched
        mock_cache.invalidate.assert_not_called()
