from datetime import datetime, timedelta
from unittest.mock import patch

from auth.scopes import READ_REPO, WRITE_REPO
from data import model
from data.database import LogEntryKind, OAuthAccessToken
from data.model.oauth import DatabaseAuthorizationProvider
from test.fixtures import *

REDIRECT_URI = "http://foo/bar/baz"


class MockDatabaseAuthorizationProvider(DatabaseAuthorizationProvider):
    def __init__(self, user=None):
        self._user = user

    def get_authorized_user(self):
        return self._user or model.user.get_user("devtable")


def setup(num_assignments=0):
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, "test", "http://foo/bar", REDIRECT_URI)
    token_assignment = model.oauth.assign_token_to_user(
        application, user, REDIRECT_URI, READ_REPO.scope, "token"
    )
    return (application, token_assignment, user, org)


def create_access_token_for_last_accessed_test(application_name, expires_at):
    owner = model.user.get_user("devtable")
    application = model.oauth.create_application(owner, application_name, "", "")
    token, access_token = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        READ_REPO.scope,
        "Bearer",
        3600,
    )
    (
        OAuthAccessToken.update(expires_at=expires_at)
        .where(OAuthAccessToken.id == token.id)
        .execute()
    )
    token.expires_at = expires_at
    return token, access_token


def test_oauth_access_token_metadata_fields_are_nullable():
    assert OAuthAccessToken._meta.fields["created"].null is True
    assert OAuthAccessToken._meta.fields["created"].default == datetime.now
    assert OAuthAccessToken._meta.fields["last_accessed"].null is True


def test_oauth_access_token_last_accessed_indexed_by_application():
    assert (("application", "last_accessed"), False) in OAuthAccessToken._meta.indexes


def test_oauth_api_token_log_kinds_seeded(initialized_db):
    expected_log_kinds = {"create_oauth_api_token", "revoke_oauth_api_token"}
    found_log_kinds = {
        kind.name for kind in LogEntryKind.select().where(LogEntryKind.name << expected_log_kinds)
    }
    assert found_log_kinds == expected_log_kinds


def test_oauth_access_token_created_defaults_to_now(initialized_db):
    owner = model.user.get_user("devtable")
    application = model.oauth.create_application(owner, "metadata-defaults", "", "")

    before = datetime.now()
    token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        READ_REPO.scope,
        "Bearer",
        3600,
    )
    after = datetime.now()

    assert token.last_accessed is None
    assert before <= token.created <= after


def test_validate_access_token_updates_last_accessed_for_active_token(initialized_db):
    now = datetime(2026, 1, 1, 12, 0, 0)
    token, access_token = create_access_token_for_last_accessed_test(
        "last-accessed-active",
        now + timedelta(hours=1),
    )

    with patch("data.model.oauth.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        found = model.oauth.validate_access_token(access_token)

    assert found.id == token.id
    assert found.last_accessed == now
    assert OAuthAccessToken.get_by_id(token.id).last_accessed == now


def test_validate_access_token_does_not_update_expired_token(initialized_db):
    now = datetime(2026, 1, 1, 12, 0, 0)
    token, access_token = create_access_token_for_last_accessed_test(
        "last-accessed-expired",
        now - timedelta(seconds=1),
    )

    with patch("data.model.oauth.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        found = model.oauth.validate_access_token(access_token)

    assert found.id == token.id
    assert found.last_accessed is None
    assert OAuthAccessToken.get_by_id(token.id).last_accessed is None


def test_validate_access_token_does_not_update_invalid_suffix(initialized_db):
    now = datetime(2026, 1, 1, 12, 0, 0)
    token, access_token = create_access_token_for_last_accessed_test(
        "last-accessed-invalid-suffix",
        now + timedelta(hours=1),
    )
    prefix_length = model.oauth.ACCESS_TOKEN_PREFIX_LENGTH
    replacement = "x" if access_token[prefix_length] != "x" else "y"
    invalid_access_token = (
        access_token[:prefix_length] + replacement + access_token[prefix_length + 1 :]
    )

    assert model.oauth.validate_access_token(invalid_access_token) is None
    assert OAuthAccessToken.get_by_id(token.id).last_accessed is None


def test_validate_access_token_honors_oauth_last_accessed_debounce(initialized_db):
    now = datetime(2026, 1, 1, 12, 0, 0)
    previous = now - timedelta(seconds=30)
    token, access_token = create_access_token_for_last_accessed_test(
        "last-accessed-debounce",
        now + timedelta(hours=1),
    )
    (
        OAuthAccessToken.update(last_accessed=previous)
        .where(OAuthAccessToken.id == token.id)
        .execute()
    )
    token.last_accessed = previous

    with patch.dict(
        model.oauth.config.app_config,
        {"OAUTH_TOKEN_LAST_ACCESSED_UPDATE_THRESHOLD_S": 60},
        clear=False,
    ):
        with patch("data.model.oauth.datetime") as mock_datetime:
            mock_datetime.now.return_value = now
            found = model.oauth.validate_access_token(access_token)

    assert found.last_accessed == previous
    assert OAuthAccessToken.get_by_id(token.id).last_accessed == previous


def test_validate_access_token_ignores_user_last_accessed_feature_flag(initialized_db):
    now = datetime(2026, 1, 1, 12, 0, 0)
    token, access_token = create_access_token_for_last_accessed_test(
        "last-accessed-user-feature-disabled",
        now + timedelta(hours=1),
    )

    with patch.dict(
        model.oauth.config.app_config,
        {"FEATURE_USER_LAST_ACCESSED": False},
        clear=False,
    ):
        with patch("data.model.oauth.datetime") as mock_datetime:
            mock_datetime.now.return_value = now
            found = model.oauth.validate_access_token(access_token)

    assert found.last_accessed == now
    assert OAuthAccessToken.get_by_id(token.id).last_accessed == now


def test_get_token_response_with_assignment_id(initialized_db):
    application, token_assignment, user, org = setup()

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        db_auth_provider = MockDatabaseAuthorizationProvider()
        response = db_auth_provider.get_token_response(
            "token",
            application.client_id,
            REDIRECT_URI,
            token_assignment.uuid,
            scope=READ_REPO.scope,
        )

    assert response.status_code == 302
    assert "error" not in response.headers["Location"]
    assert model.oauth.get_token_assignment(token_assignment.uuid, user, org) is None


def test_delete_application(initialized_db):
    application, token_assignment, user, org = setup()

    model.oauth.delete_application(org, application.client_id)

    assert model.oauth.get_token_assignment(token_assignment.uuid, user, org) is None
    assert model.oauth.lookup_application(org, application.client_id) is None


def test_get_assigned_authorization_for_user(initialized_db):
    application, token_assignment, user, org = setup()
    assigned_oauth = model.oauth.get_assigned_authorization_for_user(user, token_assignment.uuid)
    assert assigned_oauth is not None
    assert assigned_oauth.uuid == token_assignment.uuid


def test_list_assigned_authorizations_for_user(initialized_db):
    application, token_assignment, user, org = setup()
    second_token_assignment = model.oauth.assign_token_to_user(
        application, user, REDIRECT_URI, READ_REPO.scope, "token"
    )

    assigned_oauths = model.oauth.list_assigned_authorizations_for_user(user)
    assert len(assigned_oauths) == 3
    assert assigned_oauths[1].uuid == token_assignment.uuid
    assert assigned_oauths[2].uuid == second_token_assignment.uuid


def test_get_oauth_application_for_client_id(initialized_db):
    application, token_assignment, user, org = setup()
    assert model.oauth.get_oauth_application_for_client_id(application.client_id) == application


def test_assign_token_to_user(initialized_db):
    application, token_assignment, user, org = setup()
    created_assignment = model.oauth.get_token_assignment(token_assignment.uuid, user, org)
    assert created_assignment is not None
    assert created_assignment.uuid == token_assignment.uuid
    assert created_assignment.application == application
    assert created_assignment.assigned_user == user
    assert created_assignment.redirect_uri == REDIRECT_URI
    assert created_assignment.scope == READ_REPO.scope
    assert created_assignment.response_type == "token"


def test_get_token_assignment_for_client_id(initialized_db):
    application, token_assignment, user, org = setup()
    assert (
        model.oauth.get_token_assignment_for_client_id(
            token_assignment.uuid, user, application.client_id
        )
        == token_assignment
    )


def test_get_token_assignment_for_request_matches_exact_request(initialized_db):
    application, token_assignment, user, org = setup()

    assert (
        model.oauth.get_token_assignment_for_request(
            token_assignment.uuid,
            user,
            application.client_id,
            REDIRECT_URI,
            "token",
            READ_REPO.scope,
        )
        == token_assignment
    )
    assert (
        model.oauth.get_token_assignment_for_request(
            token_assignment.uuid,
            user,
            application.client_id,
            REDIRECT_URI,
            "code",
            READ_REPO.scope,
        )
        is None
    )
    assert (
        model.oauth.get_token_assignment_for_request(
            token_assignment.uuid,
            user,
            application.client_id,
            "http://foo/other",
            "token",
            READ_REPO.scope,
        )
        is None
    )


def test_token_assignment_for_app_a_cannot_authorize_app_b(initialized_db):
    org = model.organization.get_organization("buynlarge")
    user = model.user.get_user("freshuser")
    app_a = model.oauth.create_application(org, "test-a", "http://foo/a", REDIRECT_URI)
    app_b = model.oauth.create_application(org, "test-b", "http://foo/b", REDIRECT_URI)
    assignment = model.oauth.assign_token_to_user(
        app_a, user, REDIRECT_URI, READ_REPO.scope, "token"
    )

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        with patch("data.model.oauth.features") as mock_features:
            mock_features.PUBLIC_OAUTH_APPS = False
            db_auth_provider = MockDatabaseAuthorizationProvider(user)
            response = db_auth_provider.get_token_response(
                "token",
                app_b.client_id,
                REDIRECT_URI,
                assignment.uuid,
                scope=READ_REPO.scope,
            )

    assert response.status_code == 302
    assert "error=unauthorized_client" in response.headers["Location"]
    assert model.oauth.get_assigned_authorization_for_user(user, assignment.uuid) is not None


def test_token_assignment_scope_must_cover_requested_scope(initialized_db):
    org = model.organization.get_organization("buynlarge")
    user = model.user.get_user("freshuser")
    application = model.oauth.create_application(org, "test-scope", "http://foo/bar", REDIRECT_URI)

    narrower_assignment = model.oauth.assign_token_to_user(
        application, user, REDIRECT_URI, READ_REPO.scope, "token"
    )
    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        with patch("data.model.oauth.features") as mock_features:
            mock_features.PUBLIC_OAUTH_APPS = False
            db_auth_provider = MockDatabaseAuthorizationProvider(user)
            response = db_auth_provider.get_token_response(
                "token",
                application.client_id,
                REDIRECT_URI,
                narrower_assignment.uuid,
                scope=WRITE_REPO.scope,
            )

    assert response.status_code == 302
    assert "error=unauthorized_client" in response.headers["Location"]
    assert model.oauth.get_assigned_authorization_for_user(user, narrower_assignment.uuid)

    broader_assignment = model.oauth.assign_token_to_user(
        application, user, REDIRECT_URI, WRITE_REPO.scope, "token"
    )
    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        with patch("data.model.oauth.features") as mock_features:
            mock_features.PUBLIC_OAUTH_APPS = False
            db_auth_provider = MockDatabaseAuthorizationProvider(user)
            response = db_auth_provider.get_token_response(
                "token",
                application.client_id,
                REDIRECT_URI,
                broader_assignment.uuid,
                scope=READ_REPO.scope,
            )

    assert response.status_code == 302
    assert "error" not in response.headers["Location"]
    assert "access_token=" in response.headers["Location"]
    assert model.oauth.get_assigned_authorization_for_user(user, broader_assignment.uuid) is None


def test_only_exact_assignment_is_consumed_after_successful_token_issuance(initialized_db):
    application, token_assignment, user, org = setup()
    mismatched_assignment = model.oauth.assign_token_to_user(
        application, user, "http://foo/other", READ_REPO.scope, "token"
    )

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        db_auth_provider = MockDatabaseAuthorizationProvider(user)
        response = db_auth_provider.get_token_response(
            "token",
            application.client_id,
            REDIRECT_URI,
            mismatched_assignment.uuid,
            scope=READ_REPO.scope,
        )

    assert response.status_code == 302
    assert "access_token=" in response.headers["Location"]
    assert model.oauth.get_assigned_authorization_for_user(user, mismatched_assignment.uuid)

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        db_auth_provider = MockDatabaseAuthorizationProvider(user)
        response = db_auth_provider.get_token_response(
            "token",
            application.client_id,
            REDIRECT_URI,
            token_assignment.uuid,
            scope=READ_REPO.scope,
        )

    assert response.status_code == 302
    assert "access_token=" in response.headers["Location"]
    assert model.oauth.get_assigned_authorization_for_user(user, token_assignment.uuid) is None


# Security tests for PROJQUAY-9849: OAuth Redirect URI Validation Bypass
def test_validate_redirect_uri_blocks_subdomain_takeover(initialized_db):
    """Test that subdomain takeover attacks are blocked"""
    org = model.organization.get_organization("buynlarge")
    # Create app with proper FQDN for subdomain testing
    application = model.oauth.create_application(
        org, "test_subdomain", "https://example.com", "https://example.com/callback"
    )

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Subdomain takeover attack
        malicious_uri = "https://example.com.evil.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)


def test_validate_redirect_uri_blocks_path_traversal(initialized_db):
    """Test that path traversal attacks are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Literal path traversal
        malicious_uri = f"{application.redirect_uri}/../../evil"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # Relative path traversal
        malicious_uri_2 = f"{application.redirect_uri}/../evil"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_validate_redirect_uri_blocks_url_encoded_traversal(initialized_db):
    """Test that URL-encoded path traversal is blocked (critical coverage gap)"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # URL-encoded ../ (%2e%2e)
        malicious_uri = f"{application.redirect_uri}/%2e%2e/evil"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # Double URL-encoded ../ (%252e%252e - percent symbol itself encoded)
        malicious_uri_2 = f"{application.redirect_uri}/%252e%252e/evil"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_validate_redirect_uri_blocks_scheme_mismatch(initialized_db):
    """Test that scheme downgrade attacks are blocked"""
    org = model.organization.get_organization("buynlarge")
    # Create app with HTTPS to test scheme downgrade
    application = model.oauth.create_application(
        org, "test_https_scheme", "https://example.com", "https://example.com/callback"
    )

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Configured as https, block http downgrade
        malicious_uri = "http://example.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)


def test_validate_redirect_uri_blocks_domain_mismatch(initialized_db):
    """Test that different domains are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Different domain entirely
        malicious_uri = "https://evil.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)


def test_validate_redirect_uri_allows_exact_match(initialized_db):
    """Test that exact matches are allowed"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Exact match should work
        assert db_auth_provider.validate_redirect_uri(
            application.client_id, application.redirect_uri
        )


def test_validate_redirect_uri_allows_subpath(initialized_db):
    """Test that legitimate subpaths are allowed"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Subpath should work
        legitimate_uri = f"{application.redirect_uri}/success"
        assert db_auth_provider.validate_redirect_uri(application.client_id, legitimate_uri)


def test_validate_redirect_uri_allows_query_params(initialized_db):
    """Test that query parameters are allowed"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Query params should work (no % in path, only in query string)
        legitimate_uri = f"{application.redirect_uri}?code=123&state=abc"
        assert db_auth_provider.validate_redirect_uri(application.client_id, legitimate_uri)


def test_validate_redirect_uri_blocks_percent_in_path(initialized_db):
    """Test that percent-encoding in path after prefix is blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Any percent-encoding after configured prefix should be blocked
        malicious_uri = f"{application.redirect_uri}/%20space"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # Block even benign-looking encoding
        malicious_uri_2 = f"{application.redirect_uri}/success%2Fpath"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_validate_redirect_uri_with_internal_redirect(initialized_db):
    """Test that internal redirects work correctly"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        with patch("data.model.oauth.get_app_url", return_value="https://quay.io"):
            db_auth_provider = MockDatabaseAuthorizationProvider()

            # Internal redirect should be allowed with exact match
            internal_uri = "https://quay.io/oauth/callback"
            assert db_auth_provider.validate_redirect_uri(application.client_id, internal_uri)


def test_validate_redirect_uri_blocks_empty_uri(initialized_db):
    """Test that empty or None redirect URIs are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Empty string should be blocked
        assert not db_auth_provider.validate_redirect_uri(application.client_id, "")

        # None should be blocked
        assert not db_auth_provider.validate_redirect_uri(application.client_id, None)


def test_validate_redirect_uri_blocks_username_in_uri(initialized_db):
    """Test that URIs with username are blocked"""
    org = model.organization.get_organization("buynlarge")
    # Create app with https URI to test username blocking
    application = model.oauth.create_application(
        org, "test_https", "https://example.com", "https://example.com/callback"
    )

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # URI with username should be blocked
        malicious_uri = "https://user@example.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # URI with username and password should be blocked
        malicious_uri_2 = "https://user:pass@example.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_validate_redirect_uri_with_root_path(initialized_db):
    """Test validation when configured URI has root path"""
    org = model.organization.get_organization("buynlarge")
    # Create app with root path
    application = model.oauth.create_application(
        org, "test_root", "http://example.com", "http://example.com/"
    )

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Valid subpath from root should be allowed
        assert db_auth_provider.validate_redirect_uri(
            application.client_id, "http://example.com/callback"
        )

        # Path not starting with / should be blocked
        assert not db_auth_provider.validate_redirect_uri(
            application.client_id, "http://example.comevil"
        )


def test_validate_redirect_uri_blocks_path_prefix_mismatch(initialized_db):
    """Test that non-matching path prefixes are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Completely different path should be blocked
        malicious_uri = "http://foo/different/path"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # Path that doesn't match configured prefix
        malicious_uri_2 = "http://foo/ba"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_delete_bootstrap_tokens_keeps_requested_token_and_unmarked_tokens(initialized_db):
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application("cleanup-bootstrap", owner)
    keep_token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")
    stale_token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:write")
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:read",
        "Bearer",
        3600,
    )

    model.oauth.delete_bootstrap_tokens(application, keep_token_id=keep_token.id)

    assert model.oauth.lookup_access_token_by_uuid(keep_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(stale_token.uuid) is None
    assert model.oauth.lookup_access_token_by_uuid(unmarked_token.uuid) is not None


def test_delete_bootstrap_tokens_noops_when_only_kept_token_exists(initialized_db):
    owner = model.user.get_user("devtable")
    application = model.oauth.create_bootstrap_application("cleanup-bootstrap", owner)
    keep_token, _ = model.oauth.create_bootstrap_oauth_api_token(application, owner, "repo:read")
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:read",
        "Bearer",
        3600,
    )

    model.oauth.delete_bootstrap_tokens(application, keep_token_id=keep_token.id)

    assert model.oauth.lookup_access_token_by_uuid(keep_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(unmarked_token.uuid) is not None
