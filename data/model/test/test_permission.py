"""Tests for permission module optimizations."""

import pytest

from data.model.organization import create_organization
from data.model.permission import _get_user_repo_permissions, get_org_wide_permissions
from data.model.repository import create_repository
from data.model.team import add_user_to_team, create_team
from data.model.user import create_user_noverify, get_user
from test.fixtures import *


class TestGetOrgWidePermissions:
    """Tests for get_org_wide_permissions with org_filter."""

    def test_org_filter_is_applied(self, initialized_db):
        """Test that org_filter actually filters results to the specified org."""
        user = get_user("devtable")

        # Get all permissions without filter
        all_perms = list(get_org_wide_permissions(user))
        all_org_names = {p.organization.username for p in all_perms}

        # Get permissions filtered to buynlarge only
        filtered_perms = list(get_org_wide_permissions(user, org_filter="buynlarge"))
        filtered_org_names = {p.organization.username for p in filtered_perms}

        # With filter, should only return buynlarge if user is a member there
        # The key assertion is that the filter works (all results are from the filtered org)
        for perm in filtered_perms:
            assert perm.organization.username == "buynlarge"

    def test_org_filter_returns_empty_for_non_member(self, initialized_db):
        """Test that org_filter returns empty for orgs user is not a member of."""
        # Create a user not in any org
        user = create_user_noverify("testpermuser", "testperm@example.com")

        # Should return empty for any org
        perms = list(get_org_wide_permissions(user, org_filter="buynlarge"))
        assert len(perms) == 0

    def test_org_filter_reduces_results(self, initialized_db):
        """
        Verify that org_filter parameter actually filters at the database level.

        This test demonstrates the bug fix: before, the filter was discarded
        because the .where() result wasn't assigned back.
        """
        admin_user = get_user("devtable")

        # Create multiple orgs with devtable as admin
        org1 = create_organization("filterorg1", "filter1@example.com", admin_user)
        org2 = create_organization("filterorg2", "filter2@example.com", admin_user)

        # Get permissions for all orgs
        all_perms = list(get_org_wide_permissions(admin_user))
        all_org_names = {p.organization.username for p in all_perms}

        # Get filtered to just filterorg1
        filtered_perms = list(get_org_wide_permissions(admin_user, org_filter="filterorg1"))
        filtered_org_names = {p.organization.username for p in filtered_perms}

        # All perms should have multiple orgs
        assert len(all_org_names) > 1

        # Filtered should only have filterorg1
        assert filtered_org_names == {"filterorg1"}


def test_get_user_repo_permissions_returns_direct_and_team(initialized_db):
    """Test that UNION query returns both direct and team-based permissions."""
    admin_user = get_user("devtable")
    test_user = create_user_noverify("unionuser", "unionuser@example.com")

    # Create org and team
    org = create_organization("unionorg", "unionorg@example.com", admin_user)
    team = create_team("devs", org, "member")
    add_user_to_team(test_user, team)

    from data.database import RepositoryPermission, Role

    # Create two repos - one with direct permission, one with team permission
    repo1 = create_repository("unionorg", "directrepo", admin_user)
    repo2 = create_repository("unionorg", "teamrepo", admin_user)

    read_role = Role.get(Role.name == "read")
    RepositoryPermission.create(user=test_user, repository=repo1, role=read_role)
    RepositoryPermission.create(team=team, repository=repo2, role=read_role)

    # Get all permissions - UNION should return both direct and team permissions
    perms = list(_get_user_repo_permissions(test_user))
    repo_names = {p.repository.name for p in perms}

    assert "directrepo" in repo_names
    assert "teamrepo" in repo_names
