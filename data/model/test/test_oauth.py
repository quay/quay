from unittest.mock import patch

from auth.scopes import READ_REPO
from data import model
from data.model.oauth import DatabaseAuthorizationProvider
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
    """Test that subdomain takeover attacks are blocked (CVE-worthy)"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Malicious: https://example.com -> https://example.com.evil.com
        malicious_uri = f"{application.redirect_uri}.evil.com"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)


def test_validate_redirect_uri_blocks_path_traversal(initialized_db):
    """Test that path traversal attacks are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Malicious: /callback -> /callback/../../evil
        malicious_uri = f"{application.redirect_uri}/../../evil"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # Also block relative path traversal
        malicious_uri_2 = f"{application.redirect_uri}/../evil"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_validate_redirect_uri_blocks_username_attack(initialized_db):
    """Test that username/basic auth attacks are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Malicious: https://example.com/callback@attacker.com
        malicious_uri = f"{application.redirect_uri}@attacker.com"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # Also block explicit username:password
        malicious_uri_2 = "https://user:pass@attacker.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_validate_redirect_uri_blocks_scheme_mismatch(initialized_db):
    """Test that scheme downgrade attacks are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # If configured as https, block http
        if application.redirect_uri.startswith("https://"):
            malicious_uri = application.redirect_uri.replace("https://", "http://")
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

        # Query params should work
        legitimate_uri = f"{application.redirect_uri}?code=123&state=abc"
        assert db_auth_provider.validate_redirect_uri(application.client_id, legitimate_uri)


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

        # Empty string should be blocked (line 76-77)
        assert not db_auth_provider.validate_redirect_uri(application.client_id, "")

        # None should be blocked (line 76-77)
        assert not db_auth_provider.validate_redirect_uri(application.client_id, None)


def test_validate_redirect_uri_blocks_username_in_uri(initialized_db):
    """Test that URIs with username are blocked"""
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")
    # Create app with https URI to test username blocking
    application = model.oauth.create_application(
        org, "test_https", "https://example.com", "https://example.com/callback"
    )

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # URI with username should be blocked (line 91-92)
        malicious_uri = "https://user@example.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # URI with username and password should be blocked (line 91-92)
        malicious_uri_2 = "https://user:pass@example.com/callback"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)


def test_validate_redirect_uri_with_root_path(initialized_db):
    """Test validation when configured URI has root path"""
    user = model.user.get_user("devtable")
    org = model.organization.get_organization("buynlarge")
    # Create app with root path
    application = model.oauth.create_application(
        org, "test_root", "http://example.com", "http://example.com/"
    )

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Valid subpath from root should be allowed (line 101-105)
        assert db_auth_provider.validate_redirect_uri(
            application.client_id, "http://example.com/callback"
        )

        # Path not starting with / should be blocked (line 102-103)
        assert not db_auth_provider.validate_redirect_uri(
            application.client_id, "http://example.comevil"
        )


def test_validate_redirect_uri_blocks_path_prefix_mismatch(initialized_db):
    """Test that non-matching path prefixes are blocked"""
    application, _, _, _ = setup()

    with patch("data.model.oauth.url_for", return_value="/oauth/callback"):
        db_auth_provider = MockDatabaseAuthorizationProvider()

        # Completely different path should be blocked (line 108-113)
        malicious_uri = "http://foo/different/path"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri)

        # Path that doesn't match configured prefix (line 108-113)
        malicious_uri_2 = "http://foo/ba"
        assert not db_auth_provider.validate_redirect_uri(application.client_id, malicious_uri_2)
