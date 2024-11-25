import json
import unittest
import urllib.parse

import pytest
from httmock import HTTMock, urlmatch
from mock import patch

from app import app as realapp
from app import usermanager
from data import model
from data.database import TeamMember
from data.users.externaloidc import OIDCUsers
from features import FeatureNameValue
from initdb import finished_database_for_testing, setup_database_for_testing
from oauth.oidc import OIDCLoginService, PasswordGrantException
from test.fixtures import *


@pytest.fixture()
def discovery_content():
    return {
        "scopes_supported": ["openid"],
        "authorization_endpoint": "http://fakeoidc/authorize",
        "token_endpoint": "http://fakeoidc/token",
        "jwks_uri": "http://fakeoidc/jwks",
        "userinfo_endpoint": "http://fakeoidc/userinfo",
    }


@pytest.fixture()
def discovery_handler(discovery_content):
    @urlmatch(netloc=r"fakeoidc", path=r".+openid.+")
    def handler(_, __):
        return json.dumps(discovery_content)

    return handler


@pytest.fixture()
def token_handler_password_grant():
    @urlmatch(netloc=r"fakeoidc", path=r"/token")
    def handler(_, request):
        params = urllib.parse.parse_qs(request.body)
        if params.get("grant_type")[0] != "password":
            return {"status_code": 400, "content": "Invalid authorization type"}

        if params.get("username")[0] != "someusername":
            return {"status_code": 401, "content": "Invalid login credentials"}

        if params.get("password")[0] != "somepassword":
            return {"status_code": 401, "content": "Invalid login credentials"}

        content = {
            "access_token": "sometoken",
        }
        return {"status_code": 200, "content": json.dumps(content)}

    return handler


@pytest.fixture()
def userinfo_content():
    return {
        "sub": "cooluser",
        "preferred_username": "someusername",
        "email": "foo@example.com",
    }


@pytest.fixture
def userinfo_handler(userinfo_content):
    @urlmatch(netloc=r"fakeoidc", path=r"/userinfo")
    def handler(_, req):
        if req.headers.get("Authorization") != "Bearer sometoken":
            return {"status_code": 401, "content": "Missing expected header"}

        return {"status_code": 200, "content": json.dumps(userinfo_content)}

    return handler


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

    def fake_oidc_login_service(self):
        config = {
            "CLIENT_ID": "foo",
            "CLIENT_SECRET": "bar",
            "SERVICE_NAME": "Some Cool Service",
            "SERVICE_ICON": "http://some/icon",
            "OIDC_SERVER": "http://fakeoidc",
            "DEBUGGING": True,
        }
        return OIDCLoginService(config, "OIDC_LOGIN_CONFIG")

    def setUp(self):
        setup_database_for_testing(self)
        self.oidc_instance = self.fake_oidc()
        self.oidc_login_service = self.fake_oidc_login_service()

    def tearDown(self):
        finished_database_for_testing(self)

    def test_sync_for_empty_oidc_groups(self):
        user_obj = model.user.get_user("devtable")

        test_org = model.organization.create_organization(
            "testorg", "testorg@example.com", user_obj
        )
        team_1 = model.team.create_team("team_1", test_org, "member")
        assert model.team.add_user_to_team(user_obj, team_1)

        team_2 = model.team.create_team("team_2", test_org, "member")
        assert model.team.add_user_to_team(user_obj, team_2)

        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        self.oidc_instance.sync_oidc_groups([], user_obj)
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync

        self.oidc_instance.sync_oidc_groups(None, user_obj)
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync

    def test_sync_for_non_empty_oidc_groups(self):
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
        assert model.team.set_team_syncing(team_1, "oidc", {"group_name": "test_org_1_team_1"})

        team_2 = model.team.create_team("team_2", test_org_2, "member")
        assert model.team.set_team_syncing(team_2, "oidc", {"group_name": "test_org_2_team_2"})

        team_3 = model.team.create_team("team_3", test_org_3, "member")
        assert model.team.set_team_syncing(team_3, "ldap", {"group_name": "test_org_3_team_3"})

        user_groups = [
            "test_org_1_team_1",
            "test_org_2_team_2",
            "test_org_3_team_3",
            "wrong_group_name",
        ]
        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        self.oidc_instance.sync_oidc_groups(user_groups, user_obj)

        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()

        assert user_teams_before_sync + 2 == user_teams_after_sync

    def test_resync_for_empty_quay_teams(self):
        user_obj = model.user.get_user("devtable")

        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        self.oidc_instance.resync_quay_teams([], user_obj)
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
        self.oidc_instance.resync_quay_teams([], user_obj)
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync

    def test_resync_for_non_empty_quay_teams(self):
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
        assert model.team.set_team_syncing(team_1, "oidc", {"group_name": "test_org_1_team_1"})
        assert model.team.add_user_to_team(user_obj, team_1)

        # add user to another team that has team sync enabled with oidc login service
        team_2 = model.team.create_team("team_1", test_org_2, "member")
        assert model.team.set_team_syncing(team_2, "oidc", {"group_name": "test_org_2_team_1"})
        assert model.team.add_user_to_team(user_obj, team_2)

        # add user to another team that has team sync enabled with oidc login service
        team_3 = model.team.create_team("team_2", test_org_2, "member")
        assert model.team.set_team_syncing(team_3, "oidc", {"group_name": "test_org_2_team_2"})
        assert model.team.add_user_to_team(user_obj, team_3)

        user_groups = ["test_org_1_team_1", "another_group", "test_org_2_team_2"]
        # user should be removed from team_2
        self.oidc_instance.resync_quay_teams(user_groups, user_obj)
        assert (
            TeamMember.select()
            .where(TeamMember.user == user_obj, TeamMember.team == team_2)
            .count()
            == 0
        )

        # user should part of team_1 and team_3
        assert (
            TeamMember.select()
            .where(TeamMember.user == user_obj, TeamMember.team << [team_1, team_3])
            .count()
            == 2
        )

    def test_sync_user_groups_for_empty_user_obj(self):
        assert self.oidc_instance.sync_user_groups([], None, self.oidc_login_service) is None
        assert self.oidc_instance.sync_user_groups(None, None, self.oidc_login_service) is None

        user_groups = ["test_org_1_team_1", "another_group"]
        assert (
            self.oidc_instance.sync_user_groups(user_groups, None, self.oidc_login_service) is None
        )

        user_obj = model.user.get_user("devtable")
        fresh_user = model.user.get_user("freshuser")
        test_org_1 = model.organization.create_organization(
            "test_org_1", "testorg1@example.com", user_obj
        )
        # team set to sync but user is not added to team
        team_1 = model.team.create_team("team_1", test_org_1, "member")
        assert model.team.set_team_syncing(
            team_1, self.oidc_login_service.service_id(), {"group_name": "test_org_1_team_1"}
        )

        test_org_2 = model.organization.create_organization(
            "test_org_2", "testorg2@example.com", fresh_user
        )
        # team set to sync and user is added to team
        team_2 = model.team.create_team("team_1", test_org_2, "member")
        assert model.team.set_team_syncing(
            team_2, self.oidc_login_service.service_id(), {"group_name": "test_org_2_team_1"}
        )
        assert model.team.add_user_to_team(user_obj, team_2)

        user_teams_before_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        # user will be removed from team_2
        self.oidc_instance.sync_user_groups([], user_obj, self.oidc_login_service)
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync + 1

        # user will be removed from team_1
        self.oidc_instance.sync_user_groups(user_groups, user_obj, self.oidc_login_service)
        user_teams_after_sync = TeamMember.select().where(TeamMember.user == user_obj).count()
        assert user_teams_before_sync == user_teams_after_sync

    def test_missing_verify_credentials(self):
        result, error_msg = self.oidc_instance.verify_credentials(None, "password")
        assert result is None
        assert error_msg == "Missing username or email."

        result, error_msg = self.oidc_instance.verify_credentials("username", None)
        assert result is None
        assert error_msg == "Anonymous binding not allowed."

    def test_query_users(self):
        result, service, error_msg = self.oidc_instance.query_users("some_query_here", None)
        assert len(result) == 0
        assert service == "oidc"
        assert error_msg == "Not supported"


def test_verify_credentials(discovery_handler, token_handler_password_grant, userinfo_handler):
    oidc_instance = OIDCAuthTests().fake_oidc()
    with HTTMock(discovery_handler, token_handler_password_grant, userinfo_handler):
        result, error_msg = oidc_instance.verify_credentials("username", "password")
        # no result because invalid credentials
        assert result is None

        result, error_msg = oidc_instance.verify_credentials("someusername", "somepassword")
        assert result.username == "someusername"
        assert result.email == "foo@example.com"
        assert result.id == "cooluser"
        assert error_msg is None


def test_service_metadata(discovery_handler, token_handler_password_grant, userinfo_handler):
    oidc_instance = OIDCAuthTests().fake_oidc()
    with HTTMock(discovery_handler, token_handler_password_grant, userinfo_handler):
        result = oidc_instance.service_metadata()
        assert result["issuer_domain"] == "fakeoidc"


def test_user_restrictions(discovery_handler, token_handler_password_grant, userinfo_handler):
    oidc_instance = OIDCAuthTests().fake_oidc()
    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with HTTMock(discovery_handler, token_handler_password_grant, userinfo_handler):
            result, error_msg = oidc_instance.verify_credentials("someusername", "somepassword")
            assert result.username == "someusername"
            assert error_msg is None
            # check if user is super user
            check_is_superuser = usermanager.is_superuser(result.username)
            assert check_is_superuser == False
            # turn on restricted users
            check_is_restricted_user = usermanager.is_restricted_user(result.username)
            assert check_is_restricted_user == True
