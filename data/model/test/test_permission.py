"""Tests for permission module optimizations."""

import pytest
from playhouse.test_utils import assert_query_count

from data.model.organization import create_organization
from data.model.permission import (
    _get_user_repo_permissions,
    get_org_wide_permissions,
    get_user_teams_in_org,
    is_org_admin,
)
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


def test_batch_team_permission_functions(initialized_db):
    """Test get_user_teams_in_org and is_org_admin for batch permission checks."""
    admin_user = get_user("devtable")
    test_user = create_user_noverify("batchuser", "batchuser@example.com")

    # Create org with admin and member teams
    org = create_organization("batchorg", "batchorg@example.com", admin_user)
    member_team = create_team("members", org, "member")
    add_user_to_team(test_user, member_team)

    # Test get_user_teams_in_org returns correct teams
    user_teams = get_user_teams_in_org(test_user, "batchorg")
    assert "members" in user_teams
    assert "owners" not in user_teams  # Only admin_user is in owners

    # Test is_org_admin
    assert is_org_admin(admin_user, "batchorg") is True
    assert is_org_admin(test_user, "batchorg") is False


def test_batch_team_lookup_uses_single_query(initialized_db):
    """
    Verify batch team lookup uses O(1) queries instead of O(N).

    Before optimization: Calling ViewTeamPermission().can() for each team
    triggers multiple queries per team (permission loading, team lookup, etc.)

    After optimization: get_user_teams_in_org() returns all teams in 1 query,
    regardless of how many teams exist in the organization.
    """
    admin_user = get_user("devtable")
    test_user = create_user_noverify("querycountuser", "querycountuser@example.com")

    # Create org with 10 teams
    org = create_organization("querycountorg", "querycountorg@example.com", admin_user)
    for i in range(10):
        team = create_team(f"team{i}", org, "member")
        if i < 5:  # Add user to first 5 teams
            add_user_to_team(test_user, team)

    # Single query to get all user's teams (O(1) instead of O(N))
    with assert_query_count(1):
        user_teams = get_user_teams_in_org(test_user, "querycountorg")

    assert len(user_teams) == 5

    # is_org_admin also uses single query
    with assert_query_count(1):
        is_admin = is_org_admin(test_user, "querycountorg")

    assert is_admin is False
