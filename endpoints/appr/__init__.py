import logging

from functools import wraps

from cnr.exception import Forbidden
from flask import Blueprint

from app import metric_queue
from auth.permissions import (
    AdministerRepositoryPermission,
    ReadRepositoryPermission,
    ModifyRepositoryPermission,
)
from endpoints.appr.decorators import require_repo_permission
from util.metrics.metricqueue import time_blueprint


appr_bp = Blueprint("appr", __name__)
time_blueprint(appr_bp, metric_queue)
logger = logging.getLogger(__name__)


def _raise_method(repository, scopes):
    raise Forbidden(
        "Unauthorized access for: %s" % repository, {"package": repository, "scopes": scopes}
    )


def _get_reponame_kwargs(*args, **kwargs):
    return [kwargs["namespace"], kwargs["package_name"]]


require_app_repo_read = require_repo_permission(
    ReadRepositoryPermission,
    scopes=["pull"],
    allow_public=True,
    raise_method=_raise_method,
    get_reponame_method=_get_reponame_kwargs,
)

require_app_repo_write = require_repo_permission(
    ModifyRepositoryPermission,
    scopes=["pull", "push"],
    raise_method=_raise_method,
    get_reponame_method=_get_reponame_kwargs,
)

require_app_repo_admin = require_repo_permission(
    AdministerRepositoryPermission,
    scopes=["pull", "push"],
    raise_method=_raise_method,
    get_reponame_method=_get_reponame_kwargs,
)
