import json
import time
import unittest
import urllib.parse

import jwt
import pytest
from authlib.jose import JsonWebKey
from cryptography.hazmat.primitives import serialization
from httmock import HTTMock, urlmatch
from mock import patch

import app as app_module
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
        "email_verified": True,
    }


@pytest.fixture
def userinfo_handler(userinfo_content):
    @urlmatch(netloc=r"fakeoidc", path=r"/userinfo")
    def handler(_, req):
        if req.headers.get("Authorization") != "Bearer sometoken":
            return {"status_code": 401, "content": "Missing expected header"}

        return {"status_code": 200, "content": json.dumps(userinfo_content)}

    return handler


def _generate_signing_key(kid):
    """
    Generates an RSA signing key for building id_tokens in tests, mirroring
    the fixtures in oauth/test/test_oidc.py.
    """
    jwk = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    return {
        "id": kid,
        "private_key": jwk.get_private_key().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        "jwk": jwk.as_dict(),
    }


def _sign_id_token(signing_key, sub):
    """
    Builds an RS256-signed id_token for the app's `testoidc` service
    (CLIENT_ID `foo`, OIDC_SERVER `http://fakeoidc`).
    """
    token_data = {
        "iss": "http://fakeoidc",
        "aud": "foo",
        "nbf": int(time.time()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "sub": sub,
    }
    return jwt.encode(
        token_data, signing_key["private_key"], "RS256", headers={"kid": signing_key["id"]}
    )


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

        # attempt to sync already synced groups
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

    def test_has_password_set_returns_false(self):
        # PROJQUAY-10510: OIDCUsers must return False so require_fresh_login
        # skips the fresh-login check for OIDC browser users (who have no
        # Quay-local password and cannot complete password verification).
        assert self.oidc_instance.has_password_set("any_oidc_user") is False
        assert self.oidc_instance.has_password_set("another_user") is False

    def _password_grant_mocks(
        self,
        email_verified=True,
        userinfo_sub="cooluser",
        impersonated=False,
        id_token=None,
        signing_key=None,
    ):
        """
        Handlers for a successful ROPC login against the app's `testoidc`
        service (registered from TESTOIDC_LOGIN_CONFIG): a token for
        someusername/somepassword and userinfo with sub `cooluser` and email
        `foo@example.com`. Mirrors the module-level fixtures, which unittest
        methods cannot receive. Pass `email_verified=False` to exercise the
        unverified-email path, `userinfo_sub` to vary the userinfo sub,
        `impersonated=True` to mark the principal as impersonated, and
        `id_token`/`signing_key` to include (and serve keys for) an id_token
        in the grant response.
        """

        @urlmatch(netloc=r"fakeoidc", path=r".+openid.+")
        def discovery(_, __):
            return json.dumps(
                {
                    "scopes_supported": ["openid"],
                    "authorization_endpoint": "http://fakeoidc/authorize",
                    "token_endpoint": "http://fakeoidc/token",
                    "jwks_uri": "http://fakeoidc/jwks",
                    "userinfo_endpoint": "http://fakeoidc/userinfo",
                }
            )

        @urlmatch(netloc=r"fakeoidc", path=r"/token")
        def token(_, request):
            params = urllib.parse.parse_qs(request.body)
            if params.get("grant_type")[0] != "password":
                return {"status_code": 400, "content": "Invalid authorization type"}
            if params.get("username")[0] != "someusername":
                return {"status_code": 401, "content": "Invalid login credentials"}
            if params.get("password")[0] != "somepassword":
                return {"status_code": 401, "content": "Invalid login credentials"}
            content = {"access_token": "sometoken"}
            if id_token is not None:
                content["id_token"] = id_token
            return {"status_code": 200, "content": json.dumps(content)}

        @urlmatch(netloc=r"fakeoidc", path=r"/userinfo")
        def userinfo(_, req):
            if req.headers.get("Authorization") != "Bearer sometoken":
                return {"status_code": 401, "content": "Missing expected header"}
            return {
                "status_code": 200,
                "content": json.dumps(
                    {
                        "sub": userinfo_sub,
                        "preferred_username": "someusername",
                        "email": "foo@example.com",
                        "email_verified": email_verified,
                        "impersonated": impersonated,
                    }
                ),
            }

        handlers = [discovery, token, userinfo]

        if signing_key is not None:

            @urlmatch(netloc=r"fakeoidc", path=r"/jwks")
            def jwks(_, __):
                jwk = signing_key["jwk"].copy()
                jwk.update({"kid": signing_key["id"]})
                return {"status_code": 200, "content": json.dumps({"keys": [jwk]})}

            handlers.append(jwks)

        return tuple(handlers)

    def test_verify_and_link_user_matches_browser_sub_binding(self):
        # An account provisioned by the OIDC browser flow is bound to the
        # provider's login service by sub; a password login must match that
        # binding instead of trying to create a second account.
        browser_user = model.user.create_federated_user(
            "browseruser",
            "foo@example.com",
            "testoidc",
            "cooluser",
            set_password_notification=False,
        )

        with HTTMock(*self._password_grant_mocks()):
            result, error_msg = self.oidc_instance.verify_and_link_user(
                "someusername", "somepassword"
            )

        assert error_msg is None
        assert result is not None
        assert result.id == browser_user.id

    def test_verify_and_link_user_creates_account_bound_by_sub(self):
        # No binding exists: the new account must be bound by (provider, sub),
        # the same key the browser flow matches. The internal "oidc" binding
        # by username is attached as well (matching the pre-fix password path)
        # so confirm_existing_user keeps working for such accounts.
        with HTTMock(*self._password_grant_mocks()):
            result, error_msg = self.oidc_instance.verify_and_link_user(
                "someusername", "somepassword"
            )

        assert error_msg is None
        assert result is not None
        assert result.username == "someusername"

        sub_binding = model.user.lookup_federated_login(result, "testoidc")
        assert sub_binding is not None
        assert sub_binding.service_ident == "cooluser"

        legacy_binding = model.user.lookup_federated_login(result, "oidc")
        assert legacy_binding is not None
        assert legacy_binding.service_ident == "someusername"

        # The internal binding must keep password confirmation working for the
        # account created by the password flow (confirm_existing_user looks up
        # the internal service by username).
        with HTTMock(*self._password_grant_mocks()):
            confirmed, confirm_error = self.oidc_instance.confirm_existing_user(
                result.username, "somepassword"
            )
        assert confirm_error is None
        assert confirmed is not None
        assert confirmed.id == result.id

    def test_verify_and_link_user_does_not_upgrade_legacy_binding_without_verified_email(self):
        # An unverified (or absent) e-mail claim must not be used to satisfy
        # the e-mail agreement required to attach the (provider, sub) binding
        # to a legacy ("oidc", username) account: the password flow applies the
        # same verified-e-mail rule as the browser flow.
        legacy_user = model.user.create_federated_user(
            "legacyuser",
            "foo@example.com",
            "oidc",
            "someusername",
            set_password_notification=False,
        )

        oidc_services = [
            s for s in app_module.oauth_login.services if isinstance(s, OIDCLoginService)
        ]
        assert oidc_services

        with (
            patch.object(oidc_services[0], "_mailing", False),
            patch("features.MAILING", FeatureNameValue("MAILING", False)),
        ):
            with HTTMock(*self._password_grant_mocks(email_verified=False)):
                result, error_msg = self.oidc_instance.verify_and_link_user(
                    "someusername", "somepassword"
                )

        # The legacy account is not upgraded: the unverified e-mail cannot
        # establish the agreement, and the sub binding is not attached to it.
        assert error_msg is None
        assert result is not None
        assert result.id != legacy_user.id
        assert model.user.lookup_federated_login(legacy_user, "testoidc") is None

        # A separate account, bound by (provider, sub) and created without an
        # e-mail (a unique placeholder is assigned), is provisioned instead.
        sub_binding = model.user.lookup_federated_login(result, "testoidc")
        assert sub_binding is not None
        assert sub_binding.service_ident == "cooluser"
        assert result.email != "foo@example.com"

    def test_verify_and_link_user_accepts_matching_id_token_sub(self):
        # When the password grant returns an id_token, its sub must agree
        # with the userinfo sub (browser-flow parity); matching subs log in
        # normally.
        signing_key = _generate_signing_key("matchingkey")
        id_token = _sign_id_token(signing_key, sub="cooluser")

        with HTTMock(*self._password_grant_mocks(id_token=id_token, signing_key=signing_key)):
            result, error_msg = self.oidc_instance.verify_and_link_user(
                "someusername", "somepassword"
            )

        assert error_msg is None
        assert result is not None
        assert result.username == "someusername"

    def test_verify_and_link_user_rejects_userinfo_sub_mismatch(self):
        # A userinfo sub that differs from the signed id_token sub must be
        # rejected before any account is selected or linked.
        signing_key = _generate_signing_key("mismatchkey")
        id_token = _sign_id_token(signing_key, sub="cooluser")

        with HTTMock(
            *self._password_grant_mocks(
                userinfo_sub="someothersub", id_token=id_token, signing_key=signing_key
            )
        ):
            result, error_msg = self.oidc_instance.verify_and_link_user(
                "someusername", "somepassword"
            )

        assert result is None
        assert error_msg is not None
        assert "Mismatch in `sub`" in str(error_msg)

    def test_verify_and_link_user_email_collision_returns_error_with_mailing_disabled(self):
        # With MAILING disabled, create_user_noverify skips the e-mail
        # uniqueness check; the flow must still return the collision error
        # for a verified e-mail owned by another user instead of failing
        # with an unhandled database error.
        model.user.create_user_noverify("unrelateduser2", "foo@example.com")

        with patch("features.MAILING", FeatureNameValue("MAILING", False)):
            with HTTMock(*self._password_grant_mocks()):
                result, error_msg = self.oidc_instance.verify_and_link_user(
                    "someusername", "somepassword"
                )

        assert result is None
        assert error_msg is not None
        assert "foo@example.com" in str(error_msg)

        unrelated_user = model.user.get_user("unrelateduser2")
        assert model.user.lookup_federated_login(unrelated_user, "testoidc") is None

    def test_verify_and_link_user_rejects_impersonated_principal(self):
        # Browser-flow parity: userinfo marking the principal as impersonated
        # must be rejected before any account is selected or linked.
        with HTTMock(*self._password_grant_mocks(impersonated=True)):
            result, error_msg = self.oidc_instance.verify_and_link_user(
                "someusername", "somepassword"
            )

        assert result is None
        assert error_msg is not None
        assert "impersonated" in str(error_msg)

    def test_verify_and_link_user_requires_email_when_mailing_enabled(self):
        # Browser-flow parity: when the login service requires a verified
        # e-mail (FEATURE_MAILING on its login config), a password login for
        # an identity without one is rejected before any binding is matched.
        browser_user = model.user.create_federated_user(
            "browseruser",
            "foo@example.com",
            "testoidc",
            "cooluser",
            set_password_notification=False,
        )

        oidc_services = [
            s for s in app_module.oauth_login.services if isinstance(s, OIDCLoginService)
        ]
        assert oidc_services

        with patch.object(oidc_services[0], "_mailing", True):
            with HTTMock(*self._password_grant_mocks(email_verified=False)):
                result, error_msg = self.oidc_instance.verify_and_link_user(
                    "someusername", "somepassword"
                )

        assert result is None
        assert error_msg is not None
        assert "verified email address is required" in str(error_msg)

        # The existing (provider, sub) binding must not have been matched.
        assert model.user.lookup_federated_login(browser_user, "testoidc") is not None

    def test_verify_and_link_user_upgrades_legacy_username_binding(self):
        # An account created by the pre-fix password-login path is bound to
        # the internal "oidc" service by username. A password login must
        # attach the (provider, sub) binding so the browser flow can match it
        # too, while keeping the legacy binding intact.
        legacy_user = model.user.create_federated_user(
            "legacyuser",
            "foo@example.com",
            "oidc",
            "someusername",
            set_password_notification=False,
        )

        with HTTMock(*self._password_grant_mocks()):
            result, error_msg = self.oidc_instance.verify_and_link_user(
                "someusername", "somepassword"
            )

        assert error_msg is None
        assert result is not None
        assert result.id == legacy_user.id

        sub_binding = model.user.lookup_federated_login(result, "testoidc")
        assert sub_binding is not None
        assert sub_binding.service_ident == "cooluser"

        legacy_binding = model.user.lookup_federated_login(result, "oidc")
        assert legacy_binding is not None
        assert legacy_binding.service_ident == "someusername"

    def test_verify_and_link_user_email_collision_returns_error(self):
        # The provider-verified email is owned by an unrelated account and no
        # matching binding exists: linking must be refused with an error, not
        # silently attached to the existing account.
        model.user.create_user_noverify("unrelateduser", "foo@example.com")

        with HTTMock(*self._password_grant_mocks()):
            result, error_msg = self.oidc_instance.verify_and_link_user(
                "someusername", "somepassword"
            )

        assert result is None
        assert error_msg is not None

        unrelated_user = model.user.get_user("unrelateduser")
        assert model.user.lookup_federated_login(unrelated_user, "testoidc") is None


class OIDCSuperuserSyncTests(unittest.TestCase):
    def setUp(self):
        setup_database_for_testing(self)

    def tearDown(self):
        finished_database_for_testing(self)

    def _make_oidc(self, superuser_group=None, global_readonly_group=None):
        return OIDCUsers(
            client_id="quay-test",
            client_secret="secret",
            oidc_server="http://test-server/realms/myrealm",
            service_name="test",
            login_scopes=["openid"],
            preferred_group_claim_name="groups",
            oidc_superuser_group=superuser_group,
            oidc_global_readonly_superuser_group=global_readonly_group,
        )

    def test_sync_superuser_grants_when_in_group(self):
        oidc = self._make_oidc(superuser_group="quay-superusers")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["quay-superusers", "other-group"], user_obj)
            mock_um.register_superuser.assert_called_once_with("devtable")
            mock_um.deregister_superuser.assert_not_called()

    def test_sync_superuser_revokes_when_not_in_group(self):
        oidc = self._make_oidc(superuser_group="quay-superusers")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["other-group"], user_obj)
            mock_um.deregister_superuser.assert_called_once_with("devtable")
            mock_um.register_superuser.assert_not_called()

    def test_sync_superuser_revokes_when_groups_empty(self):
        oidc = self._make_oidc(superuser_group="quay-superusers")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status([], user_obj)
            mock_um.deregister_superuser.assert_called_once_with("devtable")

    def test_sync_superuser_noop_when_groups_none(self):
        oidc = self._make_oidc(superuser_group="quay-superusers")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(None, user_obj)
            mock_um.register_superuser.assert_not_called()
            mock_um.deregister_superuser.assert_not_called()

    def test_sync_superuser_noop_when_no_group_configured(self):
        oidc = self._make_oidc()
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["quay-superusers"], user_obj)
            mock_um.register_superuser.assert_not_called()
            mock_um.deregister_superuser.assert_not_called()

    def test_sync_superuser_noop_when_user_obj_none(self):
        oidc = self._make_oidc(superuser_group="quay-superusers")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["quay-superusers"], None)
            mock_um.register_superuser.assert_not_called()
            mock_um.deregister_superuser.assert_not_called()

    def test_sync_global_readonly_grants_when_in_group(self):
        oidc = self._make_oidc(global_readonly_group="quay-readonly")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["quay-readonly"], user_obj)
            mock_um.register_global_readonly_superuser.assert_called_once_with("devtable")
            mock_um.deregister_global_readonly_superuser.assert_not_called()

    def test_sync_global_readonly_revokes_when_not_in_group(self):
        oidc = self._make_oidc(global_readonly_group="quay-readonly")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["other-group"], user_obj)
            mock_um.deregister_global_readonly_superuser.assert_called_once_with("devtable")
            mock_um.register_global_readonly_superuser.assert_not_called()

    def test_sync_global_readonly_revokes_when_groups_empty(self):
        oidc = self._make_oidc(global_readonly_group="quay-readonly")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status([], user_obj)
            mock_um.deregister_global_readonly_superuser.assert_called_once_with("devtable")
            mock_um.register_global_readonly_superuser.assert_not_called()

    def test_sync_global_readonly_noop_when_groups_none(self):
        oidc = self._make_oidc(global_readonly_group="quay-readonly")
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(None, user_obj)
            mock_um.register_global_readonly_superuser.assert_not_called()
            mock_um.deregister_global_readonly_superuser.assert_not_called()

    def test_sync_global_readonly_noop_when_no_group_configured(self):
        oidc = self._make_oidc()
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["quay-readonly"], user_obj)
            mock_um.register_global_readonly_superuser.assert_not_called()
            mock_um.deregister_global_readonly_superuser.assert_not_called()

    def test_sync_global_readonly_noop_when_user_obj_none(self):
        oidc = self._make_oidc(global_readonly_group="quay-readonly")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["quay-readonly"], None)
            mock_um.register_global_readonly_superuser.assert_not_called()
            mock_um.deregister_global_readonly_superuser.assert_not_called()

    def test_sync_both_superuser_and_global_readonly(self):
        oidc = self._make_oidc(
            superuser_group="quay-superusers",
            global_readonly_group="quay-readonly",
        )
        user_obj = model.user.get_user("devtable")

        with patch("app.usermanager") as mock_um:
            oidc.sync_superuser_status(["quay-superusers", "quay-readonly"], user_obj)
            mock_um.register_superuser.assert_called_once_with("devtable")
            mock_um.register_global_readonly_superuser.assert_called_once_with("devtable")

    def test_sync_user_groups_does_not_call_sync_superuser_status(self):
        oidc = self._make_oidc(superuser_group="quay-superusers")
        user_obj = model.user.get_user("devtable")

        with patch.object(oidc, "sync_superuser_status") as mock_sync:
            groups = ["quay-superusers"]
            oidc.sync_user_groups(groups, user_obj, None)
            mock_sync.assert_not_called()


def test_has_password_set_returns_false_standalone():
    # Standalone (no DB) variant so codecov/patch sees the method covered.
    oidc_instance = OIDCAuthTests().fake_oidc()
    assert oidc_instance.has_password_set("any_oidc_user") is False
    assert oidc_instance.has_password_set("another_user") is False


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
