from unittest.mock import MagicMock, patch

import pytest
import sentry_sdk

from util.saas.exceptionlog import FakeSentry, FakeSentryClient, Sentry


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

    def test_sentry_connection_test_with_real_sentry(self):
        """Test that test_sentry_connection returns True when Sentry is properly configured."""
        mock_app = MagicMock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "https://test@sentry.io/123",
            "SENTRY_ENVIRONMENT": "test",
        }.get(key, default)

        with patch("util.saas.exceptionlog.sentry_sdk") as mock_sentry_sdk:
            mock_initialized_sentry = MagicMock()
            mock_sentry_sdk.init.return_value = mock_initialized_sentry

            mock_sentry_sdk.capture_message.return_value = None

            sentry = Sentry(mock_app)

            # Test the connection
            result = sentry.test_sentry_connection()

            mock_sentry_sdk.capture_message.assert_called_once_with(
                "Manual Sentry connection test", level="info"
            )

            # Should return True when connection succeeds
            assert result is True

    def test_sentry_connection_test_with_fake_sentry(self):
        """Test that test_sentry_connection returns False when using FakeSentry."""
        mock_app = MagicMock()
        mock_app.config.get.return_value = "FakeSentry"

        sentry = Sentry(mock_app)

        # Test the connection
        result = sentry.test_sentry_connection()

        # Should return False when using FakeSentry
        assert result is False

    def test_sentry_connection_test_with_none_state(self):
        """Test that test_sentry_connection returns False when state is None."""
        sentry = Sentry()

        # Test the connection
        result = sentry.test_sentry_connection()

        # Should return False when state is None
        assert result is False

    def test_sentry_connection_test_with_exception(self):
        """Test that test_sentry_connection returns False and logs when capture_message fails."""
        mock_app = MagicMock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "https://test@sentry.io/123",
            "SENTRY_ENVIRONMENT": "test",
        }.get(key, default)

        with patch("util.saas.exceptionlog.sentry_sdk") as mock_sentry_sdk:
            mock_initialized_sentry = MagicMock()
            mock_sentry_sdk.init.return_value = mock_initialized_sentry

            mock_sentry_sdk.capture_message.side_effect = Exception("Connection failed")

            sentry = Sentry(mock_app)

            with patch("util.saas.exceptionlog.logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = sentry.test_sentry_connection()

                mock_sentry_sdk.capture_message.assert_called_once_with(
                    "Manual Sentry connection test", level="info"
                )

                mock_logger.error.assert_called_once_with(
                    "Sentry connection test failed: %s", "Connection failed"
                )

                # Should return False when connection fails
                assert result is False
