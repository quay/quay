from unittest.mock import MagicMock, patch

from workers.worker import Worker


def test_worker_name_defined_outside_sentry_condition():
    """Test that worker_name is defined regardless of Sentry configuration."""
    with patch("workers.worker.app") as mock_app:
        mock_app.config.get.return_value = "FakeSentry"  # Disable Sentry

        worker = Worker()

        # The worker_name should be available even when Sentry is disabled
        # We can't directly access it since it's local to __init__, but we can
        # verify that the Worker initializes without errors
        assert worker is not None


def test_sentry_not_initialized_when_disabled():
    """Test that Sentry is not initialized when disabled."""
    with patch("workers.worker.app") as mock_app, patch(
        "workers.worker.sentry_sdk"
    ) as mock_sentry_sdk:

        # Configure Sentry to be disabled
        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "FakeSentry",
        }.get(key, default)

        worker = Worker()

        # Verify Sentry was not initialized
        mock_sentry_sdk.init.assert_not_called()
        mock_sentry_sdk.set_tag.assert_not_called()


def test_sentry_not_initialized_when_no_dsn():
    """Test that Sentry is not initialized when DSN is empty."""
    with patch("workers.worker.app") as mock_app, patch(
        "workers.worker.sentry_sdk"
    ) as mock_sentry_sdk:

        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "",
        }.get(key, default)

        worker = Worker()

        # Verify Sentry was not initialized
        mock_sentry_sdk.init.assert_not_called()
        mock_sentry_sdk.set_tag.assert_not_called()


def test_exception_capture_in_operation():
    """Test that exceptions are captured by Sentry in operations."""
    with patch("workers.worker.app") as mock_app, patch(
        "workers.worker.sentry_sdk"
    ) as mock_sentry_sdk, patch("workers.worker.UseThenDisconnect") as mock_use_then_disconnect:

        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "https://test@sentry.io/123",
        }.get(key, default)

        worker = Worker()

        def failing_operation():
            raise ValueError("Test exception")

        worker.add_operation(failing_operation, 60)

        wrapped_operation = worker._operations[0][0]

        wrapped_operation()

        mock_sentry_sdk.capture_exception.assert_called_once()


def test_default_sentry_config_values():
    """Test that default Sentry configuration values are used when not specified."""
    with patch("workers.worker.app") as mock_app, patch(
        "workers.worker.sentry_sdk"
    ) as mock_sentry_sdk, patch("socket.gethostname") as mock_hostname:

        mock_app.config.get.side_effect = lambda key, default=None: {
            "EXCEPTION_LOG_TYPE": "Sentry",
            "SENTRY_DSN": "https://test@sentry.io/123",
        }.get(key, default)

        mock_hostname.return_value = "test-host"

        worker = Worker()

        call_args = mock_sentry_sdk.init.call_args
        assert call_args is not None

        kwargs = call_args.kwargs
        assert kwargs["dsn"] == "https://test@sentry.io/123"
        assert kwargs["environment"] == "production"  # default
        assert kwargs["traces_sample_rate"] == 0.1  # default
        assert kwargs["profiles_sample_rate"] == 0.1  # default

        # Verify the SDK was called exactly once
        assert mock_sentry_sdk.init.call_count == 1
