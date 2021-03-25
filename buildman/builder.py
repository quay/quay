import logging
import logging.config
import os
import time
import socket

import features

from app import (
    app,
    userfiles as user_files,
    build_logs,
    dockerfile_build_queue,
    instance_keys,
    OVERRIDE_CONFIG_DIRECTORY,
)
from util.log import logfile_path

from buildman.manager.ephemeral import EphemeralBuilderManager
from buildman.server import BuilderServer

from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

logger = logging.getLogger(__name__)

BUILD_MANAGERS = {
    "ephemeral": EphemeralBuilderManager,
}

EXTERNALLY_MANAGED = "external"

DEFAULT_CONTROLLER_PORT = 8686


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

    server = BuilderServer(
        app.config["SERVER_HOSTNAME"],
        manager_hostname,
        dockerfile_build_queue,
        build_logs,
        user_files,
        manager_klass,
        build_manager_config[1],
        instance_keys,
    )
    server.run("0.0.0.0", controller_port)


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
