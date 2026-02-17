"""Tests for FEATURE_EXTENDED_ACTION_LOGGING feature flag behavior."""

from unittest.mock import MagicMock, patch

import pytest

from app import app


class TestFeatureExtendedActionLogging:
    """Tests for the extended action logging feature flag."""

    def test_extended_logging_disabled_by_default(self):
        """When FEATURE_EXTENDED_ACTION_LOGGING is False, extended params are not passed."""
        with app.test_request_context(
            "/api/v1/test",
            method="GET",
            headers={"User-Agent": "test-agent", "Authorization": "Bearer token"},
        ):
            with patch("endpoints.api.logs_model") as mock_logs_model:
                with patch("endpoints.api.get_authenticated_user") as mock_get_user:
                    mock_get_user.return_value = MagicMock(username="testuser")

                    # Import log_action after patching
                    from endpoints.api import log_action

                    # Call with feature flag disabled (default)
                    with patch.dict(app.config, {"FEATURE_EXTENDED_ACTION_LOGGING": False}):
                        log_action("push_repo", "testuser")

                    # Verify log_action was called
                    mock_logs_model.log_action.assert_called_once()

                    # Get the call kwargs
                    call_kwargs = mock_logs_model.log_action.call_args[1]

                    # Extended params should NOT be present
                    assert "request_url" not in call_kwargs
                    assert "http_method" not in call_kwargs
                    assert "auth_type" not in call_kwargs
                    assert "user_agent" not in call_kwargs

    def test_extended_logging_enabled(self):
        """When FEATURE_EXTENDED_ACTION_LOGGING is True, extended params are passed."""
        with app.test_request_context(
            "/api/v1/test",
            method="POST",
            headers={"User-Agent": "test-agent", "Authorization": "Bearer token"},
        ):
            with patch("endpoints.api.logs_model") as mock_logs_model:
                with patch("endpoints.api.get_authenticated_user") as mock_get_user:
                    mock_get_user.return_value = MagicMock(username="testuser")

                    # Import log_action after patching
                    from endpoints.api import log_action

                    # Call with feature flag enabled
                    with patch.dict(app.config, {"FEATURE_EXTENDED_ACTION_LOGGING": True}):
                        log_action("push_repo", "testuser")

                    # Verify log_action was called
                    mock_logs_model.log_action.assert_called_once()

                    # Get the call kwargs
                    call_kwargs = mock_logs_model.log_action.call_args[1]

                    # Extended params SHOULD be present
                    assert "request_url" in call_kwargs
                    assert "http_method" in call_kwargs
                    assert call_kwargs["http_method"] == "POST"
                    assert "auth_type" in call_kwargs
                    assert "user_agent" in call_kwargs

    def test_url_sanitized_when_extended_logging_enabled(self):
        """When extended logging is enabled, sensitive params in URL are redacted."""
        with app.test_request_context(
            "/api/v1/test?token=secret123&scope=read",
            method="GET",
            headers={},
        ):
            with patch("endpoints.api.logs_model") as mock_logs_model:
                with patch("endpoints.api.get_authenticated_user") as mock_get_user:
                    mock_get_user.return_value = MagicMock(username="testuser")

                    from endpoints.api import log_action

                    with patch.dict(app.config, {"FEATURE_EXTENDED_ACTION_LOGGING": True}):
                        log_action("test_action", "testuser")

                    call_kwargs = mock_logs_model.log_action.call_args[1]

                    # URL should be sanitized - secret123 should not be present
                    request_url = call_kwargs.get("request_url", "")
                    assert "secret123" not in request_url
                    assert "scope=read" in request_url or "scope" in request_url
