import logging
import os
import re

from flask import make_response, render_template
from flask_restful import reqparse

from config import frontend_visible_config
from external_libraries import get_external_javascript, get_external_css

from config_app.c_app import app, IS_KUBERNETES
from config_app._init_config import ROOT_DIR
from config_app.config_util.k8sconfig import get_k8s_namespace


def truthy_bool(param):
    return param not in {False, "false", "False", "0", "FALSE", "", "null"}


DEFAULT_JS_BUNDLE_NAME = "configapp"
PARAM_REGEX = re.compile(r"<([^:>]+:)*([\w]+)>")
logger = logging.getLogger(__name__)
TYPE_CONVERTER = {
    truthy_bool: "boolean",
    str: "string",
    str: "string",
    reqparse.text_type: "string",
    int: "integer",
}


def _list_files(path, extension, contains=""):
    """
    Returns a list of all the files with the given extension found under the given path.
    """

    def matches(f):
        return os.path.splitext(f)[1] == "." + extension and contains in os.path.splitext(f)[0]

    def join_path(dp, f):
        # Remove the static/ prefix. It is added in the template.
        return os.path.join(dp, f)[len(ROOT_DIR) + 1 + len("config_app/static/") :]

    filepath = os.path.join(os.path.join(ROOT_DIR, "config_app/static/"), path)
    return [join_path(dp, f) for dp, _, files in os.walk(filepath) for f in files if matches(f)]


FONT_AWESOME_4 = "netdna.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.css"


def render_page_template(name, route_data=None, js_bundle_name=DEFAULT_JS_BUNDLE_NAME, **kwargs):
    """
    Renders the page template with the given name as the response and returns its contents.
    """
    main_scripts = _list_files("build", "js", js_bundle_name)

    use_cdn = os.getenv("TESTING") == "true"

    external_styles = get_external_css(local=not use_cdn, exclude=FONT_AWESOME_4)
    external_scripts = get_external_javascript(local=not use_cdn)

    contents = render_template(
        name,
        route_data=route_data,
        main_scripts=main_scripts,
        external_styles=external_styles,
        external_scripts=external_scripts,
        config_set=frontend_visible_config(app.config),
        kubernetes_namespace=IS_KUBERNETES and get_k8s_namespace(),
        **kwargs
    )

    resp = make_response(contents)
    resp.headers["X-FRAME-OPTIONS"] = "DENY"
    return resp


def fully_qualified_name(method_view_class):
    return "%s.%s" % (method_view_class.__module__, method_view_class.__name__)
