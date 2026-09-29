"""
E2E tests for authentication flows through V2 registry endpoints.

These tests verify complete authentication flows from user login through V2
registry push/pull operations. They exercise the integration between
authentication systems (OIDC, LDAP, app-specific tokens, robot accounts) and
the V2 registry auth endpoint.

Tier 1: Mocked tests (CI/CD) - Fast feedback on every PR.
    External providers (OIDC, LDAP) are mocked at the service boundary so that
    every internal code path (credential validation, scope negotiation, JWT
    minting, permission downscoping) is exercised without network dependencies.
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import jwt
import pytest
from flask import url_for
from freezegun import freeze_time

from app import app as original_app
from app import instance_keys
from auth.credential_consts import APP_SPECIFIC_TOKEN_USERNAME, OAUTH_TOKEN_USERNAME
from data import model
from data.model.appspecifictoken import (
    create_token,
    get_full_token_string,
    revoke_token,
)
from data.model.user import get_robot_and_metadata, get_user
from data.registry_model import registry_model
from endpoints.test.shared import conduct_call, gen_basic_auth
from test.fixtures import *  # noqa: F401, F403
from util.security.registry_jwt import decode_bearer_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_actions(decoded, repo_name):
    """Extract the actions list for *repo_name* from a decoded JWT."""
    for entry in decoded.get("access", []):
        if entry["name"] == repo_name:
            return entry["actions"]
    return []


def _build_id_token(sub, email, username, issuer="http://fakeoidc", exp=None):
    """Return a JWT string **and** the raw payload dict for mock OIDC tests.

    Because ``validate_sso_oauth_token`` delegates decoding to the mocked
    ``OIDCLoginService.decode_user_jwt``, the token only needs to be a
    syntactically valid JWT so that ``is_jwt`` and ``get_jwt_issuer`` succeed.

    Returns:
        ``(token_string, payload_dict)`` — callers can feed *payload_dict*
        straight into the mock without a redundant ``jwt.decode`` call.
    """
    now = int(time.time())
    payload = {
        "iss": issuer,
        "sub": sub,
        "email": email,
        "email_verified": True,
        "preferred_username": username,
        "iat": now,
        "exp": exp or (now + 600),
    }
    token_str = jwt.encode(payload, "test-secret-key-for-e2e-tests", algorithm="HS256")
    return token_str, payload


def _make_oidc_mock(decoded_payload, side_effect=None):
    """Create a mock ``OIDCLoginService`` that returns *decoded_payload*."""
    from oauth.oidc import OIDCLoginService

    svc = MagicMock(spec=OIDCLoginService)
    svc.service_id.return_value = "testoidc"
    svc.service_name.return_value = "Test OIDC"
    svc.login_binding_field.return_value = None
    svc.config = {}
    svc.allowed_clients = []
    svc.get_user_id.return_value = decoded_payload.get("sub") if decoded_payload else None

    if side_effect:
        svc.decode_user_jwt.side_effect = side_effect
    else:
        svc.decode_user_jwt.return_value = decoded_payload
    return svc


def _ensure_federated_login(user, service_id, service_ident):
    """Link *user* to a federated service, skipping if already linked."""
    if model.user.lookup_federated_login(user, service_id) is not None:
        return
    model.user.attach_federated_login(user, service_id, service_ident)


# ---------------------------------------------------------------------------
# Fixtures for resource lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture()
def devtable_app_token():
    """Create an app-specific token for devtable; delete on teardown."""
    user = model.user.get_user("devtable")
    token = create_token(user, "E2E test token")
    yield token, get_full_token_string(token)
    try:
        token.delete_instance()
    except model.appspecifictoken.AppSpecificAuthToken.DoesNotExist:
        pass


@pytest.fixture()
def expired_app_token():
    """Create an already-expired app-specific token; delete on teardown."""
    user = model.user.get_user("devtable")
    expired_time = datetime(2020, 1, 1, 0, 0, 0)
    token = create_token(user, "Expired E2E token", expiration=expired_time)
    yield token, get_full_token_string(token)
    try:
        token.delete_instance()
    except model.appspecifictoken.AppSpecificAuthToken.DoesNotExist:
        pass


@pytest.fixture()
def revocable_app_token():
    """Create a token that the test will revoke; ensure cleanup regardless."""
    user = model.user.get_user("devtable")
    token = create_token(user, "Token to revoke")
    yield token, get_full_token_string(token)
    try:
        token.delete_instance()
    except model.appspecifictoken.AppSpecificAuthToken.DoesNotExist:
        pass


@pytest.fixture()
def oauth_read_token():
    """Create an OAuth app + read-only access token; clean up on teardown."""
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")

    oauth_app = model.oauth.create_application(
        org,
        "test-e2e-oauth-app",
        "http://localhost/callback",
        "http://localhost",
        client_id="test-e2e-client-id",
    )
    token_obj, token_string = model.oauth.create_user_access_token(
        user, oauth_app.client_id, "repo:read"
    )

    yield token_obj, token_string

    try:
        token_obj.delete_instance()
    finally:
        oauth_app.delete_instance()


@pytest.fixture()
def disabled_freshuser_token():
    """Create a token for freshuser, disable the account, restore on teardown."""
    user = model.user.get_user("freshuser")
    token = create_token(user, "Disable test token")
    token_code = get_full_token_string(token)

    user.enabled = False
    user.save()

    yield token_code

    try:
        user.enabled = True
        user.save()
    finally:
        try:
            token.delete_instance()
        except model.appspecifictoken.AppSpecificAuthToken.DoesNotExist:
            pass


@pytest.fixture()
def oidc_new_user_cleanup():
    """Yield a username; delete the user and its federated login on teardown."""
    username = "brandnewoidcusere2e"
    yield username
    created = model.user.get_user(username)
    if created is not None:
        fed = model.user.lookup_federated_login(created, "testoidc")
        if fed is not None:
            fed.delete_instance()
        try:
            model.user.delete_user(created, [])
        except Exception:
            created.delete_instance(recursive=True)


# ===========================================================================
# OIDC Authentication Flow Tests (Tests 1-4)
# ===========================================================================


class TestOIDCAuthFlow:
    """End-to-end tests for OIDC authentication through V2 registry auth.

    OIDC tokens reach the V2 auth endpoint as ``$oauthtoken:<jwt>`` via the
    basic auth header.  The credential validator identifies the JWT, resolves
    the issuer to a configured ``OIDCLoginService``, verifies the signature,
    and links/creates the Quay user.  These tests mock the
    ``OIDCLoginService`` at the boundary so that every downstream path
    (``validate_sso_oauth_token → _conduct_oauth_login → v2auth``) runs
    against the real code.
    """

    # ---- Test 1 ----

    def test_oidc_login_v2_bearer_push_pull(self, app, client):
        """OIDC login → V2 bearer token → push/pull manifest success.

        A user authenticates with an OIDC JWT token via ``$oauthtoken``,
        receives a V2 bearer token, then uses it to push and pull a manifest.
        """
        user = model.user.get_user("devtable")
        sub = "oidc-devtable-001"

        id_token, payload = _build_id_token(sub, "devtable@example.com", "devtable")
        _ensure_federated_login(user, "testoidc", sub)
        svc = _make_oidc_mock(payload)

        with patch("auth.oauth.oauth_login") as mock_mgr:
            mock_mgr.get_service_by_issuer.return_value = svc

            params = {
                "service": original_app.config["SERVER_HOSTNAME"],
                "scope": "repository:devtable/simple:pull,push",
            }
            headers = {"Authorization": gen_basic_auth(OAUTH_TOKEN_USERNAME, id_token)}

            resp = conduct_call(
                client,
                "v2.generate_registry_jwt",
                url_for,
                "GET",
                params,
                {},
                200,
                headers=headers,
            )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "devtable/simple")
        assert "push" in actions, "OIDC user should have push access to own repo"
        assert "pull" in actions, "OIDC user should have pull access to own repo"

        # Use the OIDC-issued bearer token to push a manifest.
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=201,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        # Use the same token to pull the manifest back.
        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

    # ---- Test 2 ----

    def test_oidc_user_org_membership_access(self, app, client):
        """OIDC user with org membership can access org repositories.

        An OIDC-authenticated user who is an admin of an organization
        receives full access and can push/pull manifests to that org's repos.
        """
        user = model.user.get_user("devtable")
        sub = "oidc-devtable-001"

        id_token, payload = _build_id_token(sub, "devtable@example.com", "devtable")
        _ensure_federated_login(user, "testoidc", sub)
        svc = _make_oidc_mock(payload)

        with patch("auth.oauth.oauth_login") as mock_mgr:
            mock_mgr.get_service_by_issuer.return_value = svc

            params = {
                "service": original_app.config["SERVER_HOSTNAME"],
                "scope": "repository:buynlarge/orgrepo:pull,push,*",
            }
            headers = {"Authorization": gen_basic_auth(OAUTH_TOKEN_USERNAME, id_token)}

            resp = conduct_call(
                client,
                "v2.generate_registry_jwt",
                url_for,
                "GET",
                params,
                {},
                200,
                headers=headers,
            )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "buynlarge/orgrepo")
        assert "push" in actions, "Org admin should have push via OIDC"
        assert "pull" in actions, "Org admin should have pull via OIDC"
        assert "*" in actions, "Org admin should have admin via OIDC"

        # Use the OIDC-issued bearer token to push and pull an org repo manifest.
        repo_ref = registry_model.lookup_repository("buynlarge", "orgrepo")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "buynlarge/orgrepo", "manifest_ref": manifest.digest},
            expected_code=201,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "buynlarge/orgrepo", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

    # ---- Test 3 ----

    def test_oidc_expired_token_rejected(self, app, client):
        """OIDC token expiration is enforced (expired token rejected).

        An expired JWT is rejected during V2 auth, yielding a 401.
        """
        expired_token, _ = _build_id_token(
            "oidc-expired",
            "expired@example.com",
            "expireduser",
            exp=int(time.time()) - 3600,
        )

        svc = _make_oidc_mock(
            decoded_payload=None,
            side_effect=jwt.ExpiredSignatureError("Signature has expired"),
        )

        with patch("auth.oauth.oauth_login") as mock_mgr:
            mock_mgr.get_service_by_issuer.return_value = svc

            params = {
                "service": original_app.config["SERVER_HOSTNAME"],
                "scope": "repository:devtable/simple:pull",
            }
            headers = {"Authorization": gen_basic_auth(OAUTH_TOKEN_USERNAME, expired_token)}

            conduct_call(
                client,
                "v2.generate_registry_jwt",
                url_for,
                "GET",
                params,
                {},
                401,
                headers=headers,
            )

    # ---- Test 4 ----

    def test_oidc_first_login_creates_user(self, app, client, oidc_new_user_cleanup):
        """OIDC login creates Quay user on first authentication.

        A brand-new user authenticating via OIDC gets a Quay account created
        and linked to their OIDC identity.  The ``oidc_new_user_cleanup``
        fixture guarantees the user is removed on teardown.
        """
        new_sub = "oidc-brand-new-user-e2e-99"
        new_username = oidc_new_user_cleanup
        new_email = "brandnewe2e@example.com"

        assert model.user.get_user(new_username) is None

        id_token, payload = _build_id_token(new_sub, new_email, new_username)
        svc = _make_oidc_mock(payload)

        with patch("auth.oauth.oauth_login") as mock_mgr:
            mock_mgr.get_service_by_issuer.return_value = svc

            params = {
                "service": original_app.config["SERVER_HOSTNAME"],
                "scope": "",
            }
            headers = {"Authorization": gen_basic_auth(OAUTH_TOKEN_USERNAME, id_token)}

            resp = conduct_call(
                client,
                "v2.generate_registry_jwt",
                url_for,
                "GET",
                params,
                {},
                200,
                headers=headers,
            )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        created_user = model.user.get_user(new_username)
        assert created_user is not None, "First OIDC login should create a Quay user"
        assert decoded["sub"] == new_username

        fed = model.user.lookup_federated_login(created_user, "testoidc")
        assert fed is not None, "New user should be linked to OIDC service"
        assert fed.service_ident == new_sub


# ===========================================================================
# LDAP Authentication Flow Tests (Tests 5-7)
# ===========================================================================


class TestLDAPAuthFlow:
    """End-to-end tests for LDAP authentication through V2 registry auth.

    LDAP reaches the V2 auth endpoint as ``username:password`` basic auth.
    The credential validator delegates to ``authentication.verify_and_link_user``
    which, when backed by LDAP, performs the LDAP bind.  These tests mock that
    backend call while exercising the full V2 auth → JWT scope negotiation.
    """

    # ---- Test 5 ----

    def test_ldap_login_v2_bearer_push_pull(self, app, client):
        """LDAP login → V2 bearer token → push/pull manifest success.

        A user authenticates with LDAP credentials, receives a V2 bearer
        token, then uses it to push and pull a manifest.
        """
        user = model.user.get_user("devtable")

        with patch("auth.credentials.authentication") as mock_auth:
            mock_auth.verify_and_link_user.return_value = (user, None)

            params = {
                "service": original_app.config["SERVER_HOSTNAME"],
                "scope": "repository:devtable/simple:pull,push",
            }
            headers = {"Authorization": gen_basic_auth("devtable", "ldap-password")}

            resp = conduct_call(
                client,
                "v2.generate_registry_jwt",
                url_for,
                "GET",
                params,
                {},
                200,
                headers=headers,
            )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "devtable/simple")
        assert "push" in actions, "LDAP user should have push to own repo"
        assert "pull" in actions, "LDAP user should have pull to own repo"

        # Use the LDAP-issued bearer token to push a manifest.
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=201,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        # Use the same token to pull the manifest back.
        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

    # ---- Test 6 ----

    def test_ldap_group_membership_maps_to_team_permissions(self, app, client):
        """LDAP group membership maps to Quay team permissions.

        An LDAP user whose group/team gives them read-only access to an
        organization repository is correctly downscoped to pull-only and
        can fetch the manifest but not push.
        """
        reader = model.user.get_user("reader")

        with patch("auth.credentials.authentication") as mock_auth:
            mock_auth.verify_and_link_user.return_value = (reader, None)

            params = {
                "service": original_app.config["SERVER_HOSTNAME"],
                "scope": "repository:buynlarge/orgrepo:pull,push,*",
            }
            headers = {"Authorization": gen_basic_auth("reader", "ldap-password")}

            resp = conduct_call(
                client,
                "v2.generate_registry_jwt",
                url_for,
                "GET",
                params,
                {},
                200,
                headers=headers,
            )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "reader"
        actions = _get_actions(decoded, "buynlarge/orgrepo")
        assert "pull" in actions, "Reader should have pull via LDAP group"
        assert "push" not in actions, "Reader should NOT have push"
        assert "*" not in actions, "Reader should NOT have admin"

        # Pull succeeds with the downscoped token.
        repo_ref = registry_model.lookup_repository("buynlarge", "orgrepo")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "buynlarge/orgrepo", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

        # Push is rejected — the bearer token lacks the push action.
        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "buynlarge/orgrepo", "manifest_ref": manifest.digest},
            expected_code=401,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

    # ---- Test 7 ----

    def test_ldap_authentication_fails_with_wrong_password(self, app, client):
        """LDAP user authentication fails with incorrect password.

        The V2 auth endpoint rejects the request with 401 when the LDAP
        backend reports invalid credentials.
        """
        with patch("auth.credentials.authentication") as mock_auth:
            mock_auth.verify_and_link_user.return_value = (
                None,
                "Invalid username or password.",
            )

            params = {
                "service": original_app.config["SERVER_HOSTNAME"],
                "scope": "repository:devtable/simple:pull",
            }
            headers = {"Authorization": gen_basic_auth("devtable", "wrong-ldap-password")}

            conduct_call(
                client,
                "v2.generate_registry_jwt",
                url_for,
                "GET",
                params,
                {},
                401,
                headers=headers,
            )


# ===========================================================================
# App-Specific Token Flow Tests (Tests 8-10)
# ===========================================================================


class TestAppSpecificTokenFlow:
    """End-to-end tests for app-specific token authentication through V2 auth.

    App-specific tokens use the ``$app:<token_code>`` basic auth format.
    The credential validator looks up the token by prefix/suffix and validates
    expiration.  No external services are needed; the tokens exist directly in
    the database.  All token lifecycle is managed by yield fixtures.
    """

    # ---- Test 8 ----

    def test_app_token_push_pull_success(self, app, client, devtable_app_token):
        """Create app token → authenticate with token → push/pull succeeds.

        The full app-specific token lifecycle: create a token, authenticate
        via V2 auth, and use the bearer token to push and pull a manifest.
        """
        _token_obj, token_code = devtable_app_token

        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/simple:pull,push",
        }
        headers = {"Authorization": gen_basic_auth(APP_SPECIFIC_TOKEN_USERNAME, token_code)}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "devtable/simple")
        assert "push" in actions, "App token should grant push"
        assert "pull" in actions, "App token should grant pull"

        # Use the app-token-issued bearer to push a manifest.
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=201,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        # Use the same bearer to pull the manifest back.
        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

    # ---- Test 9 ----

    @freeze_time("2025-06-15 12:00:00")
    def test_expired_app_token_rejected(self, app, client, expired_app_token):
        """Expired app token is rejected during V2 auth.

        Time is frozen to 2025-06-15 while the token expired on 2020-01-01,
        ensuring deterministic validation independent of wall-clock time.
        """
        _token_obj, token_code = expired_app_token

        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/simple:pull",
        }
        headers = {"Authorization": gen_basic_auth(APP_SPECIFIC_TOKEN_USERNAME, token_code)}

        conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            401,
            headers=headers,
        )

    # ---- Test 10 ----

    def test_revoked_app_token_cannot_authenticate(self, app, client, revocable_app_token):
        """Revoked app token cannot authenticate.

        After an app-specific token is deleted, it can no longer be used.
        """
        token_obj, token_code = revocable_app_token

        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/simple:pull",
        }
        headers = {"Authorization": gen_basic_auth(APP_SPECIFIC_TOKEN_USERNAME, token_code)}

        # Token works before revocation
        conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        # Revoke
        revoke_token(token_obj)

        # Token no longer works
        conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            401,
            headers=headers,
        )


# ===========================================================================
# Permission Boundary Tests (Tests 11-12)
# ===========================================================================


class TestPermissionBoundaries:
    """Tests for permission boundary enforcement in V2 registry auth."""

    # ---- Test 11 ----

    def test_readonly_user_can_pull_but_push_rejected(self, app, client):
        """Read-only user can pull but push is rejected (403-equivalent downscope).

        A user with only read permissions obtains a bearer token that
        contains pull but NOT push.  The token allows fetching the manifest
        but the manifest endpoint rejects a push attempt.
        """
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:buynlarge/orgrepo:pull,push,*",
        }
        headers = {"Authorization": gen_basic_auth("reader", "password")}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "reader"
        actions = _get_actions(decoded, "buynlarge/orgrepo")
        assert "pull" in actions, "Read-only user should have pull"
        assert "push" not in actions, "Read-only user must NOT have push"
        assert "*" not in actions, "Read-only user must NOT have admin"

        # Pull succeeds with the pull-only token.
        repo_ref = registry_model.lookup_repository("buynlarge", "orgrepo")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "buynlarge/orgrepo", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

        # Push is rejected — the bearer token lacks the push action.
        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "buynlarge/orgrepo", "manifest_ref": manifest.digest},
            expected_code=401,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

    # ---- Test 12 ----

    def test_oauth_scope_limits_v2_access(self, app, client, oauth_read_token):
        """OAuth scope limitation prevents unauthorized actions.

        An OAuth access token with only ``repo:read`` scope limits the V2
        bearer to pull-only.  The token allows fetching a manifest but the
        manifest endpoint rejects a push attempt.
        """
        _token_obj, token_string = oauth_read_token

        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/simple:pull,push,*",
        }
        headers = {"Authorization": gen_basic_auth(OAUTH_TOKEN_USERNAME, token_string)}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "devtable/simple")
        assert "pull" in actions, "Read-only OAuth scope should allow pull"
        assert "push" not in actions, "Read-only OAuth scope must NOT allow push"
        assert "*" not in actions, "Read-only OAuth scope must NOT allow admin"

        # Pull succeeds with the read-only OAuth bearer.
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

        # Push is rejected — the bearer token lacks the push action.
        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=401,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )


# ===========================================================================
# Robot Account Authentication Tests
# ===========================================================================


class TestRobotAccountAuth:
    """Tests for robot account authentication through V2 registry auth."""

    def test_robot_account_push_pull(self, app, client):
        """Robot account can authenticate and push/pull manifests.

        Robot credentials use the ``namespace+name:token`` basic auth format.
        Tests that the robot can authenticate and actually push and pull a
        manifest on a mirrored repo where it is the configured mirroring robot.
        """
        parent = get_user("devtable")
        _, robot_password, _ = get_robot_and_metadata("dtrobot", parent)

        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/mirrored:pull,push",
        }
        headers = {"Authorization": gen_basic_auth("devtable+dtrobot", robot_password)}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable+dtrobot"
        actions = _get_actions(decoded, "devtable/mirrored")
        assert "push" in actions, "Mirror robot should have push"
        assert "pull" in actions, "Mirror robot should have pull"

        # Use the robot-issued bearer to push a manifest.
        repo_ref = registry_model.lookup_repository("devtable", "mirrored")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "devtable/mirrored", "manifest_ref": manifest.digest},
            expected_code=201,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        # Use the same bearer to pull the manifest back.
        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/mirrored", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )

    def test_robot_invalid_credentials_rejected(self, app, client):
        """Robot account with invalid credentials is rejected with 401."""
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/simple:pull",
        }
        headers = {"Authorization": gen_basic_auth("devtable+dtrobot", "invalid-robot-token")}

        conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            401,
            headers=headers,
        )


# ===========================================================================
# Repository State Impact on Auth
# ===========================================================================


class TestRepositoryStateAuth:
    """Tests for repository state impact on V2 auth permissions."""

    def test_readonly_repo_blocks_push(self, app, client):
        """Push is blocked for READ_ONLY state repositories.

        Even a superuser cannot push; pull remains available.  The manifest
        endpoint enforces this beyond the token scopes.
        """
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/readonly:pull,push,*",
        }
        headers = {"Authorization": gen_basic_auth("devtable", "password")}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        actions = _get_actions(decoded, "devtable/readonly")
        assert "pull" in actions, "Pull allowed for READ_ONLY repos"
        assert "push" not in actions, "Push blocked for READ_ONLY repos"
        assert "*" not in actions, "Admin blocked for READ_ONLY repos"

        # Pull the manifest from the read-only repo.
        repo_ref = registry_model.lookup_repository("devtable", "readonly")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/readonly", "manifest_ref": manifest.digest},
            expected_code=200,
            headers={"Authorization": "Bearer %s" % token},
        )

    def test_mirror_repo_only_mirror_robot_can_push(self, app, client):
        """Only the mirroring robot can push to MIRROR state repositories.

        Regular users (including the repo owner) are downscoped to pull-only.
        The manifest endpoints confirm the actual push/pull behaviour.
        """
        # Owner cannot push
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/mirrored:pull,push,*",
        }
        headers = {"Authorization": gen_basic_auth("devtable", "password")}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        owner_token = resp.json["token"]
        decoded = decode_bearer_token(owner_token, instance_keys, original_app.config)
        actions = _get_actions(decoded, "devtable/mirrored")
        assert "pull" in actions
        assert "push" not in actions, "Owner should not push to MIRROR repo"

        # Owner can pull the manifest.
        repo_ref = registry_model.lookup_repository("devtable", "mirrored")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        owner_bearer = {"Authorization": "Bearer %s" % owner_token}

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/mirrored", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=owner_bearer,
        )

        # Owner push is rejected.
        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "devtable/mirrored", "manifest_ref": manifest.digest},
            expected_code=401,
            headers=owner_bearer,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        # Mirror robot CAN push
        parent = get_user("devtable")
        _, robot_password, _ = get_robot_and_metadata("dtrobot", parent)

        headers = {"Authorization": gen_basic_auth("devtable+dtrobot", robot_password)}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        robot_token = resp.json["token"]
        decoded = decode_bearer_token(robot_token, instance_keys, original_app.config)
        actions = _get_actions(decoded, "devtable/mirrored")
        assert "push" in actions, "Mirror robot should push"
        assert "pull" in actions, "Mirror robot should pull"

        # Robot can push and pull the manifest.
        robot_bearer = {"Authorization": "Bearer %s" % robot_token}

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "devtable/mirrored", "manifest_ref": manifest.digest},
            expected_code=201,
            headers=robot_bearer,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "devtable/mirrored", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=robot_bearer,
        )


# ===========================================================================
# Multi-Scope / Combined Flow Tests
# ===========================================================================


class TestMultiScopeAuth:
    """Cross-cutting tests for combined and edge-case scenarios."""

    def test_multiple_scopes_downscoped_per_repo(self, app, client):
        """Multiple scopes are independently downscoped per repository.

        Requesting scopes for two repositories in one auth request yields
        independent permission sets for each.
        """
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": [
                "repository:buynlarge/orgrepo:pull,push",
                "repository:devtable/simple:pull,push",
            ],
        }
        headers = {"Authorization": gen_basic_auth("reader", "password")}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        org_actions = _get_actions(decoded, "buynlarge/orgrepo")
        assert "pull" in org_actions
        assert "push" not in org_actions

        own_actions = _get_actions(decoded, "devtable/simple")
        assert own_actions == [], "Reader has no access to devtable/simple"

    def test_anonymous_can_pull_public_repo(self, app, client):
        """Anonymous users can pull from public repositories."""
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:public/publicrepo:pull",
        }

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "(anonymous)"
        actions = _get_actions(decoded, "public/publicrepo")
        assert "pull" in actions

        # Anonymous bearer can actually fetch the manifest.
        repo_ref = registry_model.lookup_repository("public", "publicrepo")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "public/publicrepo", "manifest_ref": manifest.digest},
            expected_code=200,
            headers={"Authorization": "Bearer %s" % token},
        )

    def test_anonymous_cannot_push(self, app, client):
        """Anonymous users cannot push to any repository."""
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:public/publicrepo:pull,push",
        }

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "(anonymous)"
        actions = _get_actions(decoded, "public/publicrepo")
        assert "push" not in actions

        # Push is rejected at the manifest endpoint as well.
        repo_ref = registry_model.lookup_repository("public", "publicrepo")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "public/publicrepo", "manifest_ref": manifest.digest},
            expected_code=401,
            headers={"Authorization": "Bearer %s" % token},
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

    def test_disabled_user_app_token_rejected(self, app, client, disabled_freshuser_token):
        """App-specific tokens for disabled users are rejected."""
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:freshuser/somerepo:pull",
        }
        headers = {
            "Authorization": gen_basic_auth(APP_SPECIFIC_TOKEN_USERNAME, disabled_freshuser_token),
        }

        conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            401,
            headers=headers,
        )

    def test_superuser_gets_full_access(self, app, client):
        """Superuser receives full push/pull/* access to any repository."""
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:public/publicrepo:pull,push,*",
        }
        headers = {"Authorization": gen_basic_auth("devtable", "password")}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "public/publicrepo")
        assert "push" in actions
        assert "pull" in actions
        assert "*" in actions

        # Superuser can push and pull manifests on any repo.
        repo_ref = registry_model.lookup_repository("public", "publicrepo")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        bearer_headers = {"Authorization": "Bearer %s" % token}

        conduct_call(
            client,
            "v2.write_manifest_by_digest",
            url_for,
            "PUT",
            {"repository": "public/publicrepo", "manifest_ref": manifest.digest},
            expected_code=201,
            headers=bearer_headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            {"repository": "public/publicrepo", "manifest_ref": manifest.digest},
            expected_code=200,
            headers=bearer_headers,
        )
