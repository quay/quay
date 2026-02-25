import pytest
from peewee import IntegrityError
from playhouse.test_utils import assert_query_count

from data.database import OrganizationContactEmail
from data.model.organization import (
    create_organization,
    delete_contact_email,
    find_organizations_by_contact_email,
    get_contact_email,
    get_organization,
    get_organization_member_set,
    get_organizations,
    is_org_admin,
    set_contact_email,
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


class TestOrganizationContactEmail:
    """Tests for the OrganizationContactEmail model."""

    def test_create_with_email(self, initialized_db):
        """Test creating an OrganizationContactEmail with a contact email."""
        org = get_organization("buynlarge")
        record = OrganizationContactEmail.create(
            organization=org, contact_email="contact@example.com"
        )
        assert record.contact_email == "contact@example.com"
        assert record.organization_id == org.id

    def test_create_with_null_email(self, initialized_db):
        """Test creating an OrganizationContactEmail with a null contact email."""
        org = get_organization("buynlarge")
        record = OrganizationContactEmail.create(organization=org, contact_email=None)
        assert record.contact_email is None
        assert record.organization_id == org.id

    def test_unique_constraint_on_organization(self, initialized_db):
        """Test that only one contact email record can exist per organization."""
        org = get_organization("buynlarge")
        OrganizationContactEmail.create(organization=org, contact_email="first@example.com")

        with pytest.raises(IntegrityError):
            OrganizationContactEmail.create(organization=org, contact_email="second@example.com")

    def test_multiple_orgs_can_share_email(self, initialized_db):
        """Test that multiple organizations can have the same contact email."""
        org1 = get_organization("buynlarge")
        admin = get_user("devtable")
        org2 = create_organization("testsharedorg", "shared@example.com", admin)

        shared_email = "shared@example.com"
        record1 = OrganizationContactEmail.create(
            organization=org1, contact_email=shared_email
        )
        record2 = OrganizationContactEmail.create(
            organization=org2, contact_email=shared_email
        )

        assert record1.contact_email == shared_email
        assert record2.contact_email == shared_email
        assert record1.organization_id != record2.organization_id


class TestContactEmailCRUD:
    """Tests for contact_email CRUD functions."""

    def test_get_contact_email_returns_none_when_no_record(self, initialized_db):
        """Test get_contact_email returns None when no record exists."""
        org = get_organization("buynlarge")
        assert get_contact_email(org) is None

    def test_get_contact_email_returns_email(self, initialized_db):
        """Test get_contact_email returns the stored email."""
        org = get_organization("buynlarge")
        OrganizationContactEmail.create(organization=org, contact_email="test@example.com")
        assert get_contact_email(org) == "test@example.com"

    def test_set_contact_email_creates_record(self, initialized_db):
        """Test set_contact_email creates a new record."""
        org = get_organization("buynlarge")
        record = set_contact_email(org, "new@example.com")
        assert record.contact_email == "new@example.com"
        assert get_contact_email(org) == "new@example.com"

    def test_set_contact_email_updates_existing(self, initialized_db):
        """Test set_contact_email updates an existing record."""
        org = get_organization("buynlarge")
        set_contact_email(org, "first@example.com")
        set_contact_email(org, "updated@example.com")
        assert get_contact_email(org) == "updated@example.com"

    def test_delete_contact_email(self, initialized_db):
        """Test delete_contact_email removes the record."""
        org = get_organization("buynlarge")
        set_contact_email(org, "delete-me@example.com")
        assert get_contact_email(org) == "delete-me@example.com"

        delete_contact_email(org)
        assert get_contact_email(org) is None

    def test_delete_contact_email_no_record(self, initialized_db):
        """Test delete_contact_email is safe when no record exists."""
        org = get_organization("buynlarge")
        delete_contact_email(org)  # Should not raise

    def test_find_organizations_by_contact_email_single(self, initialized_db):
        """Test find_organizations_by_contact_email returns matching org."""
        admin = get_user("devtable")
        org = create_organization("findorg1", None, admin, contact_email="find@example.com")
        results = list(find_organizations_by_contact_email("find@example.com"))
        assert len(results) == 1
        assert results[0].username == "findorg1"

    def test_find_organizations_by_contact_email_multiple(self, initialized_db):
        """Test find_organizations_by_contact_email returns multiple matching orgs."""
        admin = get_user("devtable")
        create_organization("findorg2", None, admin, contact_email="shared@example.com")
        create_organization("findorg3", None, admin, contact_email="shared@example.com")
        results = list(find_organizations_by_contact_email("shared@example.com"))
        assert len(results) == 2
        names = {r.username for r in results}
        assert names == {"findorg2", "findorg3"}

    def test_find_organizations_by_contact_email_no_match(self, initialized_db):
        """Test find_organizations_by_contact_email returns empty for no match."""
        results = list(find_organizations_by_contact_email("nonexistent@example.com"))
        assert len(results) == 0


class TestCreateOrganizationContactEmail:
    """Tests for create_organization() with contact_email support."""

    def test_create_org_generates_uuid_email(self, initialized_db):
        """Test that create_organization generates a UUID for User.email."""
        admin = get_user("devtable")
        org = create_organization("uuidorg", "ignored@example.com", admin)
        # User.email should be a UUID, not the passed email
        assert org.email != "ignored@example.com"
        # UUID format: 8-4-4-4-12 hex chars
        assert len(org.email) == 36
        assert org.email.count("-") == 4

    def test_create_org_no_contact_email(self, initialized_db):
        """Test creating org without contact_email."""
        admin = get_user("devtable")
        org = create_organization("nocontactorg", None, admin)
        assert get_contact_email(org) is None

    def test_create_org_with_contact_email(self, initialized_db):
        """Test creating org with contact_email stores it in separate table."""
        admin = get_user("devtable")
        org = create_organization(
            "contactorg", None, admin, contact_email="contact@example.com"
        )
        assert get_contact_email(org) == "contact@example.com"

    def test_create_two_orgs_same_contact_email(self, initialized_db):
        """Test two orgs can share the same contact_email."""
        admin = get_user("devtable")
        org1 = create_organization(
            "shareorg1", None, admin, contact_email="same@example.com"
        )
        org2 = create_organization(
            "shareorg2", None, admin, contact_email="same@example.com"
        )
        assert get_contact_email(org1) == "same@example.com"
        assert get_contact_email(org2) == "same@example.com"

    def test_create_org_backward_compat(self, initialized_db):
        """Test that existing callers (without contact_email) still work."""
        admin = get_user("devtable")
        org = create_organization("compatorg", "compat@example.com", admin)
        assert org.organization is True
        assert org.username == "compatorg"
