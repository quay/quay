"""Pyroscope profiling: enable only when configured and server is reachable."""

import logging

import requests

logger = logging.getLogger(__name__)


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
        logger.info("Pyroscope server reachable at %s", server_address)
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
        logger.warning("Error connecting to Pyroscope server: %s", e)
    except ImportError:
        logger.warning("Pyroscope enabled but pyroscope-io not installed. pip install pyroscope-io")
    except Exception as e:
        logger.warning("Pyroscope startup failed: %s", e)
