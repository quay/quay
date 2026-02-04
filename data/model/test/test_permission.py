"""Tests for permission module optimizations."""

import pytest

from data.model.organization import create_organization
from data.model.permission import get_org_wide_permissions
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
