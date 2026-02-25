"""
Tests for util/profiling/pyroscope.py.

Covers init_pyroscope: disabled config, missing address, server reachable,
server unreachable, and connection errors.
"""

from unittest.mock import MagicMock, Mock, patch

from requests.exceptions import RequestException

from util.profiling.pyroscope import init_pyroscope


class TestInitPyroscope:
    """Tests for init_pyroscope."""

    def test_disabled_does_not_call_requests(self):
        """When PROFILING_TYPE is not Pyroscope, requests.get is not called."""
        app = Mock()
        app.config = {"PROFILING_TYPE": ""}
        with patch("util.profiling.pyroscope.requests.get") as mock_get:
            init_pyroscope(app)
        mock_get.assert_not_called()

    def test_enabled_no_address_logs_warning(self):
        """When enabled but no address, log warning and return."""
        app = Mock()
        app.config = {"PROFILING_TYPE": "Pyroscope", "PYROSCOPE_SERVER_ADDRESS": None}
        with patch("util.profiling.pyroscope.logger") as mock_logger:
            init_pyroscope(app)
        mock_logger.warning.assert_called_once()
        assert "PYROSCOPE_SERVER_ADDRESS" in mock_logger.warning.call_args[0][0]

    def test_server_reachable_configures_pyroscope(self):
        """When server returns 200, pyroscope.configure is called."""
        app = Mock()
        app.config = {
            "PROFILING_TYPE": "Pyroscope",
            "PYROSCOPE_SERVER_ADDRESS": "http://pyroscope:4040",
            "PYROSCOPE_APPLICATION_NAME": "quay",
        }
        response = Mock()
        response.status_code = 200
        mock_pyroscope = MagicMock()
        with (
            patch("util.profiling.pyroscope.requests.get", return_value=response),
            patch.dict("sys.modules", {"pyroscope": mock_pyroscope}),
        ):
            init_pyroscope(app)
        mock_pyroscope.configure.assert_called_once_with(
            application_name="quay",
            server_address="http://pyroscope:4040",
            oncpu=True,
            gil_only=True,
            enable_logging=True,
        )

    def test_server_unreachable_logs_warning(self):
        """When server returns non-200, log warning and do not configure."""
        app = Mock()
        app.config = {
            "PROFILING_TYPE": "Pyroscope",
            "PYROSCOPE_SERVER_ADDRESS": "http://pyroscope:4040",
        }
        response = Mock()
        response.status_code = 500
        with (
            patch("util.profiling.pyroscope.requests.get", return_value=response),
            patch("util.profiling.pyroscope.logger") as mock_logger,
        ):
            init_pyroscope(app)
        mock_logger.warning.assert_called_once()
        assert "500" in str(mock_logger.warning.call_args)

    def test_connection_error_logs_warning(self):
        """When requests.get raises RequestException, log warning."""
        app = Mock()
        app.config = {
            "PROFILING_TYPE": "Pyroscope",
            "PYROSCOPE_SERVER_ADDRESS": "http://pyroscope:4040",
        }
        with (
            patch(
                "util.profiling.pyroscope.requests.get",
                side_effect=RequestException("Connection refused"),
            ),
            patch("util.profiling.pyroscope.logger") as mock_logger,
        ):
            init_pyroscope(app)
        mock_logger.warning.assert_called_once()
        assert "Connection refused" in str(mock_logger.warning.call_args)
