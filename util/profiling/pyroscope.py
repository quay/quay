"""Pyroscope profiling: enable only when configured and server is reachable."""

import logging
from urllib.parse import urlparse, urlunparse

import requests

logger = logging.getLogger(__name__)


def _safe_url(url):
    """Return URL with credentials stripped for safe logging. Does not modify the original."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            netloc = parsed.hostname or ""
            if parsed.port is not None:
                netloc = f"{netloc}:{parsed.port}"
            return urlunparse(
                (
                    parsed.scheme,
                    netloc,
                    parsed.path or "",
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
        return url
    except Exception:
        return "<redacted>"


def _sanitize_message(msg, server_address):
    """Replace server_address in msg with credential-free URL for safe logging."""
    if not msg or not server_address:
        return msg
    return str(msg).replace(server_address, _safe_url(server_address))


def init_pyroscope(app):
    """If Pyroscope is enabled and server is reachable, start profiling. Log any errors."""
    if app.config.get("PROFILING_TYPE") != "Pyroscope":
        return
    server_address = app.config.get("PYROSCOPE_SERVER_ADDRESS")
    if not server_address:
        logger.warning(
            "Pyroscope enabled but PYROSCOPE_SERVER_ADDRESS is not set. Profiling disabled."
        )
        return
    try:
        response = requests.get(server_address, timeout=5)
        if response.status_code != requests.codes.ok:
            logger.warning("Pyroscope server not reachable. Status code: %s", response.status_code)
            return
        logger.info("Pyroscope server reachable at %s", _safe_url(server_address))
        import pyroscope

        application_name = app.config.get("PYROSCOPE_APPLICATION_NAME", "quay")
        pyroscope.configure(
            application_name=application_name,
            server_address=server_address,
            oncpu=True,
            gil_only=True,
            enable_logging=True,
        )
        logger.info("Pyroscope profiling started")
    except requests.exceptions.RequestException as e:
        logger.warning(
            "Error connecting to Pyroscope server: %s",
            _sanitize_message(e, server_address),
        )
    except ImportError:
        logger.warning("Pyroscope enabled but pyroscope-io not installed. pip install pyroscope-io")
    except Exception as e:
        logger.warning(
            "Pyroscope startup failed: %s",
            _sanitize_message(e, server_address),
        )
