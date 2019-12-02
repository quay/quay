import logging

from flask import request, redirect, url_for, Blueprint
from flask_login import current_user

import features

from app import app, github_trigger
from auth.decorators import require_session_login
from auth.permissions import AdministerRepositoryPermission
from data import model
from endpoints.decorators import route_show_if, parse_repository_name
from util.http import abort


logger = logging.getLogger(__name__)
client = app.config["HTTPCLIENT"]
githubtrigger = Blueprint("callback", __name__)


@githubtrigger.route("/github/callback/trigger/<repopath:repository>", methods=["GET"])
@route_show_if(features.GITHUB_BUILD)
@require_session_login
@parse_repository_name()
def attach_github_build_trigger(namespace_name, repo_name):
    permission = AdministerRepositoryPermission(namespace_name, repo_name)
    if permission.can():
        code = request.args.get("code")
        token = github_trigger.exchange_code_for_token(app.config, client, code)
        repo = model.repository.get_repository(namespace_name, repo_name)
        if not repo:
            msg = "Invalid repository: %s/%s" % (namespace_name, repo_name)
            abort(404, message=msg)
        elif repo.kind.name != "image":
            abort(501)

        trigger = model.build.create_build_trigger(repo, "github", token, current_user.db_user())
        repo_path = "%s/%s" % (namespace_name, repo_name)
        full_url = url_for("web.buildtrigger", path=repo_path, trigger=trigger.uuid)

        logger.debug("Redirecting to full url: %s", full_url)
        return redirect(full_url)

    abort(403)
