import pytest
from playhouse.test_utils import assert_query_count

from data.model.organization import (
    create_organization,
    get_organization,
    get_organization_member_set,
    get_organizations,
    is_org_admin,
)
from data.model.team import add_user_to_team, get_organization_team
from data.model.user import (
    create_robot,
    create_user,
    get_user,
    mark_namespace_for_deletion,
)
from data.queue import WorkQueue
from test.fixtures import *


@pytest.mark.parametrize(
    "deleted",
    [
        (True),
        (False),
    ],
)
def test_get_organizations(deleted, initialized_db):
    # Delete an org.
    deleted_org = get_organization("sellnsmall")
    queue = WorkQueue("testgcnamespace", lambda db: db.transaction())
    mark_namespace_for_deletion(deleted_org, [], queue)

    orgs = get_organizations(deleted=deleted)
    assert orgs

    deleted_found = [org for org in orgs if org.id == deleted_org.id]
    assert bool(deleted_found) == deleted


def test_is_org_admin(initialized_db):
    user = get_user("devtable")
    org = get_organization("sellnsmall")
    assert is_org_admin(user, org) is True


class TestGetOrganizationMemberSet:
    """Tests for get_organization_member_set with user_ids_filter parameter."""

    def test_returns_all_members_without_filter(self, initialized_db):
        """Test that without a filter, all org members are returned."""
        org = get_organization("buynlarge")
        members = get_organization_member_set(org)

        # devtable created buynlarge, so should be a member
        assert "devtable" in members

    def test_user_ids_filter_returns_matching_members(self, initialized_db):
        """Test that user_ids_filter correctly filters to only matching members."""
        org = get_organization("buynlarge")
        user = get_user("devtable")

        # Filter to only devtable's ID
        members = get_organization_member_set(org, user_ids_filter={user.id})

        assert members == {"devtable"}

    def test_user_ids_filter_with_non_member_returns_empty(self, initialized_db):
        """Test that filtering by a non-member ID returns empty set."""
        org = get_organization("buynlarge")
        freshuser = get_user("freshuser")

        # freshuser is not a member of buynlarge
        members = get_organization_member_set(org, user_ids_filter={freshuser.id})

        assert members == set()

    def test_empty_user_ids_filter_returns_empty_set(self, initialized_db):
        """Test that an empty user_ids_filter returns empty set immediately."""
        org = get_organization("buynlarge")

        # Empty filter should short-circuit and return empty set
        members = get_organization_member_set(org, user_ids_filter=set())

        assert members == set()

    def test_user_ids_filter_with_multiple_ids(self, initialized_db):
        """Test filtering with multiple user IDs."""
        org = get_organization("buynlarge")
        devtable = get_user("devtable")
        freshuser = get_user("freshuser")

        # Add freshuser to buynlarge's owners team
        owners_team = get_organization_team("buynlarge", "owners")
        add_user_to_team(freshuser, owners_team)

        # Filter to both users
        members = get_organization_member_set(org, user_ids_filter={devtable.id, freshuser.id})

        assert "devtable" in members
        assert "freshuser" in members

    def test_include_robots_false_excludes_robots(self, initialized_db):
        """Test that include_robots=False excludes robot accounts."""
        org = get_organization("buynlarge")

        # Create a robot for the org and add to a team
        robot, _ = create_robot("testrob", org)
        owners_team = get_organization_team("buynlarge", "owners")
        add_user_to_team(robot, owners_team)

        # Without include_robots, robot should not be in the set
        members = get_organization_member_set(org, include_robots=False)
        assert robot.username not in members

        # With include_robots, robot should be in the set
        members_with_robots = get_organization_member_set(org, include_robots=True)
        assert robot.username in members_with_robots

    def test_user_ids_filter_with_robot_id_and_include_robots(self, initialized_db):
        """Test that user_ids_filter works correctly with robot IDs."""
        org = get_organization("buynlarge")

        # Create a robot and add to team
        robot, _ = create_robot("filterrob", org)
        owners_team = get_organization_team("buynlarge", "owners")
        add_user_to_team(robot, owners_team)

        # Filter to robot ID with include_robots=True
        members = get_organization_member_set(org, include_robots=True, user_ids_filter={robot.id})
        assert members == {robot.username}

        # Filter to robot ID with include_robots=False should return empty
        members_no_robots = get_organization_member_set(
            org, include_robots=False, user_ids_filter={robot.id}
        )
        assert members_no_robots == set()

    def test_user_ids_filter_executes_single_query(self, initialized_db):
        """
        Verify that user_ids_filter results in a single query regardless of filter size.

        This is the key optimization: by accepting user IDs directly instead of User
        objects, callers can use perm.user_id (already loaded) instead of perm.user
        (triggers lazy-load), eliminating N+1 queries.
        """
        admin_user = get_user("devtable")
        org = create_organization("querytestorg", "querytest@example.com", admin_user)
        owners_team = get_organization_team("querytestorg", "owners")

        # Create 50 users and add them to the org
        user_ids = {admin_user.id}
        for i in range(50):
            user = create_user(
                username=f"querytest_user_{i}",
                password="password",
                email=f"querytest_{i}@example.com",
                auto_verify=True,
            )
            add_user_to_team(user, owners_team)
            user_ids.add(user.id)

        # Key assertion: 51 user IDs in filter should still be 1 query
        with assert_query_count(1):
            members = get_organization_member_set(org, user_ids_filter=user_ids)

        assert len(members) == 51

    def test_no_filter_executes_single_query(self, initialized_db):
        """Verify get_organization_member_set without filter uses single query."""
        org = get_organization("buynlarge")

        with assert_query_count(1):
            members = get_organization_member_set(org)

        assert len(members) > 0
