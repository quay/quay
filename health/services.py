import logging
import os
import tempfile

import psutil

from app import build_logs, storage, authentication, instance_keys
from health.models_pre_oci import pre_oci_model as model

logger = logging.getLogger(__name__)


def _compute_internal_endpoint(app, endpoint):
    # Compute the URL for checking the endpoint. We append a port if and only if the
    # hostname contains one.
    hostname_parts = app.config["SERVER_HOSTNAME"].split(":")
    port = ""
    if hostname_parts[0] == "localhost":
        if len(hostname_parts) == 2:
            port = ":" + hostname_parts[1]

    scheme = app.config["PREFERRED_URL_SCHEME"]
    if app.config.get("EXTERNAL_TLS_TERMINATION", False):
        scheme = "http"

    if port == "":
        if scheme == "http":
            port = ":8080"
        else:
            port = ":8443"

    return "%s://localhost%s/%s" % (scheme, port, endpoint)


def _check_gunicorn(endpoint):
    def fn(app):
        """
        Returns the status of the gunicorn workers.
        """
        client = app.config["HTTPCLIENT"]
        registry_url = _compute_internal_endpoint(app, endpoint)
        try:
            status_code = client.get(registry_url, verify=False, timeout=2).status_code
            okay = status_code == 200
            message = ("Got non-200 response for worker: %s" % status_code) if not okay else None
            return (okay, message)
        except Exception as ex:
            logger.exception("Exception when checking worker health: %s", registry_url)
            return (False, "Exception when checking worker health: %s" % registry_url)

    return fn


def _check_jwt_proxy(app):
    """
    Returns the status of JWT proxy in the container.
    """
    client = app.config["HTTPCLIENT"]
    # FIXME(alecmerdler): This is no longer behind jwtproxy...
    registry_url = _compute_internal_endpoint(app, "secscan")
    try:
        status_code = client.get(registry_url, verify=False, timeout=2).status_code
        okay = status_code == 403
        return (
            okay,
            ("Got non-403 response for JWT proxy: %s" % status_code) if not okay else None,
        )
    except Exception as ex:
        logger.exception("Exception when checking jwtproxy health: %s", registry_url)
        return (False, "Exception when checking jwtproxy health: %s" % registry_url)


def _check_database(app):
    """
    Returns the status of the database, as accessed from this instance.
    """
    return model.check_health(app.config)


def _check_redis(app):
    """
    Returns the status of Redis, as accessed from this instance.
    """
    return build_logs.check_health()


def _check_storage(app):
    """
    Returns the status of storage, as accessed from this instance.
    """
    if app.config.get("REGISTRY_STATE", "normal") == "readonly":
        return (True, "Storage check disabled for readonly mode")

    try:
        storage.validate(storage.preferred_locations, app.config["HTTPCLIENT"])
        return (True, None)
    except Exception as ex:
        logger.exception("Storage check failed with exception %s", ex)
        return (False, "Storage check failed with exception %s" % ex.message)


def _check_auth(app):
    """
    Returns the status of the auth engine, as accessed from this instance.
    """
    return authentication.ping()


def _check_service_key(app):
    """
    Returns the status of the service key for this instance.

    If the key has disappeared or has expired, then will return False.
    """
    if not app.config.get("SETUP_COMPLETE", False):
        return (True, "Stack not fully setup; skipping check")

    try:
        kid = instance_keys.local_key_id
    except IOError as ex:
        # Key has not been created yet.
        return (True, "Stack not fully setup; skipping check")

    try:
        key_is_valid = bool(instance_keys.get_service_key_public_key(kid))
        message = "Could not find valid instance service key %s" % kid if not key_is_valid else None
        return (key_is_valid, message)
    except Exception as ex:
        logger.exception("Got exception when trying to retrieve the instance key")

        # NOTE: We return *True* here if there was an exception when retrieving the key, as it means
        # the database is down, which will be handled by the database health check.
        return (True, "Failed to get instance key due to a database issue; skipping check")


def _disk_within_threshold(path, threshold):
    usage = psutil.disk_usage(path)
    return (1.0 - (usage.percent / 100.0)) >= threshold


def _check_disk_space(for_warning):
    def _check_disk_space(app):
        """
        Returns the status of the disk space for this instance.

        If the available disk space is below a certain threshold, then will return False.
        """
        if not app.config.get("SETUP_COMPLETE", False):
            return (True, "Stack not fully setup; skipping check")

        config_key = (
            "DISKSPACE_HEALTH_WARNING_THRESHOLD" if for_warning else "DISKSPACE_HEALTH_THRESHOLD"
        )
        default_threshold = 0.1 if for_warning else 0.01

        # Check the directory in which we're running.
        currentfile = os.path.abspath(__file__)
        if not _disk_within_threshold(currentfile, app.config.get(config_key, default_threshold)):
            stats = psutil.disk_usage(currentfile)
            logger.debug("Disk space on main volume: %s", stats)
            return (False, "Disk space has gone below threshold on main volume: %s" % stats.percent)

        # Check the temp directory as well.
        tempdir = tempfile.gettempdir()
        if tempdir is not None:
            if not _disk_within_threshold(tempdir, app.config.get(config_key, default_threshold)):
                stats = psutil.disk_usage(tempdir)
                logger.debug("Disk space on temp volume: %s", stats)
                return (
                    False,
                    "Disk space has gone below threshold on temp volume: %s" % stats.percent,
                )

        return (True, "")

    return _check_disk_space


_INSTANCE_SERVICES = {
    "registry_gunicorn": _check_gunicorn("v1/_internal_ping"),
    "web_gunicorn": _check_gunicorn("_internal_ping"),
    "service_key": _check_service_key,
    "disk_space": _check_disk_space(for_warning=False),
    # https://issues.redhat.com/browse/PROJQUAY-1193
    # "jwtproxy": _check_jwt_proxy, TODO: remove with removal of jwtproxy in container
}

_GLOBAL_SERVICES = {
    "database": _check_database,
    "redis": _check_redis,
    "storage": _check_storage,
    "auth": _check_auth,
}

_WARNING_SERVICES = {
    "disk_space_warning": _check_disk_space(for_warning=True),
}


def check_all_services(app, skip, for_instance=False):
    """
    Returns a dictionary containing the status of all the services defined.
    """
    if for_instance:
        services = dict(_INSTANCE_SERVICES)
        services.update(_GLOBAL_SERVICES)
    else:
        services = _GLOBAL_SERVICES

    return _check_services(app, skip, services)


def check_warning_services(app, skip):
    """
    Returns a dictionary containing the status of all the warning services defined.
    """
    return _check_services(app, skip, _WARNING_SERVICES)


def _check_services(app, skip, services):
    status = {}
    for name in services:
        if name in skip:
            continue

        status[name] = services[name](app)

    return status
