import os
from functools import wraps

from flask import make_response, request
from werkzeug.utils import secure_filename

import features

from app import app
from auth.decorators import process_basic_auth_no_pass
from auth.registry_jwt_auth import process_registry_jwt_auth
from endpoints.v2 import require_repo_write
from endpoints.decorators import (
    anon_protect,
    check_pushes_disabled,
    check_readonly,
    disallow_for_account_recovery_mode,
    parse_repository_name,
    route_show_if,
)
from pulp import pulp_bp, pulp_client

# UPLOAD_FOLDER = '/quay-registry'
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


BASE_PULP_PLUGIN_RPM_ROUTE = "/<repopath:repository>/_pulp/rpm"


@pulp_bp.route(BASE_PULP_PLUGIN_RPM_ROUTE, methods=["GET"])
@parse_repository_name()
@anon_protect
def pulp_plugin_support(namespace_name, repo_name):
    raise NotImplementedError()


@pulp_bp.route(BASE_PULP_PLUGIN_RPM_ROUTE, methods=["POST"])
@route_show_if(features.PULP_PLUGIN)
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_basic_auth_no_pass
@require_repo_write(allow_for_superuser=False, disallow_for_restricted_users=True)
@anon_protect
@check_readonly
@check_pushes_disabled
def pulp_publish_rpm(namespace_name, repo_name):
    ref_name = "/".join([namespace_name, repo_name])

    pulp_repo = pulp_client.get_repository(ref_name)
    if pulp_repo.json().get("count") == 0:
        assert pulp_client.create_repository(ref_name).status_code // 100 == 2

    repository_prn = pulp_repo.json()["results"][0]["prn"]

    pulp_dist = pulp_client.get_distribution(ref_name)
    if pulp_dist.json().get("count") == 0:
        assert pulp_client.create_distribution(ref_name, repository_prn, basepath=ref_name).status_code // 100 == 2

    fname, file_obj = next(request.files.items())
    filename = secure_filename(fname)
    # file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # content_upload = pulp_client.create_content(repository_prn, os.path.join(app.config['UPLOAD_FOLDER'], filename))
    content_upload = pulp_client.create_content(repository_prn, f=file_obj)

    return make_response("%s/%s" % (namespace_name, repo_name), 202)
