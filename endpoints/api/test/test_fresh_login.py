"""
Tests that verify @require_fresh_login is enforced on sensitive mutation endpoints.

Each test sets the session login_time past FRESH_LOGIN_TIMEOUT and verifies that
the endpoint returns 401 with a FreshLoginRequired error before performing the
underlying mutation.
"""

import datetime

import pytest

from app import instance_keys
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.model import api_token
from endpoints.api import FRESH_LOGIN_TIMEOUT, api, require_fresh_login
from endpoints.api.appspecifictokens import AppToken, AppTokens
from endpoints.api.billing import (
    OrganizationCard,
    OrganizationPlan,
    OrganizationRhSku,
    OrganizationRhSkuBatchRemoval,
    OrganizationRhSkuSubscriptionField,
    UserCard,
    UserPlan,
)
from endpoints.api.mirror import RepoMirrorResource
from endpoints.api.org_mirror import OrgMirrorConfig
from endpoints.api.organization import (
    Organization,
    OrganizationApplicationResetClientSecret,
    OrganizationApplicationResource,
    OrganizationApplications,
    OrganizationList,
    OrganizationMember,
    OrganizationProxyCacheConfig,
)
from endpoints.api.organization_application_tokens import (
    OrganizationApplicationToken,
    OrganizationApplicationTokens,
)
from endpoints.api.permission import RepositoryTeamPermission, RepositoryUserPermission
from endpoints.api.team import InviteTeamMember, OrganizationTeam, TeamMember
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import (
    ClientKey,
    ConvertToOrganization,
    DetachExternal,
    User,
    UserAuthorization,
)
from endpoints.exception import Unauthorized
from endpoints.test.shared import client_with_identity
from test.fixtures import *

# Margin beyond FRESH_LOGIN_TIMEOUT to ensure the session is stale
_STALE_MARGIN = datetime.timedelta(minutes=10)


def _stale_session(cl):
    """Set session login_time past FRESH_LOGIN_TIMEOUT so the session is stale."""
    with cl.session_transaction() as sess:
        sess["login_time"] = datetime.datetime.now() - FRESH_LOGIN_TIMEOUT - _STALE_MARGIN


def _assert_fresh_login_required(response):
    """Assert the response is a 401 FreshLoginRequired error."""
    assert response.status_code == 401
    data = response.json
    assert (
        data.get("title") == "fresh_login_required"
        or data.get("error_type") == "fresh_login_required"
    )


# ---------------------------------------------------------------------------
# Organization endpoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "endpoint, method, params, body",
    [
        (OrganizationList, "POST", {}, {"name": "freshorg", "email": "f@e.com"}),
        (
            Organization,
            "PUT",
            {"orgname": "buynlarge"},
            {"email": "new@example.com"},
        ),
        (
            OrganizationMember,
            "DELETE",
            {"orgname": "buynlarge", "membername": "reader"},
            None,
        ),
        (
            OrganizationApplications,
            "POST",
            {"orgname": "buynlarge"},
            {"name": "testapp"},
        ),
        (
            OrganizationApplicationResource,
            "PUT",
            {"orgname": "buynlarge", "client_id": "fakeclientid"},
            {
                "name": "updated-app",
                "redirect_uri": "http://example.com/callback",
                "application_uri": "http://example.com",
            },
        ),
        (
            OrganizationApplicationResource,
            "DELETE",
            {"orgname": "buynlarge", "client_id": "fakeclientid"},
            None,
        ),
        (
            OrganizationApplicationResetClientSecret,
            "POST",
            {"orgname": "buynlarge", "client_id": "fakeclientid"},
            None,
        ),
        (
            OrganizationApplicationTokens,
            "POST",
            {"orgname": "buynlarge", "client_id": "fakeclientid"},
            {"scope": "repo:read"},
        ),
        (
            OrganizationApplicationToken,
            "DELETE",
            {"orgname": "buynlarge", "client_id": "fakeclientid", "token_uuid": "faketoken"},
            None,
        ),
        (
            OrganizationProxyCacheConfig,
            "POST",
            {"orgname": "buynlarge"},
            {"upstream_registry": "docker.io"},
        ),
    ],
)
def test_organization_mutation_requires_fresh_login(endpoint, method, params, body, app):
    with client_with_identity("devtable", app) as cl:
        _stale_session(cl)
        result = conduct_api_call(cl, endpoint, method, params, body, expected_code=401)
        _assert_fresh_login_required(result)


# ---------------------------------------------------------------------------
# Permission endpoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "endpoint, method, params, body",
    [
        (
            RepositoryUserPermission,
            "PUT",
            {"repository": "devtable/simple", "username": "public"},
            {"role": "read"},
        ),
        (
            RepositoryUserPermission,
            "DELETE",
            {"repository": "devtable/simple", "username": "public"},
            None,
        ),
        (
            RepositoryTeamPermission,
            "PUT",
            {"repository": "buynlarge/orgrepo", "teamname": "owners"},
            {"role": "admin"},
        ),
        (
            RepositoryTeamPermission,
            "DELETE",
            {"repository": "buynlarge/orgrepo", "teamname": "owners"},
            None,
        ),
    ],
)
def test_permission_mutation_requires_fresh_login(endpoint, method, params, body, app):
    with client_with_identity("devtable", app) as cl:
        _stale_session(cl)
        result = conduct_api_call(cl, endpoint, method, params, body, expected_code=401)
        _assert_fresh_login_required(result)


# ---------------------------------------------------------------------------
# Team endpoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "endpoint, method, params, body",
    [
        (
            OrganizationTeam,
            "PUT",
            {"orgname": "buynlarge", "teamname": "newteam"},
            {"role": "member"},
        ),
        (
            OrganizationTeam,
            "DELETE",
            {"orgname": "buynlarge", "teamname": "readers"},
            None,
        ),
        (
            TeamMember,
            "PUT",
            {"orgname": "buynlarge", "teamname": "owners", "membername": "reader"},
            None,
        ),
        (
            TeamMember,
            "DELETE",
            {"orgname": "buynlarge", "teamname": "owners", "membername": "devtable"},
            None,
        ),
        (
            InviteTeamMember,
            "PUT",
            {
                "orgname": "buynlarge",
                "teamname": "owners",
                "email": "fresh@example.com",
            },
            None,
        ),
        (
            InviteTeamMember,
            "DELETE",
            {
                "orgname": "buynlarge",
                "teamname": "owners",
                "email": "fresh@example.com",
            },
            None,
        ),
    ],
)
def test_team_mutation_requires_fresh_login(endpoint, method, params, body, app):
    with client_with_identity("devtable", app) as cl:
        _stale_session(cl)
        result = conduct_api_call(cl, endpoint, method, params, body, expected_code=401)
        _assert_fresh_login_required(result)


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "endpoint, method, params, body",
    [
        (User, "PUT", {}, {"email": "new@example.com"}),
        (User, "DELETE", {}, None),
        (ClientKey, "POST", {}, {"password": "password"}),
        (
            ConvertToOrganization,
            "POST",
            {},
            {"adminUser": "devtable", "adminPassword": "password"},
        ),
        (DetachExternal, "POST", {"service_id": "github"}, None),
        (
            UserAuthorization,
            "DELETE",
            {"access_token_uuid": "00000000-0000-0000-0000-000000000000"},
            None,
        ),
    ],
)
def test_user_mutation_requires_fresh_login(endpoint, method, params, body, app):
    with client_with_identity("devtable", app) as cl:
        _stale_session(cl)
        result = conduct_api_call(cl, endpoint, method, params, body, expected_code=401)
        _assert_fresh_login_required(result)


# ---------------------------------------------------------------------------
# Billing endpoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "endpoint, method, params, body",
    [
        (UserCard, "POST", {}, {"token": "tok_test"}),
        (OrganizationCard, "POST", {"orgname": "buynlarge"}, {"token": "tok_test"}),
        (UserPlan, "POST", {}, {"plan": "free"}),
        (UserPlan, "PUT", {}, {"plan": "free"}),
        (OrganizationPlan, "POST", {"orgname": "buynlarge"}, {"plan": "free"}),
        (OrganizationPlan, "PUT", {"orgname": "buynlarge"}, {"plan": "free"}),
        (
            OrganizationRhSku,
            "POST",
            {"orgname": "buynlarge"},
            {"subscriptions": [{"subscription_id": 1}]},
        ),
        (
            OrganizationRhSkuBatchRemoval,
            "POST",
            {"orgname": "buynlarge"},
            {"subscriptions": [{"subscription_id": 1}]},
        ),
        (
            OrganizationRhSkuSubscriptionField,
            "DELETE",
            {"orgname": "buynlarge", "subscription_id": 1},
            None,
        ),
    ],
)
def test_billing_mutation_requires_fresh_login(endpoint, method, params, body, app):
    with client_with_identity("devtable", app) as cl:
        _stale_session(cl)
        result = conduct_api_call(cl, endpoint, method, params, body, expected_code=401)
        _assert_fresh_login_required(result)


# ---------------------------------------------------------------------------
# Mirror endpoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "endpoint, method, params, body",
    [
        (
            RepoMirrorResource,
            "POST",
            {"repository": "devtable/simple"},
            {
                "external_reference": "docker.io/library/alpine",
                "sync_interval": 3600,
                "sync_start_date": "2025-01-01T00:00:00Z",
                "root_rule": {"rule_kind": "tag_glob_csv", "rule_value": ["latest"]},
            },
        ),
        (
            RepoMirrorResource,
            "PUT",
            {"repository": "devtable/simple"},
            {"sync_interval": 7200},
        ),
        (
            OrgMirrorConfig,
            "POST",
            {"orgname": "buynlarge"},
            {"external_registry_url": "https://quay.io", "external_namespace": "projectquay"},
        ),
        (
            OrgMirrorConfig,
            "PUT",
            {"orgname": "buynlarge"},
            {"sync_interval": 7200},
        ),
    ],
)
def test_mirror_mutation_requires_fresh_login(endpoint, method, params, body, app):
    with client_with_identity("devtable", app) as cl:
        _stale_session(cl)
        result = conduct_api_call(cl, endpoint, method, params, body, expected_code=401)
        _assert_fresh_login_required(result)


# ---------------------------------------------------------------------------
# Robot credentials
# ---------------------------------------------------------------------------
def _put_repo_permission_as_robot(app, bearer, expected_code):
    with client_with_identity(None, app) as cl:
        conduct_api_call(
            cl,
            RepositoryUserPermission,
            "PUT",
            {"repository": "devtable/simple", "username": "public"},
            {"role": "read"},
            expected_code,
            headers={"Authorization": "Bearer " + bearer},
        )


# repo:read pins scope enforcement after the exemption: require_repo_admin refuses it before
# require_fresh_login runs, so it does not exercise the exemption itself.
@pytest.mark.parametrize("scope, expected_code", [("repo:admin", 200), ("repo:read", 403)])
def test_robot_api_token_skips_fresh_login(scope, expected_code, app):
    robot = model.user.lookup_robot("devtable+dtrobot")
    model.permission.set_user_repo_permission(robot.username, "devtable", "simple", "admin")
    _, secret = api_token.create_token_under_limit(
        robot, model.user.get_user("devtable"), scope, 3600, "CI token"
    )

    _put_repo_permission_as_robot(app, secret, expected_code)


def test_federated_robot_jwt_skips_fresh_login(app):
    robot, _ = model.user.create_robot("freshfed", model.user.get_user("devtable"))
    model.permission.set_user_repo_permission(robot.username, "devtable", "simple", "admin")
    binding = model.user.create_robot_federation_config(
        robot,
        [
            {
                "issuer": "https://issuer.example",
                "subject": "system:serviceaccount:ci:builder",
                "audiences": ["quay"],
                "api_scopes": "repo:admin",
            }
        ],
    )[0]
    token = model.user.generate_federated_robot_jwt_token(
        instance_keys, robot, "repo:admin", binding
    )

    _put_repo_permission_as_robot(app, token, 200)


def test_plain_robot_credentials_require_fresh_login_refused(app):
    robot = model.user.lookup_robot("devtable+dtrobot")
    with app.test_request_context():
        ValidateResult(AuthKind.credentials, robot=robot).apply_to_context()
        with pytest.raises(Unauthorized):
            require_fresh_login(lambda: None)()


@pytest.mark.parametrize(
    "endpoint, method, params, body",
    [
        (AppTokens, "POST", None, {"title": "ci"}),
        (AppToken, "GET", {"token_uuid": "someuuid"}, None),
        (AppToken, "DELETE", {"token_uuid": "someuuid"}, None),
        (User, "PUT", None, {"password": "newpassword123"}),
        (User, "DELETE", None, None),
    ],
)
def test_robot_api_token_refused_on_user_account_endpoints(endpoint, method, params, body, app):
    robot = model.user.lookup_robot("devtable+dtrobot")
    _, secret = api_token.create_token_under_limit(
        robot, model.user.get_user("devtable"), "user:admin", 3600, "CI token"
    )

    with client_with_identity(None, app) as cl:
        conduct_api_call(
            cl, endpoint, method, params, body, 403, headers={"Authorization": "Bearer " + secret}
        )
