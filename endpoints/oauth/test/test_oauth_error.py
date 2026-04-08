"""
Tests for OAuth error rendering - covers new code in PR #4383.
"""

import pytest
from mock import Mock, patch

from endpoints.oauth.login import _render_ologin_error, _sanitize_error_message
from test.fixtures import *


class TestSanitizeErrorMessage:
    """Tests for _sanitize_error_message function - covers line 111-112."""

    def test_sanitize_truncates_long_messages(self):
        """Test that messages longer than 250 characters are truncated."""
        long_message = "a" * 300
        result = _sanitize_error_message(long_message)
        assert len(result) == 250
        assert result == "a" * 250


class TestRenderOAuthErrorAuthenticated:
    """Tests for _render_ologin_error with authenticated users - covers lines 167-169."""

    @patch("endpoints.oauth.login.request")
    @patch("endpoints.oauth.login.get_authenticated_user")
    @patch("endpoints.oauth.login.redirect")
    @patch("features.USER_CREATION", True)
    @patch("features.DIRECT_LOGIN", True)
    @patch("features.INVITE_ONLY_USER_CREATION", False)
    def test_react_ui_authenticated_user_adds_params(
        self, mock_redirect, mock_get_user, mock_request, app
    ):
        """Test that authenticated user params are added to redirect URL."""
        # Setup authenticated user
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_get_user.return_value = mock_user

        # Setup React UI
        mock_request.cookies.get.return_value = "react"
        mock_request.headers.get.return_value = "http://localhost:9000/"
        mock_redirect.return_value = Mock()

        # Execute
        _render_ologin_error("GitHub", "Error", False)

        # Verify authenticated params are present
        call_args = mock_redirect.call_args[0][0]
        assert "authenticated=true" in call_args
        assert "username=testuser" in call_args

    @patch("endpoints.oauth.login.request")
    @patch("endpoints.oauth.login.get_authenticated_user")
    @patch("endpoints.oauth.login.redirect")
    @patch("features.USER_CREATION", True)
    @patch("features.DIRECT_LOGIN", True)
    @patch("features.INVITE_ONLY_USER_CREATION", False)
    def test_react_ui_unauthenticated_user_no_params(
        self, mock_redirect, mock_get_user, mock_request, app
    ):
        """Test that unauthenticated user doesn't add authenticated params."""
        # Setup unauthenticated (None)
        mock_get_user.return_value = None

        # Setup React UI
        mock_request.cookies.get.return_value = "react"
        mock_request.headers.get.return_value = "http://localhost:9000/"
        mock_redirect.return_value = Mock()

        # Execute
        _render_ologin_error("GitHub", "Error", False)

        # Verify authenticated params are NOT present
        call_args = mock_redirect.call_args[0][0]
        assert "authenticated" not in call_args
        assert "username" not in call_args

    @patch("endpoints.oauth.login.request")
    @patch("endpoints.oauth.login.get_authenticated_user")
    @patch("endpoints.oauth.login.redirect")
    def test_react_ui_no_referer_uses_relative_redirect(
        self, mock_redirect, mock_get_user, mock_request, app
    ):
        """Test fallback to relative redirect when Referer header is missing."""
        mock_get_user.return_value = None
        mock_request.cookies.get.return_value = "react"
        mock_request.headers.get.return_value = None  # No Referer header
        mock_redirect.return_value = Mock()

        _render_ologin_error("GitHub", "Error", False)

        # Verify relative redirect (no origin prefix)
        call_args = mock_redirect.call_args[0][0]
        assert call_args.startswith("/oauth-error?")
        assert "http" not in call_args  # No absolute URL

    @patch("endpoints.oauth.login.request")
    @patch("endpoints.oauth.login.get_authenticated_user")
    @patch("endpoints.oauth.login.redirect")
    def test_react_ui_register_redirect_param(
        self, mock_redirect, mock_get_user, mock_request, app
    ):
        """Test register_redirect parameter is added when True."""
        mock_get_user.return_value = None
        mock_request.cookies.get.return_value = "react"
        mock_request.headers.get.return_value = "http://localhost:9000/"
        mock_redirect.return_value = Mock()

        _render_ologin_error("GitHub", "Error", register_redirect=True)

        # Verify register_redirect param
        call_args = mock_redirect.call_args[0][0]
        assert "register_redirect=true" in call_args

    @patch("endpoints.oauth.login.request")
    @patch("endpoints.oauth.login.get_authenticated_user")
    @patch("endpoints.oauth.login.index")
    def test_angular_ui_patternfly_cookie_false(self, mock_index, mock_get_user, mock_request, app):
        """Test that patternfly cookie 'false' uses Angular UI."""
        mock_get_user.return_value = None
        mock_request.cookies.get.return_value = "false"  # Not "true"/"react"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_index.return_value = mock_response

        result = _render_ologin_error("GitHub", "Error", False)

        # Verify Angular template is used (not redirect)
        mock_index.assert_called_once()
        assert result.status_code == 400
