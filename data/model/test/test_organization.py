import pytest
from playhouse.test_utils import assert_query_count

from data.model.organization import (
    create_organization,
    find_organizations_by_email,
    get_organization,
    get_organization_member_set,
    get_organizations,
    is_org_admin,
)
from data.model.team import add_user_to_team, get_organization_team
from data.model.user import (
    create_robot,
    create_user,
    find_user_by_email,
    get_user,
    mark_namespace_for_deletion,
)
from data.queue import WorkQueue
from test.fixtures import *
from util.validation import validate_email


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


class TestCreateOrganizationEmail:
    """Tests for create_organization with email stored directly in User.email."""

    def test_create_org_with_email_stores_in_user_email(self, initialized_db):
        """Test that create_organization with email stores it in User.email."""
        admin = get_user("devtable")
        org = create_organization("emailorg1", "real@example.com", admin)
        assert org.email == "real@example.com"

    def test_create_org_without_email_generates_uuid(self, initialized_db):
        """Test that create_organization without email generates a non-email UUID in User.email."""
        admin = get_user("devtable")
        org = create_organization("uuidorg1", None, admin)
        assert not validate_email(org.email), f"Expected non-email UUID, got: {org.email}"

    def test_create_org_contact_email_takes_priority(self, initialized_db):
        """Test that contact_email parameter takes priority over email parameter."""
        admin = get_user("devtable")
        org = create_organization(
            "contactorg1", "fallback@example.com", admin, contact_email="contact@example.com"
        )
        assert org.email == "contact@example.com"

    def test_create_org_email_fallback(self, initialized_db):
        """Test that email parameter is used when contact_email is not provided."""
        admin = get_user("devtable")
        org = create_organization("emailfallbackorg", "fallback@example.com", admin)
        assert org.email == "fallback@example.com"

    def test_two_orgs_can_share_same_email(self, initialized_db):
        """Test that two organizations can have the same email address."""
        admin = get_user("devtable")
        shared = "shared@example.com"
        org1 = create_organization("sharedorg1", shared, admin)
        org2 = create_organization("sharedorg2", shared, admin)
        assert org1.email == shared
        assert org2.email == shared
        assert org1.id != org2.id

    def test_org_can_share_email_with_user(self, initialized_db):
        """Test that an org can be created with the same email as an existing user.

        Regression test: create_user_noverify INSERTs with organization=false,
        so the partial unique index fires during INSERT. The fix is to insert
        with a placeholder email, set organization=true, then apply the real email.
        """
        admin = get_user("devtable")
        user_email = admin.email  # devtable's email
        org = create_organization("overlaporg", user_email, admin)
        assert org.email == user_email
        assert org.organization is True
        # The original user still has their email
        admin_refreshed = get_user("devtable")
        assert admin_refreshed.email == user_email

    def test_find_organizations_by_email_single_match(self, initialized_db):
        """Test find_organizations_by_email returns a single matching org."""
        admin = get_user("devtable")
        org = create_organization("findorg1", "find@example.com", admin)
        results = list(find_organizations_by_email("find@example.com"))
        assert len(results) == 1
        assert results[0].id == org.id

    def test_find_organizations_by_email_multiple_matches(self, initialized_db):
        """Test find_organizations_by_email returns multiple matching orgs."""
        admin = get_user("devtable")
        shared = "shared-find@example.com"
        org1 = create_organization("findorg2a", shared, admin)
        org2 = create_organization("findorg2b", shared, admin)
        results = list(find_organizations_by_email(shared))
        assert len(results) == 2
        result_ids = {r.id for r in results}
        assert org1.id in result_ids
        assert org2.id in result_ids

    def test_find_organizations_by_email_no_match(self, initialized_db):
        """Test find_organizations_by_email returns empty when no match."""
        results = list(find_organizations_by_email("nonexistent@example.com"))
        assert len(results) == 0

    def test_recovery_lookup_shared_email_finds_user_and_orgs(self, initialized_db):
        """Integration test: when a user and orgs share an email, the recovery
        query functions return both independently — find_user_by_email returns
        only the user, find_organizations_by_email returns only the orgs.

        Regression test for the combined recovery email flow where a single
        email may now match a personal user AND multiple organizations.
        """
        admin = get_user("devtable")
        shared = admin.email  # e.g. devtable@devtable.com

        org1 = create_organization("recoveryorg1", shared, admin)
        org2 = create_organization("recoveryorg2", shared, admin)

        # find_user_by_email should return ONLY the non-org user
        found_user = find_user_by_email(shared)
        assert found_user is not None
        assert found_user.organization is False
        assert found_user.username == "devtable"

        # find_organizations_by_email should return ONLY the orgs
        found_orgs = list(find_organizations_by_email(shared))
        assert len(found_orgs) == 2
        org_names = {o.username for o in found_orgs}
        assert "recoveryorg1" in org_names
        assert "recoveryorg2" in org_names

        # Neither function returns the wrong type
        for org in found_orgs:
            assert org.organization is True
        assert found_user.id not in {o.id for o in found_orgs}
