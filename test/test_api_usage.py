# coding=utf-8

import unittest
import datetime
import logging
import time
import re
import json as py_json

from mock import patch
from calendar import timegm
from contextlib import contextmanager
from httmock import urlmatch, HTTMock, all_requests
from urllib.parse import urlencode
from urllib.parse import urlparse, urlunparse, parse_qs

from playhouse.test_utils import assert_query_count, _QueryLogHandler
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from endpoints.api import api_bp, api
from endpoints.building import PreparedBuild
from endpoints.webhooks import webhooks
from app import (
    app,
    config_provider,
    all_queues,
    dockerfile_build_queue,
    notification_queue,
    storage,
    docker_v2_signing_key,
)
from buildtrigger.basehandler import BuildTriggerHandler
from initdb import setup_database_for_testing, finished_database_for_testing
from data import database, model, appr_model
from data.appr_model.models import NEW_MODELS
from data.database import RepositoryActionCount, Repository as RepositoryTable
from data.logs_model import logs_model
from data.registry_model import registry_model
from test.helpers import assert_action_logged, check_transitive_modifications
from util.secscan.fake import fake_security_scanner

from endpoints.api.team import (
    TeamMember,
    TeamMemberList,
    TeamMemberInvite,
    OrganizationTeam,
    TeamPermissions,
    InviteTeamMember,
)
from endpoints.api.tag import RepositoryTagImages, RepositoryTag, RestoreTag, ListRepositoryTags
from endpoints.api.search import EntitySearch, ConductSearch
from endpoints.api.image import RepositoryImage, RepositoryImageList
from endpoints.api.build import RepositoryBuildStatus, RepositoryBuildList, RepositoryBuildResource
from endpoints.api.robot import (
    UserRobotList,
    OrgRobot,
    OrgRobotList,
    UserRobot,
    RegenerateUserRobot,
    RegenerateOrgRobot,
)
from endpoints.api.trigger import (
    BuildTriggerActivate,
    BuildTriggerSources,
    BuildTriggerSubdirs,
    TriggerBuildList,
    ActivateBuildTrigger,
    BuildTrigger,
    BuildTriggerList,
    BuildTriggerAnalyze,
    BuildTriggerFieldValues,
    BuildTriggerSourceNamespaces,
)
from endpoints.api.repoemail import RepositoryAuthorizedEmail
from endpoints.api.repositorynotification import (
    RepositoryNotification,
    RepositoryNotificationList,
    TestRepositoryNotification,
)
from endpoints.api.user import (
    PrivateRepositories,
    ConvertToOrganization,
    Signout,
    Signin,
    User,
    UserAuthorizationList,
    UserAuthorization,
    UserNotification,
    UserNotificationList,
    StarredRepositoryList,
    StarredRepository,
)

from endpoints.api.repotoken import RepositoryToken, RepositoryTokenList
from endpoints.api.prototype import PermissionPrototype, PermissionPrototypeList
from endpoints.api.logs import (
    UserLogs,
    OrgLogs,
    OrgAggregateLogs,
    UserAggregateLogs,
    RepositoryLogs,
    RepositoryAggregateLogs,
)
from endpoints.api.billing import UserCard, UserPlan, ListPlans, OrganizationCard, OrganizationPlan
from endpoints.api.discovery import DiscoveryResource
from endpoints.api.error import Error
from endpoints.api.organization import (
    OrganizationList,
    OrganizationMember,
    OrgPrivateRepositories,
    OrganizationMemberList,
    Organization,
    ApplicationInformation,
    OrganizationApplications,
    OrganizationApplicationResource,
    OrganizationApplicationResetClientSecret,
    Organization,
)
from endpoints.api.repository import RepositoryList, RepositoryVisibility, Repository

from endpoints.api.repository_models_pre_oci import REPOS_PER_PAGE

from endpoints.api.permission import (
    RepositoryUserPermission,
    RepositoryTeamPermission,
    RepositoryTeamPermissionList,
    RepositoryUserPermissionList,
)
from endpoints.api.superuser import (
    SuperUserLogs,
    SuperUserManagement,
    SuperUserServiceKeyManagement,
    SuperUserServiceKey,
    SuperUserServiceKeyApproval,
    SuperUserTakeOwnership,
)
from endpoints.api.globalmessages import (
    GlobalUserMessage,
    GlobalUserMessages,
)
from endpoints.api.secscan import RepositoryImageSecurity, RepositoryManifestSecurity
from endpoints.api.manifest import RepositoryManifestLabels, ManageRepositoryManifestLabel
from util.morecollections import AttrDict

try:
    app.register_blueprint(api_bp, url_prefix="/api")
except ValueError:
    # This blueprint was already registered
    pass

app.register_blueprint(webhooks, url_prefix="/webhooks")

# The number of queries we run for guests on API calls.
BASE_QUERY_COUNT = 0

# The number of queries we run for logged in users on API calls.
BASE_LOGGEDIN_QUERY_COUNT = BASE_QUERY_COUNT + 1

# The number of queries we run for logged in users on API calls that check
# access permissions.
BASE_PERM_ACCESS_QUERY_COUNT = BASE_LOGGEDIN_QUERY_COUNT + 2

NO_ACCESS_USER = "freshuser"
READ_ACCESS_USER = "reader"
ADMIN_ACCESS_USER = "devtable"
PUBLIC_USER = "public"

ADMIN_ACCESS_EMAIL = "jschorr@devtable.com"

ORG_REPO = "orgrepo"

ORGANIZATION = "buynlarge"

NEW_USER_DETAILS = {
    "username": "bobby",
    "password": "password",
    "email": "bobby@tables.com",
}

FAKE_APPLICATION_CLIENT_ID = "deadbeef"

CSRF_TOKEN_KEY = "_csrf_token"


class AppConfigChange(object):
    """
    AppConfigChange takes a dictionary that overrides the global app config for a given block of
    code.

    The values are restored on exit.
    """

    def __init__(self, changes=None):
        self._changes = changes or {}
        self._originals = {}
        self._to_rm = []

    def __enter__(self):
        for key in list(self._changes.keys()):
            try:
                self._originals[key] = app.config[key]
            except KeyError:
                self._to_rm.append(key)
            app.config[key] = self._changes[key]

    def __exit__(self, type, value, traceback):
        for key in list(self._originals.keys()):
            app.config[key] = self._originals[key]

        for key in self._to_rm:
            del app.config[key]


class ApiTestCase(unittest.TestCase):
    maxDiff = None

    def _add_csrf(self, without_csrf, explicit_csrf=None):
        parts = urlparse(without_csrf)
        query = parse_qs(parts[4])

        with self.app.session_transaction() as sess:
            if explicit_csrf is not None:
                query[CSRF_TOKEN_KEY] = explicit_csrf
            else:
                sess[CSRF_TOKEN_KEY] = "something"
                query[CSRF_TOKEN_KEY] = sess[CSRF_TOKEN_KEY]

        return urlunparse(list(parts[0:4]) + [urlencode(query)] + list(parts[5:]))

    def url_for(self, resource_name, params=None, skip_csrf=False, explicit_csrf=None):
        params = params or {}
        url = api.url_for(resource_name, **params)
        if not skip_csrf:
            url = self._add_csrf(url, explicit_csrf)
        return url

    def setUp(self):
        setup_database_for_testing(self)
        self.app = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.__enter__()

    def tearDown(self):
        finished_database_for_testing(self)
        config_provider.clear()
        self.ctx.__exit__(True, None, None)

    def setCsrfToken(self, token):
        with self.app.session_transaction() as sess:
            sess[CSRF_TOKEN_KEY] = token

    @contextmanager
    def toggleFeature(self, name, enabled):
        import features

        previous_value = getattr(features, name)
        setattr(features, name, enabled)
        yield
        setattr(features, name, previous_value)

    def getJsonResponse(self, resource_name, params={}, expected_code=200):
        rv = self.app.get(api.url_for(resource_name, **params))
        self.assertEqual(expected_code, rv.status_code)
        data = rv.data
        parsed = py_json.loads(data)
        return parsed

    def postResponse(
        self, resource_name, params={}, data={}, file=None, headers=None, expected_code=200
    ):
        data = py_json.dumps(data)

        headers = headers or {}
        headers.update({"Content-Type": "application/json"})

        if file is not None:
            data = {"file": file}
            headers = None

        rv = self.app.post(self.url_for(resource_name, params), data=data, headers=headers)
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def getResponse(self, resource_name, params={}, expected_code=200):
        rv = self.app.get(api.url_for(resource_name, **params))
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def putResponse(self, resource_name, params={}, data={}, expected_code=200):
        rv = self.app.put(
            self.url_for(resource_name, params),
            data=py_json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def deleteResponse(self, resource_name, params={}, expected_code=204):
        rv = self.app.delete(self.url_for(resource_name, params))

        if rv.status_code != expected_code:
            print("Mismatch data for resource DELETE %s: %s" % (resource_name, rv.data))

        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def deleteEmptyResponse(self, resource_name, params={}, expected_code=204):
        rv = self.app.delete(self.url_for(resource_name, params))
        self.assertEqual(rv.status_code, expected_code)
        self.assertEqual(rv.data, b"")  # ensure response body empty
        return

    def postJsonResponse(self, resource_name, params={}, data={}, expected_code=200):
        rv = self.app.post(
            self.url_for(resource_name, params),
            data=py_json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

        if rv.status_code != expected_code:
            print("Mismatch data for resource POST %s: %s" % (resource_name, rv.data))

        self.assertEqual(rv.status_code, expected_code)
        data = rv.data
        parsed = py_json.loads(data.decode("utf-8"))
        return parsed

    def putJsonResponse(
        self,
        resource_name,
        params={},
        data={},
        expected_code=200,
        skip_csrf=False,
        explicit_csrf=None,
    ):
        rv = self.app.put(
            self.url_for(resource_name, params, skip_csrf, explicit_csrf),
            data=py_json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

        if rv.status_code != expected_code:
            print("Mismatch data for resource PUT %s: %s" % (resource_name, rv.data))

        self.assertEqual(rv.status_code, expected_code)
        data = rv.data
        parsed = py_json.loads(data.decode("utf-8"))
        return parsed

    def assertNotInTeam(self, data, membername):
        for memberData in data["members"]:
            if memberData["name"] == membername:
                self.fail(membername + " found in team: " + data["name"])

    def assertInTeam(self, data, membername):
        for member_data in data["members"]:
            if member_data["name"] == membername:
                return

        self.fail(membername + " not found in team: " + data["name"])

    def login(self, username, password="password"):
        return self.postJsonResponse(Signin, data=dict(username=username, password=password))


class TestCSRFFailure(ApiTestCase):
    def test_csrf_failure(self):
        self.login(READ_ACCESS_USER)

        # Make sure a simple post call succeeds.
        self.putJsonResponse(User, data=dict(password="newpasswordiscool"))

        # Change the session's CSRF token.
        self.setCsrfToken("someinvalidtoken")

        # Verify that the call now fails.
        self.putJsonResponse(
            User, data=dict(password="newpasswordiscool"), expected_code=403, explicit_csrf="foobar"
        )

    def test_csrf_failure_empty_token(self):
        self.login(READ_ACCESS_USER)

        # Change the session's CSRF token to be empty.
        self.setCsrfToken("")

        # Verify that the call now fails.
        self.putJsonResponse(
            User, data=dict(password="newpasswordiscool"), expected_code=403, explicit_csrf="foobar"
        )

    def test_csrf_failure_missing_token(self):
        self.login(READ_ACCESS_USER)

        # Make sure a simple post call without a token at all fails.
        self.putJsonResponse(
            User, data=dict(password="newpasswordiscool"), skip_csrf=True, expected_code=403
        )

        # Change the session's CSRF token to be empty.
        self.setCsrfToken("")

        # Verify that the call still fails.
        self.putJsonResponse(
            User,
            data=dict(password="newpasswordiscool"),
            skip_csrf=True,
            expected_code=403,
            explicit_csrf="foobar",
        )


class TestDiscovery(ApiTestCase):
    def test_discovery(self):
        json = self.getJsonResponse(DiscoveryResource)
        assert "paths" in json


class TestErrorDescription(ApiTestCase):
    def test_get_error(self):
        json = self.getJsonResponse(Error, params=dict(error_type="not_found"))
        assert json["title"] == "not_found"
        assert "type" in json
        assert "description" in json


class TestPlans(ApiTestCase):
    def test_plans(self):
        json = self.getJsonResponse(ListPlans)
        found = set([])
        for method_info in json["plans"]:
            found.add(method_info["stripeId"])

        assert "free" in found


class TestLoggedInUser(ApiTestCase):
    def test_guest(self):
        self.getJsonResponse(User, expected_code=401)

    def test_user(self):
        self.login(READ_ACCESS_USER)
        json = self.getJsonResponse(User)
        assert json["anonymous"] == False
        assert json["username"] == READ_ACCESS_USER


class TestUserStarredRepositoryList(ApiTestCase):
    def test_get_stars_guest(self):
        self.getJsonResponse(StarredRepositoryList, expected_code=401)

    def test_get_stars_user(self):
        self.login(READ_ACCESS_USER)

        # Queries: Base + the list query
        with assert_query_count(BASE_LOGGEDIN_QUERY_COUNT + 1):
            self.getJsonResponse(StarredRepositoryList, expected_code=200)

    def test_star_repo_guest(self):
        self.postJsonResponse(
            StarredRepositoryList,
            data={"namespace": "public", "repository": "publicrepo",},
            expected_code=401,
        )

    def test_star_and_unstar_repo_user(self):
        self.login(READ_ACCESS_USER)

        # Queries: Base + the list query
        with assert_query_count(BASE_LOGGEDIN_QUERY_COUNT + 1):
            json = self.getJsonResponse(StarredRepositoryList)
            assert json["repositories"] == []

        json = self.postJsonResponse(
            StarredRepositoryList,
            data={"namespace": "public", "repository": "publicrepo",},
            expected_code=201,
        )
        assert json["namespace"] == "public"
        assert json["repository"] == "publicrepo"

        self.deleteEmptyResponse(
            StarredRepository, params=dict(repository="public/publicrepo"), expected_code=204
        )

        json = self.getJsonResponse(StarredRepositoryList)
        assert json["repositories"] == []


class TestUserNotification(ApiTestCase):
    def test_get(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(UserNotificationList)

        # Make sure each notification can be retrieved.
        for notification in json["notifications"]:
            njson = self.getJsonResponse(UserNotification, params=dict(uuid=notification["id"]))
            self.assertEqual(notification["id"], njson["id"])

        # Update a notification.
        assert json["notifications"]
        assert not json["notifications"][0]["dismissed"]

        notification = json["notifications"][0]
        pjson = self.putJsonResponse(
            UserNotification, params=dict(uuid=notification["id"]), data=dict(dismissed=True)
        )

        self.assertEqual(True, pjson["dismissed"])

    def test_org_notifications(self):
        # Create a notification on the organization.
        org = model.user.get_user_or_org(ORGANIZATION)
        model.notification.create_notification("test_notification", org, {"org": "notification"})

        # Ensure it is visible to the org admin.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(UserNotificationList)
        notification = json["notifications"][0]

        self.assertEqual(notification["kind"], "test_notification")
        self.assertEqual(notification["metadata"], {"org": "notification"})

        # Ensure it is not visible to an org member.
        self.login(READ_ACCESS_USER)
        json = self.getJsonResponse(UserNotificationList)
        self.assertEqual(0, len(json["notifications"]))


class TestGetUserPrivateAllowed(ApiTestCase):
    def test_nonallowed(self):
        self.login(READ_ACCESS_USER)
        json = self.getJsonResponse(PrivateRepositories)
        assert json["privateCount"] == 0
        assert not json["privateAllowed"]

    def test_allowed(self):
        self.login(ADMIN_ACCESS_USER)

        # Change the subscription of the namespace.
        self.putJsonResponse(UserPlan, data=dict(plan="personal-2018"))

        json = self.getJsonResponse(PrivateRepositories)
        assert json["privateCount"] >= 6
        assert not json["privateAllowed"]

        # Change the subscription of the namespace.
        self.putJsonResponse(UserPlan, data=dict(plan="bus-large-2018"))

        json = self.getJsonResponse(PrivateRepositories)
        assert json["privateAllowed"]


class TestConvertToOrganization(ApiTestCase):
    def test_sameadminuser(self):
        self.login(READ_ACCESS_USER)
        json = self.postJsonResponse(
            ConvertToOrganization,
            data={"adminUser": READ_ACCESS_USER, "adminPassword": "password", "plan": "free"},
            expected_code=400,
        )

        self.assertEqual("The admin user is not valid", json["detail"])

    def test_sameadminuser_by_email(self):
        self.login(READ_ACCESS_USER)
        json = self.postJsonResponse(
            ConvertToOrganization,
            data={"adminUser": "no1@thanks.com", "adminPassword": "password", "plan": "free"},
            expected_code=400,
        )

        self.assertEqual("The admin user is not valid", json["detail"])

    def test_invalidadminuser(self):
        self.login(READ_ACCESS_USER)
        json = self.postJsonResponse(
            ConvertToOrganization,
            data={"adminUser": "unknownuser", "adminPassword": "password", "plan": "free"},
            expected_code=400,
        )

        self.assertEqual("The admin user credentials are not valid", json["detail"])

    def test_invalidadminpassword(self):
        self.login(READ_ACCESS_USER)
        json = self.postJsonResponse(
            ConvertToOrganization,
            data={"adminUser": ADMIN_ACCESS_USER, "adminPassword": "invalidpass", "plan": "free"},
            expected_code=400,
        )

        self.assertEqual("The admin user credentials are not valid", json["detail"])

    def test_convert(self):
        self.login(READ_ACCESS_USER)

        # Add at least one permission for the read-user.
        read_user = model.user.get_user(READ_ACCESS_USER)
        simple_repo = model.repository.get_repository(ADMIN_ACCESS_USER, "simple")
        read_role = database.Role.get(name="read")

        database.RepositoryPermission.create(user=read_user, repository=simple_repo, role=read_role)

        # Convert the read user into an organization.
        json = self.postJsonResponse(
            ConvertToOrganization,
            data={"adminUser": ADMIN_ACCESS_USER, "adminPassword": "password", "plan": "free"},
        )

        self.assertEqual(True, json["success"])

        # Verify the organization exists.
        organization = model.organization.get_organization(READ_ACCESS_USER)
        assert organization is not None

        # Verify the admin user is the org's admin.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(Organization, params=dict(orgname=READ_ACCESS_USER))

        self.assertEqual(READ_ACCESS_USER, json["name"])
        self.assertEqual(True, json["is_admin"])

        # Verify the now-org has no permissions.
        count = (
            database.RepositoryPermission.select()
            .where(database.RepositoryPermission.user == organization)
            .count()
        )
        self.assertEqual(0, count)

    def test_convert_via_email(self):
        self.login(READ_ACCESS_USER)
        json = self.postJsonResponse(
            ConvertToOrganization,
            data={"adminUser": ADMIN_ACCESS_EMAIL, "adminPassword": "password", "plan": "free"},
        )

        self.assertEqual(True, json["success"])

        # Verify the organization exists.
        organization = model.organization.get_organization(READ_ACCESS_USER)
        assert organization is not None

        # Verify the admin user is the org's admin.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(Organization, params=dict(orgname=READ_ACCESS_USER))

        self.assertEqual(READ_ACCESS_USER, json["name"])
        self.assertEqual(True, json["is_admin"])


class TestChangeUserDetails(ApiTestCase):
    def test_changepassword(self):
        self.login(READ_ACCESS_USER)
        self.putJsonResponse(User, data=dict(password="newpasswordiscool"))
        self.login(READ_ACCESS_USER, password="newpasswordiscool")

    def test_changepassword_unicode(self):
        self.login(READ_ACCESS_USER)
        self.putJsonResponse(User, data=dict(password="someunicode北京市pass"))
        self.login(READ_ACCESS_USER, password="someunicode北京市pass")

    def test_changeeemail(self):
        self.login(READ_ACCESS_USER)

        self.putJsonResponse(User, data=dict(email="test+foo@devtable.com"))

    def test_changeinvoiceemail(self):
        self.login(READ_ACCESS_USER)

        json = self.putJsonResponse(User, data=dict(invoice_email=True))
        self.assertEqual(True, json["invoice_email"])

        json = self.putJsonResponse(User, data=dict(invoice_email=False))
        self.assertEqual(False, json["invoice_email"])

    def test_changeusername_temp(self):
        self.login(READ_ACCESS_USER)
        user = model.user.get_user(READ_ACCESS_USER)
        model.user.create_user_prompt(user, "confirm_username")
        self.assertTrue(model.user.has_user_prompt(user, "confirm_username"))

        # Add a robot under the user's namespace.
        model.user.create_robot("somebot", user)

        # Rename the user.
        json = self.putJsonResponse(User, data=dict(username="someotherusername"))

        # Ensure the username was changed.
        self.assertEqual("someotherusername", json["username"])
        self.assertFalse(model.user.has_user_prompt(user, "confirm_username"))

        # Ensure the robot was changed.
        self.assertIsNone(model.user.get_user(READ_ACCESS_USER + "+somebot"))
        self.assertIsNotNone(model.user.get_user("someotherusername+somebot"))

    def test_changeusername_temp_samename(self):
        self.login(READ_ACCESS_USER)
        user = model.user.get_user(READ_ACCESS_USER)
        model.user.create_user_prompt(user, "confirm_username")
        self.assertTrue(model.user.has_user_prompt(user, "confirm_username"))

        json = self.putJsonResponse(User, data=dict(username=READ_ACCESS_USER))

        # Ensure the username was not changed but they are no longer temporarily named.
        self.assertEqual(READ_ACCESS_USER, json["username"])
        self.assertFalse(model.user.has_user_prompt(user, "confirm_username"))

    def test_changeusername_notallowed(self):
        with self.toggleFeature("USER_RENAME", False):
            self.login(ADMIN_ACCESS_USER)
            user = model.user.get_user(ADMIN_ACCESS_USER)
            self.assertFalse(model.user.has_user_prompt(user, "confirm_username"))

            json = self.putJsonResponse(User, data=dict(username="someotherusername"))
            self.assertEqual(ADMIN_ACCESS_USER, json["username"])
            self.assertTrue("prompts" in json)

            self.assertIsNone(model.user.get_user("someotherusername"))
            self.assertIsNotNone(model.user.get_user(ADMIN_ACCESS_USER))

    def test_changeusername_allowed(self):
        with self.toggleFeature("USER_RENAME", True):
            self.login(ADMIN_ACCESS_USER)
            user = model.user.get_user(ADMIN_ACCESS_USER)
            self.assertFalse(model.user.has_user_prompt(user, "confirm_username"))

            json = self.putJsonResponse(User, data=dict(username="someotherusername"))
            self.assertEqual("someotherusername", json["username"])
            self.assertTrue("prompts" in json)

            self.assertIsNotNone(model.user.get_user("someotherusername"))
            self.assertIsNone(model.user.get_user(ADMIN_ACCESS_USER))

    def test_changeusername_already_used(self):
        self.login(READ_ACCESS_USER)
        user = model.user.get_user(READ_ACCESS_USER)
        model.user.create_user_prompt(user, "confirm_username")
        self.assertTrue(model.user.has_user_prompt(user, "confirm_username"))

        # Try to change to a used username.
        self.putJsonResponse(User, data=dict(username=ADMIN_ACCESS_USER), expected_code=400)

        # Change to a new username.
        self.putJsonResponse(User, data=dict(username="unusedusername"))


class TestCreateNewUser(ApiTestCase):
    def test_existingusername(self):
        json = self.postJsonResponse(
            User,
            data=dict(username=READ_ACCESS_USER, password="password", email="test@example.com"),
            expected_code=400,
        )

        self.assertEqual("The username already exists", json["detail"])

    def test_trycreatetooshort(self):
        json = self.postJsonResponse(
            User,
            data=dict(username="a", password="password", email="test@example.com"),
            expected_code=400,
        )

        self.assertEqual(
            "Invalid namespace a: Namespace must be between 2 and 255 characters in length",
            json["detail"],
        )

    def test_trycreateregexmismatch(self):
        json = self.postJsonResponse(
            User,
            data=dict(username="auserName", password="password", email="test@example.com"),
            expected_code=400,
        )

        self.assertEqual(
            "Invalid namespace auserName: Namespace must match expression ^([a-z0-9]+(?:[._-][a-z0-9]+)*)$",
            json["detail"],
        )

    def test_createuser(self):
        data = self.postJsonResponse(User, data=NEW_USER_DETAILS, expected_code=200)
        self.assertEqual(True, data["awaiting_verification"])

    def test_createuser_captcha(self):
        @urlmatch(netloc=r"(.*\.)?google.com", path="/recaptcha/api/siteverify")
        def captcha_endpoint(url, request):
            if url.query.find("response=somecode") > 0:
                return {"status_code": 200, "content": py_json.dumps({"success": True})}
            else:
                return {"status_code": 400, "content": py_json.dumps({"success": False})}

        with HTTMock(captcha_endpoint):
            with self.toggleFeature("RECAPTCHA", True):
                # Try with a missing captcha.
                self.postResponse(User, data=NEW_USER_DETAILS, expected_code=400)

                # Try with an invalid captcha.
                details = dict(NEW_USER_DETAILS)
                details["recaptcha_response"] = "someinvalidcode"
                self.postResponse(User, data=details, expected_code=400)

                # Try with a valid captcha.
                details = dict(NEW_USER_DETAILS)
                details["recaptcha_response"] = "somecode"
                self.postResponse(User, data=details, expected_code=200)

    def test_createuser_withteaminvite(self):
        inviter = model.user.get_user(ADMIN_ACCESS_USER)
        team = model.team.get_organization_team(ORGANIZATION, "owners")
        invite = model.team.add_or_invite_to_team(inviter, team, None, NEW_USER_DETAILS["email"])

        details = {"invite_code": invite.invite_token}
        details.update(NEW_USER_DETAILS)

        data = self.postJsonResponse(User, data=details, expected_code=200)

        # Make sure the user is verified since the email address of the user matches
        # that of the team invite.
        self.assertFalse("awaiting_verification" in data)

        # Make sure the user was not (yet) added to the team.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )
        self.assertNotInTeam(json, NEW_USER_DETAILS["username"])

    def test_createuser_withteaminvite_differentemails(self):
        inviter = model.user.get_user(ADMIN_ACCESS_USER)
        team = model.team.get_organization_team(ORGANIZATION, "owners")
        invite = model.team.add_or_invite_to_team(inviter, team, None, "differentemail@example.com")

        details = {"invite_code": invite.invite_token}
        details.update(NEW_USER_DETAILS)

        data = self.postJsonResponse(User, data=details, expected_code=200)

        # Make sure the user is *not* verified since the email address of the user
        # does not match that of the team invite.
        self.assertTrue(data["awaiting_verification"])

        # Make sure the user was not (yet) added to the team.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )
        self.assertNotInTeam(json, NEW_USER_DETAILS["username"])

    def test_createuser_withmultipleteaminvites(self):
        inviter = model.user.get_user(ADMIN_ACCESS_USER)
        owners_team = model.team.get_organization_team(ORGANIZATION, "owners")
        readers_team = model.team.get_organization_team(ORGANIZATION, "readers")
        other_owners_team = model.team.get_organization_team("library", "owners")

        owners_invite = model.team.add_or_invite_to_team(
            inviter, owners_team, None, NEW_USER_DETAILS["email"]
        )

        readers_invite = model.team.add_or_invite_to_team(
            inviter, readers_team, None, NEW_USER_DETAILS["email"]
        )

        other_owners_invite = model.team.add_or_invite_to_team(
            inviter, other_owners_team, None, NEW_USER_DETAILS["email"]
        )

        # Create the user and ensure they have a verified email address.
        details = {"invite_code": owners_invite.invite_token}
        details.update(NEW_USER_DETAILS)

        data = self.postJsonResponse(User, data=details, expected_code=200)

        # Make sure the user is verified since the email address of the user matches
        # that of the team invite.
        self.assertFalse("awaiting_verification" in data)

        # Make sure the user was not (yet) added to the teams.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )
        self.assertNotInTeam(json, NEW_USER_DETAILS["username"])

        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="readers")
        )
        self.assertNotInTeam(json, NEW_USER_DETAILS["username"])

        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname="library", teamname="owners")
        )
        self.assertNotInTeam(json, NEW_USER_DETAILS["username"])

        # Accept the first invitation.
        self.login(NEW_USER_DETAILS["username"])
        self.putJsonResponse(TeamMemberInvite, params=dict(code=owners_invite.invite_token))

        # Make sure both codes are now invalid.
        self.putResponse(
            TeamMemberInvite, params=dict(code=owners_invite.invite_token), expected_code=400
        )

        self.putResponse(
            TeamMemberInvite, params=dict(code=readers_invite.invite_token), expected_code=400
        )

        # Make sure the user is now in the two invited teams under the organization, but not
        # in the other org's team.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )
        self.assertInTeam(json, NEW_USER_DETAILS["username"])

        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="readers")
        )
        self.assertInTeam(json, NEW_USER_DETAILS["username"])

        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname="library", teamname="owners")
        )
        self.assertNotInTeam(json, NEW_USER_DETAILS["username"])

        # Accept the second invitation.
        self.login(NEW_USER_DETAILS["username"])
        self.putJsonResponse(TeamMemberInvite, params=dict(code=other_owners_invite.invite_token))

        # Make sure the user was added to the other organization.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname="library", teamname="owners")
        )
        self.assertInTeam(json, NEW_USER_DETAILS["username"])

        # Make sure the invitation codes are now invalid.
        self.putResponse(
            TeamMemberInvite, params=dict(code=other_owners_invite.invite_token), expected_code=400
        )


class TestDeleteNamespace(ApiTestCase):
    def test_deletenamespaces(self):
        self.login(ADMIN_ACCESS_USER)

        # Try to first delete the user. Since they are the sole admin of three orgs, it should fail.
        with check_transitive_modifications():
            self.deleteResponse(User, expected_code=400)

        # Delete the three orgs, checking in between.
        with check_transitive_modifications():
            self.deleteEmptyResponse(
                Organization, params=dict(orgname=ORGANIZATION), expected_code=204
            )
            self.deleteResponse(User, expected_code=400)  # Should still fail.
            self.deleteEmptyResponse(
                Organization, params=dict(orgname="library"), expected_code=204
            )
            self.deleteResponse(User, expected_code=400)  # Should still fail.
            self.deleteEmptyResponse(Organization, params=dict(orgname="titi"), expected_code=204)

        # Add some queue items for the user.
        notification_queue.put([ADMIN_ACCESS_USER, "somerepo", "somename"], "{}")
        dockerfile_build_queue.put([ADMIN_ACCESS_USER, "anotherrepo"], "{}")

        # Now delete the user.
        with check_transitive_modifications():
            self.deleteEmptyResponse(User, expected_code=204)

        # Ensure the queue items are gone.
        self.assertIsNone(notification_queue.get())
        self.assertIsNone(dockerfile_build_queue.get())

    def test_delete_federateduser(self):
        self.login(PUBLIC_USER)

        # Add some federated logins.
        user = model.user.get_user(PUBLIC_USER)
        model.user.attach_federated_login(user, "github", "something", {})

        with check_transitive_modifications():
            self.deleteEmptyResponse(User, expected_code=204)

    def test_delete_prompted_user(self):
        self.login("randomuser")
        with check_transitive_modifications():
            self.deleteEmptyResponse(User, expected_code=204)


class TestSignin(ApiTestCase):
    def test_signin_unicode(self):
        self.postResponse(
            Signin,
            data=dict(username="\xe5\x8c\x97\xe4\xba\xac\xe5\xb8\x82", password="password"),
            expected_code=403,
        )

    def test_signin_invitecode(self):
        # Create a new user (unverified)
        data = self.postJsonResponse(User, data=NEW_USER_DETAILS, expected_code=200)
        self.assertTrue(data["awaiting_verification"])

        # Try to sign in without an invite code.
        data = self.postJsonResponse(Signin, data=NEW_USER_DETAILS, expected_code=403)
        self.assertTrue(data["needsEmailVerification"])

        # Try to sign in with an invalid invite code.
        details = {"invite_code": "someinvalidcode"}
        details.update(NEW_USER_DETAILS)

        data = self.postJsonResponse(Signin, data=details, expected_code=403)
        self.assertTrue(data["needsEmailVerification"])

        # Sign in with an invite code and ensure the user becomes verified.
        inviter = model.user.get_user(ADMIN_ACCESS_USER)
        team = model.team.get_organization_team(ORGANIZATION, "owners")
        invite = model.team.add_or_invite_to_team(inviter, team, None, NEW_USER_DETAILS["email"])

        details = {"invite_code": invite.invite_token}
        details.update(NEW_USER_DETAILS)

        data = self.postJsonResponse(Signin, data=details, expected_code=200)
        self.assertFalse("needsEmailVerification" in data)


class TestSignout(ApiTestCase):
    def test_signout(self):
        self.login(READ_ACCESS_USER)

        read_user = model.user.get_user(READ_ACCESS_USER)
        json = self.getJsonResponse(User)
        assert json["username"] == READ_ACCESS_USER

        self.postResponse(Signout)

        # Make sure we're now signed out.
        self.getJsonResponse(User, expected_code=401)

        # Make sure the user's UUID has rotated, to ensure sessions are no longer valid.
        read_user_again = model.user.get_user(READ_ACCESS_USER)
        self.assertNotEqual(read_user.uuid, read_user_again.uuid)


class TestConductSearch(ApiTestCase):
    def test_noaccess(self):
        self.login(NO_ACCESS_USER)

        json = self.getJsonResponse(ConductSearch, params=dict(query="read"))

        self.assertEqual(0, len(json["results"]))

        json = self.getJsonResponse(ConductSearch, params=dict(query="owners"))

        self.assertEqual(0, len(json["results"]))

    def test_nouser(self):
        json = self.getJsonResponse(ConductSearch, params=dict(query="read"))

        self.assertEqual(0, len(json["results"]))

        json = self.getJsonResponse(ConductSearch, params=dict(query="public"))

        self.assertEqual(2, len(json["results"]))
        self.assertEqual(json["results"][0]["kind"], "repository")
        self.assertEqual(json["results"][0]["name"], "publicrepo")

        self.assertEqual(json["results"][1]["kind"], "user")
        self.assertEqual(json["results"][1]["name"], "public")

        json = self.getJsonResponse(ConductSearch, params=dict(query="owners"))

        self.assertEqual(0, len(json["results"]))

    def test_orgmember(self):
        self.login(READ_ACCESS_USER)

        json = self.getJsonResponse(ConductSearch, params=dict(query="owners"))

        self.assertEqual(0, len(json["results"]))

        json = self.getJsonResponse(ConductSearch, params=dict(query="readers"))

        self.assertEqual(1, len(json["results"]))
        self.assertEqual(json["results"][0]["kind"], "team")
        self.assertEqual(json["results"][0]["name"], "readers")

    def test_orgadmin(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(ConductSearch, params=dict(query="owners"))

        self.assertEqual(4, len(json["results"]))
        self.assertEqual(json["results"][0]["kind"], "team")
        self.assertEqual(json["results"][0]["name"], "owners")

        json = self.getJsonResponse(ConductSearch, params=dict(query="readers"))

        self.assertEqual(1, len(json["results"]))
        self.assertEqual(json["results"][0]["kind"], "team")
        self.assertEqual(json["results"][0]["name"], "readers")

    def test_explicit_permission(self):
        self.login("reader")

        json = self.getJsonResponse(ConductSearch, params=dict(query="shared"))

        self.assertEqual(1, len(json["results"]))
        self.assertEqual(json["results"][0]["kind"], "repository")
        self.assertEqual(json["results"][0]["name"], "shared")

    def test_full_text(self):
        self.login(ADMIN_ACCESS_USER)

        # Make sure the repository is found via `full` and `text search`.
        json = self.getJsonResponse(ConductSearch, params=dict(query="full"))
        self.assertEqual(1, len(json["results"]))
        self.assertEqual(json["results"][0]["kind"], "repository")
        self.assertEqual(json["results"][0]["name"], "text-full-repo")

        json = self.getJsonResponse(ConductSearch, params=dict(query="text search"))
        self.assertEqual(1, len(json["results"]))
        self.assertEqual(json["results"][0]["kind"], "repository")
        self.assertEqual(json["results"][0]["name"], "text-full-repo")


class TestGetMatchingEntities(ApiTestCase):
    def test_simple_lookup(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            EntitySearch,
            params=dict(prefix=ADMIN_ACCESS_USER, namespace=ORGANIZATION, includeTeams="true"),
        )
        self.assertEqual(1, len(json["results"]))

    def test_simple_lookup_noorg(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(EntitySearch, params=dict(prefix=ADMIN_ACCESS_USER))
        self.assertEqual(1, len(json["results"]))

    def test_unicode_search(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            EntitySearch, params=dict(prefix="北京市", namespace=ORGANIZATION, includeTeams="true")
        )
        self.assertEqual(0, len(json["results"]))

    def test_notinorg(self):
        self.login(NO_ACCESS_USER)

        json = self.getJsonResponse(
            EntitySearch, params=dict(prefix="o", namespace=ORGANIZATION, includeTeams="true")
        )

        names = set([r["name"] for r in json["results"]])
        assert "outsideorg" in names
        assert not "owners" in names

    def test_prefix_disabled(self):
        with patch("features.PARTIAL_USER_AUTOCOMPLETE", False):
            self.login(NO_ACCESS_USER)

            json = self.getJsonResponse(
                EntitySearch, params=dict(prefix="o", namespace=ORGANIZATION, includeTeams="true")
            )

            names = set([r["name"] for r in json["results"]])
            assert not "outsideorg" in names
            assert not "owners" in names

            json = self.getJsonResponse(
                EntitySearch,
                params=dict(prefix="outsideorg", namespace=ORGANIZATION, includeTeams="true"),
            )
            names = set([r["name"] for r in json["results"]])
            assert "outsideorg" in names
            assert not "owners" in names

    def test_inorg(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            EntitySearch, params=dict(prefix="o", namespace=ORGANIZATION, includeTeams="true")
        )

        names = set([r["name"] for r in json["results"]])
        assert "outsideorg" in names
        assert "owners" in names

    def test_inorg_withorgs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            EntitySearch,
            params=dict(prefix=ORGANIZATION[0], namespace=ORGANIZATION, includeOrgs="true"),
        )

        names = set([r["name"] for r in json["results"]])
        assert ORGANIZATION in names


class TestCreateOrganization(ApiTestCase):
    def test_existinguser(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            OrganizationList,
            data=dict(name=ADMIN_ACCESS_USER, email="testorg@example.com"),
            expected_code=400,
        )

        self.assertEqual("A user or organization with this name already exists", json["detail"])

    def test_existingorg(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            OrganizationList,
            data=dict(name=ORGANIZATION, email="testorg@example.com"),
            expected_code=400,
        )

        self.assertEqual("A user or organization with this name already exists", json["detail"])

    def test_createorg(self):
        self.login(ADMIN_ACCESS_USER)

        data = self.postResponse(
            OrganizationList,
            data=dict(name="neworg", email="testorg@example.com"),
            expected_code=201,
        )

        self.assertEqual(b'"Created"', data.strip())

        # Ensure the org was created.
        organization = model.organization.get_organization("neworg")
        assert organization is not None

        # Verify the admin user is the org's admin.
        json = self.getJsonResponse(Organization, params=dict(orgname="neworg"))
        self.assertEqual("neworg", json["name"])
        self.assertEqual(True, json["is_admin"])

    def test_createorg_viaoauth(self):
        # Attempt with no auth.
        self.postResponse(
            OrganizationList,
            data=dict(name="neworg", email="testorg@example.com"),
            expected_code=401,
        )

        # Attempt with auth with invalid scope.
        dt_user = model.user.get_user(ADMIN_ACCESS_USER)
        token, code = model.oauth.create_access_token_for_testing(dt_user, "deadbeef", "repo:read")
        self.postResponse(
            OrganizationList,
            data=dict(name="neworg", email="testorg@example.com"),
            headers=dict(Authorization="Bearer " + code),
            expected_code=403,
        )

        # Create OAuth token with user:admin scope.
        token, code = model.oauth.create_access_token_for_testing(
            dt_user, "deadbeef", "user:admin", access_token="d" * 40
        )
        data = self.postResponse(
            OrganizationList,
            data=dict(name="neworg", email="testorg@example.com"),
            headers=dict(Authorization="Bearer " + code),
            expected_code=201,
        )

        self.assertEqual(b'"Created"', data.strip())


class TestGetOrganization(ApiTestCase):
    def test_unknownorg(self):
        self.login(ADMIN_ACCESS_USER)
        self.getResponse(Organization, params=dict(orgname="notvalid"), expected_code=404)

    def test_cannotaccess(self):
        self.login(NO_ACCESS_USER)
        self.getResponse(Organization, params=dict(orgname=ORGANIZATION), expected_code=200)

    def test_getorganization(self):
        self.login(READ_ACCESS_USER)
        json = self.getJsonResponse(Organization, params=dict(orgname=ORGANIZATION))

        self.assertEqual(ORGANIZATION, json["name"])
        self.assertEqual(False, json["is_admin"])

    def test_getorganization_asadmin(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(Organization, params=dict(orgname=ORGANIZATION))

        self.assertEqual(ORGANIZATION, json["name"])
        self.assertEqual(True, json["is_admin"])


class TestChangeOrganizationDetails(ApiTestCase):
    def test_changeinvoiceemail(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.putJsonResponse(
            Organization, params=dict(orgname=ORGANIZATION), data=dict(invoice_email=True)
        )

        self.assertEqual(True, json["invoice_email"])

        json = self.putJsonResponse(
            Organization, params=dict(orgname=ORGANIZATION), data=dict(invoice_email=False)
        )
        self.assertEqual(False, json["invoice_email"])

    def test_changemail(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.putJsonResponse(
            Organization, params=dict(orgname=ORGANIZATION), data=dict(email="newemail@example.com")
        )

        self.assertEqual("newemail@example.com", json["email"])


class TestGetOrganizationPrototypes(ApiTestCase):
    def test_getprototypes(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(PermissionPrototypeList, params=dict(orgname=ORGANIZATION))

        assert len(json["prototypes"]) > 0


class TestCreateOrganizationPrototypes(ApiTestCase):
    def test_invaliduser(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            PermissionPrototypeList,
            params=dict(orgname=ORGANIZATION),
            data=dict(
                activating_user={"name": "unknownuser"},
                role="read",
                delegate={"kind": "team", "name": "owners"},
            ),
            expected_code=400,
        )

        self.assertEqual("Unknown activating user", json["detail"])

    def test_missingdelegate(self):
        self.login(ADMIN_ACCESS_USER)

        self.postJsonResponse(
            PermissionPrototypeList,
            params=dict(orgname=ORGANIZATION),
            data=dict(role="read"),
            expected_code=400,
        )

    def test_createprototype(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            PermissionPrototypeList,
            params=dict(orgname=ORGANIZATION),
            data=dict(role="read", delegate={"kind": "team", "name": "readers"}),
        )

        self.assertEqual("read", json["role"])
        pid = json["id"]

        # Verify the prototype exists.
        json = self.getJsonResponse(PermissionPrototypeList, params=dict(orgname=ORGANIZATION))

        ids = set([p["id"] for p in json["prototypes"]])
        assert pid in ids


class TestDeleteOrganizationPrototypes(ApiTestCase):
    def test_deleteprototype(self):
        self.login(ADMIN_ACCESS_USER)

        # Get the existing prototypes
        json = self.getJsonResponse(PermissionPrototypeList, params=dict(orgname=ORGANIZATION))

        ids = [p["id"] for p in json["prototypes"]]
        pid = ids[0]

        # Delete a prototype.
        self.deleteEmptyResponse(
            PermissionPrototype, params=dict(orgname=ORGANIZATION, prototypeid=pid)
        )

        # Verify the prototype no longer exists.
        json = self.getJsonResponse(PermissionPrototypeList, params=dict(orgname=ORGANIZATION))

        newids = [p["id"] for p in json["prototypes"]]
        assert not pid in newids


class TestUpdateOrganizationPrototypes(ApiTestCase):
    def test_updateprototype(self):
        self.login(ADMIN_ACCESS_USER)

        # Get the existing prototypes
        json = self.getJsonResponse(PermissionPrototypeList, params=dict(orgname=ORGANIZATION))

        ids = [p["id"] for p in json["prototypes"]]
        pid = ids[0]

        # Update a prototype.
        json = self.putJsonResponse(
            PermissionPrototype,
            params=dict(orgname=ORGANIZATION, prototypeid=pid),
            data=dict(role="admin"),
        )

        self.assertEqual("admin", json["role"])


class TestGetOrganizationMembers(ApiTestCase):
    def test_getmembers(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(OrganizationMemberList, params=dict(orgname=ORGANIZATION))

        membernames = [member["name"] for member in json["members"]]
        assert ADMIN_ACCESS_USER in membernames
        assert READ_ACCESS_USER in membernames
        assert not NO_ACCESS_USER in membernames

        for member in json["members"]:
            membername = member["name"]
            response = self.getJsonResponse(
                OrganizationMember, params=dict(orgname=ORGANIZATION, membername=membername)
            )

            self.assertEqual(member, response)


class TestRemoveOrganizationMember(ApiTestCase):
    def test_try_remove_only_admin(self):
        self.login(ADMIN_ACCESS_USER)

        self.deleteResponse(
            OrganizationMember,
            params=dict(orgname=ORGANIZATION, membername=ADMIN_ACCESS_USER),
            expected_code=400,
        )

    def test_remove_member(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(OrganizationMemberList, params=dict(orgname=ORGANIZATION))

        membernames = [member["name"] for member in json["members"]]
        assert ADMIN_ACCESS_USER in membernames
        assert READ_ACCESS_USER in membernames

        self.deleteEmptyResponse(
            OrganizationMember, params=dict(orgname=ORGANIZATION, membername=READ_ACCESS_USER)
        )

        json = self.getJsonResponse(OrganizationMemberList, params=dict(orgname=ORGANIZATION))

        membernames = [member["name"] for member in json["members"]]
        assert ADMIN_ACCESS_USER in membernames
        assert not READ_ACCESS_USER in membernames

    def test_remove_member_repo_permission(self):
        self.login(ADMIN_ACCESS_USER)

        # Add read user as a direct permission on the admin user's repo.
        model.permission.set_user_repo_permission(
            READ_ACCESS_USER, ADMIN_ACCESS_USER, "simple", "read"
        )

        # Verify the user has a permission on the admin user's repo.
        admin_perms = [
            p.user.username for p in model.user.get_all_repo_users(ADMIN_ACCESS_USER, "simple")
        ]
        assert READ_ACCESS_USER in admin_perms

        # Add read user as a direct permission on the org repo.
        model.permission.set_user_repo_permission(READ_ACCESS_USER, ORGANIZATION, ORG_REPO, "read")

        # Verify the user has a permission on the org repo.
        org_perms = [p.user.username for p in model.user.get_all_repo_users(ORGANIZATION, ORG_REPO)]
        assert READ_ACCESS_USER in org_perms

        # Remove the user from the org.
        self.deleteEmptyResponse(
            OrganizationMember, params=dict(orgname=ORGANIZATION, membername=READ_ACCESS_USER)
        )

        # Verify that the user's permission on the org repo is gone, but it is still
        # present on the other repo.
        org_perms = [p.user.username for p in model.user.get_all_repo_users(ORGANIZATION, ORG_REPO)]
        assert not READ_ACCESS_USER in org_perms

        admin_perms = [
            p.user.username for p in model.user.get_all_repo_users(ADMIN_ACCESS_USER, "simple")
        ]
        assert READ_ACCESS_USER in admin_perms


class TestGetOrganizationPrivateAllowed(ApiTestCase):
    def test_existingorg(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(OrgPrivateRepositories, params=dict(orgname=ORGANIZATION))

        self.assertEqual(True, json["privateAllowed"])
        assert not "reposAllowed" in json

    def test_neworg(self):
        self.login(ADMIN_ACCESS_USER)

        data = self.postResponse(
            OrganizationList, data=dict(name="neworg", email="test@example.com"), expected_code=201
        )

        json = self.getJsonResponse(OrgPrivateRepositories, params=dict(orgname="neworg"))

        self.assertEqual(False, json["privateAllowed"])


class TestUpdateOrganizationTeam(ApiTestCase):
    def test_updateexisting(self):
        self.login(ADMIN_ACCESS_USER)

        data = self.putJsonResponse(
            OrganizationTeam,
            params=dict(orgname=ORGANIZATION, teamname="readers"),
            data=dict(description="My cool team", role="creator"),
        )

        self.assertEqual("My cool team", data["description"])
        self.assertEqual("creator", data["role"])

    def test_attemptchangeroleonowners(self):
        self.login(ADMIN_ACCESS_USER)

        self.putJsonResponse(
            OrganizationTeam,
            params=dict(orgname=ORGANIZATION, teamname="owners"),
            data=dict(role="creator"),
            expected_code=400,
        )

    def test_createnewteam(self):
        self.login(ADMIN_ACCESS_USER)

        data = self.putJsonResponse(
            OrganizationTeam,
            params=dict(orgname=ORGANIZATION, teamname="newteam"),
            data=dict(description="My cool team", role="member"),
        )

        self.assertEqual("My cool team", data["description"])
        self.assertEqual("member", data["role"])

        # Verify the team was created.
        json = self.getJsonResponse(Organization, params=dict(orgname=ORGANIZATION))
        assert "newteam" in json["teams"]


class TestDeleteOrganizationTeam(ApiTestCase):
    def test_deleteteam(self):
        self.login(ADMIN_ACCESS_USER)

        self.deleteEmptyResponse(
            OrganizationTeam, params=dict(orgname=ORGANIZATION, teamname="readers")
        )

        # Make sure the team was deleted
        json = self.getJsonResponse(Organization, params=dict(orgname=ORGANIZATION))
        assert not "readers" in json["teams"]

    def test_attemptdeleteowners(self):
        self.login(ADMIN_ACCESS_USER)

        resp = self.deleteResponse(
            OrganizationTeam,
            params=dict(orgname=ORGANIZATION, teamname="owners"),
            expected_code=400,
        )
        data = py_json.loads(resp)
        msg = (
            "Deleting team 'owners' would remove admin ability for user "
            + "'devtable' in organization 'buynlarge'"
        )
        self.assertEqual(msg, data["message"])


class TestTeamPermissions(ApiTestCase):
    def test_team_permissions(self):
        self.login(ADMIN_ACCESS_USER)

        resp = self.getJsonResponse(
            TeamPermissions, params=dict(orgname=ORGANIZATION, teamname="readers")
        )

        self.assertEqual(1, len(resp["permissions"]))


class TestGetOrganizationTeamMembers(ApiTestCase):
    def test_invalidteam(self):
        self.login(ADMIN_ACCESS_USER)

        self.getResponse(
            TeamMemberList,
            params=dict(orgname=ORGANIZATION, teamname="notvalid"),
            expected_code=404,
        )

    def test_getmembers(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="readers")
        )

        self.assertInTeam(json, READ_ACCESS_USER)


class TestUpdateOrganizationTeamMember(ApiTestCase):
    def test_addmember_alreadyteammember(self):
        self.login(ADMIN_ACCESS_USER)

        membername = READ_ACCESS_USER
        self.putResponse(
            TeamMember,
            params=dict(orgname=ORGANIZATION, teamname="readers", membername=membername),
            expected_code=400,
        )

    def test_addmember_orgmember(self):
        self.login(ADMIN_ACCESS_USER)

        membername = READ_ACCESS_USER
        self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="owners", membername=membername)
        )

        # Verify the user was added to the team.
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )

        self.assertInTeam(json, membername)

    def test_addmember_robot(self):
        self.login(ADMIN_ACCESS_USER)

        membername = ORGANIZATION + "+coolrobot"
        self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="readers", membername=membername)
        )

        # Verify the user was added to the team.
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="readers")
        )

        self.assertInTeam(json, membername)

    def test_addmember_invalidrobot(self):
        self.login(ADMIN_ACCESS_USER)

        membername = "freshuser+anotherrobot"
        self.putResponse(
            TeamMember,
            params=dict(orgname=ORGANIZATION, teamname="readers", membername=membername),
            expected_code=400,
        )

    def test_addmember_nonorgmember(self):
        self.login(ADMIN_ACCESS_USER)

        membername = NO_ACCESS_USER
        response = self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="owners", membername=membername)
        )

        self.assertEqual(True, response["invited"])

        # Make sure the user is not (yet) part of the team.
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="readers")
        )

        for member in json["members"]:
            self.assertNotEqual(membername, member["name"])

    def test_updatemembers_syncedteam(self):
        self.login(ADMIN_ACCESS_USER)

        with patch("endpoints.api.team.authentication", AttrDict({"federated_service": "foobar"})):
            # Add the user to a non-synced team, which should succeed.
            self.putJsonResponse(
                TeamMember,
                params=dict(orgname=ORGANIZATION, teamname="owners", membername=READ_ACCESS_USER),
            )

            # Remove the user from the non-synced team, which should succeed.
            self.deleteEmptyResponse(
                TeamMember,
                params=dict(orgname=ORGANIZATION, teamname="owners", membername=READ_ACCESS_USER),
            )

            # Attempt to add the user to a synced team, which should fail.
            self.putResponse(
                TeamMember,
                params=dict(orgname=ORGANIZATION, teamname="synced", membername=READ_ACCESS_USER),
                expected_code=400,
            )

            # Attempt to remove the user from the synced team, which should fail.
            self.deleteResponse(
                TeamMember,
                params=dict(orgname=ORGANIZATION, teamname="synced", membername=READ_ACCESS_USER),
                expected_code=400,
            )

            # Add a robot to the synced team, which should succeed.
            self.putJsonResponse(
                TeamMember,
                params=dict(
                    orgname=ORGANIZATION, teamname="synced", membername=ORGANIZATION + "+coolrobot"
                ),
            )

            # Remove the robot from the non-synced team, which should succeed.
            self.deleteEmptyResponse(
                TeamMember,
                params=dict(
                    orgname=ORGANIZATION, teamname="synced", membername=ORGANIZATION + "+coolrobot"
                ),
            )

            # Invite a team member to a non-synced team, which should succeed.
            self.putJsonResponse(
                InviteTeamMember,
                params=dict(
                    orgname=ORGANIZATION, teamname="owners", email="someguy+new@devtable.com"
                ),
            )

            # Attempt to invite a team member to a synced team, which should fail.
            self.putResponse(
                InviteTeamMember,
                params=dict(
                    orgname=ORGANIZATION, teamname="synced", email="someguy+new@devtable.com"
                ),
                expected_code=400,
            )


class TestAcceptTeamMemberInvite(ApiTestCase):
    def test_accept(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the invite.
        membername = NO_ACCESS_USER
        response = self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="owners", membername=membername)
        )

        self.assertEqual(True, response["invited"])

        # Login as the user.
        self.login(membername)

        # Accept the invite.
        user = model.user.get_user(membername)
        invites = list(model.team.lookup_team_invites(user))
        self.assertEqual(1, len(invites))

        self.putJsonResponse(TeamMemberInvite, params=dict(code=invites[0].invite_token))

        # Verify the user is now on the team.
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )

        self.assertInTeam(json, membername)

        # Verify the accept now fails.
        self.putResponse(
            TeamMemberInvite, params=dict(code=invites[0].invite_token), expected_code=400
        )

    def test_accept_via_email(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the invite.
        member = model.user.get_user(NO_ACCESS_USER)
        response = self.putJsonResponse(
            InviteTeamMember,
            params=dict(orgname=ORGANIZATION, teamname="owners", email=member.email),
        )

        self.assertEqual(True, response["invited"])

        # Login as the user.
        self.login(member.username)

        # Accept the invite.
        invites = list(model.team.lookup_team_invites_by_email(member.email))
        self.assertEqual(1, len(invites))

        self.putJsonResponse(TeamMemberInvite, params=dict(code=invites[0].invite_token))

        # Verify the user is now on the team.
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )

        self.assertInTeam(json, member.username)

        # Verify the accept now fails.
        self.putResponse(
            TeamMemberInvite, params=dict(code=invites[0].invite_token), expected_code=400
        )

    def test_accept_invite_different_user(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the invite.
        response = self.putJsonResponse(
            TeamMember,
            params=dict(orgname=ORGANIZATION, teamname="owners", membername=NO_ACCESS_USER),
        )

        self.assertEqual(True, response["invited"])

        # Login as a different user.
        self.login(PUBLIC_USER)

        # Try to accept the invite.
        user = model.user.get_user(NO_ACCESS_USER)
        invites = list(model.team.lookup_team_invites(user))
        self.assertEqual(1, len(invites))

        self.putResponse(
            TeamMemberInvite, params=dict(code=invites[0].invite_token), expected_code=400
        )

        # Ensure the invite is still valid.
        user = model.user.get_user(NO_ACCESS_USER)
        invites = list(model.team.lookup_team_invites(user))
        self.assertEqual(1, len(invites))

        # Ensure the user is *not* a member of the team.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )
        self.assertNotInTeam(json, PUBLIC_USER)

    def test_accept_invite_different_email(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the invite.
        response = self.putJsonResponse(
            InviteTeamMember,
            params=dict(orgname=ORGANIZATION, teamname="owners", email="someemail@example.com"),
        )

        self.assertEqual(True, response["invited"])

        # Login as a different user.
        self.login(PUBLIC_USER)

        # Try to accept the invite.
        invites = list(model.team.lookup_team_invites_by_email("someemail@example.com"))
        self.assertEqual(1, len(invites))

        self.putResponse(
            TeamMemberInvite, params=dict(code=invites[0].invite_token), expected_code=400
        )

        # Ensure the invite is still valid.
        invites = list(model.team.lookup_team_invites_by_email("someemail@example.com"))
        self.assertEqual(1, len(invites))

        # Ensure the user is *not* a member of the team.
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="owners")
        )
        self.assertNotInTeam(json, PUBLIC_USER)


class TestDeclineTeamMemberInvite(ApiTestCase):
    def test_decline_wronguser(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the invite.
        membername = NO_ACCESS_USER
        response = self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="owners", membername=membername)
        )

        self.assertEqual(True, response["invited"])

        # Try to decline the invite.
        user = model.user.get_user(membername)
        invites = list(model.team.lookup_team_invites(user))
        self.assertEqual(1, len(invites))

        self.deleteResponse(
            TeamMemberInvite, params=dict(code=invites[0].invite_token), expected_code=400
        )

    def test_decline(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the invite.
        membername = NO_ACCESS_USER
        response = self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="owners", membername=membername)
        )

        self.assertEqual(True, response["invited"])

        # Login as the user.
        self.login(membername)

        # Decline the invite.
        user = model.user.get_user(membername)
        invites = list(model.team.lookup_team_invites(user))
        self.assertEqual(1, len(invites))

        self.deleteEmptyResponse(TeamMemberInvite, params=dict(code=invites[0].invite_token))

        # Make sure the invite was deleted.
        self.deleteResponse(
            TeamMemberInvite, params=dict(code=invites[0].invite_token), expected_code=400
        )


class TestDeleteOrganizationTeamMember(ApiTestCase):
    def test_deletememberinvite(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the initial member count
        json = self.getJsonResponse(
            TeamMemberList,
            params=dict(orgname=ORGANIZATION, teamname="readers", includePending=True),
        )

        self.assertEqual(len(json["members"]), 3)

        membername = NO_ACCESS_USER
        response = self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="readers", membername=membername)
        )

        self.assertEqual(True, response["invited"])

        # Verify the invite was added.
        json = self.getJsonResponse(
            TeamMemberList,
            params=dict(orgname=ORGANIZATION, teamname="readers", includePending=True),
        )

        self.assertEqual(len(json["members"]), 4)

        # Delete the invite.
        self.deleteEmptyResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="readers", membername=membername)
        )

        # Verify the user was removed from the team.
        json = self.getJsonResponse(
            TeamMemberList,
            params=dict(orgname=ORGANIZATION, teamname="readers", includePending=True),
        )

        self.assertEqual(len(json["members"]), 3)

    def test_deletemember(self):
        self.login(ADMIN_ACCESS_USER)

        self.deleteEmptyResponse(
            TeamMember,
            params=dict(orgname=ORGANIZATION, teamname="readers", membername=READ_ACCESS_USER),
        )

        # Verify the user was removed from the team.
        json = self.getJsonResponse(
            TeamMemberList, params=dict(orgname=ORGANIZATION, teamname="readers")
        )

        self.assertEqual(len(json["members"]), 1)


class TestCreateRepo(ApiTestCase):
    def test_invalidreponame(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            RepositoryList,
            data=dict(repository="some/repo", visibility="public", description=""),
            expected_code=400,
        )

        self.assertEqual("Invalid repository name", json["detail"])

    def test_duplicaterepo(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            RepositoryList,
            data=dict(repository="simple", visibility="public", description=""),
            expected_code=400,
        )

        self.assertEqual("Repository already exists", json["detail"])

    def test_createrepo(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            RepositoryList,
            data=dict(repository="newrepo", visibility="public", description=""),
            expected_code=201,
        )

        self.assertEqual(ADMIN_ACCESS_USER, json["namespace"])
        self.assertEqual("newrepo", json["name"])

    def test_create_app_repo(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            RepositoryList,
            data=dict(
                repository="newrepo", visibility="public", description="", repo_kind="application"
            ),
            expected_code=201,
        )

        self.assertEqual(ADMIN_ACCESS_USER, json["namespace"])
        self.assertEqual("newrepo", json["name"])
        self.assertEqual("application", json["kind"])

    def test_createrepo_underorg(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.postJsonResponse(
            RepositoryList,
            data=dict(
                namespace=ORGANIZATION, repository="newrepo", visibility="private", description=""
            ),
            expected_code=201,
        )

        self.assertEqual(ORGANIZATION, json["namespace"])
        self.assertEqual("newrepo", json["name"])


class TestListRepos(ApiTestCase):
    def test_list_app_repos(self):
        self.login(ADMIN_ACCESS_USER)

        # Create an app repo.
        self.postJsonResponse(
            RepositoryList,
            data=dict(
                repository="newrepo", visibility="public", description="", repo_kind="application"
            ),
            expected_code=201,
        )

        json = self.getJsonResponse(
            RepositoryList,
            params=dict(namespace=ADMIN_ACCESS_USER, public=False, repo_kind="application"),
        )

        self.assertEqual(1, len(json["repositories"]))
        self.assertEqual("application", json["repositories"][0]["kind"])

    def test_listrepos_asguest(self):
        # Queries: Base + the list query
        with assert_query_count(BASE_QUERY_COUNT + 1):
            json = self.getJsonResponse(RepositoryList, params=dict(public=True))
            self.assertEqual(len(json["repositories"]), 1)

    def assertPublicRepos(self, has_extras=False):
        public_user = model.user.get_user("public")

        # Delete all existing repos under the namespace.
        for repo in list(
            RepositoryTable.select().where(RepositoryTable.namespace_user == public_user)
        ):
            model.gc.purge_repository(repo, force=True)

        # Add public repos until we have enough for a few pages.
        required = set()
        for i in range(0, REPOS_PER_PAGE * 3):
            name = "publicrepo%s" % i
            model.repository.create_repository("public", name, public_user, visibility="public")
            required.add(name)

        # Request results until we no longer have any.
        next_page = None
        while True:
            json = self.getJsonResponse(
                RepositoryList, params=dict(public=True, next_page=next_page)
            )
            for repo in json["repositories"]:
                name = repo["name"]
                if name in required:
                    required.remove(name)
                else:
                    self.assertTrue(has_extras, "Could not find name %s in repos created" % name)

            if "next_page" in json:
                self.assertEqual(len(json["repositories"]), REPOS_PER_PAGE)
            else:
                break

            next_page = json["next_page"]

    def test_listrepos_asguest_withpages(self):
        self.assertPublicRepos()

    def test_listrepos_asorgmember_withpages(self):
        self.login(READ_ACCESS_USER)
        self.assertPublicRepos(has_extras=True)

    def test_listrepos_filter(self):
        self.login(READ_ACCESS_USER)
        json = self.getJsonResponse(
            RepositoryList, params=dict(namespace=ORGANIZATION, public=False)
        )

        self.assertGreater(len(json["repositories"]), 0)

        for repo in json["repositories"]:
            self.assertEqual(ORGANIZATION, repo["namespace"])

    def test_listrepos_allparams(self):
        # Add a repository action count entry for one of the org repos.
        repo = model.repository.get_repository(ORGANIZATION, ORG_REPO)
        RepositoryActionCount.create(repository=repo, count=10, date=datetime.datetime.utcnow())

        self.login(ADMIN_ACCESS_USER)

        # Queries: Base + the list query + the popularity and last modified queries + full perms load
        with assert_query_count(BASE_LOGGEDIN_QUERY_COUNT + 5):
            json = self.getJsonResponse(
                RepositoryList,
                params=dict(
                    namespace=ORGANIZATION, public=False, last_modified=True, popularity=True
                ),
            )

        self.assertGreater(len(json["repositories"]), 0)

        for repository in json["repositories"]:
            self.assertEqual(ORGANIZATION, repository["namespace"])
            if repository["name"] == ORG_REPO:
                self.assertGreater(repository["popularity"], 0)

    def test_listrepos_starred_nouser(self):
        self.getResponse(
            RepositoryList,
            params=dict(last_modified=True, popularity=True, starred=True),
            expected_code=400,
        )

    def test_listrepos_starred(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            RepositoryList, params=dict(last_modified=True, popularity=True, starred=True)
        )

        self.assertTrue(len(json["repositories"]) > 0)

        for repo in json["repositories"]:
            self.assertTrue(repo["is_starred"])

    def test_listrepos_asguest_allparams(self):
        json = self.getJsonResponse(
            RepositoryList, params=dict(namespace=ORGANIZATION, public=False, last_modified=True)
        )

        for repo in json["repositories"]:
            self.assertEqual(ORGANIZATION, repo["namespace"])

    def assertRepositoryVisible(self, namespace, name):
        json = self.getJsonResponse(RepositoryList, params=dict(namespace=namespace, public=False))
        self.assertEqual(1, len(json["repositories"]))
        self.assertEqual(name, json["repositories"][0]["name"])

    def assertRepositoryNotVisible(self, namespace, name):
        json = self.getJsonResponse(RepositoryList, params=dict(namespace=namespace, public=False))
        for repo in json["repositories"]:
            self.assertNotEqual(name, repo["name"])

        json = self.getJsonResponse(RepositoryList, params=dict(starred=True))
        for repo in json["repositories"]:
            self.assertNotEqual(name, repo["name"])

    def test_listrepos_starred_filtered(self):
        admin_user = model.user.get_user(ADMIN_ACCESS_USER)
        reader_user = model.user.get_user(READ_ACCESS_USER)

        # Create a new organization.
        new_org = model.organization.create_organization(
            "neworg", "neworg@devtable.com", admin_user
        )
        admin_team = model.team.create_team("admin", new_org, "admin")

        # Add a repository to the organization.
        repo = model.repository.create_repository("neworg", "somerepo", admin_user)

        with self.add_to_team_temporarily(reader_user, admin_team):
            # Star the repository for the user.
            model.repository.star_repository(reader_user, repo)

        # Verify that the user cannot see the repo, since they are no longer allowed to do so.
        self.login(READ_ACCESS_USER)
        self.assertRepositoryNotVisible("neworg", "somerepo")

    @contextmanager
    def add_to_team_temporarily(self, user, team):
        model.team.add_user_to_team(user, team)
        yield
        model.team.remove_user_from_team(
            team.organization.username, team.name, user.username, ADMIN_ACCESS_USER
        )

    def test_listrepos_org_filtered(self):
        admin_user = model.user.get_user(ADMIN_ACCESS_USER)
        reader_user = model.user.get_user(READ_ACCESS_USER)

        # Create a new organization.
        new_org = model.organization.create_organization(
            "neworg", "neworg@devtable.com", admin_user
        )

        admin_team = model.team.create_team("admin", new_org, "admin")
        creator_team = model.team.create_team("creators", new_org, "creator")
        member_team = model.team.create_team("members", new_org, "member")

        # Add a repository to the organization.
        model.repository.create_repository("neworg", "somerepo", admin_user)

        # Verify that the admin user can view it.
        self.login(ADMIN_ACCESS_USER)
        self.assertRepositoryVisible("neworg", "somerepo")

        # Add reader to a creator team under the org and verify they *cannot* see the repository.
        with self.add_to_team_temporarily(reader_user, creator_team):
            self.login(READ_ACCESS_USER)
            self.assertRepositoryNotVisible("neworg", "somerepo")

        # Add reader to a member team under the org and verify they *cannot* see the repository.
        with self.add_to_team_temporarily(reader_user, member_team):
            self.login(READ_ACCESS_USER)
            self.assertRepositoryNotVisible("neworg", "somerepo")

        # Add reader to an admin team under the org and verify they *can* see the repository.
        with self.add_to_team_temporarily(reader_user, admin_team):
            self.login(READ_ACCESS_USER)
            self.assertRepositoryVisible("neworg", "somerepo")

        # Verify that the public user cannot see the repository.
        self.login(PUBLIC_USER)
        self.assertRepositoryNotVisible("neworg", "somerepo")


class TestViewPublicRepository(ApiTestCase):
    def test_normalview(self):
        resp = self.getJsonResponse(Repository, params=dict(repository="public/publicrepo"))
        self.assertFalse("stats" in resp)

    def test_normalview_withstats(self):
        resp = self.getJsonResponse(
            Repository, params=dict(repository="public/publicrepo", includeStats=True)
        )
        self.assertTrue("stats" in resp)

    def test_anon_access_disabled(self):
        import features

        features.ANONYMOUS_ACCESS = False
        try:
            self.getResponse(
                Repository, params=dict(repository="public/publicrepo"), expected_code=401
            )
        finally:
            features.ANONYMOUS_ACCESS = True


class TestUpdateRepo(ApiTestCase):
    SIMPLE_REPO = ADMIN_ACCESS_USER + "/simple"

    def test_updatedescription(self):
        self.login(ADMIN_ACCESS_USER)

        self.putJsonResponse(
            Repository,
            params=dict(repository=self.SIMPLE_REPO),
            data=dict(description="Some cool repo"),
        )

        # Verify the repo description was updated.
        json = self.getJsonResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        self.assertEqual("Some cool repo", json["description"])


class TestChangeRepoVisibility(ApiTestCase):
    SIMPLE_REPO = ADMIN_ACCESS_USER + "/simple"

    def test_trychangevisibility(self):
        self.login(ADMIN_ACCESS_USER)

        # Make public.
        self.postJsonResponse(
            RepositoryVisibility,
            params=dict(repository=self.SIMPLE_REPO),
            data=dict(visibility="public"),
        )

        # Verify the visibility.
        json = self.getJsonResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        self.assertEqual(True, json["is_public"])

        # Change the subscription of the namespace.
        self.putJsonResponse(UserPlan, data=dict(plan="personal-2018"))

        # Try to make private.
        self.postJsonResponse(
            RepositoryVisibility,
            params=dict(repository=self.SIMPLE_REPO),
            data=dict(visibility="private"),
            expected_code=402,
        )

        # Verify the visibility.
        json = self.getJsonResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        self.assertEqual(True, json["is_public"])

    def test_changevisibility(self):
        self.login(ADMIN_ACCESS_USER)

        # Make public.
        self.postJsonResponse(
            RepositoryVisibility,
            params=dict(repository=self.SIMPLE_REPO),
            data=dict(visibility="public"),
        )

        # Verify the visibility.
        json = self.getJsonResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        self.assertEqual(True, json["is_public"])

        # Make private.
        self.postJsonResponse(
            RepositoryVisibility,
            params=dict(repository=self.SIMPLE_REPO),
            data=dict(visibility="private"),
        )

        # Verify the visibility.
        json = self.getJsonResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        self.assertEqual(False, json["is_public"])


class TestDeleteRepository(ApiTestCase):
    SIMPLE_REPO = ADMIN_ACCESS_USER + "/simple"
    COMPLEX_REPO = ADMIN_ACCESS_USER + "/complex"

    def test_deleterepo(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the repo exists.
        self.getResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        # Add a build queue item for the repo.
        dockerfile_build_queue.put([ADMIN_ACCESS_USER, "simple"], "{}")

        # Delete the repository.
        self.deleteEmptyResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        # Ensure the queue item is gone.
        self.assertIsNone(dockerfile_build_queue.get())

        # Verify the repo was deleted.
        self.getResponse(Repository, params=dict(repository=self.SIMPLE_REPO), expected_code=404)

    def test_verify_queue_removal(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the repo exists.
        self.getResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        # Add a build queue item for the repo and another repo.
        dockerfile_build_queue.put([ADMIN_ACCESS_USER, "simple"], "{}", available_after=-1)
        dockerfile_build_queue.put([ADMIN_ACCESS_USER, "anotherrepo"], "{}", available_after=-1)

        # Delete the repository.
        self.deleteEmptyResponse(Repository, params=dict(repository=self.SIMPLE_REPO))

        # Ensure the other queue item is still present.
        self.assertIsNotNone(dockerfile_build_queue.get())

    def test_deleterepo2(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the repo exists.
        self.getResponse(Repository, params=dict(repository=self.COMPLEX_REPO))

        self.deleteEmptyResponse(Repository, params=dict(repository=self.COMPLEX_REPO))

        # Verify the repo was deleted.
        self.getResponse(Repository, params=dict(repository=self.COMPLEX_REPO), expected_code=404)

    def test_populate_and_delete_repo(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the repo exists.
        self.getResponse(Repository, params=dict(repository=self.COMPLEX_REPO))

        # Make sure the repository has some images and tags.
        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, "complex")
        self.assertTrue(len(list(registry_model.list_all_active_repository_tags(repo_ref))) > 0)

        # Add some data for the repository, in addition to is already existing images and tags.
        repository = model.repository.get_repository(ADMIN_ACCESS_USER, "complex")

        # Create some access tokens.
        access_token = model.token.create_access_token(repository, "read")
        model.token.create_access_token(repository, "write")

        delegate_token = model.token.create_delegate_token(
            ADMIN_ACCESS_USER, "complex", "sometoken", "read"
        )
        model.token.create_delegate_token(ADMIN_ACCESS_USER, "complex", "sometoken", "write")

        # Create some repository builds.
        model.build.create_repository_build(repository, access_token, {}, "someid", "foobar")
        model.build.create_repository_build(repository, delegate_token, {}, "someid2", "foobar2")

        # Create some notifications.
        model.notification.create_repo_notification(repository, "repo_push", "hipchat", {}, {})
        model.notification.create_repo_notification(repository, "build_queued", "slack", {}, {})

        # Create some logs.
        logs_model.log_action("push_repo", ADMIN_ACCESS_USER, repository=repository)
        logs_model.log_action("push_repo", ADMIN_ACCESS_USER, repository=repository)

        # Create some build triggers.
        user = model.user.get_user(ADMIN_ACCESS_USER)
        model.build.create_build_trigger(repository, "github", "sometoken", user)
        model.build.create_build_trigger(repository, "github", "anothertoken", user)

        # Create some email authorizations.
        model.repository.create_email_authorization_for_repo(
            ADMIN_ACCESS_USER, "complex", "a@b.com"
        )
        model.repository.create_email_authorization_for_repo(
            ADMIN_ACCESS_USER, "complex", "b@c.com"
        )

        # Create some repository action count entries.
        RepositoryActionCount.create(repository=repository, date=datetime.datetime.now(), count=1)
        RepositoryActionCount.create(
            repository=repository,
            date=datetime.datetime.now() - datetime.timedelta(days=2),
            count=2,
        )
        RepositoryActionCount.create(
            repository=repository,
            date=datetime.datetime.now() - datetime.timedelta(days=5),
            count=6,
        )

        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, "complex")
        tag = registry_model.get_repo_tag(repo_ref, "prod")
        manifest = registry_model.get_manifest_for_tag(tag)

        # Create some labels.
        registry_model.create_manifest_label(manifest, "foo", "bar", "manifest")
        registry_model.create_manifest_label(manifest, "foo", "baz", "manifest")
        registry_model.create_manifest_label(
            manifest, "something", "{}", "api", media_type_name="application/json"
        )

        registry_model.create_manifest_label(manifest, "something", '{"some": "json"}', "manifest")

        # Delete the repository.
        with check_transitive_modifications():
            self.deleteEmptyResponse(Repository, params=dict(repository=self.COMPLEX_REPO))

        # Verify the repo was deleted.
        self.getResponse(Repository, params=dict(repository=self.COMPLEX_REPO), expected_code=404)


class TestGetRepository(ApiTestCase):
    PUBLIC_REPO = PUBLIC_USER + "/publicrepo"

    def test_get_largerepo(self):
        self.login(ADMIN_ACCESS_USER)

        # base + repo + is_starred + tags
        with assert_query_count(BASE_LOGGEDIN_QUERY_COUNT + 4):
            self.getJsonResponse(Repository, params=dict(repository=ADMIN_ACCESS_USER + "/simple"))

        # base + repo + is_starred + tags
        with assert_query_count(BASE_LOGGEDIN_QUERY_COUNT + 4):
            json = self.getJsonResponse(
                Repository, params=dict(repository=ADMIN_ACCESS_USER + "/gargantuan")
            )

        self.assertEqual(ADMIN_ACCESS_USER, json["namespace"])
        self.assertEqual("gargantuan", json["name"])

        self.assertEqual(False, json["is_public"])

    def test_getrepo_badnames(self):
        self.login(ADMIN_ACCESS_USER)

        bad_names = ["logs", "build", "tokens", "foo.bar", "foo-bar", "foo_bar"]

        # For each bad name, create the repo.
        for bad_name in bad_names:
            json = self.postJsonResponse(
                RepositoryList,
                expected_code=201,
                data=dict(repository=bad_name, visibility="public", description=""),
            )

            # Make sure we can retrieve its information.
            json = self.getJsonResponse(
                Repository, params=dict(repository=ADMIN_ACCESS_USER + "/" + bad_name)
            )

            self.assertEqual(ADMIN_ACCESS_USER, json["namespace"])
            self.assertEqual(bad_name, json["name"])
            self.assertEqual(True, json["is_public"])

    def test_getrepo_public_asguest(self):
        json = self.getJsonResponse(Repository, params=dict(repository=self.PUBLIC_REPO))

        self.assertEqual(PUBLIC_USER, json["namespace"])
        self.assertEqual("publicrepo", json["name"])

        self.assertEqual(True, json["is_public"])
        self.assertEqual(False, json["is_organization"])

        self.assertEqual(False, json["can_write"])
        self.assertEqual(False, json["can_admin"])

        assert "latest" in json["tags"]

    def test_getrepo_public_asowner(self):
        self.login(PUBLIC_USER)

        json = self.getJsonResponse(Repository, params=dict(repository=self.PUBLIC_REPO))

        self.assertEqual(False, json["is_organization"])
        self.assertEqual(True, json["can_write"])
        self.assertEqual(True, json["can_admin"])

    def test_getrepo_building(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            Repository, params=dict(repository=ADMIN_ACCESS_USER + "/building")
        )

        self.assertEqual(True, json["can_write"])
        self.assertEqual(True, json["can_admin"])
        self.assertEqual(False, json["is_organization"])

    def test_getrepo_org_asnonmember(self):
        self.getResponse(
            Repository, params=dict(repository=ORGANIZATION + "/" + ORG_REPO), expected_code=401
        )

    def test_getrepo_org_asreader(self):
        self.login(READ_ACCESS_USER)

        json = self.getJsonResponse(
            Repository, params=dict(repository=ORGANIZATION + "/" + ORG_REPO)
        )

        self.assertEqual(ORGANIZATION, json["namespace"])
        self.assertEqual(ORG_REPO, json["name"])

        self.assertEqual(False, json["can_write"])
        self.assertEqual(False, json["can_admin"])

        self.assertEqual(True, json["is_organization"])

    def test_getrepo_org_asadmin(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            Repository, params=dict(repository=ORGANIZATION + "/" + ORG_REPO)
        )

        self.assertEqual(True, json["can_write"])
        self.assertEqual(True, json["can_admin"])

        self.assertEqual(True, json["is_organization"])


class TestRepositoryBuildResource(ApiTestCase):
    def test_repo_build_invalid_url(self):
        self.login(ADMIN_ACCESS_USER)

        self.postJsonResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(archive_url="hppt://quay.io"),
            expected_code=400,
        )

    def test_cancel_invalidbuild(self):
        self.login(ADMIN_ACCESS_USER)

        self.deleteResponse(
            RepositoryBuildResource,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", build_uuid="invalid"),
            expected_code=404,
        )

    def test_cancel_waitingbuild(self):
        self.login(ADMIN_ACCESS_USER)

        # Request a (fake) build.
        json = self.postJsonResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(file_id="foobarbaz"),
            expected_code=201,
        )

        uuid = json["id"]

        # Check for the build.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        self.assertEqual(1, len(json["builds"]))
        self.assertEqual(uuid, json["builds"][0]["id"])

        # Find the build's queue item.
        build_ref = database.RepositoryBuild.get(uuid=uuid)
        queue_item = database.QueueItem.get(id=build_ref.queue_id)

        self.assertTrue(queue_item.available)
        self.assertTrue(queue_item.retries_remaining > 0)

        # Cancel the build.
        self.deleteResponse(
            RepositoryBuildResource,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", build_uuid=uuid),
            expected_code=201,
        )

        # Check for the build.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        self.assertEqual(1, len(json["builds"]))
        self.assertEqual("cancelled", json["builds"][0]["phase"])

        # Check for the build's queue item.
        try:
            database.QueueItem.get(id=build_ref.queue_id)
            self.fail("QueueItem still exists for build")
        except database.QueueItem.DoesNotExist:
            pass

    def test_attemptcancel_scheduledbuild(self):
        self.login(ADMIN_ACCESS_USER)

        # Request a (fake) build.
        json = self.postJsonResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(file_id="foobarbaz"),
            expected_code=201,
        )

        uuid = json["id"]

        # Check for the build.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        self.assertEqual(1, len(json["builds"]))
        self.assertEqual(uuid, json["builds"][0]["id"])

        # Set queue item to be picked up.
        build_ref = database.RepositoryBuild.get(uuid=uuid)
        qi = database.QueueItem.get(id=build_ref.queue_id)
        qi.available = False
        qi.save()

        # Try to cancel the build.
        self.deleteResponse(
            RepositoryBuildResource,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", build_uuid=uuid),
            expected_code=201,
        )

    def test_attemptcancel_workingbuild(self):
        self.login(ADMIN_ACCESS_USER)

        # Request a (fake) build.
        json = self.postJsonResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(file_id="foobarbaz"),
            expected_code=201,
        )

        uuid = json["id"]

        # Check for the build.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        self.assertEqual(1, len(json["builds"]))
        self.assertEqual(uuid, json["builds"][0]["id"])

        # Set the build to a different phase.
        rb = database.RepositoryBuild.get(uuid=uuid)
        rb.phase = database.BUILD_PHASE.BUILDING
        rb.save()

        # Try to cancel the build.
        self.deleteResponse(
            RepositoryBuildResource,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", build_uuid=uuid),
            expected_code=400,
        )


class TestRepoBuilds(ApiTestCase):
    def test_getrepo_nobuilds(self):
        self.login(ADMIN_ACCESS_USER)

        # Queries: Permission + the list query + app check
        with assert_query_count(3):
            json = self.getJsonResponse(
                RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
            )

        assert len(json["builds"]) == 0

    def test_getrepobuilds(self):
        self.login(ADMIN_ACCESS_USER)

        # Queries: Permission + the list query + app check
        with assert_query_count(3):
            json = self.getJsonResponse(
                RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/building")
            )

        assert len(json["builds"]) > 0
        build = json["builds"][-1]

        assert "id" in build
        assert "status" in build

        # Check the status endpoint.
        status_json = self.getJsonResponse(
            RepositoryBuildStatus,
            params=dict(repository=ADMIN_ACCESS_USER + "/building", build_uuid=build["id"]),
        )

        self.assertEqual(status_json["id"], build["id"])
        self.assertEqual(status_json["resource_key"], build["resource_key"])
        self.assertEqual(status_json["trigger"], build["trigger"])


class TestRequestRepoBuild(ApiTestCase):
    def test_requestbuild_noidurl(self):
        self.login(ADMIN_ACCESS_USER)

        # Request a (fake) build without a file ID or URL.
        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(),
            expected_code=400,
        )

    def test_requestbuild_invalidurls(self):
        self.login(ADMIN_ACCESS_USER)

        # Request a (fake) build with and invalid URL.
        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(archive_url="foobarbaz"),
            expected_code=400,
        )

        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(archive_url="file://foobarbaz"),
            expected_code=400,
        )

    def test_requestrepobuild_withurl(self):
        self.login(ADMIN_ACCESS_USER)

        # Ensure we are not yet building.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        assert len(json["builds"]) == 0

        # Request a (fake) build.
        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(archive_url="http://quay.io/robots.txt"),
            expected_code=201,
        )

        # Check for the build.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        assert len(json["builds"]) > 0
        self.assertEqual("http://quay.io/robots.txt", json["builds"][0]["archive_url"])

    def test_requestrepobuild_withfile(self):
        self.login(ADMIN_ACCESS_USER)

        # Ensure we are not yet building.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        assert len(json["builds"]) == 0

        # Request a (fake) build.
        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(file_id="foobarbaz"),
            expected_code=201,
        )

        # Check for the build.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        assert len(json["builds"]) > 0

    def test_requestrepobuild_with_robot(self):
        self.login(ADMIN_ACCESS_USER)

        # Ensure we are not yet building.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        assert len(json["builds"]) == 0

        # Request a (fake) build.
        pull_robot = ADMIN_ACCESS_USER + "+dtrobot"
        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(file_id="foobarbaz", pull_robot=pull_robot),
            expected_code=201,
        )

        # Check for the build.
        json = self.getJsonResponse(
            RepositoryBuildList, params=dict(repository=ADMIN_ACCESS_USER + "/building")
        )

        assert len(json["builds"]) > 0

    def test_requestrepobuild_with_invalid_robot(self):
        self.login(ADMIN_ACCESS_USER)

        # Request a (fake) build.
        pull_robot = ADMIN_ACCESS_USER + "+invalidrobot"
        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(file_id="foobarbaz", pull_robot=pull_robot),
            expected_code=404,
        )

    def test_requestrepobuild_with_unauthorized_robot(self):
        self.login(ADMIN_ACCESS_USER)

        # Request a (fake) build.
        pull_robot = "freshuser+anotherrobot"
        self.postResponse(
            RepositoryBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(file_id="foobarbaz", pull_robot=pull_robot),
            expected_code=403,
        )


class TestRepositoryEmail(ApiTestCase):
    def test_emailnotauthorized(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the e-mail address is not authorized.
        self.getResponse(
            RepositoryAuthorizedEmail,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", email="test@example.com"),
            expected_code=404,
        )

    def test_emailnotauthorized_butsent(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the e-mail address is not authorized.
        json = self.getJsonResponse(
            RepositoryAuthorizedEmail,
            params=dict(
                repository=ADMIN_ACCESS_USER + "/simple", email="jschorr+other@devtable.com"
            ),
        )

        self.assertEqual(False, json["confirmed"])
        self.assertEqual(ADMIN_ACCESS_USER, json["namespace"])
        self.assertEqual("simple", json["repository"])

    def test_emailauthorized(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the e-mail address is authorized.
        json = self.getJsonResponse(
            RepositoryAuthorizedEmail,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", email="jschorr@devtable.com"),
        )

        self.assertEqual(True, json["confirmed"])
        self.assertEqual(ADMIN_ACCESS_USER, json["namespace"])
        self.assertEqual("simple", json["repository"])

    def test_send_email_authorization(self):
        self.login(ADMIN_ACCESS_USER)

        # Send the email.
        json = self.postJsonResponse(
            RepositoryAuthorizedEmail,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", email="jschorr+foo@devtable.com"),
        )

        self.assertEqual(False, json["confirmed"])
        self.assertEqual(ADMIN_ACCESS_USER, json["namespace"])
        self.assertEqual("simple", json["repository"])


class TestRepositoryNotifications(ApiTestCase):
    def test_testnotification(self):
        self.login(ADMIN_ACCESS_USER)

        # Add a notification.
        json = self.postJsonResponse(
            RepositoryNotificationList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(
                config={"url": "http://example.com"},
                event="repo_push",
                method="webhook",
                eventConfig={},
            ),
            expected_code=201,
        )
        uuid = json["uuid"]

        self.assertIsNone(notification_queue.get())

        # Issue a test notification.
        self.postJsonResponse(
            TestRepositoryNotification,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", uuid=uuid),
        )

        # Ensure the item is in the queue.
        time.sleep(1)  # Makes sure the queue get works on MySQL with its second-level precision.
        found = notification_queue.get()
        self.assertIsNotNone(found)
        self.assertTrue("notification_uuid" in found["body"])

    def test_webhooks(self):
        self.login(ADMIN_ACCESS_USER)

        # Add a notification.
        json = self.postJsonResponse(
            RepositoryNotificationList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(
                config={"url": "http://example.com"},
                event="repo_push",
                method="webhook",
                eventConfig={},
            ),
            expected_code=201,
        )

        self.assertEqual("repo_push", json["event"])
        self.assertEqual("webhook", json["method"])
        self.assertEqual("http://example.com", json["config"]["url"])
        self.assertIsNone(json["title"])

        wid = json["uuid"]

        # Get the notification.
        json = self.getJsonResponse(
            RepositoryNotification, params=dict(repository=ADMIN_ACCESS_USER + "/simple", uuid=wid)
        )

        self.assertEqual(wid, json["uuid"])
        self.assertEqual("repo_push", json["event"])
        self.assertEqual("webhook", json["method"])
        self.assertIsNone(json["title"])

        # Verify the notification is listed.
        json = self.getJsonResponse(
            RepositoryNotificationList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        ids = [w["uuid"] for w in json["notifications"]]
        assert wid in ids

        # Delete the notification.
        self.deleteEmptyResponse(
            RepositoryNotification,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", uuid=wid),
            expected_code=204,
        )

        # Verify the notification is gone.
        self.getResponse(
            RepositoryNotification,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", uuid=wid),
            expected_code=404,
        )

        # Add another notification.
        json = self.postJsonResponse(
            RepositoryNotificationList,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple"),
            data=dict(
                config={"url": "http://example.com"},
                event="repo_push",
                method="webhook",
                title="Some Notification",
                eventConfig={},
            ),
            expected_code=201,
        )

        self.assertEqual("repo_push", json["event"])
        self.assertEqual("webhook", json["method"])
        self.assertEqual("http://example.com", json["config"]["url"])
        self.assertEqual("Some Notification", json["title"])

        wid = json["uuid"]

        # Get the notification.
        json = self.getJsonResponse(
            RepositoryNotification, params=dict(repository=ADMIN_ACCESS_USER + "/simple", uuid=wid)
        )

        self.assertEqual(wid, json["uuid"])
        self.assertEqual("repo_push", json["event"])
        self.assertEqual("webhook", json["method"])
        self.assertEqual("Some Notification", json["title"])


class TestListAndGetImage(ApiTestCase):
    def test_listandgetimages(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            RepositoryImageList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        assert len(json["images"]) > 0

        for image in json["images"]:
            assert "id" in image
            assert "tags" in image
            assert "created" in image
            assert "comment" in image
            assert "command" in image
            assert "ancestors" in image
            assert "size" in image

            ijson = self.getJsonResponse(
                RepositoryImage,
                params=dict(repository=ADMIN_ACCESS_USER + "/simple", image_id=image["id"]),
            )

            self.assertEqual(image["id"], ijson["id"])


class TestGetImageChanges(ApiTestCase):
    def test_getimagechanges(self):
        self.login(ADMIN_ACCESS_USER)

        # Find an image to check.
        json = self.getJsonResponse(
            RepositoryImageList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )

        image_id = json["images"][0]["id"]

        # Lookup the image's changes.
        # TODO: Fix me once we can get fake changes into the test data
        # self.getJsonResponse(RepositoryImageChanges,
        #                     params=dict(repository=ADMIN_ACCESS_USER + '/simple',
        #                                 image_id=image_id))


class TestRestoreTag(ApiTestCase):
    def test_restoretag_invalidtag(self):
        self.login(ADMIN_ACCESS_USER)

        self.postResponse(
            RestoreTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="invalidtag"),
            data=dict(image="invalid_image"),
            expected_code=404,
        )

    def test_restoretag_invalidimage(self):
        self.login(ADMIN_ACCESS_USER)

        self.postResponse(
            RestoreTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest"),
            data=dict(image="invalid_image"),
            expected_code=404,
        )

    def test_restoretag_invalidmanifest(self):
        self.login(ADMIN_ACCESS_USER)

        self.postResponse(
            RestoreTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest"),
            data=dict(manifest_digest="invalid_digest"),
            expected_code=404,
        )

    def test_restoretag(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            ListRepositoryTags, params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest")
        )

        self.assertEqual(2, len(json["tags"]))
        self.assertFalse("end_ts" in json["tags"][0])

        previous_image_id = json["tags"][1]["docker_image_id"]

        self.postJsonResponse(
            RestoreTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest"),
            data=dict(image=previous_image_id),
        )

        json = self.getJsonResponse(
            ListRepositoryTags, params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest")
        )
        self.assertEqual(3, len(json["tags"]))
        self.assertFalse("end_ts" in json["tags"][0])
        self.assertEqual(previous_image_id, json["tags"][0]["docker_image_id"])

    def test_restoretag_to_digest(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            ListRepositoryTags, params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest")
        )

        self.assertEqual(2, len(json["tags"]))
        self.assertFalse("end_ts" in json["tags"][0])

        previous_manifest = json["tags"][1]["manifest_digest"]

        self.postJsonResponse(
            RestoreTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest"),
            data=dict(image="foo", manifest_digest=previous_manifest),
        )

        json = self.getJsonResponse(
            ListRepositoryTags, params=dict(repository=ADMIN_ACCESS_USER + "/history", tag="latest")
        )
        self.assertEqual(3, len(json["tags"]))
        self.assertFalse("end_ts" in json["tags"][0])
        self.assertEqual(previous_manifest, json["tags"][0]["manifest_digest"])


class TestListAndDeleteTag(ApiTestCase):
    def test_invalid_tags(self):
        self.login(ADMIN_ACCESS_USER)

        # List the images for staging.
        json = self.getJsonResponse(
            RepositoryTagImages,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="staging"),
        )

        staging_images = json["images"]

        # Try to add some invalid tags.
        self.putResponse(
            RepositoryTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="-fail"),
            data=dict(image=staging_images[0]["id"]),
            expected_code=400,
        )

        self.putResponse(
            RepositoryTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="北京"),
            data=dict(image=staging_images[0]["id"]),
            expected_code=400,
        )

    def test_listdeletecreateandmovetag(self):
        self.login(ADMIN_ACCESS_USER)

        # List the images for prod.
        json = self.getJsonResponse(
            RepositoryTagImages, params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="prod")
        )

        prod_images = json["images"]
        assert len(prod_images) > 0

        # List the images for staging.
        json = self.getJsonResponse(
            RepositoryTagImages,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="staging"),
        )

        staging_images = json["images"]
        assert len(prod_images) == len(staging_images) + 2

        # Delete prod.
        self.deleteEmptyResponse(
            RepositoryTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="prod"),
            expected_code=204,
        )

        # Make sure the tag is gone.
        self.getResponse(
            RepositoryTagImages,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="prod"),
            expected_code=404,
        )

        # Make the sure the staging images are still there.
        json = self.getJsonResponse(
            RepositoryTagImages,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="staging"),
        )

        self.assertEqual(staging_images, json["images"])

        # Require a valid tag name.
        self.putResponse(
            RepositoryTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="-fail"),
            data=dict(image=staging_images[0]["id"]),
            expected_code=400,
        )

        # Add a new tag to the staging image.
        self.putResponse(
            RepositoryTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="sometag"),
            data=dict(image=staging_images[0]["id"]),
            expected_code=201,
        )

        # Make sure the tag is present.
        json = self.getJsonResponse(
            RepositoryTagImages,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="sometag"),
        )

        assert json["images"]

        # Move the tag.
        self.putResponse(
            RepositoryTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="sometag"),
            data=dict(image=staging_images[-1]["id"]),
            expected_code=201,
        )

        # Make sure the tag has moved.
        json = self.getJsonResponse(
            RepositoryTagImages,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="sometag"),
        )

        sometag_new_images = json["images"]
        assert sometag_new_images

    def test_deletesubtag(self):
        self.login(ADMIN_ACCESS_USER)

        # List the images for prod.
        json = self.getJsonResponse(
            RepositoryTagImages, params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="prod")
        )

        prod_images = json["images"]
        assert len(prod_images) > 0

        # Delete staging.
        self.deleteEmptyResponse(
            RepositoryTag,
            params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="staging"),
            expected_code=204,
        )

        # Make sure the prod images are still around.
        json = self.getJsonResponse(
            RepositoryTagImages, params=dict(repository=ADMIN_ACCESS_USER + "/complex", tag="prod")
        )

        self.assertEqual(prod_images, json["images"])

    def test_listtag_digest(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(
            ListRepositoryTags,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", page=1, limit=1),
        )
        self.assertTrue("manifest_digest" in json["tags"][0])

    def test_listtagpagination(self):
        self.login(ADMIN_ACCESS_USER)

        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, "simple")
        latest_tag = registry_model.get_repo_tag(repo_ref, "latest")

        # Create 8 tags in the simple repo.
        remaining_tags = {"latest", "prod"}
        for i in range(1, 9):
            tag_name = "tag" + str(i)
            remaining_tags.add(tag_name)
            assert registry_model.retarget_tag(
                repo_ref, tag_name, latest_tag.manifest, storage, docker_v2_signing_key
            )

        # Make sure we can iterate over all of them.
        json = self.getJsonResponse(
            ListRepositoryTags,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", page=1, limit=5),
        )
        self.assertEqual(1, json["page"])
        self.assertEqual(5, len(json["tags"]))
        self.assertTrue(json["has_additional"])

        names = {tag["name"] for tag in json["tags"]}
        remaining_tags = remaining_tags - names
        self.assertEqual(5, len(remaining_tags))

        json = self.getJsonResponse(
            ListRepositoryTags,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", page=2, limit=5),
        )

        self.assertEqual(2, json["page"])
        self.assertEqual(5, len(json["tags"]))
        self.assertFalse(json["has_additional"])

        names = {tag["name"] for tag in json["tags"]}
        remaining_tags = remaining_tags - names
        self.assertEqual(0, len(remaining_tags))

        json = self.getJsonResponse(
            ListRepositoryTags,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", page=3, limit=5),
        )

        self.assertEqual(3, json["page"])
        self.assertEqual(0, len(json["tags"]))
        self.assertFalse(json["has_additional"])


class TestRepoPermissions(ApiTestCase):
    def listUserPermissions(self, namespace=ADMIN_ACCESS_USER, repo="simple"):
        return self.getJsonResponse(
            RepositoryUserPermissionList, params=dict(repository=namespace + "/" + repo)
        )["permissions"]

    def listTeamPermissions(self):
        response = self.getJsonResponse(
            RepositoryTeamPermissionList, params=dict(repository=ORGANIZATION + "/" + ORG_REPO)
        )
        return response["permissions"]

    def test_userpermissions_underorg(self):
        self.login(ADMIN_ACCESS_USER)

        permissions = self.listUserPermissions(namespace=ORGANIZATION, repo=ORG_REPO)

        self.assertEqual(1, len(permissions))
        assert "outsideorg" in permissions
        self.assertEqual("read", permissions["outsideorg"]["role"])
        self.assertEqual(False, permissions["outsideorg"]["is_org_member"])

        # Add another user.
        self.putJsonResponse(
            RepositoryUserPermission,
            params=dict(repository=ORGANIZATION + "/" + ORG_REPO, username=ADMIN_ACCESS_USER),
            data=dict(role="admin"),
        )

        # Verify the user is present.
        permissions = self.listUserPermissions(namespace=ORGANIZATION, repo=ORG_REPO)

        self.assertEqual(2, len(permissions))
        assert ADMIN_ACCESS_USER in permissions
        self.assertEqual("admin", permissions[ADMIN_ACCESS_USER]["role"])
        self.assertEqual(True, permissions[ADMIN_ACCESS_USER]["is_org_member"])

    def test_userpermissions(self):
        self.login(ADMIN_ACCESS_USER)

        # The repo should start with just the admin as a user perm.
        permissions = self.listUserPermissions()

        self.assertEqual(1, len(permissions))
        assert ADMIN_ACCESS_USER in permissions
        self.assertEqual("admin", permissions[ADMIN_ACCESS_USER]["role"])
        self.assertFalse("is_org_member" in permissions[ADMIN_ACCESS_USER])

        # Add another user.
        self.putJsonResponse(
            RepositoryUserPermission,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", username=NO_ACCESS_USER),
            data=dict(role="read"),
        )

        # Verify the user is present.
        permissions = self.listUserPermissions()

        self.assertEqual(2, len(permissions))
        assert NO_ACCESS_USER in permissions
        self.assertEqual("read", permissions[NO_ACCESS_USER]["role"])
        self.assertFalse("is_org_member" in permissions[NO_ACCESS_USER])

        json = self.getJsonResponse(
            RepositoryUserPermission,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", username=NO_ACCESS_USER),
        )
        self.assertEqual("read", json["role"])

        # Change the user's permissions.
        self.putJsonResponse(
            RepositoryUserPermission,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", username=NO_ACCESS_USER),
            data=dict(role="admin"),
        )

        # Verify.
        permissions = self.listUserPermissions()

        self.assertEqual(2, len(permissions))
        assert NO_ACCESS_USER in permissions
        self.assertEqual("admin", permissions[NO_ACCESS_USER]["role"])

        # Delete the user's permission.
        self.deleteEmptyResponse(
            RepositoryUserPermission,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", username=NO_ACCESS_USER),
        )

        # Verify.
        permissions = self.listUserPermissions()

        self.assertEqual(1, len(permissions))
        assert not NO_ACCESS_USER in permissions

    def test_teampermissions(self):
        self.login(ADMIN_ACCESS_USER)

        # The repo should start with just the readers as a team perm.
        permissions = self.listTeamPermissions()

        self.assertEqual(1, len(permissions))
        assert "readers" in permissions
        self.assertEqual("read", permissions["readers"]["role"])

        # Add another team.
        self.putJsonResponse(
            RepositoryTeamPermission,
            params=dict(repository=ORGANIZATION + "/" + ORG_REPO, teamname="owners"),
            data=dict(role="write"),
        )

        # Verify the team is present.
        permissions = self.listTeamPermissions()

        self.assertEqual(2, len(permissions))
        assert "owners" in permissions
        self.assertEqual("write", permissions["owners"]["role"])

        json = self.getJsonResponse(
            RepositoryTeamPermission,
            params=dict(repository=ORGANIZATION + "/" + ORG_REPO, teamname="owners"),
        )
        self.assertEqual("write", json["role"])

        # Change the team's permissions.
        self.putJsonResponse(
            RepositoryTeamPermission,
            params=dict(repository=ORGANIZATION + "/" + ORG_REPO, teamname="owners"),
            data=dict(role="admin"),
        )

        # Verify.
        permissions = self.listTeamPermissions()

        self.assertEqual(2, len(permissions))
        assert "owners" in permissions
        self.assertEqual("admin", permissions["owners"]["role"])

        # Delete the team's permission.
        self.deleteEmptyResponse(
            RepositoryTeamPermission,
            params=dict(repository=ORGANIZATION + "/" + ORG_REPO, teamname="owners"),
        )

        # Verify.
        permissions = self.listTeamPermissions()

        self.assertEqual(1, len(permissions))
        assert not "owners" in permissions


class TestApiTokens(ApiTestCase):
    def listTokens(self):
        return self.getJsonResponse(
            RepositoryTokenList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )["tokens"]


class TestUserCard(ApiTestCase):
    def test_getusercard(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(UserCard)

        self.assertEqual("4242", json["card"]["last4"])
        self.assertEqual("Visa", json["card"]["type"])

    def test_setusercard_error(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.postJsonResponse(UserCard, data=dict(token="sometoken"), expected_code=402)
        assert "carderror" in json


class TestOrgCard(ApiTestCase):
    def test_getorgcard(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(OrganizationCard, params=dict(orgname=ORGANIZATION))

        self.assertEqual("4242", json["card"]["last4"])
        self.assertEqual("Visa", json["card"]["type"])


class TestUserSubscription(ApiTestCase):
    def getSubscription(self):
        return self.getJsonResponse(UserPlan)

    def test_updateplan(self):
        self.login(ADMIN_ACCESS_USER)

        # Change the plan.
        self.putJsonResponse(UserPlan, data=dict(plan="free"))

        # Verify
        sub = self.getSubscription()
        self.assertEqual("free", sub["plan"])

        # Change the plan.
        self.putJsonResponse(UserPlan, data=dict(plan="bus-large-2018"))

        # Verify
        sub = self.getSubscription()
        self.assertEqual("bus-large-2018", sub["plan"])


class TestOrgSubscription(ApiTestCase):
    def getSubscription(self):
        return self.getJsonResponse(OrganizationPlan, params=dict(orgname=ORGANIZATION))

    def test_updateplan(self):
        self.login(ADMIN_ACCESS_USER)

        # Change the plan.
        self.putJsonResponse(
            OrganizationPlan, params=dict(orgname=ORGANIZATION), data=dict(plan="free")
        )

        # Verify
        sub = self.getSubscription()
        self.assertEqual("free", sub["plan"])

        # Change the plan.
        self.putJsonResponse(
            OrganizationPlan, params=dict(orgname=ORGANIZATION), data=dict(plan="bus-large-2018")
        )

        # Verify
        sub = self.getSubscription()
        self.assertEqual("bus-large-2018", sub["plan"])


class TestUserRobots(ApiTestCase):
    def getRobotNames(self):
        return [r["name"] for r in self.getJsonResponse(UserRobotList)["robots"]]

    def test_robot_list(self):
        self.login(NO_ACCESS_USER)

        # Create some robots.
        self.putJsonResponse(UserRobot, params=dict(robot_shortname="bender"), expected_code=201)

        self.putJsonResponse(UserRobot, params=dict(robot_shortname="goldy"), expected_code=201)

        self.putJsonResponse(UserRobot, params=dict(robot_shortname="coolbot"), expected_code=201)

        # Queries: Base + the lookup query
        with assert_query_count(BASE_LOGGEDIN_QUERY_COUNT + 1):
            self.getJsonResponse(UserRobotList)

        # Queries: Base + the lookup query
        with assert_query_count(BASE_LOGGEDIN_QUERY_COUNT + 1):
            self.getJsonResponse(UserRobotList, params=dict(permissions=True))

    def test_robots(self):
        self.login(NO_ACCESS_USER)

        # Create a robot.
        json = self.putJsonResponse(
            UserRobot, params=dict(robot_shortname="bender"), expected_code=201
        )

        self.assertEqual(NO_ACCESS_USER + "+bender", json["name"])

        # Verify.
        robots = self.getRobotNames()
        assert NO_ACCESS_USER + "+bender" in robots

        # Delete the robot.
        self.deleteEmptyResponse(UserRobot, params=dict(robot_shortname="bender"))

        # Verify.
        robots = self.getRobotNames()
        assert not NO_ACCESS_USER + "+bender" in robots

    def test_regenerate(self):
        self.login(NO_ACCESS_USER)

        # Create a robot.
        json = self.putJsonResponse(
            UserRobot, params=dict(robot_shortname="bender"), expected_code=201
        )

        token = json["token"]

        # Regenerate the robot.
        json = self.postJsonResponse(
            RegenerateUserRobot, params=dict(robot_shortname="bender"), expected_code=200
        )

        # Verify the token changed.
        self.assertNotEqual(token, json["token"])

        json2 = self.getJsonResponse(
            UserRobot, params=dict(robot_shortname="bender"), expected_code=200
        )

        self.assertEqual(json["token"], json2["token"])


class TestOrgRobots(ApiTestCase):
    def getRobotNames(self, include_permissions=False):
        params = dict(orgname=ORGANIZATION, permissions=include_permissions)
        return [r["name"] for r in self.getJsonResponse(OrgRobotList, params=params)["robots"]]

    def test_create_robot_with_underscores(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the robot.
        self.putJsonResponse(
            OrgRobot,
            params=dict(orgname=ORGANIZATION, robot_shortname="mr_bender"),
            expected_code=201,
        )

        # Add the robot to a team.
        membername = ORGANIZATION + "+mr_bender"
        self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="readers", membername=membername)
        )

        # Retrieve the robot's details.
        self.getJsonResponse(
            OrgRobot,
            params=dict(orgname=ORGANIZATION, robot_shortname="mr_bender"),
            expected_code=200,
        )

        # Make sure the robot shows up in the org robots list.
        self.assertTrue(membername in self.getRobotNames(include_permissions=True))

    def test_delete_robot_after_use(self):
        self.login(ADMIN_ACCESS_USER)

        # Create the robot.
        self.putJsonResponse(
            OrgRobot, params=dict(orgname=ORGANIZATION, robot_shortname="bender"), expected_code=201
        )

        # Add the robot to a team.
        membername = ORGANIZATION + "+bender"
        self.putJsonResponse(
            TeamMember, params=dict(orgname=ORGANIZATION, teamname="readers", membername=membername)
        )

        # Add a repository permission.
        self.putJsonResponse(
            RepositoryUserPermission,
            params=dict(repository=ORGANIZATION + "/" + ORG_REPO, username=membername),
            data=dict(role="read"),
        )

        # Add a permission prototype with the robot as the activating user.
        self.postJsonResponse(
            PermissionPrototypeList,
            params=dict(orgname=ORGANIZATION),
            data=dict(
                role="read",
                activating_user={"name": membername},
                delegate={"kind": "user", "name": membername},
            ),
        )

        # Add a permission prototype with the robot as the delegating user.
        self.postJsonResponse(
            PermissionPrototypeList,
            params=dict(orgname=ORGANIZATION),
            data=dict(role="read", delegate={"kind": "user", "name": membername}),
        )

        # Add a build trigger with the robot as the pull robot.
        database.BuildTriggerService.create(name="fakeservice")

        # Add a new fake trigger.
        repo = model.repository.get_repository(ORGANIZATION, ORG_REPO)
        user = model.user.get_user(ADMIN_ACCESS_USER)
        pull_robot = model.user.get_user(membername)
        trigger = model.build.create_build_trigger(
            repo, "fakeservice", "sometoken", user, pull_robot=pull_robot
        )

        # Add a fake build of the fake build trigger.
        token = model.token.create_access_token(
            repo, "write", kind="build-worker", friendly_name="Repository Build Token"
        )

        build = model.build.create_repository_build(
            repo, token, {}, "fake-dockerfile", "fake-name", trigger, pull_robot_name=membername
        )

        # Add some log entries for the robot.
        logs_model.log_action("pull_repo", ORGANIZATION, performer=pull_robot, repository=repo)

        # Delete the robot and verify it works.
        self.deleteEmptyResponse(
            OrgRobot, params=dict(orgname=ORGANIZATION, robot_shortname="bender")
        )

        # Verify the build is still present.
        self.assertIsNotNone(model.build.get_repository_build(build.uuid))

        # All the above records should now be deleted, along with the robot. We verify a few of the
        # critical ones below.

        # Check the team.
        team = model.team.get_organization_team(ORGANIZATION, "readers")
        members = [
            member.username for member in model.organization.get_organization_team_members(team.id)
        ]
        self.assertFalse(membername in members)

        # Check the robot itself.
        self.assertIsNone(model.user.get_user(membername))

    def test_robots(self):
        self.login(ADMIN_ACCESS_USER)

        # Create a robot.
        json = self.putJsonResponse(
            OrgRobot, params=dict(orgname=ORGANIZATION, robot_shortname="bender"), expected_code=201
        )

        self.assertEqual(ORGANIZATION + "+bender", json["name"])

        # Verify.
        robots = self.getRobotNames()
        assert ORGANIZATION + "+bender" in robots

        # Delete the robot.
        self.deleteEmptyResponse(
            OrgRobot, params=dict(orgname=ORGANIZATION, robot_shortname="bender")
        )

        # Verify.
        robots = self.getRobotNames()
        assert not ORGANIZATION + "+bender" in robots

    def test_regenerate(self):
        self.login(ADMIN_ACCESS_USER)

        # Create a robot.
        json = self.putJsonResponse(
            OrgRobot, params=dict(orgname=ORGANIZATION, robot_shortname="bender"), expected_code=201
        )

        token = json["token"]

        # Regenerate the robot.
        json = self.postJsonResponse(
            RegenerateOrgRobot,
            params=dict(orgname=ORGANIZATION, robot_shortname="bender"),
            expected_code=200,
        )

        # Verify the token changed.
        self.assertNotEqual(token, json["token"])

        json2 = self.getJsonResponse(
            OrgRobot, params=dict(orgname=ORGANIZATION, robot_shortname="bender"), expected_code=200
        )

        self.assertEqual(json["token"], json2["token"])


class TestLogs(ApiTestCase):
    def test_repo_logs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(RepositoryLogs, params=dict(repository="devtable/simple"))
        assert "logs" in json
        assert "start_time" in json
        assert "end_time" in json

    def test_repo_logs_crossyear(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            RepositoryLogs,
            params=dict(repository="devtable/simple", starttime="12/01/2016", endtime="1/09/2017"),
        )
        self.assertEqual("Thu, 01 Dec 2016 00:00:00 -0000", json["start_time"])
        self.assertEqual("Tue, 10 Jan 2017 00:00:00 -0000", json["end_time"])

    def test_repo_aggregate_logs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            RepositoryAggregateLogs, params=dict(repository="devtable/simple")
        )
        assert "aggregated" in json
        assert len(json["aggregated"]) > 0

    def test_user_logs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(UserLogs)
        assert "logs" in json
        assert "start_time" in json
        assert "end_time" in json

    def test_org_logs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(OrgLogs, params=dict(orgname=ORGANIZATION))
        assert "logs" in json
        assert "start_time" in json
        assert "end_time" in json

    def test_user_aggregate_logs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(UserAggregateLogs)
        assert "aggregated" in json

    def test_org_logs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(OrgAggregateLogs, params=dict(orgname=ORGANIZATION))
        assert "aggregated" in json

    def test_performer(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(OrgLogs, params=dict(orgname=ORGANIZATION))
        all_logs = json["logs"]

        json = self.getJsonResponse(
            OrgLogs, params=dict(performer=READ_ACCESS_USER, orgname=ORGANIZATION)
        )

        assert len(json["logs"]) < len(all_logs)
        for log in json["logs"]:
            self.assertEqual(READ_ACCESS_USER, log["performer"]["name"])


class TestApplicationInformation(ApiTestCase):
    def test_get_info(self):
        json = self.getJsonResponse(
            ApplicationInformation, params=dict(client_id=FAKE_APPLICATION_CLIENT_ID)
        )
        assert "name" in json
        assert "uri" in json
        assert "organization" in json

    def test_get_invalid_info(self):
        self.getJsonResponse(
            ApplicationInformation, params=dict(client_id="invalid-code"), expected_code=404
        )


class TestOrganizationApplications(ApiTestCase):
    def test_list_create_applications(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(OrganizationApplications, params=dict(orgname=ORGANIZATION))

        self.assertEqual(2, len(json["applications"]))

        found = False
        for application in json["applications"]:
            if application["client_id"] == FAKE_APPLICATION_CLIENT_ID:
                found = True
                break

        self.assertTrue(found)

        # Add a new application.
        json = self.postJsonResponse(
            OrganizationApplications,
            params=dict(orgname=ORGANIZATION),
            data=dict(name="Some cool app", description="foo"),
        )

        self.assertEqual("Some cool app", json["name"])
        self.assertEqual("foo", json["description"])

        # Retrieve the apps list again
        list_json = self.getJsonResponse(
            OrganizationApplications, params=dict(orgname=ORGANIZATION)
        )
        self.assertEqual(3, len(list_json["applications"]))


class TestOrganizationApplicationResource(ApiTestCase):
    def test_get_edit_delete_application(self):
        self.login(ADMIN_ACCESS_USER)

        # Retrieve the application.
        json = self.getJsonResponse(
            OrganizationApplicationResource,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
        )

        self.assertEqual(FAKE_APPLICATION_CLIENT_ID, json["client_id"])

        # Edit the application.
        edit_json = self.putJsonResponse(
            OrganizationApplicationResource,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
            data=dict(
                name="Some App",
                description="foo",
                application_uri="bar",
                redirect_uri="baz",
                avatar_email="meh",
            ),
        )

        self.assertEqual(FAKE_APPLICATION_CLIENT_ID, edit_json["client_id"])
        self.assertEqual("Some App", edit_json["name"])
        self.assertEqual("foo", edit_json["description"])
        self.assertEqual("bar", edit_json["application_uri"])
        self.assertEqual("baz", edit_json["redirect_uri"])
        self.assertEqual("meh", edit_json["avatar_email"])

        # Retrieve the application again.
        json = self.getJsonResponse(
            OrganizationApplicationResource,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
        )

        self.assertEqual(json, edit_json)

        # Delete the application.
        self.deleteEmptyResponse(
            OrganizationApplicationResource,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
        )

        # Make sure the application is gone.
        self.getJsonResponse(
            OrganizationApplicationResource,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
            expected_code=404,
        )


class TestOrganization(ApiTestCase):
    def test_change_send_billing_invoice(self):
        self.login(ADMIN_ACCESS_USER)
        self.putJsonResponse(
            Organization,
            params=dict(orgname=ORGANIZATION),
            data=dict(invoice_email=False, invoice_email_address=None),
        )


class TestOrganizationApplicationResetClientSecret(ApiTestCase):
    def test_reset_client_secret(self):
        self.login(ADMIN_ACCESS_USER)

        # Retrieve the application.
        json = self.getJsonResponse(
            OrganizationApplicationResource,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
        )

        self.assertEqual(FAKE_APPLICATION_CLIENT_ID, json["client_id"])

        # Reset the client secret.
        reset_json = self.postJsonResponse(
            OrganizationApplicationResetClientSecret,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
        )

        self.assertEqual(FAKE_APPLICATION_CLIENT_ID, reset_json["client_id"])
        self.assertNotEqual(reset_json["client_secret"], json["client_secret"])

        # Verify it was changed in the DB.
        json = self.getJsonResponse(
            OrganizationApplicationResource,
            params=dict(orgname=ORGANIZATION, client_id=FAKE_APPLICATION_CLIENT_ID),
        )
        self.assertEqual(reset_json["client_secret"], json["client_secret"])


class FakeBuildTrigger(BuildTriggerHandler):
    @classmethod
    def service_name(cls):
        return "fakeservice"

    def list_build_source_namespaces(self):
        return [
            {"name": "first", "id": "first"},
            {"name": "second", "id": "second"},
        ]

    def list_build_sources_for_namespace(self, namespace):
        if namespace == "first":
            return [{"name": "source",}]
        elif namespace == "second":
            return [{"name": self.auth_token,}]
        else:
            return []

    def list_build_subdirs(self):
        return [self.auth_token, "foo", "bar", self.config["somevalue"]]

    def handle_trigger_request(self, request):
        prepared = PreparedBuild(self.trigger)
        prepared.build_name = "build-name"
        prepared.tags = ["bar"]
        prepared.dockerfile_id = "foo"
        prepared.subdirectory = "subdir"
        prepared.metadata = {"foo": "bar"}
        prepared.is_manual = False
        return prepared

    def is_active(self):
        return "active" in self.config and self.config["active"]

    def activate(self, standard_webhook_url):
        self.config["active"] = True
        return self.config, {}

    def deactivate(self):
        self.config["active"] = False
        return self.config

    def manual_start(self, run_parameters=None):
        prepared = PreparedBuild(self.trigger)
        prepared.build_name = "build-name"
        prepared.tags = ["bar"]
        prepared.dockerfile_id = "foo"
        prepared.subdirectory = "subdir"
        prepared.metadata = {"foo": "bar"}
        prepared.is_manual = True
        prepared.context = "/"
        return prepared

    def get_repository_url(self):
        return "http://foo/" + self.config["build_source"]

    def load_dockerfile_contents(self):
        if not "dockerfile" in self.config:
            return None

        return self.config["dockerfile"]

    def list_field_values(self, field_name, limit=None):
        if field_name == "test_field":
            return [1, 2, 3]

        return None


class TestBuildTriggers(ApiTestCase):
    def test_list_build_triggers(self):
        self.login(ADMIN_ACCESS_USER)

        # Check a repo with no known triggers.
        json = self.getJsonResponse(
            BuildTriggerList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )
        self.assertEqual(0, len(json["triggers"]))

        # Check a repo with one known trigger.
        json = self.getJsonResponse(
            BuildTriggerList, params=dict(repository=ADMIN_ACCESS_USER + "/building")
        )
        self.assertEqual(1, len(json["triggers"]))

        trigger = json["triggers"][0]

        assert "id" in trigger
        assert "is_active" in trigger
        assert "config" in trigger
        assert "service" in trigger

        # Verify the get trigger method.
        trigger_json = self.getJsonResponse(
            BuildTrigger,
            params=dict(repository=ADMIN_ACCESS_USER + "/building", trigger_uuid=trigger["id"]),
        )

        self.assertEqual(trigger, trigger_json)

        # Check the recent builds for the trigger.
        builds_json = self.getJsonResponse(
            TriggerBuildList,
            params=dict(repository=ADMIN_ACCESS_USER + "/building", trigger_uuid=trigger["id"]),
        )

        assert "builds" in builds_json

    def test_delete_build_trigger(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(
            BuildTriggerList, params=dict(repository=ADMIN_ACCESS_USER + "/building")
        )
        self.assertEqual(1, len(json["triggers"]))
        trigger = json["triggers"][0]

        # Delete the trigger.
        self.deleteEmptyResponse(
            BuildTrigger,
            params=dict(repository=ADMIN_ACCESS_USER + "/building", trigger_uuid=trigger["id"]),
        )

        # Verify it was deleted.
        json = self.getJsonResponse(
            BuildTriggerList, params=dict(repository=ADMIN_ACCESS_USER + "/building")
        )
        self.assertEqual(0, len(json["triggers"]))

    def test_analyze_fake_trigger(self):
        self.login(ADMIN_ACCESS_USER)

        database.BuildTriggerService.create(name="fakeservice")

        # Add a new fake trigger.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, "simple")
        user = model.user.get_user(ADMIN_ACCESS_USER)
        trigger = model.build.create_build_trigger(repo, "fakeservice", "sometoken", user)

        # Analyze the trigger's dockerfile: First, no dockerfile.
        trigger_config = {}
        analyze_json = self.postJsonResponse(
            BuildTriggerAnalyze,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual("warning", analyze_json["status"])
        self.assertEqual(
            "Specified Dockerfile path for the trigger was not "
            + "found on the main branch. This trigger may fail.",
            analyze_json["message"],
        )

        # Analyze the trigger's dockerfile: Second, missing FROM in dockerfile.
        trigger_config = {"dockerfile": "MAINTAINER me"}
        analyze_json = self.postJsonResponse(
            BuildTriggerAnalyze,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual("warning", analyze_json["status"])
        self.assertEqual("No FROM line found in the Dockerfile", analyze_json["message"])

        # Analyze the trigger's dockerfile: Third, dockerfile with public repo.
        trigger_config = {"dockerfile": "FROM somerepo"}
        analyze_json = self.postJsonResponse(
            BuildTriggerAnalyze,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual("publicbase", analyze_json["status"])

        # Analyze the trigger's dockerfile: Fourth, dockerfile with private repo with an invalid path.
        trigger_config = {"dockerfile": "FROM localhost:5000/somepath"}
        analyze_json = self.postJsonResponse(
            BuildTriggerAnalyze,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual("warning", analyze_json["status"])
        self.assertEqual(
            '"localhost:5000/somepath" is not a valid Quay repository path', analyze_json["message"]
        )

        # Analyze the trigger's dockerfile: Fifth, dockerfile with private repo that does not exist.
        trigger_config = {"dockerfile": "FROM localhost:5000/nothere/randomrepo"}
        analyze_json = self.postJsonResponse(
            BuildTriggerAnalyze,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual("error", analyze_json["status"])
        nofound = (
            'Repository "localhost:5000/%s/randomrepo" referenced by the Dockerfile was not found'
        )
        self.assertEqual(nofound % "nothere", analyze_json["message"])

        # Analyze the trigger's dockerfile: Sixth, dockerfile with private repo that the user cannot see
        trigger_config = {"dockerfile": "FROM localhost:5000/randomuser/randomrepo"}
        analyze_json = self.postJsonResponse(
            BuildTriggerAnalyze,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual("error", analyze_json["status"])
        self.assertEqual(nofound % "randomuser", analyze_json["message"])

        # Analyze the trigger's dockerfile: Seventh, dockerfile with private repo that the user see.
        trigger_config = {"dockerfile": "FROM localhost:5000/devtable/complex"}
        analyze_json = self.postJsonResponse(
            BuildTriggerAnalyze,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual("requiresrobot", analyze_json["status"])
        self.assertEqual("devtable", analyze_json["namespace"])
        self.assertEqual("complex", analyze_json["name"])
        self.assertEqual(ADMIN_ACCESS_USER + "+dtrobot", analyze_json["robots"][0]["name"])

    def test_fake_trigger(self):
        self.login(ADMIN_ACCESS_USER)

        database.BuildTriggerService.create(name="fakeservice")

        # Add a new fake trigger.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, "simple")
        user = model.user.get_user(ADMIN_ACCESS_USER)
        trigger = model.build.create_build_trigger(repo, "fakeservice", "sometoken", user)

        # Verify the trigger.
        json = self.getJsonResponse(
            BuildTriggerList, params=dict(repository=ADMIN_ACCESS_USER + "/simple")
        )
        self.assertEqual(1, len(json["triggers"]))
        self.assertEqual(trigger.uuid, json["triggers"][0]["id"])
        self.assertEqual(trigger.service.name, json["triggers"][0]["service"])
        self.assertEqual(False, json["triggers"][0]["is_active"])

        # List the trigger's source namespaces.
        namespace_json = self.getJsonResponse(
            BuildTriggerSourceNamespaces,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
        )
        self.assertEqual(
            [{"id": "first", "name": "first"}, {"id": "second", "name": "second"}],
            namespace_json["namespaces"],
        )

        source_json = self.postJsonResponse(
            BuildTriggerSources,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data=dict(namespace="first"),
        )
        self.assertEqual([{"name": "source"}], source_json["sources"])

        # List the trigger's subdirs.
        subdir_json = self.postJsonResponse(
            BuildTriggerSubdirs,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"somevalue": "meh"},
        )

        self.assertEqual(
            {
                "status": "success",
                "dockerfile_paths": ["/sometoken", "/foo", "/bar", "/meh"],
                "contextMap": {"/bar": ["/"], "/foo": ["/"], "/meh": ["/"], "/sometoken": ["/"]},
            },
            subdir_json,
        )

        # Activate the trigger.
        trigger_config = {"build_source": "somesource"}
        activate_json = self.postJsonResponse(
            BuildTriggerActivate,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
        )

        self.assertEqual(True, activate_json["is_active"])

        # Make sure the trigger has a write token.
        trigger = model.build.get_build_trigger(trigger.uuid)
        self.assertNotEqual(None, trigger.write_token)
        self.assertEqual(True, py_json.loads(trigger.config)["active"])

        # Make sure we cannot activate again.
        self.postResponse(
            BuildTriggerActivate,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config},
            expected_code=400,
        )

        # Retrieve values for a field.
        result = self.postJsonResponse(
            BuildTriggerFieldValues,
            params=dict(
                repository=ADMIN_ACCESS_USER + "/simple",
                trigger_uuid=trigger.uuid,
                field_name="test_field",
            ),
        )

        self.assertEqual(result["values"], [1, 2, 3])

        self.postResponse(
            BuildTriggerFieldValues,
            params=dict(
                repository=ADMIN_ACCESS_USER + "/simple",
                trigger_uuid=trigger.uuid,
                field_name="another_field",
            ),
            expected_code=404,
        )

        # Start a manual build.
        start_json = self.postJsonResponse(
            ActivateBuildTrigger,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data=dict(),
            expected_code=201,
        )

        assert "id" in start_json
        self.assertEqual("build-name", start_json["display_name"])
        self.assertEqual(["bar"], start_json["tags"])
        self.assertEqual("subdir", start_json["subdirectory"])
        self.assertEqual("somesource", start_json["trigger"]["build_source"])

        # Verify the metadata was added.
        build_obj = database.RepositoryBuild.get(database.RepositoryBuild.uuid == start_json["id"])
        self.assertEqual("bar", py_json.loads(build_obj.job_config)["trigger_metadata"]["foo"])

        # Start another manual build, with a ref.
        self.postJsonResponse(
            ActivateBuildTrigger,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data=dict(refs={"kind": "branch", "name": "foobar"}),
            expected_code=201,
        )

        # Start another manual build with a null ref.
        self.postJsonResponse(
            ActivateBuildTrigger,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data=dict(refs=None),
            expected_code=201,
        )

    def test_invalid_robot_account(self):
        self.login(ADMIN_ACCESS_USER)

        database.BuildTriggerService.create(name="fakeservice")

        # Add a new fake trigger.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, "simple")
        user = model.user.get_user(ADMIN_ACCESS_USER)
        trigger = model.build.create_build_trigger(repo, "fakeservice", "sometoken", user)

        # Try to activate it with an invalid robot account.
        trigger_config = {}
        self.postJsonResponse(
            BuildTriggerActivate,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config, "pull_robot": "someinvalidrobot"},
            expected_code=404,
        )

    def test_unauthorized_robot_account(self):
        self.login(ADMIN_ACCESS_USER)

        database.BuildTriggerService.create(name="fakeservice")

        # Add a new fake trigger.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, "simple")
        user = model.user.get_user(ADMIN_ACCESS_USER)
        trigger = model.build.create_build_trigger(repo, "fakeservice", "sometoken", user)

        # Try to activate it with a robot account in the wrong namespace.
        trigger_config = {}
        self.postJsonResponse(
            BuildTriggerActivate,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config, "pull_robot": "freshuser+anotherrobot"},
            expected_code=403,
        )

    def test_robot_account(self):
        self.login(ADMIN_ACCESS_USER)

        database.BuildTriggerService.create(name="fakeservice")

        # Add a new fake trigger.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, "simple")
        user = model.user.get_user(ADMIN_ACCESS_USER)
        trigger = model.build.create_build_trigger(repo, "fakeservice", "sometoken", user)

        # Try to activate it with a robot account.
        trigger_config = {}
        activate_json = self.postJsonResponse(
            BuildTriggerActivate,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data={"config": trigger_config, "pull_robot": ADMIN_ACCESS_USER + "+dtrobot"},
        )

        # Verify that the robot was saved.
        self.assertEqual(True, activate_json["is_active"])
        self.assertEqual(ADMIN_ACCESS_USER + "+dtrobot", activate_json["pull_robot"]["name"])

        # Start a manual build.
        start_json = self.postJsonResponse(
            ActivateBuildTrigger,
            params=dict(repository=ADMIN_ACCESS_USER + "/simple", trigger_uuid=trigger.uuid),
            data=dict(refs=dict(kind="branch", name="foobar")),
            expected_code=201,
        )

        assert "id" in start_json
        self.assertEqual("build-name", start_json["display_name"])
        self.assertEqual(["bar"], start_json["tags"])


class TestUserAuthorizations(ApiTestCase):
    def test_list_get_delete_user_authorizations(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(UserAuthorizationList)

        self.assertEqual(1, len(json["authorizations"]))

        authorization = json["authorizations"][0]

        assert "uuid" in authorization
        assert "scopes" in authorization
        assert "application" in authorization

        # Retrieve the authorization.
        get_json = self.getJsonResponse(
            UserAuthorization, params=dict(access_token_uuid=authorization["uuid"])
        )
        self.assertEqual(authorization, get_json)

        # Delete the authorization.
        self.deleteEmptyResponse(
            UserAuthorization, params=dict(access_token_uuid=authorization["uuid"])
        )

        # Verify it has been deleted.
        self.getJsonResponse(
            UserAuthorization,
            params=dict(access_token_uuid=authorization["uuid"]),
            expected_code=404,
        )


class TestSuperUserLogs(ApiTestCase):
    def test_get_logs(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(SuperUserLogs)

        assert "logs" in json
        assert len(json["logs"]) > 0


class TestSuperUserTakeOwnership(ApiTestCase):
    def test_take_ownership_superuser(self):
        self.login(ADMIN_ACCESS_USER)

        # Should fail to take ownership of a superuser.
        self.postResponse(
            SuperUserTakeOwnership, params=dict(namespace=ADMIN_ACCESS_USER), expected_code=400
        )

    def test_take_ownership_invalid_namespace(self):
        self.login(ADMIN_ACCESS_USER)
        self.postResponse(
            SuperUserTakeOwnership, params=dict(namespace="invalid"), expected_code=404
        )

    def test_take_ownership_non_superuser(self):
        self.login(READ_ACCESS_USER)
        self.postResponse(
            SuperUserTakeOwnership, params=dict(namespace="freshuser"), expected_code=403
        )

    def test_take_ownership_user(self):
        self.login(ADMIN_ACCESS_USER)

        with assert_action_logged("take_ownership"):
            # Take ownership of the read user.
            self.postResponse(SuperUserTakeOwnership, params=dict(namespace=READ_ACCESS_USER))

            # Ensure that the read access user is now an org, with the superuser as the owner.
            reader = model.user.get_user_or_org(READ_ACCESS_USER)
            self.assertTrue(reader.organization)

            usernames = [admin.username for admin in model.organization.get_admin_users(reader)]
            self.assertIn(ADMIN_ACCESS_USER, usernames)

    def test_take_ownership_org(self):
        # Create a new org with another user as owner.
        public_user = model.user.get_user(PUBLIC_USER)
        org = model.organization.create_organization("someorg", "some@example.com", public_user)

        # Ensure that the admin is not yet owner of the org.
        usernames = [admin.username for admin in model.organization.get_admin_users(org)]
        self.assertNotIn(ADMIN_ACCESS_USER, usernames)

        with assert_action_logged("take_ownership"):
            # Take ownership.
            self.login(ADMIN_ACCESS_USER)
            self.postResponse(SuperUserTakeOwnership, params=dict(namespace="someorg"))

            # Ensure now in the admin users.
            usernames = [admin.username for admin in model.organization.get_admin_users(org)]
            self.assertIn(ADMIN_ACCESS_USER, usernames)


class TestSuperUserKeyManagement(ApiTestCase):
    def test_get_update_keys(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(SuperUserServiceKeyManagement)
        key_count = len(json["keys"])

        key = json["keys"][0]
        self.assertTrue("name" in key)
        self.assertTrue("service" in key)
        self.assertTrue("kid" in key)
        self.assertTrue("created_date" in key)
        self.assertTrue("expiration_date" in key)
        self.assertTrue("jwk" in key)
        self.assertTrue("approval" in key)
        self.assertTrue("metadata" in key)

        with assert_action_logged("service_key_modify"):
            # Update the key's name.
            self.putJsonResponse(
                SuperUserServiceKey, params=dict(kid=key["kid"]), data=dict(name="somenewname")
            )

            # Ensure the key's name has been changed.
            json = self.getJsonResponse(SuperUserServiceKey, params=dict(kid=key["kid"]))
            self.assertEqual("somenewname", json["name"])

        with assert_action_logged("service_key_modify"):
            # Update the key's metadata.
            self.putJsonResponse(
                SuperUserServiceKey,
                params=dict(kid=key["kid"]),
                data=dict(metadata=dict(foo="bar")),
            )

            # Ensure the key's metadata has been changed.
            json = self.getJsonResponse(SuperUserServiceKey, params=dict(kid=key["kid"]))
            self.assertEqual("bar", json["metadata"]["foo"])

        with assert_action_logged("service_key_extend"):
            # Change the key's expiration.
            self.putJsonResponse(
                SuperUserServiceKey, params=dict(kid=key["kid"]), data=dict(expiration=None)
            )

            # Ensure the key's expiration has been changed.
            json = self.getJsonResponse(SuperUserServiceKey, params=dict(kid=key["kid"]))
            self.assertIsNone(json["expiration_date"])

        with assert_action_logged("service_key_delete"):
            # Delete the key.
            self.deleteEmptyResponse(SuperUserServiceKey, params=dict(kid=key["kid"]))

            # Ensure the key no longer exists.
            self.getResponse(SuperUserServiceKey, params=dict(kid=key["kid"]), expected_code=404)

            json = self.getJsonResponse(SuperUserServiceKeyManagement)
            self.assertEqual(key_count - 1, len(json["keys"]))

    def test_approve_key(self):
        self.login(ADMIN_ACCESS_USER)

        # Ensure the key is not yet approved.
        json = self.getJsonResponse(SuperUserServiceKey, params=dict(kid="kid3"))
        self.assertEqual("unapprovedkey", json["name"])
        self.assertIsNone(json["approval"])

        # Approve the key.
        with assert_action_logged("service_key_approve"):
            self.postResponse(
                SuperUserServiceKeyApproval,
                params=dict(kid="kid3"),
                data=dict(notes="testapprove"),
                expected_code=201,
            )

            # Ensure the key is approved.
            json = self.getJsonResponse(SuperUserServiceKey, params=dict(kid="kid3"))
            self.assertEqual("unapprovedkey", json["name"])
            self.assertIsNotNone(json["approval"])
            self.assertEqual("ServiceKeyApprovalType.SUPERUSER", json["approval"]["approval_type"])
            self.assertEqual(ADMIN_ACCESS_USER, json["approval"]["approver"]["username"])
            self.assertEqual("testapprove", json["approval"]["notes"])

    def test_approve_preapproved(self):
        self.login(ADMIN_ACCESS_USER)

        new_key = {
            "service": "coolservice",
            "name": "mynewkey",
            "metadata": dict(foo="baz"),
            "notes": "whazzup!?",
            "expiration": timegm(
                (datetime.datetime.now() + datetime.timedelta(days=1)).utctimetuple()
            ),
        }

        # Create the key (preapproved automatically)
        json = self.postJsonResponse(SuperUserServiceKeyManagement, data=new_key)

        # Try to approve again.
        self.postResponse(
            SuperUserServiceKeyApproval, params=dict(kid=json["kid"]), expected_code=201
        )

    def test_create_key(self):
        self.login(ADMIN_ACCESS_USER)

        new_key = {
            "service": "coolservice",
            "name": "mynewkey",
            "metadata": dict(foo="baz"),
            "notes": "whazzup!?",
            "expiration": timegm(
                (datetime.datetime.now() + datetime.timedelta(days=1)).utctimetuple()
            ),
        }

        with assert_action_logged("service_key_create"):
            # Create the key.
            json = self.postJsonResponse(SuperUserServiceKeyManagement, data=new_key)
            self.assertEqual("mynewkey", json["name"])
            self.assertTrue("kid" in json)
            self.assertTrue("public_key" in json)
            self.assertTrue("private_key" in json)

            # Verify the private key is a valid PEM.
            serialization.load_pem_private_key(
                json["private_key"].encode("utf-8"), None, default_backend()
            )

            # Verify the key.
            kid = json["kid"]

            json = self.getJsonResponse(SuperUserServiceKey, params=dict(kid=kid))
            self.assertEqual("mynewkey", json["name"])
            self.assertEqual("coolservice", json["service"])
            self.assertEqual("baz", json["metadata"]["foo"])
            self.assertEqual(kid, json["kid"])

            self.assertIsNotNone(json["approval"])
            self.assertEqual("ServiceKeyApprovalType.SUPERUSER", json["approval"]["approval_type"])
            self.assertEqual(ADMIN_ACCESS_USER, json["approval"]["approver"]["username"])
            self.assertEqual("whazzup!?", json["approval"]["notes"])


class TestRepositoryManifestLabels(ApiTestCase):
    def test_basic_labels(self):
        self.login(ADMIN_ACCESS_USER)

        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, "complex")
        tag = registry_model.get_repo_tag(repo_ref, "prod")
        repository = ADMIN_ACCESS_USER + "/complex"

        # Check the existing labels on the complex repo, which should be empty
        json = self.getJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
        )

        self.assertEqual(0, len(json["labels"]))

        self.postJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="bad_label", value="world", media_type="text/plain"),
            expected_code=400,
        )

        self.postJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="hello", value="world", media_type="bad_media_type"),
            expected_code=400,
        )

        # Add some labels to the manifest.
        with assert_action_logged("manifest_label_add"):
            label1 = self.postJsonResponse(
                RepositoryManifestLabels,
                params=dict(repository=repository, manifestref=tag.manifest_digest),
                data=dict(key="hello", value="world", media_type="text/plain"),
                expected_code=201,
            )

        with assert_action_logged("manifest_label_add"):
            label2 = self.postJsonResponse(
                RepositoryManifestLabels,
                params=dict(repository=repository, manifestref=tag.manifest_digest),
                data=dict(key="hi", value="there", media_type="text/plain"),
                expected_code=201,
            )

        with assert_action_logged("manifest_label_add"):
            label3 = self.postJsonResponse(
                RepositoryManifestLabels,
                params=dict(repository=repository, manifestref=tag.manifest_digest),
                data=dict(key="hello", value="someone", media_type="application/json"),
                expected_code=201,
            )

        # Ensure we have *3* labels
        json = self.getJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
        )

        self.assertEqual(3, len(json["labels"]))

        self.assertNotEqual(label2["label"]["id"], label1["label"]["id"])
        self.assertNotEqual(label3["label"]["id"], label1["label"]["id"])
        self.assertNotEqual(label2["label"]["id"], label3["label"]["id"])

        self.assertEqual("text/plain", label1["label"]["media_type"])
        self.assertEqual("text/plain", label2["label"]["media_type"])
        self.assertEqual("application/json", label3["label"]["media_type"])

        # Ensure we can retrieve each of the labels.
        for label in json["labels"]:
            label_json = self.getJsonResponse(
                ManageRepositoryManifestLabel,
                params=dict(
                    repository=repository, manifestref=tag.manifest_digest, labelid=label["id"]
                ),
            )
            self.assertEqual(label["id"], label_json["id"])

        # Delete a label.
        with assert_action_logged("manifest_label_delete"):
            self.deleteEmptyResponse(
                ManageRepositoryManifestLabel,
                params=dict(
                    repository=repository,
                    manifestref=tag.manifest_digest,
                    labelid=label1["label"]["id"],
                ),
            )

        # Ensure the label is gone.
        json = self.getJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
        )

        self.assertEqual(2, len(json["labels"]))

        # Check filtering.
        json = self.getJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest, filter="hello"),
        )

        self.assertEqual(1, len(json["labels"]))

    def test_prefixed_labels(self):
        self.login(ADMIN_ACCESS_USER)

        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, "complex")
        tag = registry_model.get_repo_tag(repo_ref, "prod")
        repository = ADMIN_ACCESS_USER + "/complex"

        self.postJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="com.dockers.whatever", value="pants", media_type="text/plain"),
            expected_code=201,
        )

        self.postJsonResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="my.cool.prefix.for.my.label", value="value", media_type="text/plain"),
            expected_code=201,
        )

    def test_add_invalid_media_type(self):
        self.login(ADMIN_ACCESS_USER)

        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, "complex")
        tag = registry_model.get_repo_tag(repo_ref, "prod")
        repository = ADMIN_ACCESS_USER + "/complex"

        self.postResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="hello", value="world", media_type="some/invalid"),
            expected_code=400,
        )

    def test_add_invalid_key(self):
        self.login(ADMIN_ACCESS_USER)

        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, "complex")
        tag = registry_model.get_repo_tag(repo_ref, "prod")
        repository = ADMIN_ACCESS_USER + "/complex"

        # Try to add an empty label key.
        self.postResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="", value="world"),
            expected_code=400,
        )

        # Try to add an invalid label key.
        self.postResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="invalid___key", value="world"),
            expected_code=400,
        )

        # Try to add a label key in a reserved namespace.
        self.postResponse(
            RepositoryManifestLabels,
            params=dict(repository=repository, manifestref=tag.manifest_digest),
            data=dict(key="io.docker.whatever", value="world"),
            expected_code=400,
        )


class TestSuperUserManagement(ApiTestCase):
    def test_get_user(self):
        self.login(ADMIN_ACCESS_USER)

        json = self.getJsonResponse(SuperUserManagement, params=dict(username="freshuser"))
        self.assertEqual("freshuser", json["username"])
        self.assertEqual("jschorr+test@devtable.com", json["email"])
        self.assertEqual(False, json["super_user"])

    def test_delete_user(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the user exists.
        json = self.getJsonResponse(SuperUserManagement, params=dict(username="freshuser"))
        self.assertEqual("freshuser", json["username"])

        # Delete the user.
        self.deleteEmptyResponse(
            SuperUserManagement, params=dict(username="freshuser"), expected_code=204
        )

        # Verify the user no longer exists.
        self.getResponse(SuperUserManagement, params=dict(username="freshuser"), expected_code=404)

    def test_change_user_password(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the user exists.
        json = self.getJsonResponse(SuperUserManagement, params=dict(username="freshuser"))
        self.assertEqual("freshuser", json["username"])
        self.assertEqual("jschorr+test@devtable.com", json["email"])

        # Update the user.
        json = self.putJsonResponse(
            SuperUserManagement,
            params=dict(username="freshuser"),
            data=dict(password="somepassword"),
        )
        self.assertTrue("encrypted_password" in json)

    def test_update_user(self):
        self.login(ADMIN_ACCESS_USER)

        # Verify the user exists.
        json = self.getJsonResponse(SuperUserManagement, params=dict(username="freshuser"))
        self.assertEqual("freshuser", json["username"])
        self.assertEqual("jschorr+test@devtable.com", json["email"])

        # Update the user.
        json = self.putJsonResponse(
            SuperUserManagement, params=dict(username="freshuser"), data=dict(email="foo@bar.com")
        )
        self.assertFalse("encrypted_password" in json)

        # Verify the user was updated.
        json = self.getJsonResponse(SuperUserManagement, params=dict(username="freshuser"))
        self.assertEqual("freshuser", json["username"])
        self.assertEqual("foo@bar.com", json["email"])

    def test_set_message(self):
        self.login(ADMIN_ACCESS_USER)

        # Create a message
        message = {"content": "new message", "severity": "info", "media_type": "text/plain"}
        self.postResponse(GlobalUserMessages, data=dict(message=message), expected_code=201)

        json = self.getJsonResponse(GlobalUserMessages)
        self.assertEqual(len(json["messages"]), 3)

        has_matching_message = False
        for message in json["messages"]:
            new_message_match = message["content"] == "new message"
            severity_match = message["severity"] == "info"
            media_type_match = message["media_type"] == "text/plain"
            if new_message_match and severity_match and media_type_match:
                has_matching_message = True
                break

        self.assertTrue(
            has_matching_message, "Could not find matching message in: " + str(json["messages"])
        )
        self.assertNotEqual(json["messages"][0]["content"], json["messages"][2]["content"])
        self.assertTrue(json["messages"][2]["uuid"])

    def test_delete_message(self):
        self.login(ADMIN_ACCESS_USER)
        json = self.getJsonResponse(GlobalUserMessages)
        self.deleteEmptyResponse(GlobalUserMessage, {"uuid": json["messages"][0]["uuid"]}, 204)

        json = self.getJsonResponse(GlobalUserMessages)

        self.assertEqual(len(json["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
