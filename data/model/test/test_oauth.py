from datetime import datetime, timedelta
from unittest.mock import patch

from auth.scopes import READ_REPO
from data import model
from data.model._basequery import update_last_accessed
from data.model.oauth import (
    DatabaseAuthorizationProvider,
    count_active_tokens,
    create_oauth_api_token,
    delete_application_token,
    delete_bootstrap_token,
    get_or_create_application,
    list_application_tokens,
    list_bootstrap_tokens,
    validate_access_token,
)
from test.fixtures import *

REDIRECT_URI = "http://foo/bar/baz"


class MockDatabaseAuthorizationProvider(DatabaseAuthorizationProvider):
    def get_authorized_user(self):
        return model.user.get_user("devtable")


def setup(num_assignments=0):
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, "test", "http://foo/bar", REDIRECT_URI)
    token_assignment = model.oauth.assign_token_to_user(
        application, user, REDIRECT_URI, READ_REPO.scope, "token"
    )
    return (application, token_assignment, user, org)


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


# Tests for bootstrap token model functions


def test_get_or_create_application_creates_new(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-test-new", user)
    assert app is not None
    assert app.name == "bootstrap-test-new"
    assert app.application_uri == ""
    assert app.redirect_uri == ""
    assert app.organization == user


def test_get_or_create_application_finds_existing(initialized_db):
    user = model.user.get_user("devtable")
    # Create first
    app1 = get_or_create_application("bootstrap-test-existing", user)
    # Find existing
    app2 = get_or_create_application("bootstrap-test-existing", user)
    assert app1.client_id == app2.client_id
    assert app1.id == app2.id


def test_get_or_create_application_returns_first_by_id(initialized_db):
    user = model.user.get_user("devtable")
    # Create two applications with the same name
    app1 = model.oauth.create_application(user, "dup-app-name", "", "")
    app2 = model.oauth.create_application(user, "dup-app-name", "", "")
    assert app1.id < app2.id

    found = get_or_create_application("dup-app-name", user)
    assert found.id == app1.id


def test_create_oauth_api_token_populates_fields(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-token-test", user)

    before = datetime.now()
    token_record, access_token = create_oauth_api_token(
        application=app,
        user=user,
        scope="repo:read",
        expiration_seconds=3600,
    )
    after = datetime.now()

    assert token_record.created_by == user
    assert token_record.authorized_user == user
    assert token_record.scope == "repo:read"
    assert token_record.created is not None
    assert before <= token_record.created <= after
    assert token_record.expires_at > datetime.now()
    assert token_record.expires_at <= datetime.now() + timedelta(seconds=3601)


def test_create_oauth_api_token_sets_both_users(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-both-users", user)

    token_record, _ = create_oauth_api_token(
        application=app,
        user=user,
        scope="repo:read",
    )

    assert token_record.authorized_user == user
    assert token_record.created_by == user


def test_create_oauth_api_token_returns_valid_token(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-validate", user)

    token_record, access_token = create_oauth_api_token(
        application=app,
        user=user,
        scope="repo:read",
    )

    validated = validate_access_token(access_token)
    assert validated is not None
    assert validated.uuid == token_record.uuid


def test_create_oauth_api_token_default_expiration(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-default-exp", user)

    token_record, _ = create_oauth_api_token(
        application=app,
        user=user,
        scope="repo:read",
    )

    # Default is 10 years (315576000 seconds)
    expected_min = datetime.now() + timedelta(seconds=315576000 - 60)
    expected_max = datetime.now() + timedelta(seconds=315576000 + 60)
    assert expected_min <= token_record.expires_at <= expected_max


def test_count_active_tokens(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("count-active-test", user)

    assert count_active_tokens(app) == 0

    create_oauth_api_token(app, user, "repo:read")
    create_oauth_api_token(app, user, "repo:read")
    assert count_active_tokens(app) == 2


def test_count_active_tokens_excludes_expired(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("count-expired-test", user)

    create_oauth_api_token(app, user, "repo:read", expiration_seconds=3600)
    token_record, _ = create_oauth_api_token(app, user, "repo:read", expiration_seconds=1)
    token_record.expires_at = datetime.utcnow() - timedelta(seconds=10)
    token_record.save()

    assert count_active_tokens(app) == 1


def test_list_application_tokens(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("list-tokens-test", user)

    create_oauth_api_token(app, user, "repo:read")
    create_oauth_api_token(app, user, "repo:write")

    tokens, next_page = list_application_tokens(app)
    assert len(tokens) >= 2
    scopes = [t.scope for t in tokens]
    assert "repo:read" in scopes
    assert "repo:write" in scopes


def test_delete_application_token(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("delete-token-test", user)

    token_record, access_token = create_oauth_api_token(app, user, "repo:read")
    assert delete_application_token(app, token_record.uuid) is True
    assert validate_access_token(access_token) is None


def test_delete_application_token_nonexistent(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("delete-missing-test", user)

    assert delete_application_token(app, "nonexistent-uuid") is False


def test_last_accessed_starts_null(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("last-accessed-null", user)

    token_record, _ = create_oauth_api_token(app, user, "repo:read")
    assert token_record.last_accessed is None


def test_last_accessed_updated_after_validation(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("last-accessed-update", user)

    token_record, access_token = create_oauth_api_token(app, user, "repo:read")
    assert token_record.last_accessed is None

    validated = validate_access_token(access_token)
    assert validated is not None

    with patch(
        "data.model._basequery.config.app_config",
        {"FEATURE_USER_LAST_ACCESSED": True, "LAST_ACCESSED_UPDATE_THRESHOLD_S": 0},
    ):
        update_last_accessed(validated)

    assert validated.last_accessed is not None


def test_last_accessed_debounce(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("last-accessed-debounce", user)

    token_record, access_token = create_oauth_api_token(app, user, "repo:read")

    with patch(
        "data.model._basequery.config.app_config",
        {"FEATURE_USER_LAST_ACCESSED": True, "LAST_ACCESSED_UPDATE_THRESHOLD_S": 0},
    ):
        update_last_accessed(token_record)
    first_accessed = token_record.last_accessed

    with patch(
        "data.model._basequery.config.app_config",
        {"FEATURE_USER_LAST_ACCESSED": True, "LAST_ACCESSED_UPDATE_THRESHOLD_S": 9999},
    ):
        update_last_accessed(token_record)
    assert token_record.last_accessed == first_accessed


def test_list_bootstrap_tokens_returns_only_bootstrap(initialized_db):
    user = model.user.get_user("devtable")
    bootstrap_app = get_or_create_application("bootstrap-list-test", user)
    regular_app = model.oauth.create_application(
        user, "regular-app", "http://example.com", "http://example.com/callback"
    )

    create_oauth_api_token(bootstrap_app, user, "repo:read")
    create_oauth_api_token(regular_app, user, "repo:read")

    tokens, _ = list_bootstrap_tokens()
    uuids = {t.application.name for t in tokens}
    assert "bootstrap-list-test" in uuids
    assert "regular-app" not in uuids


def test_list_bootstrap_tokens_expired_filter(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-expired-filter", user)

    active_token, _ = create_oauth_api_token(app, user, "repo:read", expiration_seconds=3600)
    expired_token, _ = create_oauth_api_token(app, user, "repo:write", expiration_seconds=1)
    expired_token.expires_at = datetime.utcnow() - timedelta(seconds=10)
    expired_token.save()

    active_tokens, _ = list_bootstrap_tokens(expired=False)
    active_uuids = {t.uuid for t in active_tokens}
    assert active_token.uuid in active_uuids
    assert expired_token.uuid not in active_uuids

    expired_tokens, _ = list_bootstrap_tokens(expired=True)
    expired_uuids = {t.uuid for t in expired_tokens}
    assert expired_token.uuid in expired_uuids
    assert active_token.uuid not in expired_uuids


def test_list_bootstrap_tokens_expires_before(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-before-filter", user)

    soon_token, _ = create_oauth_api_token(app, user, "repo:read", expiration_seconds=3600)
    far_token, _ = create_oauth_api_token(app, user, "repo:write", expiration_seconds=86400 * 30)

    cutoff = datetime.utcnow() + timedelta(days=1)
    tokens, _ = list_bootstrap_tokens(expires_before=cutoff)
    uuids = {t.uuid for t in tokens}
    assert soon_token.uuid in uuids
    assert far_token.uuid not in uuids


def test_list_bootstrap_tokens_expires_after(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-after-filter", user)

    soon_token, _ = create_oauth_api_token(app, user, "repo:read", expiration_seconds=3600)
    far_token, _ = create_oauth_api_token(app, user, "repo:write", expiration_seconds=86400 * 30)

    cutoff = datetime.utcnow() + timedelta(days=1)
    tokens, _ = list_bootstrap_tokens(expires_after=cutoff)
    uuids = {t.uuid for t in tokens}
    assert far_token.uuid in uuids
    assert soon_token.uuid not in uuids


def test_delete_bootstrap_token_succeeds(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("bootstrap-delete-test", user)

    token_record, access_token = create_oauth_api_token(app, user, "repo:read")
    deleted = delete_bootstrap_token(token_record.uuid)
    assert deleted is not None
    assert deleted.uuid == token_record.uuid
    assert validate_access_token(access_token) is None


def test_delete_bootstrap_token_nonexistent(initialized_db):
    assert delete_bootstrap_token("nonexistent-uuid") is None


def test_validate_access_token_unexpired(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("validate-unexpired", user)

    token_record, access_token = create_oauth_api_token(
        app, user, "repo:read", expiration_seconds=3600
    )
    assert validate_access_token(access_token) is not None


def test_validate_access_token_expired_returns_none(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_application("validate-expired", user)

    token_record, access_token = create_oauth_api_token(
        app, user, "repo:read", expiration_seconds=1
    )
    token_record.expires_at = datetime.utcnow() - timedelta(seconds=10)
    token_record.save()

    assert validate_access_token(access_token) is None


def test_delete_bootstrap_token_rejects_non_bootstrap(initialized_db):
    user = model.user.get_user("devtable")
    regular_app = model.oauth.create_application(
        user, "regular-app-delete", "http://example.com", "http://example.com/callback"
    )
    token_record, _ = create_oauth_api_token(regular_app, user, "repo:read")

    assert delete_bootstrap_token(token_record.uuid) is None
