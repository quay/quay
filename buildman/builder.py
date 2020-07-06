import logging
import os
import time
import socket

import features

from app import app, userfiles as user_files, build_logs, dockerfile_build_queue
from util.log import logfile_path

from buildman.manager.enterprise import EnterpriseManager
from buildman.manager.ephemeral import EphemeralBuilderManager
from buildman.server import BuilderServer

from ssl import SSLContext
from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

logger = logging.getLogger(__name__)

BUILD_MANAGERS = {
    "enterprise": EnterpriseManager,
    "ephemeral": EphemeralBuilderManager,
}

EXTERNALLY_MANAGED = "external"

DEFAULT_WEBSOCKET_PORT = 8787
DEFAULT_CONTROLLER_PORT = 8686

LOG_FORMAT = "%(asctime)s [%(process)d] [%(levelname)s] [%(name)s] %(message)s"


def run_build_manager():
    if not features.BUILD_SUPPORT:
        logger.debug("Building is disabled. Please enable the feature flag")
        while True:
            time.sleep(1000)
        return

    if app.config.get("REGISTRY_STATE", "normal") == "readonly":
        logger.debug("Building is disabled while in read-only mode.")
        while True:
            time.sleep(1000)
        return

    build_manager_config = app.config.get("BUILD_MANAGER")
    if build_manager_config is None:
        return

    # If the build system is externally managed, then we just sleep this process.
    if build_manager_config[0] == EXTERNALLY_MANAGED:
        logger.debug("Builds are externally managed.")
        while True:
            time.sleep(1000)
        return

    logger.debug('Asking to start build manager with lifecycle "%s"', build_manager_config[0])
    manager_klass = BUILD_MANAGERS.get(build_manager_config[0])
    if manager_klass is None:
        return

    manager_hostname = os.environ.get(
        "BUILDMAN_HOSTNAME", app.config.get("BUILDMAN_HOSTNAME", app.config["SERVER_HOSTNAME"])
    )
    websocket_port = int(
        os.environ.get(
            "BUILDMAN_WEBSOCKET_PORT",
            app.config.get("BUILDMAN_WEBSOCKET_PORT", DEFAULT_WEBSOCKET_PORT),
        )
    )
    controller_port = int(
        os.environ.get(
            "BUILDMAN_CONTROLLER_PORT",
            app.config.get("BUILDMAN_CONTROLLER_PORT", DEFAULT_CONTROLLER_PORT),
        )
    )

    logger.debug(
        "Will pass buildman hostname %s to builders for websocket connection", manager_hostname
    )

    logger.debug('Starting build manager with lifecycle "%s"', build_manager_config[0])
    ssl_context = None
    if os.environ.get("SSL_CONFIG"):
        logger.debug("Loading SSL cert and key")
        ssl_context = SSLContext()
        ssl_context.load_cert_chain(
            os.path.join(os.environ.get("SSL_CONFIG"), "ssl.cert"),
            os.path.join(os.environ.get("SSL_CONFIG"), "ssl.key"),
        )

    server = BuilderServer(
        app.config["SERVER_HOSTNAME"],
        dockerfile_build_queue,
        build_logs,
        user_files,
        manager_klass,
        build_manager_config[1],
        manager_hostname,
    )
    server.run("0.0.0.0", websocket_port, controller_port, ssl=ssl_context)


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    logging.getLogger("peewee").setLevel(logging.WARN)
    logging.getLogger("boto").setLevel(logging.WARN)

    if app.config.get("EXCEPTION_LOG_TYPE", "FakeSentry") == "Sentry":
        buildman_name = "%s:buildman" % socket.gethostname()
        setup_logging(
            SentryHandler(app.config.get("SENTRY_DSN", ""), name=buildman_name, level=logging.ERROR)
        )

    run_build_manager()
