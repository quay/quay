"""Tests for determine_auth_type_and_performer_kind function."""

from unittest.mock import MagicMock, patch

import pytest

from app import app
from auth.auth_context import determine_auth_type_and_performer_kind


class MockAuthContext:
    """Mock auth context for testing different auth scenarios."""

    def __init__(self, **kwargs):
        self.appspecifictoken = kwargs.get("appspecifictoken")
        self.oauthtoken = kwargs.get("oauthtoken")
        self.token = kwargs.get("token")
        self.sso_token = kwargs.get("sso_token")
        self.user = kwargs.get("user")
        self.robot = kwargs.get("robot")


class TestDetermineAuthTypeAndPerformerKind:
    """Tests for the determine_auth_type_and_performer_kind helper function."""

    def test_oauth_token_parameter(self):
        """When oauth_token is passed, returns oauth auth type."""
        oauth_token = MagicMock()
        auth_type, performer_kind = determine_auth_type_and_performer_kind(
            auth_context=None, oauth_token=oauth_token
        )
        assert auth_type == "oauth"
        assert performer_kind == "oauth"

    def test_app_specific_token_context(self):
        """Auth context with app_specific_token."""
        ctx = MockAuthContext(appspecifictoken=MagicMock())
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "app_specific_token"
        assert performer_kind == "app_specific_token"

    def test_oauth_token_context(self):
        """Auth context with oauth token."""
        ctx = MockAuthContext(oauthtoken=MagicMock())
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "oauth"
        assert performer_kind == "oauth"

    def test_token_context(self):
        """Auth context with generic token."""
        ctx = MockAuthContext(token=MagicMock())
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "token"
        assert performer_kind == "token"

    def test_sso_token_context(self):
        """Auth context with SSO token."""
        ctx = MockAuthContext(sso_token=MagicMock())
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "sso"
        assert performer_kind == "user"

    def test_user_context(self):
        """Auth context with just a user (no token)."""
        ctx = MockAuthContext(user=MagicMock())
        with app.test_request_context(headers={}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "anonymous"  # No auth mechanism detected
        assert performer_kind == "user"

    def test_robot_context_alone(self):
        """Auth context with just a robot."""
        ctx = MockAuthContext(robot=MagicMock())
        with app.test_request_context(headers={}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "anonymous"  # No auth mechanism detected from context
        assert performer_kind == "robot"

    def test_robot_with_oauth_token(self):
        """Robot authenticated via OAuth token - auth_type is oauth, performer is robot."""
        ctx = MockAuthContext(oauthtoken=MagicMock(), robot=MagicMock())
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "oauth"
        assert performer_kind == "robot"

    def test_robot_with_generic_token(self):
        """Robot authenticated via generic token."""
        ctx = MockAuthContext(token=MagicMock(), robot=MagicMock())
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "token"
        assert performer_kind == "robot"

    def test_bearer_header_fallback(self):
        """Falls back to Authorization header for bearer token."""
        with app.test_request_context(headers={"Authorization": "Bearer some-token-value"}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=None)
        assert auth_type == "bearer"
        assert performer_kind == "anonymous"

    def test_basic_header_fallback(self):
        """Falls back to Authorization header for basic auth."""
        with app.test_request_context(headers={"Authorization": "Basic dXNlcjpwYXNz"}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=None)
        assert auth_type == "basic"
        assert performer_kind == "anonymous"

    def test_session_auth_fallback(self):
        """Session-based authentication when no header present."""
        # Session-based test requires a full request context with session.
        # Test that when session has login_time, auth_type is 'session'.
        with app.test_request_context(headers={}):
            from flask import session

            # Directly set session value in the test context
            session["login_time"] = 1234567890
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=None)
        assert auth_type == "session"
        assert performer_kind == "anonymous"

    def test_anonymous_fallback(self):
        """Defaults to anonymous when nothing is detected."""
        with app.test_request_context(headers={}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=None)
        assert auth_type == "anonymous"
        assert performer_kind == "anonymous"

    def test_outside_request_context(self):
        """Handles RuntimeError when called outside request context gracefully."""
        # Call without any request context - should handle gracefully
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=None)
        assert auth_type == "anonymous"
        assert performer_kind == "anonymous"

    def test_oauth_token_takes_precedence(self):
        """OAuth token parameter takes precedence over auth context."""
        ctx = MockAuthContext(appspecifictoken=MagicMock())
        oauth_token = MagicMock()
        auth_type, performer_kind = determine_auth_type_and_performer_kind(
            auth_context=ctx, oauth_token=oauth_token
        )
        # oauth_token wins over app_specific_token in context
        assert auth_type == "oauth"
        assert performer_kind == "oauth"

    def test_auth_context_precedence_order(self):
        """App specific token takes precedence in the auth context chain."""
        # When multiple are set, app_specific_token wins
        ctx = MockAuthContext(
            appspecifictoken=MagicMock(),
            oauthtoken=MagicMock(),
            token=MagicMock(),
        )
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "app_specific_token"
        assert performer_kind == "app_specific_token"

    def test_case_insensitive_bearer_header(self):
        """Bearer header is matched case-insensitively."""
        with app.test_request_context(headers={"Authorization": "BEARER TOKEN"}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=None)
        assert auth_type == "bearer"

    def test_case_insensitive_basic_header(self):
        """Basic header is matched case-insensitively."""
        with app.test_request_context(headers={"Authorization": "BASIC dXNlcjpwYXNz"}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=None)
        assert auth_type == "basic"

    def test_robot_with_app_specific_token(self):
        """Robot authenticated via app-specific token."""
        ctx = MockAuthContext(appspecifictoken=MagicMock(), robot=MagicMock())
        auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert auth_type == "app_specific_token"
        assert performer_kind == "robot"

    def test_user_and_robot_both_set(self):
        """When both user and robot are set, robot takes precedence for performer_kind."""
        ctx = MockAuthContext(user=MagicMock(), robot=MagicMock())
        with app.test_request_context(headers={}):
            auth_type, performer_kind = determine_auth_type_and_performer_kind(auth_context=ctx)
        assert performer_kind == "robot"
