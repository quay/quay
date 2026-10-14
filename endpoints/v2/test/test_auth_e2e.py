"""Integration tests for V2 registry authentication flows.

These tests exercise credential handling, identity linking, token issuance,
scope negotiation, and manifest authorization through Flask's test client.
These are backend integration tests, not black-box end-to-end tests.
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import jwt
from flask import url_for

from app import app as original_app
from app import instance_keys
from auth.credential_consts import APP_SPECIFIC_TOKEN_USERNAME, OAUTH_TOKEN_USERNAME
from data import model
from data.model.appspecifictoken import (
    create_token,
    get_full_token_string,
    revoke_token,
)
from data.registry_model import registry_model
from endpoints.test.shared import conduct_call, gen_basic_auth
from test.fixtures import *  # noqa: F401, F403
from test.test_ldap import mock_ldap
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


def _generate_registry_token(client, scope, credentials=None, expected_code=200):
    """Request a registry bearer token for *scope* using optional credentials."""
    headers = None
    if credentials is not None:
        headers = {"Authorization": gen_basic_auth(*credentials)}

    return conduct_call(
        client,
        "v2.generate_registry_jwt",
        url_for,
        "GET",
        {"service": original_app.config["SERVER_HOSTNAME"], "scope": scope},
        {},
        expected_code,
        headers=headers,
    )


def _build_id_token(sub, email, username, issuer="http://fakeoidc"):
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
        "exp": now + 600,
    }
    token_str = jwt.encode(payload, "test-secret-key-for-auth-tests", algorithm="HS256")
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


def _manifest_request(client, repository, token, method, expected_code):
    """Check bearer authorization using a manifest already in the test database."""
    namespace, repo_name = repository.split("/", 1)
    repo_ref = registry_model.lookup_repository(namespace, repo_name)
    tag = registry_model.get_repo_tag(repo_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)
    endpoint = {
        "GET": "v2.fetch_manifest_by_digest",
        "PUT": "v2.write_manifest_by_digest",
    }[method]
    raw_body = manifest.internal_manifest_bytes.as_encoded_str() if method == "PUT" else None

    return conduct_call(
        client,
        endpoint,
        url_for,
        method,
        {"repository": repository, "manifest_ref": manifest.digest},
        expected_code=expected_code,
        headers={"Authorization": "Bearer %s" % token},
        raw_body=raw_body,
    )


# ===========================================================================
# OIDC Authentication Integration Tests
# ===========================================================================


class TestOIDCAuthIntegration:
    """Test OIDC identity linking and error handling through V2 auth.

    OIDC tokens reach the V2 auth endpoint as ``$oauthtoken:<jwt>`` via the
    basic auth header. Issuer lookup, user linking and creation through
    ``_conduct_oauth_login``, and scope negotiation use the real code.
    The provider's token decoder is mocked, so these tests do not exercise
    signature or expiry validation.
    """

    def test_oidc_token_authorizes_manifest_put_and_fetch(self, app, client):
        """OIDC identity linking issues a bearer accepted by manifest routes.

        A user authenticates with an OIDC JWT token via ``$oauthtoken``,
        receives a V2 bearer token, then exercises manifest PUT and fetch
        authorization using a manifest already in the test database.
        """
        user = model.user.get_user("devtable")
        sub = "oidc-devtable-001"

        id_token, payload = _build_id_token(sub, "devtable@example.com", "devtable")
        _ensure_federated_login(user, "testoidc", sub)
        svc = _make_oidc_mock(payload)

        with patch("auth.oauth.oauth_login") as mock_mgr:
            mock_mgr.get_service_by_issuer.return_value = svc

            resp = _generate_registry_token(
                client,
                "repository:devtable/simple:pull,push",
                (OAUTH_TOKEN_USERNAME, id_token),
            )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "devtable/simple")
        assert "push" in actions, "OIDC user should have push access to own repo"
        assert "pull" in actions, "OIDC user should have pull access to own repo"

        _manifest_request(client, "devtable/simple", token, "PUT", expected_code=201)
        _manifest_request(client, "devtable/simple", token, "GET", expected_code=200)

    def test_oidc_decode_error_returns_unauthorized(self, app, client):
        """A token decode error from the OIDC service produces a 401."""
        id_token, _ = _build_id_token("oidc-invalid", "invalid@example.com", "invaliduser")
        svc = _make_oidc_mock(
            decoded_payload=None,
            side_effect=jwt.InvalidTokenError("Unable to decode token"),
        )

        with patch("auth.oauth.oauth_login") as mock_mgr:
            mock_mgr.get_service_by_issuer.return_value = svc

            _generate_registry_token(
                client,
                "repository:devtable/simple:pull",
                (OAUTH_TOKEN_USERNAME, id_token),
                expected_code=401,
            )

        svc.decode_user_jwt.assert_called_once()

    def test_oidc_first_login_creates_user(self, app, client):
        """OIDC login creates Quay user on first authentication.

        A brand-new user authenticating via OIDC gets a Quay account created
        and linked to their OIDC identity. The isolated test database discards
        the created user after the test.
        """
        new_sub = "oidc-brand-new-user-99"
        new_username = "brandnewoidcuser"
        new_email = "brandnew-oidc@example.com"

        assert model.user.get_user(new_username) is None

        id_token, payload = _build_id_token(new_sub, new_email, new_username)
        svc = _make_oidc_mock(payload)

        with patch("auth.oauth.oauth_login") as mock_mgr:
            mock_mgr.get_service_by_issuer.return_value = svc

            resp = _generate_registry_token(
                client,
                "",
                (OAUTH_TOKEN_USERNAME, id_token),
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
# LDAP Authentication Integration Tests
# ===========================================================================


class TestLDAPAuthIntegration:
    """Test LDAP credentials against V2 registry authentication.

    LDAP reaches the V2 auth endpoint as ``username:password`` basic auth.
    The credential validator delegates to ``authentication.verify_and_link_user``
    which, when backed by LDAP, performs the LDAP bind. These tests use the
    real LDAPUsers backend with an in-process LDAP server mock.
    """

    def test_ldap_login_v2_bearer_pull(self, app, client):
        """Real LDAP credentials authenticate and receive public-repository pull access."""
        with (
            mock_ldap() as ldap_users,
            patch("auth.credentials.authentication.state", ldap_users),
        ):
            resp = _generate_registry_token(
                client,
                "repository:public/publicrepo:pull",
                ("cool.user", "somepass"),
            )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)
        assert decoded["sub"] == "cool_user"
        assert "pull" in _get_actions(decoded, "public/publicrepo")

        user = model.user.get_user("cool_user")
        assert user is not None
        fed = model.user.lookup_federated_login(user, "ldap")
        assert fed is not None
        assert fed.service_ident == "cool.user"

        _manifest_request(client, "public/publicrepo", token, "GET", expected_code=200)

    def test_ldap_authentication_fails_with_wrong_password(self, app, client):
        """The LDAP backend rejects invalid credentials at the V2 auth endpoint."""
        with (
            mock_ldap() as ldap_users,
            patch("auth.credentials.authentication.state", ldap_users),
        ):
            _generate_registry_token(
                client,
                "repository:public/publicrepo:pull",
                ("cool.user", "wrong-password"),
                expected_code=401,
            )


# ===========================================================================
# App-Specific Token Tests
# ===========================================================================


class TestAppSpecificTokenAuth:
    """Test app-specific token authentication through V2 auth.

    App-specific tokens use the ``$app:<token_code>`` basic auth format.
    The credential validator looks up the token by prefix/suffix and validates
    expiration. No external services are needed; test database isolation
    discards the tokens and applications created by each test.
    """

    def test_expired_app_token_rejected(self, app, client):
        """An app token with an expiration in 2020 is rejected."""
        user = model.user.get_user("devtable")
        token = create_token(user, "Expired auth test token", expiration=datetime(2020, 1, 1))
        token_code = get_full_token_string(token)

        _generate_registry_token(
            client,
            "repository:devtable/simple:pull",
            (APP_SPECIFIC_TOKEN_USERNAME, token_code),
            expected_code=401,
        )

    def test_revoked_app_token_cannot_authenticate(self, app, client):
        """Revoked app token cannot authenticate.

        After an app-specific token is deleted, it can no longer be used.
        """
        user = model.user.get_user("devtable")
        token_obj = create_token(user, "Token to revoke")
        token_code = get_full_token_string(token_obj)

        # Token works before revocation
        _generate_registry_token(
            client,
            "repository:devtable/simple:pull",
            (APP_SPECIFIC_TOKEN_USERNAME, token_code),
        )

        # Revoke
        revoke_token(token_obj)

        # Token no longer works
        _generate_registry_token(
            client,
            "repository:devtable/simple:pull",
            (APP_SPECIFIC_TOKEN_USERNAME, token_code),
            expected_code=401,
        )


# ===========================================================================
# OAuth Scope Boundary Test
# ===========================================================================


class TestPermissionBoundaries:
    """Tests for permission boundary enforcement in V2 registry auth."""

    def test_oauth_scope_limits_v2_access(self, app, client):
        """OAuth scope limitation prevents unauthorized actions.

        An OAuth access token with only ``repo:read`` scope limits the V2
        bearer to pull-only.  The token allows fetching a manifest but the
        manifest endpoint rejects a push attempt.
        """
        user = model.user.get_user("devtable")
        org = model.organization.get_organization("buynlarge")
        oauth_app = model.oauth.create_application(
            org,
            "test-auth-oauth-app",
            "http://localhost/callback",
            "http://localhost",
            client_id="test-auth-client-id",
        )
        _token_obj, token_string = model.oauth.create_user_access_token(
            user, oauth_app.client_id, "repo:read"
        )

        resp = _generate_registry_token(
            client,
            "repository:devtable/simple:pull,push,*",
            (OAUTH_TOKEN_USERNAME, token_string),
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "devtable"
        actions = _get_actions(decoded, "devtable/simple")
        assert "pull" in actions, "Read-only OAuth scope should allow pull"
        assert "push" not in actions, "Read-only OAuth scope must NOT allow push"
        assert "*" not in actions, "Read-only OAuth scope must NOT allow admin"

        _manifest_request(client, "devtable/simple", token, "GET", expected_code=200)
        _manifest_request(client, "devtable/simple", token, "PUT", expected_code=401)


class TestAnonymousAuth:
    """Exercise anonymous authentication at the manifest endpoint."""

    def test_anonymous_cannot_push(self, app, client):
        """Anonymous users cannot push to any repository."""
        resp = _generate_registry_token(
            client,
            "repository:public/publicrepo:pull,push",
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        assert decoded["sub"] == "(anonymous)"
        actions = _get_actions(decoded, "public/publicrepo")
        assert "push" not in actions

        _manifest_request(client, "public/publicrepo", token, "PUT", expected_code=401)
