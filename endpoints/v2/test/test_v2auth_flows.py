"""

Provider HTTP responses, the LDAP directory, and storage use test doubles.
Credential validation, identity linking, team sync, bearer issuance, and registry
blob/manifest operations run through real backend code and Flask's test client.
"""

import gzip
import hashlib
import json
import tarfile
import time
from datetime import datetime
from functools import partial
from io import BytesIO
from unittest.mock import Mock, patch

import jwt
import pytest
from flask import url_for

from app import app as original_app
from app import instance_keys
from auth.credential_consts import APP_SPECIFIC_TOKEN_USERNAME, OAUTH_TOKEN_USERNAME
from auth.test.mock_oidc_server import MOCK_PRIVATE_KEY, mock_get, mock_request
from data import model
from data.database import RepositoryState, db
from data.model.appspecifictoken import (
    create_token,
    get_full_token_string,
    revoke_token,
)
from data.users.teamsync import sync_team
from endpoints.api.appspecifictokens import AppTokens
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, conduct_call, gen_basic_auth
from oauth.loginmanager import OAuthLoginManager
from test.fixtures import *  # noqa: F401, F403
from test.test_ldap import mock_ldap
from util.security.registry_jwt import decode_bearer_token

MANIFEST_TYPE = "application/vnd.docker.distribution.manifest.v2+json"
CONFIG_TYPE = "application/vnd.docker.container.image.v1+json"
LAYER_TYPE = "application/vnd.docker.image.rootfs.diff.tar.gzip"


def _get_actions(decoded, repo_name):
    """Extract the actions list for *repo_name* from a decoded JWT."""
    for entry in decoded.get("access", []):
        if entry["name"] == repo_name:
            return entry["actions"]
    return []


def _generate_registry_token(client, scope, credentials=None, expected_code=200):
    """Request a registry bearer token using optional basic credentials."""
    headers = {"Authorization": gen_basic_auth(*credentials)} if credentials else None
    return conduct_call(
        client,
        "v2.generate_registry_jwt",
        url_for,
        "GET",
        {"service": original_app.config["SERVER_HOSTNAME"], "scope": scope},
        expected_code=expected_code,
        headers=headers,
    )


def _bearer(client, repository, credentials, username, actions):
    """Obtain a bearer and check its subject and exact repository permissions."""
    response = _generate_registry_token(
        client, "repository:%s:pull,push,*" % repository, credentials
    )
    token = response.json["token"]
    decoded = decode_bearer_token(token, instance_keys, original_app.config)
    assert decoded["sub"] == username
    assert set(_get_actions(decoded, repository)) == set(actions)
    return token


def _build_id_token(sub, email, username, expires_in=600):
    """Sign a provider JWT whose claims are validated by the real OIDC decoder."""
    now = int(time.time())
    return jwt.encode(
        {
            "iss": "https://mock-oidc-server.com",
            "aud": "mock-client-id",
            "sub": sub,
            "email": email,
            "email_verified": True,
            "preferred_username": username,
            "iat": now - 7200,
            "exp": now + expires_in,
        },
        MOCK_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": "mock-key-id"},
    )


@pytest.fixture()
def oidc_provider(app):
    """Use real discovery, issuer lookup, and JWT decoding with mocked HTTP."""
    http_client = Mock()
    http_client.get.side_effect = partial(mock_get, None)
    manager = OAuthLoginManager(
        {
            "TESTOIDC_LOGIN_CONFIG": {
                "CLIENT_ID": "mock-client-id",
                "CLIENT_SECRET": "QUAY_FIXTURE_ONLY-oidc-secret",
                "OIDC_SERVER": "https://mock-oidc-server.com",
                "SERVICE_NAME": "Test OIDC",
            },
        },
        client=http_client,
    )
    with (
        patch("auth.oauth.oauth_login", manager),
        patch("oauth.oidc.request", side_effect=partial(mock_request, None)),
        # auth.oauth disables JWT verification under TESTING. Exercise the
        # production validation options only in that module: blob operations
        # need TESTING=True to preserve the database fixture's open transaction.
        patch("auth.oauth.app", Mock(config={**original_app.config, "TESTING": False})),
    ):
        yield manager.get_service("testoidc")


def _digest(content):
    """Return the registry SHA-256 digest of a byte string."""
    return "sha256:" + hashlib.sha256(content).hexdigest()


@pytest.fixture()
def auth_image(request):
    """Build a small image whose blobs and manifest are absent from the seed DB."""
    # Manifest caches outlive individual database fixtures. Give each case
    # distinct content so a cached digest cannot mask a missing upload.
    content = ("Tier 1 authentication flow: %s\n" % request.node.nodeid).encode("utf-8")
    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
        entry = tarfile.TarInfo("auth-flow.txt")
        entry.size = len(content)
        archive.addfile(entry, BytesIO(content))
    layer_tar = tar_buffer.getvalue()
    layer = gzip.compress(layer_tar, mtime=0)
    config = json.dumps(
        {
            "architecture": "amd64",
            "os": "linux",
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": [_digest(layer_tar)]},
            "history": [{"created": "2020-01-01T00:00:00Z", "created_by": "auth flow"}],
        }
    ).encode("utf-8")
    manifest = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": MANIFEST_TYPE,
            "config": {"mediaType": CONFIG_TYPE, "digest": _digest(config), "size": len(config)},
            "layers": [{"mediaType": LAYER_TYPE, "digest": _digest(layer), "size": len(layer)}],
        }
    ).encode("utf-8")
    return manifest, (config, layer)


def _registry_request(client, endpoint, repository, token, method, expected_code, **kwargs):
    """Send a bearer-authenticated registry request with the proper media type."""
    params = {"repository": repository, **kwargs.pop("params", {})}
    response = client.open(
        url_for(endpoint, **params),
        method=method,
        headers={"Authorization": "Bearer %s" % token, "Accept": MANIFEST_TYPE},
        **kwargs,
    )
    assert response.status_code == expected_code, response.data
    return response


def _manifest_request(client, repository, token, method, expected_code, image, ref="auth-flow"):
    """PUT or GET the test manifest by tag or digest through the registry API."""
    by_digest = ref.startswith("sha256:")
    endpoint = "v2.%s_manifest_by_%s" % (
        "write" if method == "PUT" else "fetch",
        "digest" if by_digest else "tagname",
    )
    return _registry_request(
        client,
        endpoint,
        repository,
        token,
        method,
        expected_code,
        params={"manifest_ref": ref},
        data=image[0] if method == "PUT" else None,
        content_type=MANIFEST_TYPE,
    )


def _pull_image(client, repository, token, image):
    """Fetch the manifest by tag and digest, then verify both blobs byte-for-byte."""
    manifest, blobs = image
    for ref in ("auth-flow", _digest(manifest)):
        response = _manifest_request(client, repository, token, "GET", 200, image, ref)
        assert response.data == manifest
        assert response.headers["Docker-Content-Digest"] == _digest(manifest)
    for blob in blobs:
        response = _registry_request(
            client,
            "v2.download_blob",
            repository,
            token,
            "GET",
            200,
            params={"digest": _digest(blob)},
        )
        assert response.data == blob
        assert response.headers["Docker-Content-Digest"] == _digest(blob)


def _push_pull_image(client, repository, token, image):
    """Upload new image content and verify a complete pull using the same bearer."""
    manifest, blobs = image
    _manifest_request(client, repository, token, "GET", 404, image)
    _manifest_request(client, repository, token, "GET", 404, image, _digest(manifest))
    for blob in blobs:
        response = _registry_request(
            client,
            "v2.start_blob_upload",
            repository,
            token,
            "POST",
            201,
            params={"digest": _digest(blob)},
            data=blob,
            content_type="application/octet-stream",
        )
        assert response.headers["Docker-Content-Digest"] == _digest(blob)
    response = _manifest_request(client, repository, token, "PUT", 201, image)
    assert response.headers["Docker-Content-Digest"] == _digest(manifest)
    _pull_image(client, repository, token, image)


def _create_repository(namespace, name, visibility="private"):
    """Set up an isolated repository without granting organization members access."""
    owner = model.user.get_user_or_org(namespace)
    repo = model.repository.create_repository(namespace, name, owner, visibility=visibility)
    assert repo is not None
    return "%s/%s" % (namespace, name)


class TestOIDCAuthIntegration:
    """Exercise signed provider tokens through V2 auth with mocked provider HTTP."""

    def test_oidc_login_v2_bearer_push_pull(self, app, client, oidc_provider, auth_image):
        """OIDC authentication issues a bearer that uploads and pulls a new image."""
        user = model.user.get_user("devtable")
        model.user.attach_federated_login(user, "testoidc", "oidc-devtable")
        id_token = _build_id_token("oidc-devtable", user.email, user.username)
        repository = _create_repository("devtable", "auth-oidc")
        token = _bearer(
            client, repository, (OAUTH_TOKEN_USERNAME, id_token), "devtable", ["pull", "push", "*"]
        )
        # PostgreSQL fixtures hold a transaction open for test isolation. Exercise
        # the same constraint on SQLite so blob operations cannot close it.
        with db.atomic():
            _push_pull_image(client, repository, token, auth_image)

    def test_oidc_org_membership_grants_repository_access(
        self, app, client, oidc_provider, auth_image
    ):
        """An OIDC user's team membership grants access to a private org repository."""
        user = model.user.get_user("reader")
        model.user.attach_federated_login(user, "testoidc", "oidc-reader")
        credentials = (OAUTH_TOKEN_USERNAME, _build_id_token("oidc-reader", user.email, "reader"))
        repository = _create_repository("buynlarge", "auth-oidc-org")
        team = model.team.create_team(
            "oidc-writers", model.organization.get_organization("buynlarge"), "member"
        )
        model.permission.set_team_repo_permission(team.name, "buynlarge", "auth-oidc-org", "write")
        denied = _bearer(client, repository, credentials, "reader", [])
        _manifest_request(client, repository, denied, "GET", 401, auth_image)

        model.team.add_user_to_team(user, team)
        token = _bearer(client, repository, credentials, "reader", ["pull", "push"])
        _push_pull_image(client, repository, token, auth_image)

    def test_expired_oidc_token_rejected(self, app, client, oidc_provider):
        """Real JWT expiration validation rejects an otherwise valid provider token."""
        user = model.user.get_user("devtable")
        model.user.attach_federated_login(user, "testoidc", "oidc-expiry")
        valid = _build_id_token("oidc-expiry", user.email, user.username)
        expired = _build_id_token("oidc-expiry", user.email, user.username, expires_in=-3600)
        _generate_registry_token(client, "", (OAUTH_TOKEN_USERNAME, valid))
        with pytest.raises(jwt.ExpiredSignatureError):
            oidc_provider.decode_user_jwt(expired)
        _generate_registry_token(client, "", (OAUTH_TOKEN_USERNAME, expired), expected_code=401)

    def test_oidc_first_login_creates_user(self, app, client, oidc_provider):
        """The first signed OIDC token creates and links a Quay user through V2 auth."""
        username = "brandnewoidcuser"
        assert model.user.get_user(username) is None
        id_token = _build_id_token("oidc-new-user", "brandnew-oidc@example.com", username)
        response = _generate_registry_token(client, "", (OAUTH_TOKEN_USERNAME, id_token))
        decoded = decode_bearer_token(response.json["token"], instance_keys, original_app.config)
        assert decoded["sub"] == username
        user = model.user.get_user(username)
        assert user is not None
        fed = model.user.lookup_federated_login(user, "testoidc")
        assert fed is not None
        assert fed.service_ident == "oidc-new-user"


class TestLDAPAuthIntegration:
    """Run the real LDAP backend and team sync against an in-process directory."""

    def test_ldap_login_v2_bearer_push_pull(self, app, client, auth_image):
        """LDAP login links a user and authorizes upload and pull of a new image."""
        with mock_ldap() as ldap_users, patch("auth.credentials.authentication.state", ldap_users):
            response = _generate_registry_token(client, "", ("cool.user", "somepass"))
            decoded = decode_bearer_token(
                response.json["token"], instance_keys, original_app.config
            )
            assert decoded["sub"] == "cool_user"
            user = model.user.get_user("cool_user")
            assert user is not None
            fed = model.user.lookup_federated_login(user, "ldap")
            assert fed is not None
            assert fed.service_ident == "cool.user"
            repository = _create_repository("cool_user", "auth-ldap")
            token = _bearer(
                client, repository, ("cool.user", "somepass"), "cool_user", ["pull", "push", "*"]
            )
            _push_pull_image(client, repository, token, auth_image)

    def test_ldap_group_membership_maps_to_team_permissions(self, app, client, auth_image):
        """LDAP group sync grants read access that the user did not have before sync."""
        repository = _create_repository("buynlarge", "auth-ldap-team")
        owner_token = _bearer(
            client, repository, ("devtable", "password"), "devtable", ["pull", "push", "*"]
        )
        _push_pull_image(client, repository, owner_token, auth_image)
        team = model.team.create_team(
            "ldap-readers", model.organization.get_organization("buynlarge"), "member"
        )
        model.permission.set_team_repo_permission(team.name, "buynlarge", "auth-ldap-team", "read")
        with mock_ldap() as ldap_users, patch("auth.credentials.authentication.state", ldap_users):
            credentials = ("someuser", "somepass")
            denied = _bearer(client, repository, credentials, "someuser", [])
            _manifest_request(client, repository, denied, "GET", 401, auth_image)
            assert list(model.team.list_team_users(team)) == []
            sync_info = model.team.set_team_syncing(
                team, ldap_users.federated_service, {"group_dn": "cn=AwesomeFolk"}
            )
            assert sync_team(ldap_users, sync_info)
            assert "someuser" in {member.username for member in model.team.list_team_users(team)}
            token = _bearer(client, repository, credentials, "someuser", ["pull"])
            _pull_image(client, repository, token, auth_image)
            _manifest_request(client, repository, token, "PUT", 401, auth_image)

    def test_ldap_authentication_fails_with_wrong_password(self, app, client):
        """An invalid LDAP password yields no bearer and creates no Quay user."""
        assert model.user.get_user("cool_user") is None
        with mock_ldap() as ldap_users, patch("auth.credentials.authentication.state", ldap_users):
            response = _generate_registry_token(
                client, "", ("cool.user", "wrong-password"), expected_code=401
            )
        assert "token" not in response.json
        assert model.user.get_user("cool_user") is None


class TestAppSpecificTokenAuth:
    """Exercise app-token creation, registry use, expiration, and revocation."""

    def test_create_app_token_v2_push_pull(self, app, client, auth_image):
        """Create an app token through the API and use it to push and pull an image."""
        with client_with_identity("devtable", app) as api_client:
            response = conduct_api_call(
                api_client, AppTokens, "POST", None, {"title": "Tier 1 registry flow"}, 200
            )
            token_code = response.json["token"]["token_code"]
        repository = _create_repository("devtable", "auth-app-token")
        token = _bearer(
            client,
            repository,
            (APP_SPECIFIC_TOKEN_USERNAME, token_code),
            "devtable",
            ["pull", "push", "*"],
        )
        _push_pull_image(client, repository, token, auth_image)

    def test_expired_app_token_rejected(self, app, client):
        """An app token with an expiration in 2020 is rejected during V2 auth."""
        user = model.user.get_user("devtable")
        token = create_token(user, "Expired auth test token", expiration=datetime(2020, 1, 1))
        _generate_registry_token(
            client,
            "repository:devtable/simple:pull",
            (APP_SPECIFIC_TOKEN_USERNAME, get_full_token_string(token)),
            expected_code=401,
        )

    def test_revoked_app_token_cannot_authenticate(self, app, client):
        """An app token authenticates successfully until it is revoked."""
        token = create_token(model.user.get_user("devtable"), "Token to revoke")
        credentials = (APP_SPECIFIC_TOKEN_USERNAME, get_full_token_string(token))
        _generate_registry_token(client, "repository:devtable/simple:pull", credentials)
        revoke_token(token)
        _generate_registry_token(
            client, "repository:devtable/simple:pull", credentials, expected_code=401
        )


class TestPermissionBoundaries:
    """Verify token downscoping is enforced on actual registry operations."""

    def test_readonly_user_can_pull_but_not_push(self, app, client, auth_image):
        """Repository read permission permits a complete pull and rejects manifest PUT."""
        repository = _create_repository("buynlarge", "auth-reader")
        owner_token = _bearer(
            client, repository, ("devtable", "password"), "devtable", ["pull", "push", "*"]
        )
        _push_pull_image(client, repository, owner_token, auth_image)
        model.permission.set_user_repo_permission("reader", "buynlarge", "auth-reader", "read")
        token = _bearer(client, repository, ("reader", "password"), "reader", ["pull"])
        _pull_image(client, repository, token, auth_image)
        # Quay's V2 bearer permission checks reject insufficient scope with 401.
        _manifest_request(client, repository, token, "PUT", 401, auth_image)

    def test_oauth_scope_limits_v2_access(self, app, client, auth_image):
        """repo:read limits a repository owner's bearer to pull and blocks uploads."""
        repository = _create_repository("devtable", "auth-oauth-scope")
        owner_token = _bearer(
            client, repository, ("devtable", "password"), "devtable", ["pull", "push", "*"]
        )
        _push_pull_image(client, repository, owner_token, auth_image)
        user = model.user.get_user("devtable")
        oauth_app = model.oauth.create_application(
            model.organization.get_organization("buynlarge"),
            "test-auth-oauth-app",
            "http://localhost/callback",
            "http://localhost",
            client_id="test-auth-client-id",
        )
        _, token_string = model.oauth.create_user_access_token(
            user, oauth_app.client_id, "repo:read"
        )
        token = _bearer(
            client, repository, (OAUTH_TOKEN_USERNAME, token_string), "devtable", ["pull"]
        )
        _pull_image(client, repository, token, auth_image)
        _manifest_request(client, repository, token, "PUT", 401, auth_image)
        _registry_request(client, "v2.start_blob_upload", repository, token, "POST", 401)
