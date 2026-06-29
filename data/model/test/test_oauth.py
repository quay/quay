from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from auth.scopes import READ_REPO
from data import model
from data.database import OAuthAccessToken
from data.model._basequery import update_last_accessed
from data.model.oauth import (
    BOOTSTRAP_APP_NAME,
    DEFAULT_TOKEN_EXPIRATION_SECONDS,
    DatabaseAuthorizationProvider,
    TokenLimitExceeded,
    count_active_tokens,
    create_oauth_api_token,
    create_oauth_api_token_under_limit,
    delete_application_token,
    delete_token_by_id,
    get_bootstrap_app_name,
    get_bootstrap_tokens,
    get_or_create_bootstrap_application,
    is_bootstrap_app_name,
    list_application_tokens,
    normalize_scope,
    validate_access_token,
    validate_bootstrap_token,
    validate_expiration,
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


def _bootstrap_config(owner="devtable", app_name=None, superusers=None):
    app_config = {
        "BOOTSTRAP_TOKEN_OWNER": owner,
        "SUPER_USERS": superusers or [owner],
    }
    if app_name is not None:
        app_config["BOOTSTRAP_APP_NAME"] = app_name
    return app_config


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
    application_with_username = model.oauth.create_application(
        org,
        "test_https_username",
        "https://example.com",
        "https://user@example.com/callback",
    )

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # URI with username should be blocked
        malicious_uri = "https://user@example.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)
        assert not db_auth_provider.validate_redirect_uri(
            application_with_username.client_id, malicious_uri
        )

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


def test_get_or_create_bootstrap_application_creates_new(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application("bootstrap-test-new", user)
    assert app is not None
    assert app.name == "bootstrap-test-new"
    assert app.application_uri == ""
    assert app.redirect_uri == ""
    assert app.organization == user


def test_get_or_create_bootstrap_application_finds_existing(initialized_db):
    user = model.user.get_user("devtable")
    # Create first
    app1 = get_or_create_bootstrap_application("bootstrap-test-existing", user)
    # Find existing
    app2 = get_or_create_bootstrap_application("bootstrap-test-existing", user)
    assert app1.client_id == app2.client_id
    assert app1.id == app2.id


def test_get_or_create_bootstrap_application_reuses_reserved_app(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)

    found = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    assert found.id == app.id


def test_get_or_create_bootstrap_application_returns_existing_reserved_app(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, BOOTSTRAP_APP_NAME, "", "")

    found = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    assert found.id == app.id


def test_get_or_create_bootstrap_application_returns_first_by_id(initialized_db):
    user = model.user.get_user("devtable")
    # Create two applications with the same name
    app1 = model.oauth.create_application(user, "dup-app-name", "", "")
    app2 = model.oauth.create_application(user, "dup-app-name", "", "")
    assert app1.id < app2.id

    found = get_or_create_bootstrap_application("dup-app-name", user)
    assert found.id == app1.id


def test_get_bootstrap_app_name_defaults_to_quay_reserved_name(initialized_db):
    assert get_bootstrap_app_name({}) == "__quay_bootstrap_app"


def test_get_bootstrap_app_name_uses_configured_value(initialized_db):
    with patch.dict(model.config.app_config, {"BOOTSTRAP_APP_NAME": "custom-bootstrap"}):
        assert get_bootstrap_app_name() == "custom-bootstrap"


def test_is_bootstrap_app_name_reserves_default_and_configured_names(initialized_db):
    app_config = {"BOOTSTRAP_APP_NAME": "custom-bootstrap"}

    assert is_bootstrap_app_name(BOOTSTRAP_APP_NAME, app_config)
    assert is_bootstrap_app_name("custom-bootstrap", app_config)
    assert not is_bootstrap_app_name("regular-app", app_config)


def test_oauth_access_token_created_default_uses_utcnow():
    assert OAuthAccessToken._meta.fields["created"].default == datetime.utcnow


def test_create_oauth_api_token_populates_fields(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "bootstrap-token-test", "", "")

    before = datetime.utcnow()
    token_record, access_token = create_oauth_api_token(
        application=app,
        user_obj=user,
        scope="repo:read",
        expiration_seconds=3600,
    )
    after = datetime.utcnow()

    assert token_record.authorized_user == user
    assert token_record.scope == "repo:read"
    assert token_record.created is not None
    assert before <= token_record.created <= after
    assert token_record.expires_at > datetime.utcnow()
    assert token_record.expires_at <= datetime.utcnow() + timedelta(seconds=3601)


def test_create_oauth_api_token_returns_valid_token(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "bootstrap-validate", "", "")

    token_record, access_token = create_oauth_api_token(
        application=app,
        user_obj=user,
        scope="repo:read",
    )

    validated = validate_access_token(access_token)
    assert validated is not None
    assert validated.uuid == token_record.uuid


def test_create_oauth_api_token_default_expiration(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "bootstrap-default-exp", "", "")

    token_record, _ = create_oauth_api_token(
        application=app,
        user_obj=user,
        scope="repo:read",
    )

    expected_min = datetime.utcnow() + timedelta(seconds=DEFAULT_TOKEN_EXPIRATION_SECONDS - 60)
    expected_max = datetime.utcnow() + timedelta(seconds=DEFAULT_TOKEN_EXPIRATION_SECONDS + 60)
    assert expected_min <= token_record.expires_at <= expected_max


def test_count_active_tokens(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "count-active-test", "", "")

    assert count_active_tokens(app) == 0

    create_oauth_api_token(app, user, "repo:read")
    create_oauth_api_token(app, user, "repo:read")
    assert count_active_tokens(app) == 2


def test_count_active_tokens_excludes_expired(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "count-expired-test", "", "")

    create_oauth_api_token(app, user, "repo:read", expiration_seconds=3600)
    token_record, _ = create_oauth_api_token(app, user, "repo:read", expiration_seconds=1)
    token_record.expires_at = datetime.utcnow() - timedelta(seconds=10)
    token_record.save()

    assert count_active_tokens(app) == 1


def test_create_oauth_api_token_under_limit_enforces_limit(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "limited-token-create-test", "", "")

    create_oauth_api_token_under_limit(app, user, "repo:read", max_active_tokens=1)

    with pytest.raises(TokenLimitExceeded):
        create_oauth_api_token_under_limit(app, user, "repo:read", max_active_tokens=1)


def test_list_application_tokens(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "list-tokens-test", "", "")

    create_oauth_api_token(app, user, "repo:read")
    create_oauth_api_token(app, user, "repo:write")

    tokens, next_page = list_application_tokens(app)
    assert len(tokens) >= 2
    scopes = [t.scope for t in tokens]
    assert "repo:read" in scopes
    assert "repo:write" in scopes


def test_delete_application_token(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "delete-token-test", "", "")

    token_record, access_token = create_oauth_api_token(app, user, "repo:read")
    assert delete_application_token(app, token_record.uuid) is True
    assert validate_access_token(access_token) is None


def test_delete_application_token_nonexistent(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "delete-missing-test", "", "")

    assert delete_application_token(app, "nonexistent-uuid") is False


def test_last_accessed_starts_null(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "last-accessed-null", "", "")

    token_record, _ = create_oauth_api_token(app, user, "repo:read")
    assert token_record.last_accessed is None


def test_last_accessed_updated_after_validation(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "last-accessed-update", "", "")

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
    app = model.oauth.create_application(user, "last-accessed-debounce", "", "")

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


def test_validate_access_token_unexpired(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "validate-unexpired", "", "")

    token_record, access_token = create_oauth_api_token(
        app, user, "repo:read", expiration_seconds=3600
    )
    assert validate_access_token(access_token) is not None


def test_validate_access_token_expired_returns_token(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "validate-expired", "", "")

    token_record, access_token = create_oauth_api_token(
        app, user, "repo:read", expiration_seconds=1
    )
    token_record.expires_at = datetime.utcnow() - timedelta(seconds=10)
    token_record.save()

    validated = validate_access_token(access_token)
    assert validated is not None
    assert validated.expires_at <= datetime.utcnow()


def test_normalize_scope_comma_separated():
    assert normalize_scope("repo:read,repo:write") == "repo:read repo:write"


def test_normalize_scope_space_separated():
    assert normalize_scope("repo:read repo:write") == "repo:read repo:write"


def test_normalize_scope_mixed_separators():
    assert normalize_scope("repo:read, repo:write  repo:admin") == "repo:read repo:write repo:admin"


def test_normalize_scope_deduplicates():
    assert normalize_scope("repo:read repo:read") == "repo:read"
    assert normalize_scope("repo:read,repo:write,repo:read") == "repo:read repo:write"
    assert normalize_scope("a b c b a") == "a b c"


def test_validate_expiration_positive_int():
    assert validate_expiration(3600) == 3600


def test_validate_expiration_positive_float():
    assert validate_expiration(3600.5) == 3600


def test_validate_expiration_zero_raises():
    with pytest.raises(ValueError, match="positive"):
        validate_expiration(0)


def test_validate_expiration_negative_raises():
    with pytest.raises(ValueError, match="positive"):
        validate_expiration(-1)


def test_validate_expiration_string_raises():
    with pytest.raises(ValueError, match="positive"):
        validate_expiration("3600")


def test_validate_expiration_bool_raises():
    with pytest.raises(ValueError, match="positive"):
        validate_expiration(True)


def test_validate_expiration_infinity_raises():
    with pytest.raises(ValueError, match="finite"):
        validate_expiration(float("inf"))


def test_validate_expiration_allows_large_finite_value():
    expiration = DEFAULT_TOKEN_EXPIRATION_SECONDS * 11
    assert validate_expiration(expiration) == expiration


# Tests for validate_bootstrap_token


def test_validate_bootstrap_token_valid(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    token_record, access_token = create_oauth_api_token(app, user, "repo:read")

    validated = validate_bootstrap_token(access_token, _bootstrap_config())
    assert validated is not None
    assert validated.uuid == token_record.uuid


def test_validate_bootstrap_token_wrong_app(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "not-bootstrap", "", "")
    _, access_token = create_oauth_api_token(app, user, "repo:read")

    assert validate_bootstrap_token(access_token, _bootstrap_config()) is None


def test_validate_bootstrap_token_uses_configured_app_name(initialized_db):
    user = model.user.get_user("devtable")
    default_app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, default_access_token = create_oauth_api_token(default_app, user, "repo:read")

    custom_name = "custom-bootstrap-validate"
    custom_app = get_or_create_bootstrap_application(custom_name, user)
    custom_token_record, custom_access_token = create_oauth_api_token(custom_app, user, "repo:read")

    app_config = _bootstrap_config(app_name=custom_name)
    validated = validate_bootstrap_token(custom_access_token, app_config)
    assert validated is not None
    assert validated.uuid == custom_token_record.uuid
    assert validate_bootstrap_token(default_access_token, app_config) is None


def test_validate_bootstrap_token_accepts_configured_superuser_owner(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    token_record, access_token = create_oauth_api_token(app, user, "repo:read")

    validated = validate_bootstrap_token(access_token, _bootstrap_config())
    assert validated is not None
    assert validated.uuid == token_record.uuid


def test_validate_bootstrap_token_requires_configured_owner_application(initialized_db):
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, BOOTSTRAP_APP_NAME, "", "")
    _, access_token = create_oauth_api_token(application, user, "repo:read")

    app_config = _bootstrap_config()
    assert validate_bootstrap_token(access_token, app_config) is None


def test_validate_bootstrap_token_requires_configured_owner_authorized_user(initialized_db):
    owner = model.user.get_user("devtable")
    other_user = model.user.get_user("public")
    application = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, owner)
    _, access_token = create_oauth_api_token(application, other_user, "repo:read")

    assert validate_bootstrap_token(access_token, _bootstrap_config()) is None


def test_validate_bootstrap_token_rejects_missing_owner(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, access_token = create_oauth_api_token(app, user, "repo:read")

    assert validate_bootstrap_token(access_token, {"SUPER_USERS": ["devtable"]}) is None


def test_validate_bootstrap_token_rejects_empty_configured_superusers(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, access_token = create_oauth_api_token(app, user, "repo:read")

    assert validate_bootstrap_token(access_token, {}) is None
    assert validate_bootstrap_token(access_token, {"SUPER_USERS": []}) is None


def test_validate_bootstrap_token_expired_still_valid(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    token_record, access_token = create_oauth_api_token(
        app, user, "repo:read", expiration_seconds=1
    )
    token_record.expires_at = datetime.utcnow() - timedelta(seconds=10)
    token_record.save()

    validated = validate_bootstrap_token(access_token, _bootstrap_config())
    assert validated is not None
    assert validated.expires_at <= datetime.utcnow()


def test_validate_bootstrap_token_invalid_code(initialized_db):
    assert validate_bootstrap_token("x" * 40) is None


def test_validate_bootstrap_token_empty_string(initialized_db):
    assert validate_bootstrap_token("") is None


# Tests for get_bootstrap_tokens and delete_token_by_id


def test_get_bootstrap_tokens(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "tokens-list-test", "", "")
    create_oauth_api_token(app, user, "repo:read")
    create_oauth_api_token(app, user, "repo:write")

    tokens = get_bootstrap_tokens(app)
    assert len(tokens) == 2


def test_get_bootstrap_tokens_empty(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "tokens-empty-test", "", "")

    assert get_bootstrap_tokens(app) == []


def test_delete_token_by_id(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "delete-by-id-test", "", "")
    token_record, _ = create_oauth_api_token(app, user, "repo:read")

    delete_token_by_id(token_record.id)
    assert get_bootstrap_tokens(app) == []


class DenyingDatabaseAuthorizationProvider(MockDatabaseAuthorizationProvider):
    def validate_access(self):
        return False


class InvalidScopeDatabaseAuthorizationProvider(MockDatabaseAuthorizationProvider):
    def validate_scope(self, client_id, scopes_string):
        return False


def test_database_authorization_provider_base_user_raises():
    with pytest.raises(NotImplementedError):
        DatabaseAuthorizationProvider().get_authorized_user()


def test_database_authorization_provider_client_validation(initialized_db):
    application, _, _, _ = setup()
    provider = MockDatabaseAuthorizationProvider()

    assert provider.token_expires_in == DEFAULT_TOKEN_EXPIRATION_SECONDS
    assert provider.validate_client_id(application.client_id)
    assert provider.get_application_for_client_id(application.client_id) == application
    assert not provider.validate_client_id("missing-client")
    assert provider.get_application_for_client_id("missing-client") is None


def test_database_authorization_provider_client_secret_validation(initialized_db):
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(
        org,
        "secret-test",
        "http://foo/bar",
        REDIRECT_URI,
        client_secret="super-secret",
    )
    provider = MockDatabaseAuthorizationProvider()

    assert provider.validate_client_secret(application.client_id, "super-secret")
    assert not provider.validate_client_secret(application.client_id, "wrong-secret")
    assert not provider.validate_client_secret("missing-client", "super-secret")


def test_validate_redirect_uri_missing_application_and_at_in_path(initialized_db):
    application, _, _, _ = setup()
    provider = MockDatabaseAuthorizationProvider()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        assert not provider.validate_redirect_uri("missing-client", REDIRECT_URI)
        assert not provider.validate_redirect_uri(application.client_id, f"{REDIRECT_URI}/@evil")


def test_scope_loading_and_subset_validation(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(
        model.user.get_user_or_org("buynlarge"), "scope-loading-test", "", ""
    )
    provider = MockDatabaseAuthorizationProvider()

    create_oauth_api_token(app, user, "repo:read", expiration_seconds=3600)
    create_oauth_api_token(app, user, "repo:write", expiration_seconds=3600)
    expired, _ = create_oauth_api_token(app, user, "repo:admin", expiration_seconds=1)
    expired.expires_at = datetime.utcnow() - timedelta(seconds=10)
    expired.save()

    loaded_scope = provider.load_authorized_scope_string(app.client_id, user.username)
    assert "repo:read" in loaded_scope
    assert "repo:write" in loaded_scope
    assert "repo:admin" not in loaded_scope
    assert provider.validate_has_scopes(app.client_id, user.username, "repo:read")
    assert not provider.validate_has_scopes(app.client_id, user.username, "repo:admin")


def test_authorization_code_persist_load_and_discard(initialized_db):
    application, _, _, _ = setup()
    provider = MockDatabaseAuthorizationProvider()
    code = "n" * 20 + "c" * 20

    provider.persist_authorization_code(application.client_id, code, READ_REPO.scope)

    assert provider.from_authorization_code(application.client_id, code, READ_REPO.scope) == (
        '{"username": "devtable"}'
    )
    assert (
        provider.from_authorization_code(
            application.client_id, "n" * 20 + "w" * 20, READ_REPO.scope
        )
        is None
    )
    assert provider.from_authorization_code(application.client_id, code, "repo:write") is None

    provider.discard_authorization_code(application.client_id, code)
    assert provider.from_authorization_code(application.client_id, code, READ_REPO.scope) is None
    provider.discard_authorization_code(application.client_id, code)


def test_persist_token_information_unknown_user_raises(initialized_db):
    application, _, _, _ = setup()
    provider = MockDatabaseAuthorizationProvider()

    with pytest.raises(RuntimeError, match="Username must be in the data field"):
        provider.persist_token_information(
            application.client_id,
            READ_REPO.scope,
            "a" * 20 + "b" * 20,
            "Bearer",
            3600,
            None,
            '{"username": "missing-user"}',
        )


def test_persist_token_information_creates_token(initialized_db):
    application, _, user, _ = setup()
    provider = MockDatabaseAuthorizationProvider()
    access_token = "a" * 20 + "b" * 20

    provider.persist_token_information(
        application.client_id,
        READ_REPO.scope,
        access_token,
        "Bearer",
        3600,
        None,
        '{"username": "devtable"}',
    )

    validated = validate_access_token(access_token)
    assert validated is not None
    assert validated.application == application
    assert validated.authorized_user == user
    assert validated.scope == READ_REPO.scope


def test_auth_denied_response_branches(initialized_db):
    application, _, _, _ = setup()
    provider = MockDatabaseAuthorizationProvider()

    unsupported = provider.get_auth_denied_response("code", application.client_id, REDIRECT_URI)
    assert unsupported.status_code == 302
    assert "unsupported_response_type" in unsupported.headers["Location"]

    with patch.object(provider, "validate_redirect_uri", return_value=False):
        invalid_redirect = provider.get_auth_denied_response(
            "token", application.client_id, REDIRECT_URI
        )
    assert invalid_redirect.status_code == 400

    with patch.object(provider, "validate_redirect_uri", return_value=True):
        denied = provider.get_auth_denied_response("token", application.client_id, REDIRECT_URI)
    assert denied.status_code == 302
    assert "authorization_denied" in denied.headers["Location"]


def test_get_token_response_error_branches(initialized_db):
    application, _, _, _ = setup()
    provider = MockDatabaseAuthorizationProvider()

    unsupported = provider.get_token_response("code", application.client_id, REDIRECT_URI)
    assert unsupported.status_code == 302
    assert "unsupported_response_type" in unsupported.headers["Location"]

    unauthorized = provider.get_token_response("token", "missing-client", REDIRECT_URI)
    assert unauthorized.status_code == 302
    assert "unauthorized_client" in unauthorized.headers["Location"]

    with patch.object(provider, "validate_redirect_uri", return_value=False):
        invalid_redirect = provider.get_token_response("token", application.client_id, REDIRECT_URI)
    assert invalid_redirect.status_code == 400

    denying_provider = DenyingDatabaseAuthorizationProvider()
    with patch.object(denying_provider, "validate_redirect_uri", return_value=True):
        denied = denying_provider.get_token_response(
            "token", application.client_id, REDIRECT_URI, scope=READ_REPO.scope
        )
    assert denied.status_code == 302
    assert "access_denied" in denied.headers["Location"]

    invalid_scope_provider = InvalidScopeDatabaseAuthorizationProvider()
    with patch.object(invalid_scope_provider, "validate_redirect_uri", return_value=True):
        invalid_scope = invalid_scope_provider.get_token_response(
            "token", application.client_id, REDIRECT_URI, scope="not-a-scope"
        )
    assert invalid_scope.status_code == 302
    assert "invalid_scope" in invalid_scope.headers["Location"]


def test_refresh_token_methods(initialized_db):
    provider = MockDatabaseAuthorizationProvider()

    assert provider.generate_refresh_token() is None
    with pytest.raises(NotImplementedError):
        provider.from_refresh_token("client", "refresh", READ_REPO.scope)
    with pytest.raises(NotImplementedError):
        provider.discard_refresh_token("client", "refresh")


def test_oauth_lookup_and_reset_helpers(initialized_db):
    application, token_assignment, user, org = setup()
    token_record, access_token = create_oauth_api_token(application, user, READ_REPO.scope)

    old_secret = application.secure_client_secret.decrypt()
    reset = model.oauth.reset_client_secret(application)
    assert reset.id == application.id
    assert reset.secure_client_secret.decrypt() != old_secret

    assert model.oauth.get_application_for_client_id(application.client_id) == application
    assert model.oauth.get_application_for_client_id("missing-client") is None
    assert model.oauth.lookup_access_token_by_uuid(token_record.uuid) == token_record
    assert model.oauth.lookup_access_token_by_uuid("missing-token") is None
    assert model.oauth.lookup_access_token_for_user(user, token_record.uuid) == token_record
    assert model.oauth.lookup_access_token_for_user(user, "missing-token") is None
    assert token_record.uuid in {
        token.uuid for token in model.oauth.list_access_tokens_for_user(user)
    }
    assert model.oauth.get_assigned_authorization_for_user(user, "missing-assignment") is None
    assert model.oauth.get_oauth_application_for_client_id("missing-client") is None
    assert model.oauth.get_token_assignment(None, user, org) is None
    assert model.oauth.get_token_assignment("missing-assignment", user, org) is None
    assert (
        model.oauth.get_token_assignment_for_client_id(
            "missing-assignment", user, application.client_id
        )
        is None
    )

    assert validate_access_token(access_token).uuid == token_record.uuid


def test_delete_application_missing_is_noop(initialized_db):
    org = model.organization.get_organization("buynlarge")
    assert model.oauth.delete_application(org, "missing-client") is None


def test_validate_access_and_bootstrap_token_short_values(initialized_db):
    assert validate_access_token("") is None
    assert validate_access_token("a" * 20) is None
    assert validate_access_token("a" * 20 + "wrong-code") is None
    assert validate_bootstrap_token("a" * 20) is None


def test_validate_access_token_wrong_code_for_existing_token(initialized_db):
    user = model.user.get_user("devtable")
    app = model.oauth.create_application(user, "wrong-code-test", "", "")
    _, access_token = create_oauth_api_token(app, user, "repo:read")

    assert validate_access_token(access_token[:20] + "wrong-code") is None


def test_validate_bootstrap_token_wrong_code_for_existing_token(initialized_db):
    user = model.user.get_user("devtable")
    app = get_or_create_bootstrap_application(BOOTSTRAP_APP_NAME, user)
    _, access_token = create_oauth_api_token(app, user, "repo:read")

    assert validate_bootstrap_token(access_token[:20] + "wrong-code", _bootstrap_config()) is None


def test_lookup_application_by_name(initialized_db):
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, "lookup-by-name", "", "")

    assert model.oauth.lookup_application_by_name(org, "lookup-by-name") == application
    assert model.oauth.lookup_application_by_name(org, "missing-name") is None


def test_lookup_applications_by_name(initialized_db):
    org1 = model.organization.get_organization("buynlarge")
    org2 = model.organization.get_organization("sellnsmall")
    app1 = model.oauth.create_application(org1, "shared-name", "", "")
    app2 = model.oauth.create_application(org2, "shared-name", "", "")

    results = model.oauth.lookup_applications_by_name("shared-name")
    assert set(a.id for a in results) == {app1.id, app2.id}

    assert model.oauth.lookup_applications_by_name("nonexistent") == []
