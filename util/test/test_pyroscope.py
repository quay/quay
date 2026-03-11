"""
Tests for util/profiling/pyroscope.py.

Covers init_pyroscope: disabled config, missing address, server reachable,
server unreachable, connection errors, ImportError, and configure exception.
Also covers _safe_url credential stripping and log sanitization.
Full coverage for util/profiling/pyroscope.py.
"""

import builtins
from unittest.mock import MagicMock, Mock, patch

from requests.exceptions import RequestException

from util.profiling.pyroscope import _safe_url, _sanitize_message, init_pyroscope


class TestSafeUrl:
    """Tests for _safe_url credential stripping."""

    def test_no_credentials_unchanged(self):
        assert _safe_url("http://pyroscope:4040") == "http://pyroscope:4040"
        assert _safe_url("https://host.example.com:4040/path") == "https://host.example.com:4040/path"

    def test_strips_credentials(self):
        assert _safe_url("http://user:secret@host:4040") == "http://host:4040"
        assert _safe_url("https://user:pass@pyroscope.example.com:4040/ingest") == (
            "https://pyroscope.example.com:4040/ingest"
        )

    def test_strips_credentials_no_port(self):
        """URL with credentials but no explicit port; parsed.port is None."""
        assert _safe_url("http://user:secret@host") == "http://host"
        assert _safe_url("https://u:p@example.com/path") == "https://example.com/path"

    def test_empty_or_none(self):
        assert _safe_url("") == ""
        assert _safe_url(None) is None

    def test_invalid_url_returns_redacted(self):
        """When urlparse/urlunparse raises, return '<redacted>'."""
        with patch("util.profiling.pyroscope.urlparse", side_effect=ValueError("invalid")):
            assert _safe_url("http://something") == "<redacted>"


class TestSanitizeMessage:
    """Tests for _sanitize_message."""

    def test_returns_msg_when_no_msg(self):
        assert _sanitize_message(None, "http://host:4040") is None
        assert _sanitize_message("", "http://host:4040") == ""

    def test_returns_msg_when_no_server_address(self):
        assert _sanitize_message("error: connection failed", None) == "error: connection failed"
        assert _sanitize_message("error", "") == "error"

    def test_replaces_server_address_in_message(self):
        url = "http://user:secret@host:4040"
        msg = f"Failed to connect to {url}"
        assert _sanitize_message(msg, url) == "Failed to connect to http://host:4040"
        assert "secret" not in _sanitize_message(msg, url)


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

    def test_server_reachable_with_credentials_logs_safe_url(self):
        """When server_address has credentials, logs must not contain them; configure gets full URL."""
        app = Mock()
        app.config = {
            "PROFILING_TYPE": "Pyroscope",
            "PYROSCOPE_SERVER_ADDRESS": "http://user:secret@pyroscope:4040",
            "PYROSCOPE_APPLICATION_NAME": "quay",
        }
        response = Mock()
        response.status_code = 200
        mock_pyroscope = MagicMock()
        with (
            patch("util.profiling.pyroscope.requests.get", return_value=response),
            patch.dict("sys.modules", {"pyroscope": mock_pyroscope}),
            patch("util.profiling.pyroscope.logger") as mock_logger,
        ):
            init_pyroscope(app)
        mock_pyroscope.configure.assert_called_once_with(
            application_name="quay",
            server_address="http://user:secret@pyroscope:4040",
            oncpu=True,
            gil_only=True,
            enable_logging=True,
        )
        log_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("reachable at" in c for c in log_calls)
        assert not any("secret" in c for c in log_calls)
        assert not any("user:secret" in c for c in log_calls)

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

    def test_import_error_logs_warning(self):
        """When pyroscope module is not installed, log warning and do not raise."""
        app = Mock()
        app.config = {
            "PROFILING_TYPE": "Pyroscope",
            "PYROSCOPE_SERVER_ADDRESS": "http://pyroscope:4040",
        }
        response = Mock()
        response.status_code = 200
        real_import = builtins.__import__

        def import_mock(name, *args, **kwargs):
            if name == "pyroscope":
                raise ImportError("No module named 'pyroscope'")
            return real_import(name, *args, **kwargs)

        with (
            patch("util.profiling.pyroscope.requests.get", return_value=response),
            patch("builtins.__import__", side_effect=import_mock),
            patch("util.profiling.pyroscope.logger") as mock_logger,
        ):
            init_pyroscope(app)
        mock_logger.warning.assert_called_once()
        assert "pyroscope-io not installed" in mock_logger.warning.call_args[0][0]

    def test_configure_exception_logs_warning(self):
        """When pyroscope.configure raises, log warning and do not raise."""
        app = Mock()
        app.config = {
            "PROFILING_TYPE": "Pyroscope",
            "PYROSCOPE_SERVER_ADDRESS": "http://pyroscope:4040",
        }
        response = Mock()
        response.status_code = 200
        mock_pyroscope = MagicMock()
        mock_pyroscope.configure.side_effect = RuntimeError("startup failed")
        with (
            patch("util.profiling.pyroscope.requests.get", return_value=response),
            patch.dict("sys.modules", {"pyroscope": mock_pyroscope}),
            patch("util.profiling.pyroscope.logger") as mock_logger,
        ):
            init_pyroscope(app)
        mock_logger.warning.assert_called_once()
        assert "startup failed" in str(mock_logger.warning.call_args)
