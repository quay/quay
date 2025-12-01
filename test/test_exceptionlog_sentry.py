from unittest.mock import MagicMock, patch

import pytest
import sentry_sdk

from util.saas.exceptionlog import (
    FakeSentry,
    FakeSentryClient,
    Sentry,
    _sentry_before_send_ignore_known,
)


class TestExceptionLogSentry:
    """Test Sentry integration in exceptionlog module."""

    def test_fake_sentry_client_methods(self):
        """Test that FakeSentryClient methods don't raise exceptions."""
        client = FakeSentryClient()

        # These should not raise any exceptions
        client.captureException()
        client.user_context()

    def test_fake_sentry_initialization(self):
        """Test that FakeSentry initializes correctly."""
        sentry = FakeSentry()
        assert sentry.client is not None
        assert isinstance(sentry.client, FakeSentryClient)

    def test_sentry_initialization_without_app(self):
        """Test that Sentry class initializes without app."""
        sentry = Sentry()
        assert sentry.app is None
        assert sentry.state is None

    def test_sentry_initialization_with_app_fake_sentry(self):
        """Test that Sentry initializes with FakeSentry when configured."""
        mock_app = MagicMock()
        mock_app.config.get.return_value = "FakeSentry"

        sentry = Sentry(mock_app)

        # Verify FakeSentry was created
        assert isinstance(sentry.state, FakeSentry)
        assert isinstance(sentry.state.client, FakeSentryClient)

    def test_sentry_initialization_with_app_real_sentry(self):
        """Test that Sentry initializes with real Sentry when configured."""
        mock_app = MagicMock()
        mock_app.config.get.return_value = "Sentry"
        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "https://test@sentry.io/123",
            "SENTRY_ENVIRONMENT": "test",
            "SENTRY_TRACES_SAMPLE_RATE": 0.5,
            "SENTRY_SAMPLE_RATE": 0.1,
            "SENTRY_PROFILES_SAMPLE_RATE": 0.3,
        }.get(key, default)

        with patch("util.saas.exceptionlog.sentry_sdk") as mock_sentry_sdk:
            # Mock the return value of sentry_sdk.init
            mock_initialized_sentry = MagicMock()
            mock_sentry_sdk.init.return_value = mock_initialized_sentry

            sentry = Sentry(mock_app)

            call_args = mock_sentry_sdk.init.call_args
            assert call_args is not None

            kwargs = call_args.kwargs
            assert kwargs["dsn"] == "https://test@sentry.io/123"
            assert kwargs["environment"] == "test"
            assert kwargs["traces_sample_rate"] == 0.5
            assert kwargs["profiles_sample_rate"] == 0.3
            assert kwargs["sample_rate"] == 0.1

            # Verify the SDK was called exactly once
            assert mock_sentry_sdk.init.call_count == 1

            # Verify the initialized Sentry SDK object is returned
            assert sentry.state is mock_initialized_sentry

    def test_sentry_initialization_with_empty_dsn(self):
        """Test that Sentry initializes with FakeSentry when DSN is empty."""
        mock_app = MagicMock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "",
        }.get(key, default)

        with patch("util.saas.exceptionlog.sentry_sdk") as mock_sentry_sdk:
            sentry = Sentry(mock_app)

            # Verify Sentry SDK was not initialized
            mock_sentry_sdk.init.assert_not_called()

            # Verify FakeSentry was created
            assert isinstance(sentry.state, FakeSentry)

    def test_sentry_initialization_default_config(self):
        """Test that Sentry uses default config values when not specified."""
        mock_app = MagicMock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "https://test@sentry.io/123",
        }.get(key, default)

        with patch("util.saas.exceptionlog.sentry_sdk") as mock_sentry_sdk:
            # Mock the return value of sentry_sdk.init
            mock_initialized_sentry = MagicMock()
            mock_sentry_sdk.init.return_value = mock_initialized_sentry

            sentry = Sentry(mock_app)

            # Verify default values are used - the SDK automatically adds additional parameters
            call_args = mock_sentry_sdk.init.call_args
            assert call_args is not None

            # Check the required parameters we explicitly set
            kwargs = call_args.kwargs
            assert kwargs["dsn"] == "https://test@sentry.io/123"
            assert kwargs["environment"] == "production"  # default
            assert kwargs["traces_sample_rate"] == 0.1  # default
            assert kwargs["profiles_sample_rate"] == 0.1  # default

            # Verify the SDK was called exactly once
            assert mock_sentry_sdk.init.call_count == 1

            # Verify the initialized Sentry SDK object is returned
            assert sentry.state is mock_initialized_sentry

    def test_sentry_getattr_delegation(self):
        """Test that Sentry.__getattr__ delegates to state."""
        mock_app = MagicMock()
        mock_app.config.get.return_value = "FakeSentry"

        sentry = Sentry(mock_app)

        # Test that __getattr__ delegates to state
        assert sentry.client is not None
        assert isinstance(sentry.client, FakeSentryClient)

    def test_sentry_getattr_none_state(self):
        """Test that Sentry.__getattr__ returns None when state is None."""
        sentry = Sentry()  # No app, so state is None

        # Test that __getattr__ returns None when state is None
        assert sentry.client is None
        assert sentry.some_nonexistent_attribute is None

    def test_sentry_extensions_registration(self):
        """Test that Sentry extension is registered with app."""
        mock_app = MagicMock()
        mock_app.config.get.return_value = "FakeSentry"
        mock_app.extensions = {}

        sentry = Sentry(mock_app)

        # Verify extension was registered
        assert "sentry" in mock_app.extensions
        assert mock_app.extensions["sentry"] is sentry.state

    def test_sentry_initialization_without_flask_integration(self):
        """Test that Sentry initializes without any integrations."""
        mock_app = MagicMock()
        mock_app.config.get.return_value = "Sentry"
        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "https://test@sentry.io/123",
            "SENTRY_ENVIRONMENT": "test",
        }.get(key, default)

        with patch("util.saas.exceptionlog.sentry_sdk") as mock_sentry_sdk:
            # Mock the return value of sentry_sdk.init
            mock_initialized_sentry = MagicMock()
            mock_sentry_sdk.init.return_value = mock_initialized_sentry

            sentry = Sentry(mock_app)

            # Verify Sentry SDK was initialized - the SDK automatically adds additional parameters
            call_args = mock_sentry_sdk.init.call_args
            assert call_args is not None

            # Check the required parameters we explicitly set
            kwargs = call_args.kwargs
            assert kwargs["dsn"] == "https://test@sentry.io/123"
            assert kwargs["environment"] == "test"
            assert kwargs["traces_sample_rate"] == 0.1
            assert kwargs["profiles_sample_rate"] == 0.1

            # Verify the SDK was called exactly once
            assert mock_sentry_sdk.init.call_count == 1

            # Verify the initialized Sentry SDK object is returned
            assert sentry.state is mock_initialized_sentry

    def test_sentry_extensions_existing(self):
        """Test that Sentry extension works with existing extensions."""
        mock_app = MagicMock()
        mock_app.config.get.return_value = "FakeSentry"
        mock_app.extensions = {"existing": "extension"}

        sentry = Sentry(mock_app)

        # Verify existing extensions are preserved
        assert "existing" in mock_app.extensions
        assert "sentry" in mock_app.extensions
        assert mock_app.extensions["sentry"] is sentry.state


class TestSentryBeforeSendFilter:
    """Test the _sentry_before_send_ignore_known filter function."""

    def test_filter_log_event_401_error(self):
        """Errors from logger.error() with 401 status should be filtered."""
        event = {
            "type": "default",
            "logentry": {"formatted": "Error 401: Invalid Bearer [token] format; Arguments: {...}"},
            "logger": "util.http",
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_filter_log_event_403_error(self):
        """Errors from logger.error() with 403 status should be filtered."""
        event = {"logentry": {"formatted": "Error 403: Forbidden; Arguments: {'status_code': 403}"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_filter_log_event_with_unauthorized(self):
        """Log events with 'unauthorized' text should be filtered."""
        event = {"logentry": {"formatted": "Unauthorized access attempt"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_filter_log_event_network_error(self):
        """Log events with network errors should be filtered."""
        event = {"logentry": {"formatted": "Connection timeout while fetching data"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_keep_log_event_with_database_error(self):
        """Errors from logger.error() with database keywords should NOT be filtered."""
        event = {"logentry": {"formatted": "Error 500: PostgreSQL connection failed"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

    def test_keep_log_event_with_redis_error(self):
        """Log events with Redis errors should NOT be filtered."""
        event = {"logentry": {"formatted": "Redis connection error on 401 status"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

    def test_existing_jwt_exception_filtering_still_works(self):
        """InvalidJWTException via event exception values should be filtered."""
        event = {
            "exception": {"values": [{"type": "InvalidJWTException", "value": "Invalid JWT token"}]}
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_event_with_both_exception_and_logentry(self):
        """Events with both exception and logentry fields should be filtered if match."""
        event = {
            "exception": {"values": [{"type": "HTTPError", "value": "Some error"}]},
            "logentry": {"formatted": "Error 401: Unauthorized"},
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_empty_logentry(self):
        """Events with empty logentry should be kept."""
        event = {"logentry": {}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

    def test_none_event(self):
        """None events should be returned as-is."""
        result = _sentry_before_send_ignore_known(None, {})
        assert result is None

    def test_event_without_searchable_text(self):
        """Events without searchable text should be kept."""
        event = {"platform": "python", "timestamp": 1234567890}
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

    def test_filter_csrf_error_in_log(self):
        """CSRF errors in log messages should be filtered."""
        event = {"logentry": {"formatted": "CSRF token mismatch error"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_filter_session_expired_in_log(self):
        """Session expired errors in log messages should be filtered."""
        event = {"logentry": {"formatted": "Session expired, please login again"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_filter_clair_vulnerability_scanner_error(self):
        """Clair vulnerability scanner errors should be filtered."""
        event = {
            "logentry": {
                "formatted": "Clair vulnerability scanner connection error when trying to connect"
            }
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_keep_important_error_overrides_filter_pattern(self):
        """Important patterns should take precedence over filter patterns."""
        event = {
            "logentry": {"formatted": "Error 401: Database authentication failed for user admin"}
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

    def test_exc_info_hint_invalidbearertokenexception(self):
        """InvalidBearerTokenException in exc_info hint should be filtered."""

        class InvalidBearerTokenException(Exception):
            pass

        event = {"message": "Some error"}
        hint = {"exc_info": (InvalidBearerTokenException, None, None)}
        result = _sentry_before_send_ignore_known(event, hint)
        assert result is None

    def test_exc_info_hint_invalidjwtexception(self):
        """InvalidJWTException in exc_info hint should be filtered."""

        class InvalidJWTException(Exception):
            pass

        event = {"message": "Some error"}
        hint = {"exc_info": (InvalidJWTException, None, None)}
        result = _sentry_before_send_ignore_known(event, hint)
        assert result is None

    def test_browser_platform_script_error_filtered(self):
        """Browser platform script errors should be filtered."""
        event = {
            "platform": "javascript",
            "exception": {"values": [{"type": "Error", "value": "Script error"}]},
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_browser_platform_cors_error_filtered(self):
        """Browser platform CORS errors should be filtered."""
        event = {
            "platform": "browser",
            "logentry": {"formatted": "CORS error: Cross-origin request blocked"},
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_logger_name_extracted(self):
        """Logger name should be included in searchable text."""
        event = {
            "logger": "util.http",
            "logentry": {"formatted": "Some error occurred"},
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

    def test_filter_otel_debug_messages(self):
        """OTEL instrumentation debug messages should be filtered."""
        event = {
            "logentry": {"formatted": "[OTEL] request {'User-Agent': 'Boto3/1.28.61', ...}"},
            "logger": "storage.cloud",
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_filter_various_4xx_codes(self):
        """Various 4xx status codes should be filtered."""
        codes = [400, 401, 403, 404, 405, 409, 410, 418, 422, 429, 451]
        for code in codes:
            event = {"logentry": {"formatted": f"Error {code}: Client error"}}
            result = _sentry_before_send_ignore_known(event, {})
            assert result is None, f"Status code {code} should be filtered"

    def test_keep_non_contextual_4xx_numbers(self):
        """Numbers like 4001 or 400473 without HTTP context should NOT be filtered."""
        # Port number
        event = {"logentry": {"formatted": "Failed to connect to port 4001"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

        # Error code without context
        event = {"logentry": {"formatted": "Database error: 400473"}}
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event

    def test_filter_status_code_tag_non_browser(self):
        """Events with status_code tag in 4xx range should be filtered for all requests."""
        event = {
            "logentry": {"formatted": "Request failed"},
            "tags": {"status_code": 404},
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result is None

    def test_keep_status_code_tag_5xx(self):
        """Events with status_code tag in 5xx range should NOT be filtered."""
        event = {
            "logentry": {"formatted": "Request failed"},
            "tags": {"status_code": 500},
        }
        result = _sentry_before_send_ignore_known(event, {})
        assert result == event
