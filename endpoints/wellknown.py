import json
import logging

from app import get_app_url
from auth.decorators import require_session_login
from auth.auth_context import get_authenticated_user
from flask import Blueprint, make_response, redirect

logger = logging.getLogger(__name__)
wellknown = Blueprint("wellknown", __name__)


@wellknown.route("/app-capabilities", methods=["GET"])
def app_capabilities():
    view_image_tmpl = "%s/{namespace}/{reponame}:{tag}" % get_app_url()

    image_security = "%s/api/v1/repository/{namespace}/{reponame}/image/{imageid}/security"
    image_security_tmpl = image_security % get_app_url()

    manifest_security = "%s/api/v1/repository/{namespace}/{reponame}/manifest/{digest}/security"
    manifest_security_tmpl = manifest_security % get_app_url()

    metadata = {
        "appName": "io.quay",
        "capabilities": {
            "io.quay.view-image": {
                "url-template": view_image_tmpl,
            },
            "io.quay.image-security": {
                "rest-api-template": image_security_tmpl,
                "deprecated": True,
            },
            "io.quay.manifest-security": {
                "rest-api-template": manifest_security_tmpl,
            },
        },
    }

    resp = make_response(json.dumps(metadata))
    resp.headers["Content-Type"] = "application/json"
    return resp


@wellknown.route("/change-password", methods=["GET"])
@require_session_login
def change_password():
    return redirect("/user/%s?tab=settings" % get_authenticated_user().username)
