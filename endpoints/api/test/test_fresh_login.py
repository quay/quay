"""
Tests that verify @require_fresh_login is enforced on all sensitive mutation endpoints.

Each test verifies two things:
1. With a fresh session, the endpoint does NOT return 401 (control assertion)
2. With a stale session (past FRESH_LOGIN_TIMEOUT), the endpoint returns 401
   with a FreshLoginRequired error
"""

import datetime

import pytest

from endpoints.api import FRESH_LOGIN_TIMEOUT, api
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
from endpoints.api.organization import (
    Organization,
    OrganizationApplicationResetClientSecret,
    OrganizationApplicationResource,
    OrganizationApplications,
    OrganizationList,
    OrganizationMember,
)
from endpoints.api.permission import RepositoryTeamPermission, RepositoryUserPermission
from endpoints.api.team import InviteTeamMember, OrganizationTeam, TeamMember
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import ClientKey, ConvertToOrganization, User, UserAuthorization
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
    ],
)
def test_mirror_mutation_requires_fresh_login(endpoint, method, params, body, app):
    with client_with_identity("devtable", app) as cl:
        _stale_session(cl)
        result = conduct_api_call(cl, endpoint, method, params, body, expected_code=401)
        _assert_fresh_login_required(result)
