from unittest.mock import patch

from auth.scopes import READ_REPO
from data import model
from data.model.oauth import DatabaseAuthorizationProvider
from data.model.organization import is_org_admin
from test.fixtures import *

REDIRECT_URI = "http://foo/bar/baz"


class MockDatabaseAuthorizationProvider(DatabaseAuthorizationProvider):
    def __init__(self, user):
        self._user = user

    def get_authorized_user(self):
        return self._user


def setup_app():
    """Create an OAuth app owned by buynlarge (devtable is admin)."""
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, "test", "http://foo/bar", REDIRECT_URI)
    return application, org


def test_non_admin_blocked_when_feature_disabled(initialized_db):
    """Non-org-admin cannot get a token when FEATURE_PUBLIC_OAUTH_APPS is disabled."""
    application, org = setup_app()
    non_admin = model.user.get_user("freshuser")

    # Confirm this user is NOT an admin of buynlarge
    assert not is_org_admin(non_admin, org)

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        with patch("data.model.oauth.features") as mock_features:
            mock_features.PUBLIC_OAUTH_APPS = False
            provider = MockDatabaseAuthorizationProvider(non_admin)
            response = provider.get_token_response(
                "token",
                application.client_id,
                REDIRECT_URI,
                scope=READ_REPO.scope,
            )

    assert response.status_code == 302
    assert "error=unauthorized_client" in response.headers["Location"]


def test_non_admin_allowed_when_feature_enabled(initialized_db):
    """Non-org-admin can get a token when FEATURE_PUBLIC_OAUTH_APPS is enabled."""
    application, org = setup_app()
    non_admin = model.user.get_user("freshuser")

    assert not is_org_admin(non_admin, org)

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        with patch("data.model.oauth.features") as mock_features:
            mock_features.PUBLIC_OAUTH_APPS = True
            provider = MockDatabaseAuthorizationProvider(non_admin)
            response = provider.get_token_response(
                "token",
                application.client_id,
                REDIRECT_URI,
                scope=READ_REPO.scope,
            )

    assert response.status_code == 302
    assert "error" not in response.headers["Location"]
    assert "access_token=" in response.headers["Location"]


def test_org_admin_allowed_regardless_of_feature_flag(initialized_db):
    """Org admin can always get a token, regardless of the flag."""
    application, org = setup_app()
    admin_user = model.user.get_user("devtable")

    assert is_org_admin(admin_user, org)

    for flag_value in (True, False):
        with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
            with patch("data.model.oauth.features") as mock_features:
                mock_features.PUBLIC_OAUTH_APPS = flag_value
                provider = MockDatabaseAuthorizationProvider(admin_user)
                response = provider.get_token_response(
                    "token",
                    application.client_id,
                    REDIRECT_URI,
                    scope=READ_REPO.scope,
                )

        assert response.status_code == 302
        assert "error" not in response.headers["Location"]
        assert "access_token=" in response.headers["Location"]


def test_token_assignment_still_works_when_feature_enabled(initialized_db):
    """Token assignment mechanism still works alongside the public apps feature."""
    application, org = setup_app()
    non_admin = model.user.get_user("freshuser")

    assert not is_org_admin(non_admin, org)

    token_assignment = model.oauth.assign_token_to_user(
        application, non_admin, REDIRECT_URI, READ_REPO.scope, "token"
    )

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        with patch("data.model.oauth.features") as mock_features:
            mock_features.PUBLIC_OAUTH_APPS = True
            provider = MockDatabaseAuthorizationProvider(non_admin)
            response = provider.get_token_response(
                "token",
                application.client_id,
                REDIRECT_URI,
                token_assignment.uuid,
                scope=READ_REPO.scope,
            )

    assert response.status_code == 302
    assert "error" not in response.headers["Location"]
    # Token assignment should be consumed (deleted)
    assert model.oauth.get_token_assignment(token_assignment.uuid, non_admin, org) is None


def test_invalid_client_id_rejected_regardless_of_feature(initialized_db):
    """Invalid client_id is always rejected, even with feature enabled."""
    non_admin = model.user.get_user("freshuser")

    with patch("data.model.oauth.url_for", return_value="http://foo/bar/baz"):
        with patch("data.model.oauth.features") as mock_features:
            mock_features.PUBLIC_OAUTH_APPS = True
            provider = MockDatabaseAuthorizationProvider(non_admin)
            response = provider.get_token_response(
                "token",
                "nonexistent_client_id",
                REDIRECT_URI,
                scope=READ_REPO.scope,
            )

    assert response.status_code == 302
    assert "error=unauthorized_client" in response.headers["Location"]
