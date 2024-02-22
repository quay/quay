import unittest

import pytest

from data import model
from data.database import TeamMember
from data.users.externaloidc import OIDCUsers
from test.fixtures import *


class OIDCAuthTests(unittest.TestCase):
    def fake_oidc(self):
        """
        Instantiates a fake OIDC instance to use in the test cases
        """
        client_id = "quay-test"
        client_secret = "secret"
        oidc_server = "http://test-server/realms/myrealm"
        service_name = "test"
        login_scopes = ["openid"]
        preferred_group_claim_name = "groups"

        oidc_instance = OIDCUsers(
            client_id,
            client_secret,
            oidc_server,
            service_name,
            login_scopes,
            preferred_group_claim_name,
        )
        return oidc_instance

    @pytest.mark.parametrize(
        "name, expected_org_name, expected_group_name",
        [
            ("", None, None),
            ("f", None, None),
            ("foobar", None, None),
            (1, None, None),
            (256, None, None),
            (" ", None, None),
            ("foo:bar", "foo", "bar"),
            ("foooooo:baaaaar", "foooooo", "baaaaar"),
        ],
    )
    def test_fetch_org_team_from_oidc_group(self, name, expected_org_name, expected_group_name):
        oidc_instance = self.fake_oidc()
        org_name, group_name = oidc_instance.fetch_org_team_from_oidc_group(name)
        assert expected_org_name == org_name
        assert expected_group_name == group_name

    def test_sync_for_empty_oidc_groups(self, initialized_db):
        oidc_instance = self.fake_oidc()
        user_obj = model.user.get_user("devtable")

        test_org = model.organization.create_organization(
            "testorg", "testorg@example.com", user_obj
        )
        team_1 = model.team.create_team("team_1", test_org, "member")
        assert model.team.add_user_to_team(user_obj, team_1)

        team_2 = model.team.create_team("team_2", test_org, "member")
        assert model.team.add_user_to_team(user_obj, team_2)

        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        oidc_instance.sync_oidc_groups([], user_obj, "oidc")
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync

    def test_sync_for_non_empty_oidc_groups(self, initialized_db):
        oidc_instance = self.fake_oidc()
        user_obj = model.user.get_user("devtable")
        fresh_user = model.user.get_user("freshuser")
        random_user = model.user.get_user("randomuser")

        test_org_1 = model.organization.create_organization(
            "test_org_1", "testorg1@example.com", user_obj
        )
        test_org_2 = model.organization.create_organization(
            "test_org_2", "testorg2@example.com", fresh_user
        )
        test_org_3 = model.organization.create_organization(
            "test_org_3", "testorg3@example.com", random_user
        )

        team_1 = model.team.create_team("team_1", test_org_1, "member")
        assert model.team.set_team_syncing(team_1, "oidc", None)

        team_2 = model.team.create_team("team_2", test_org_2, "member")
        assert model.team.set_team_syncing(team_2, "oidc", None)

        team_3 = model.team.create_team("team_3", test_org_3, "member")
        assert model.team.set_team_syncing(team_3, "ldap", None)

        user_groups = [
            "test_org_1:team_1",
            "test_org_2:team_2",
            "test_org_3:team_3",
            "wrong_group_name",
        ]
        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        oidc_instance.sync_oidc_groups(user_groups, user_obj, "oidc")

        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()

        assert user_teams_before_sync + 2 == user_teams_after_sync

    def test_resync_for_empty_quay_teams(self, initialized_db):
        oidc_instance = self.fake_oidc()
        user_obj = model.user.get_user("devtable")

        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        oidc_instance.resync_quay_teams([], user_obj, "oidc")
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync

        # add user to team that doesn't have team sync enabled
        test_org_1 = model.organization.create_organization(
            "test_org_1", "testorg1@example.com", user_obj
        )
        team_1 = model.team.create_team("team_1", test_org_1, "member")
        assert model.team.add_user_to_team(user_obj, team_1)

        # add user to team that has team sync enabled with a different login service
        team_2 = model.team.create_team("team_2", test_org_1, "member")
        assert model.team.set_team_syncing(team_2, "ldap", None)
        assert model.team.add_user_to_team(user_obj, team_2)

        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        oidc_instance.resync_quay_teams([], user_obj, "oidc")
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync

    def test_resync_for_non_empty_quay_teams(self, initialized_db):
        oidc_instance = self.fake_oidc()
        user_obj = model.user.get_user("devtable")
        fresh_user = model.user.get_user("freshuser")

        test_org_1 = model.organization.create_organization(
            "test_org_1", "testorg1@example.com", user_obj
        )
        test_org_2 = model.organization.create_organization(
            "test_org_2", "testorg2@example.com", fresh_user
        )

        # add user to team that has team sync enabled with oidc login service
        team_1 = model.team.create_team("team_1", test_org_1, "member")
        assert model.team.set_team_syncing(team_1, "oidc", {"group_name": "test_org_1:team_1"})
        assert model.team.add_user_to_team(user_obj, team_1)

        # add user to another team that has team sync enabled with oidc login service
        team_2 = model.team.create_team("team_1", test_org_2, "member")
        assert model.team.set_team_syncing(team_2, "oidc", {"group_name": "test_org_2:team_1"})
        assert model.team.add_user_to_team(user_obj, team_2)

        user_groups = ["test_org_1:team_1", "another:group"]
        # user should be removed from team_2
        oidc_instance.resync_quay_teams(user_groups, user_obj, "oidc")
        assert (
            TeamMember.select()
            .where(TeamMember.user == user_obj, TeamMember.team == team_2)
            .count()
            == 0
        )
