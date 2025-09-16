from unittest.mock import patch

import features
from data import model
from data.model import team as team_model
from endpoints.api.organization import (
    OrganizationApplications,
    OrganizationMember,
    OrganizationMemberList,
)
from endpoints.api.team import TeamMemberList, TeamPermissions
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *  # noqa: F401,F403


def _ensure_org_with_team(orgname: str = "neworg", teamname: str = "owners"):
    user = model.user.get_user("devtable")
    try:
        org = model.organization.get_organization(orgname)
    except model.InvalidOrganizationException:
        org = model.organization.create_organization(
            orgname,
            "neworg@example.com",
            user,
            email_required=features.MAILING,
            is_possible_abuser=False,
        )
    try:
        model.team.get_organization_team(orgname, teamname)
    except model.InvalidTeamException:
        model.team.create_team(teamname, org, "admin", "")

    return orgname, teamname


def test_org_members_and_team_permissions_viewable_by_global_readonly(app):
    orgname, teamname = _ensure_org_with_team()
    with patch("endpoints.api.organization.allow_if_superuser", return_value=False), patch(
        "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
    ), patch("endpoints.api.team.allow_if_superuser", return_value=False), patch(
        "endpoints.api.team.allow_if_global_readonly_superuser", return_value=True
    ):
        with client_with_identity("reader", app) as cl:
            conduct_api_call(cl, OrganizationMemberList, "GET", {"orgname": orgname}, None, 200)
            conduct_api_call(
                cl,
                TeamMemberList,
                "GET",
                {"orgname": orgname, "teamname": teamname},
                None,
                200,
            )
            conduct_api_call(
                cl,
                TeamPermissions,
                "GET",
                {"orgname": orgname, "teamname": teamname},
                None,
                200,
            )


def test_org_member_detail_viewable_by_global_readonly(app):
    orgname, teamname = _ensure_org_with_team()
    # Ensure freshuser is a member of the org's team so detail view returns 200
    freshuser = model.user.get_user("freshuser")
    owners = model.team.get_organization_team(orgname, teamname)
    try:
        team_model.add_user_to_team(freshuser, owners)
    except team_model.UserAlreadyInTeam:
        pass

    with patch("endpoints.api.organization.allow_if_superuser", return_value=False), patch(
        "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
    ):
        with client_with_identity("reader", app) as cl:
            conduct_api_call(
                cl,
                OrganizationMember,
                "GET",
                {"orgname": orgname, "membername": "freshuser"},
                None,
                200,
            )


def test_org_applications_list_viewable_by_global_readonly(app):
    orgname, _ = _ensure_org_with_team()
    with patch("endpoints.api.organization.allow_if_superuser", return_value=False), patch(
        "endpoints.api.organization.allow_if_global_readonly_superuser", return_value=True
    ):
        with client_with_identity("reader", app) as cl:
            conduct_api_call(
                cl,
                OrganizationApplications,
                "GET",
                {"orgname": orgname},
                None,
                200,
            )
