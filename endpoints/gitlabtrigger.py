import logging

from flask import Blueprint, request, redirect, url_for
from flask_login import current_user

import features

from app import app, gitlab_trigger
from auth.decorators import require_session_login
from auth.permissions import AdministerRepositoryPermission
from data import model
from endpoints.decorators import route_show_if
from util.http import abort


logger = logging.getLogger(__name__)
client = app.config["HTTPCLIENT"]
gitlabtrigger = Blueprint("gitlab", __name__)


@gitlabtrigger.route("/gitlab/callback/trigger", methods=["GET"])
@route_show_if(features.GITLAB_BUILD)
@require_session_login
def attach_gitlab_build_trigger():
    state = request.args.get("state", None)
    if not state:
        abort(400)
    state = state[len("repo:") :]
    try:
        [namespace, repository] = state.split("/")
    except ValueError:
        abort(400)

    permission = AdministerRepositoryPermission(namespace, repository)
    if permission.can():
        code = request.args.get("code")
        token = gitlab_trigger.exchange_code_for_token(
            app.config, client, code, redirect_suffix="/trigger"
        )
        if not token:
            msg = "Could not exchange token. It may have expired."
            abort(404, message=msg)

        repo = model.repository.get_repository(namespace, repository)
        if not repo:
            msg = "Invalid repository: %s/%s" % (namespace, repository)
            abort(404, message=msg)
        elif repo.kind.name != "image":
            abort(501)

        trigger = model.build.create_build_trigger(repo, "gitlab", token, current_user.db_user())
        repo_path = "%s/%s" % (namespace, repository)
        full_url = url_for("web.buildtrigger", path=repo_path, trigger=trigger.uuid)

        logger.debug("Redirecting to full url: %s", full_url)
        return redirect(full_url)

    abort(403)
