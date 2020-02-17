"""
Superuser Config API.
"""

import logging
import os
import signal
import subprocess

from flask import abort

from app import app, config_provider
from auth.permissions import SuperUserPermission
from endpoints.api.suconfig_models_pre_oci import pre_oci_model as model
from endpoints.api import ApiResource, nickname, resource, internal_only, show_if, verify_not_prod

import features


logger = logging.getLogger(__name__)


def database_is_valid():
    """
    Returns whether the database, as configured, is valid.
    """
    if app.config["TESTING"]:
        return False

    return model.is_valid()


def database_has_users():
    """
    Returns whether the database has any users defined.
    """
    return model.has_users()


@resource("/v1/superuser/registrystatus")
@internal_only
@show_if(features.SUPER_USERS)
class SuperUserRegistryStatus(ApiResource):
    """
    Resource for determining the status of the registry, such as if config exists, if a database is
    configured, and if it has any defined users.
    """

    @nickname("scRegistryStatus")
    @verify_not_prod
    def get(self):
        """
        Returns the status of the registry.
        """
        # If we have SETUP_COMPLETE, then we're ready to go!
        if app.config.get("SETUP_COMPLETE", False):
            return {"provider_id": config_provider.provider_id, "status": "ready"}

        return {"status": "setup-incomplete"}


class _AlembicLogHandler(logging.Handler):
    def __init__(self):
        super(_AlembicLogHandler, self).__init__()
        self.records = []

    def emit(self, record):
        self.records.append({"level": record.levelname, "message": record.getMessage()})


# From: https://stackoverflow.com/a/44712205
def get_process_id(name):
    """
    Return process ids found by (partial) name or regex.

    >>> get_process_id('kthreadd')
    [2]
    >>> get_process_id('watchdog')
    [10, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56, 61]  # ymmv
    >>> get_process_id('non-existent process')
    []
    """
    child = subprocess.Popen(["pgrep", name], stdout=subprocess.PIPE, shell=False)
    response = child.communicate()[0]
    return [int(pid) for pid in response.split()]


@resource("/v1/superuser/shutdown")
@internal_only
@show_if(features.SUPER_USERS)
class SuperUserShutdown(ApiResource):
    """
    Resource for sending a shutdown signal to the container.
    """

    @verify_not_prod
    @nickname("scShutdownContainer")
    def post(self):
        """
        Sends a signal to the phusion init system to shut down the container.
        """
        # Note: This method is called to set the database configuration before super users exists,
        # so we also allow it to be called if there is no valid registry configuration setup.
        if app.config["TESTING"] or not database_has_users() or SuperUserPermission().can():
            # Note: We skip if debugging locally.
            if app.config.get("DEBUGGING") == True:
                return {}

            os.kill(get_process_id("my_init")[0], signal.SIGINT)
            return {}

        abort(403)
