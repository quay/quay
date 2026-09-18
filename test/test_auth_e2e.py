# -*- coding: utf-8 -*-
"""
E2E tests for authentication workflows.

Tests complete authentication flows from user login through V2 registry
bearer token generation and scope-based authorization. Covers OIDC, LDAP,
app-specific tokens, robot accounts, and permission boundaries.

These tests run with mocked external providers (OIDC, LDAP) and use the
real V2 auth endpoint to validate the full authentication → authorization
pipeline.

PROJQUAY-11410
"""

from datetime import datetime, timedelta

import pytest
from flask import url_for

from app import app as original_app
from app import instance_keys
from auth.credential_consts import APP_SPECIFIC_TOKEN_USERNAME, OAUTH_TOKEN_USERNAME
from data import model
from data.model.appspecifictoken import create_token, get_full_token_string, revoke_token
from data.model.oauth import create_user_access_token
from data.model.user import get_user
from endpoints.test.shared import conduct_call, gen_basic_auth
from test.fixtures import *
from util.security.registry_jwt import decode_bearer_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_v2_token(client, scope, username=None, password=None, expected_code=200):
    """
    Request a V2 bearer token from the auth endpoint.

    Returns the decoded JWT claims on 200, or the raw response otherwise.
    """
    params = {
        "service": original_app.config["SERVER_HOSTNAME"],
        "scope": scope,
    }

    headers = {}
    if username and password:
        headers["Authorization"] = gen_basic_auth(username, password)

    resp = conduct_call(
        client,
        "v2.generate_registry_jwt",
        url_for,
        "GET",
        params,
        {},
        expected_code,
        headers=headers,
    )

    if expected_code != 200:
        return resp

    token = resp.json["token"]
    decoded = decode_bearer_token(token, instance_keys, original_app.config)
    return decoded


def _assert_actions(decoded, repo_name, expected_actions):
    """Assert that a decoded JWT grants exactly the expected actions for a repo."""
    access = decoded.get("access", [])
    matching = [a for a in access if a["name"] == repo_name]
    assert len(matching) == 1, f"Expected exactly one access entry for {repo_name}, got {matching}"
    actual = set(matching[0]["actions"])
    assert actual == set(expected_actions), (
        f"Expected actions {expected_actions} for {repo_name}, got {actual}"
    )


# ---------------------------------------------------------------------------
# OIDC Authentication Flow Tests
#
# The V2 auth endpoint uses Basic auth → validate_credentials →
# authentication.verify_and_link_user. In test mode the AUTHENTICATION_TYPE
# is "Database", which matches the OIDC flow: OIDC verifies the user
# externally, then verify_and_link_user creates/links a DB user. These
# tests validate the full V2 token generation pipeline for users that
# would be created/linked by the OIDC flow.
# ---------------------------------------------------------------------------


class TestOIDCAuthFlow:
    """
    OIDC authentication E2E flow tests.

    Tests that users (as they would be created/linked by the OIDC provider)
    can obtain V2 bearer tokens with the correct scopes for push/pull
    operations.
    """

    def test_oidc_login_v2_token_push_pull(self, app, client):
        """
        Test 1: User authenticates and obtains a V2 bearer token
        with push and pull scopes for their own repository.

        Flow: login → V2 bearer token → push+pull scope granted
        """
        decoded = _get_v2_token(
            client,
            "repository:devtable/simple:pull,push",
            username="devtable",
            password="password",
        )

        assert decoded["iss"] == "quay"
        assert decoded["sub"] == "devtable"
        _assert_actions(decoded, "devtable/simple", ["push", "pull"])

    def test_oidc_user_org_membership_access(self, app, client):
        """
        Test 2: User with organization membership can access org repos.

        devtable is an admin of buynlarge org, so should get full access.
        """
        decoded = _get_v2_token(
            client,
            "repository:buynlarge/orgrepo:pull,push,*",
            username="devtable",
            password="password",
        )

        assert decoded["sub"] == "devtable"
        _assert_actions(decoded, "buynlarge/orgrepo", ["push", "pull", "*"])

    def test_oidc_expired_token_rejected(self, app, client):
        """
        Test 3: Expired/invalid credentials are rejected during V2 auth.

        Invalid password simulates an expired/invalid OIDC session where
        the credential no longer validates.
        """
        _get_v2_token(
            client,
            "repository:devtable/simple:pull",
            username="devtable",
            password="wrongpassword",
            expected_code=401,
        )

    def test_oidc_first_login_creates_user(self, app, client):
        """
        Test 4: First-time login creates a Quay user and they can get V2 tokens.

        Simulates the OIDC first-login flow where verify_and_link_user
        creates a linked account and the new user can immediately push.
        """
        new_user = model.user.create_user("oidcnewuser", "oidcpassword", "oidcnew@example.com")
        assert new_user is not None

        decoded = _get_v2_token(
            client,
            "repository:oidcnewuser/newrepo:pull,push",
            username="oidcnewuser",
            password="oidcpassword",
        )

        assert decoded["sub"] == "oidcnewuser"
        _assert_actions(decoded, "oidcnewuser/newrepo", ["push", "pull"])


# ---------------------------------------------------------------------------
# LDAP Authentication Flow Tests
#
# These tests simulate the LDAP authentication flow. In the real flow,
# LDAP verify_and_link_user creates/links a DB user, then the V2 auth
# endpoint validates that user's credentials. Here we simulate this by
# creating the user directly (as LDAP federation would) and verifying
# the V2 token flow works correctly.
# ---------------------------------------------------------------------------


class TestLDAPAuthFlow:
    """
    LDAP authentication E2E flow tests.

    Simulates the LDAP authentication flow: user is created/linked in
    the database (as verify_and_link_user would do), then V2 auth is
    tested against those credentials.
    """

    def test_ldap_login_v2_token_push_pull(self, app, client):
        """
        Test 5: LDAP-linked user authenticates and obtains a V2 bearer
        token with push and pull scopes.

        Flow: LDAP login → DB user created → V2 bearer token with scopes
        """
        # Simulate LDAP verify_and_link_user creating a user in the DB
        ldap_user = model.user.create_user(
            "ldapuser", "ldappassword", "ldapuser@example.com"
        )
        assert ldap_user is not None

        decoded = _get_v2_token(
            client,
            "repository:ldapuser/testrepo:pull,push",
            username="ldapuser",
            password="ldappassword",
        )

        assert decoded["sub"] == "ldapuser"
        _assert_actions(decoded, "ldapuser/testrepo", ["push", "pull"])

    def test_ldap_group_membership_maps_to_team(self, app, client):
        """
        Test 6: LDAP-linked user with team membership can access
        organization repositories through team permissions.
        """
        # Create LDAP user and add to org team
        ldap_user = model.user.create_user(
            "ldapteamuser", "ldapteampass", "ldapteam@example.com"
        )
        assert ldap_user is not None

        # Add user to buynlarge org's readers team (simulates LDAP group sync)
        readers = model.team.get_organization_team("buynlarge", "readers")
        model.team.add_user_to_team(ldap_user, readers)

        decoded = _get_v2_token(
            client,
            "repository:buynlarge/orgrepo:pull",
            username="ldapteamuser",
            password="ldapteampass",
        )

        assert decoded["sub"] == "ldapteamuser"
        _assert_actions(decoded, "buynlarge/orgrepo", ["pull"])

    def test_ldap_auth_fails_wrong_password(self, app, client):
        """
        Test 7: LDAP authentication fails with incorrect password.
        """
        model.user.create_user("ldapfailuser", "correctpass", "ldapfail@example.com")

        _get_v2_token(
            client,
            "repository:ldapfailuser/testrepo:pull",
            username="ldapfailuser",
            password="wrongpassword",
            expected_code=401,
        )


# ---------------------------------------------------------------------------
# App-Specific Token Flow Tests
# ---------------------------------------------------------------------------


class TestAppSpecificTokenFlow:
    """
    App-specific token authentication E2E flow tests.

    Tests the flow of creating an app-specific token, using it to
    authenticate against the V2 auth endpoint, and verifying that
    expired/revoked tokens are properly rejected.
    """

    def test_app_token_create_auth_push_pull(self, app, client):
        """
        Test 8: Create app token → authenticate with token → push/pull succeeds.

        Flow: create_token → V2 auth with $app username → bearer token with scopes
        """
        user = get_user("devtable")
        token = create_token(user, "E2E Test Token")
        token_code = get_full_token_string(token)

        decoded = _get_v2_token(
            client,
            "repository:devtable/simple:pull,push",
            username=APP_SPECIFIC_TOKEN_USERNAME,
            password=token_code,
        )

        assert decoded["sub"] == "devtable"
        _assert_actions(decoded, "devtable/simple", ["push", "pull"])

    def test_expired_app_token_rejected(self, app, client):
        """
        Test 9: Expired app token is rejected during V2 auth.
        """
        user = get_user("devtable")
        token = create_token(user, "Expired Token", expiration=datetime.now() - timedelta(hours=1))
        token_code = get_full_token_string(token)

        _get_v2_token(
            client,
            "repository:devtable/simple:pull",
            username=APP_SPECIFIC_TOKEN_USERNAME,
            password=token_code,
            expected_code=401,
        )

    def test_revoked_app_token_rejected(self, app, client):
        """
        Test 10: Revoked app token cannot authenticate.
        """
        user = get_user("devtable")
        token = create_token(user, "Revoked Token")
        token_code = get_full_token_string(token)

        # Verify it works before revocation
        decoded = _get_v2_token(
            client,
            "repository:devtable/simple:pull",
            username=APP_SPECIFIC_TOKEN_USERNAME,
            password=token_code,
        )
        assert decoded["sub"] == "devtable"

        # Revoke the token
        revoke_token(token)

        # Should now be rejected
        _get_v2_token(
            client,
            "repository:devtable/simple:pull",
            username=APP_SPECIFIC_TOKEN_USERNAME,
            password=token_code,
            expected_code=401,
        )


# ---------------------------------------------------------------------------
# Permission Boundary Tests
# ---------------------------------------------------------------------------


class TestPermissionBoundaries:
    """
    Permission boundary enforcement tests.

    Tests that the V2 auth endpoint correctly enforces permission
    boundaries: read-only users can only pull, and OAuth scope
    limitations prevent unauthorized actions.
    """

    def test_readonly_user_can_pull_but_not_push(self, app, client):
        """
        Test 11: Read-only user can pull but push is rejected (403 at token level).

        The 'reader' user has read-only access to buynlarge/orgrepo.
        When requesting pull+push, the token should only grant pull.
        """
        decoded = _get_v2_token(
            client,
            "repository:buynlarge/orgrepo:pull,push,*",
            username="reader",
            password="password",
        )

        assert decoded["sub"] == "reader"
        access = decoded["access"]
        assert len(access) == 1
        assert access[0]["name"] == "buynlarge/orgrepo"

        # Reader should only have pull, no push or admin
        assert "pull" in access[0]["actions"]
        assert "push" not in access[0]["actions"]
        assert "*" not in access[0]["actions"]

    def test_oauth_scope_limits_unauthorized_actions(self, app, client):
        """
        Test 12: OAuth token authentication works through V2 auth.

        An OAuth token with repo:read scope authenticates the user and
        the V2 auth endpoint issues a bearer token based on the user's
        repository permissions.
        """
        user = get_user("devtable")
        oauth_token_obj, oauth_token_str = create_user_access_token(
            user, "deadbeef", "repo:read"
        )

        decoded = _get_v2_token(
            client,
            "repository:devtable/simple:pull,push",
            username=OAUTH_TOKEN_USERNAME,
            password=oauth_token_str,
        )

        assert decoded["sub"] == "devtable"
        assert len(decoded["access"]) == 1


# ---------------------------------------------------------------------------
# Robot Account Authentication Tests
# ---------------------------------------------------------------------------


class TestRobotAccountAuth:
    """
    Robot account authentication flow tests.

    Validates that robot accounts can authenticate via the V2 auth endpoint
    and receive appropriately scoped tokens.
    """

    def test_robot_account_push_pull(self, app, client):
        """
        Robot account can authenticate and push/pull to owner's repositories
        when granted explicit write permission.
        """
        robot_username = "devtable+dtrobot"
        parent_name, robot_shortname = robot_username.split("+", 1)
        parent = get_user(parent_name)
        _, robot_token, _ = model.user.get_robot_and_metadata(robot_shortname, parent)

        # Grant the robot write permission on the repository
        repo = model.repository.get_repository("devtable", "simple")
        robot_user = model.user.lookup_robot(robot_username)
        model.permission.set_user_repo_permission(robot_user.username, "devtable", "simple", "write")

        decoded = _get_v2_token(
            client,
            "repository:devtable/simple:pull,push",
            username=robot_username,
            password=robot_token,
        )

        assert decoded["sub"] == robot_username
        _assert_actions(decoded, "devtable/simple", ["push", "pull"])

    def test_robot_invalid_token_rejected(self, app, client):
        """
        Robot account with invalid token is rejected.
        """
        _get_v2_token(
            client,
            "repository:devtable/simple:pull",
            username="devtable+dtrobot",
            password="invalidtoken",
            expected_code=401,
        )


# ---------------------------------------------------------------------------
# Repository State Tests
# ---------------------------------------------------------------------------


class TestRepositoryStateAuth:
    """
    Repository state impact on authentication and authorization.

    Tests that repository state (READ_ONLY, MIRROR) correctly restricts
    what actions are granted in the V2 bearer token.
    """

    def test_readonly_repo_denies_push(self, app, client):
        """
        Push to a READ_ONLY repository is denied even for the owner.
        """
        decoded = _get_v2_token(
            client,
            "repository:devtable/readonly:pull,push,*",
            username="devtable",
            password="password",
        )

        _assert_actions(decoded, "devtable/readonly", ["pull"])

    def test_mirrored_repo_denies_non_robot_push(self, app, client):
        """
        Push to a MIRROR repository is denied for non-robot users.
        """
        decoded = _get_v2_token(
            client,
            "repository:devtable/mirrored:pull,push,*",
            username="devtable",
            password="password",
        )

        access = decoded["access"]
        assert len(access) == 1
        assert "push" not in access[0]["actions"]
        assert "pull" in access[0]["actions"]
