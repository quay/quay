import os
import logging

from cachetools.func import lru_cache
from flask import (
    abort,
    make_response,
    Blueprint,
    jsonify,
    session,
)

import features

from app import (
    app,
    config_provider,
    instance_keys,
)
from auth.decorators import process_auth_or_cookie
from data.database import db
from endpoints.api.discovery import swagger_route_data
from endpoints.common import render_page_template
from endpoints.decorators import (
    route_show_if,
)
from health.healthcheck import get_healthchecker
from util.cache import no_cache
from _init import ROOT_DIR


PGP_KEY_MIMETYPE = "application/pgp-keys"


@lru_cache(maxsize=1)
def _get_route_data():
    return swagger_route_data(include_internal=True, compact=True)


def render_page_template_with_routedata(name, *args, **kwargs):
    return render_page_template(name, _get_route_data(), *args, **kwargs)


# Capture the unverified SSL errors.
logger = logging.getLogger(__name__)
logging.captureWarnings(True)

healthy = Blueprint("healthy", __name__)

STATUS_TAGS = app.config["STATUS_TAGS"]


@healthy.route("/health", methods=["GET"])
@healthy.route("/health/instance", methods=["GET"])
@process_auth_or_cookie
@no_cache
def instance_health():
    checker = get_healthchecker(app, config_provider, instance_keys)
    (data, status_code) = checker.check_instance()
    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@healthy.route("/status", methods=["GET"])
@healthy.route("/health/endtoend", methods=["GET"])
@process_auth_or_cookie
@no_cache
def endtoend_health():
    checker = get_healthchecker(app, config_provider, instance_keys)
    (data, status_code) = checker.check_endtoend()
    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@healthy.route("/health/warning", methods=["GET"])
@process_auth_or_cookie
@no_cache
def warning_health():
    checker = get_healthchecker(app, config_provider, instance_keys)
    (data, status_code) = checker.check_warning()
    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@healthy.route("/health/dbrevision", methods=["GET"])
@route_show_if(features.BILLING)  # Since this is only used in production.
@process_auth_or_cookie
@no_cache
def dbrevision_health():
    # Find the revision from the database.
    result = db.execute_sql("select * from alembic_version limit 1").fetchone()
    db_revision = result[0]

    # Find the local revision from the file system.
    with open(os.path.join(ROOT_DIR, "ALEMBIC_HEAD"), "r") as f:
        local_revision = f.readline().split(" ")[0]

    data = {
        "db_revision": db_revision,
        "local_revision": local_revision,
    }

    status_code = 200 if db_revision == local_revision else 400

    response = jsonify(dict(data=data, status_code=status_code))
    response.status_code = status_code
    return response


@healthy.route("/health/enabledebug/<secret>", methods=["GET"])
@no_cache
def enable_health_debug(secret):
    if not secret:
        abort(404)

    if not app.config.get("ENABLE_HEALTH_DEBUG_SECRET"):
        abort(404)

    if app.config.get("ENABLE_HEALTH_DEBUG_SECRET") != secret:
        abort(404)

    session["health_debug"] = True
    return make_response("Health check debug information enabled")
