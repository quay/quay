import os
import re

from flask import Blueprint
from cachetools.func import lru_cache

from config_app.config_endpoints.common import render_page_template
from config_app.config_endpoints.api.discovery import generate_route_data
from config_app.config_endpoints.api import no_cache

setup_web = Blueprint("setup_web", __name__, template_folder="templates")


def _get_readonly_fields():
    """
    Returns a list of fields which should be marked as "Read Only" in the
    UI as they are most likely managed by an external service such as an
    Operator.

    This expects an environment variable with the following format:
    CONFIG_READ_ONLY_FIELDS=redis,hostname
    """
    environment_variable_name = "CONFIG_READ_ONLY_FIELDS"
    values = os.getenv(environment_variable_name, "").split(",")
    selected = [value for value in values if re.match(r"^[a-z]{1,30}$", value)]
    return selected


@lru_cache(maxsize=1)
def _get_route_data():
    return generate_route_data()


def render_page_template_with_routedata(name, *args, **kwargs):
    return render_page_template(name, _get_route_data(), *args, **kwargs)


@no_cache
@setup_web.route("/", methods=["GET"], defaults={"path": ""})
def index(path, **kwargs):
    return render_page_template_with_routedata(
        "index.html", js_bundle_name="configapp", read_only_fields=_get_readonly_fields(), **kwargs
    )
