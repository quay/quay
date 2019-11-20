import logging

from flask import request, redirect, url_for, Blueprint
from flask_login import current_user

from app import app
from auth.decorators import require_session_login
from buildtrigger.basehandler import BuildTriggerHandler
from buildtrigger.bitbuckethandler import BitbucketBuildTrigger
from data import model
from endpoints.decorators import route_show_if
from util.http import abort

import features

logger = logging.getLogger(__name__)
client = app.config["HTTPCLIENT"]
bitbuckettrigger = Blueprint("bitbuckettrigger", __name__)


@bitbuckettrigger.route("/bitbucket/callback/trigger/<trigger_uuid>", methods=["GET"])
@route_show_if(features.BITBUCKET_BUILD)
@require_session_login
def attach_bitbucket_build_trigger(trigger_uuid):
    trigger = model.build.get_build_trigger(trigger_uuid)
    if not trigger or trigger.service.name != BitbucketBuildTrigger.service_name():
        abort(404)

    if trigger.connected_user != current_user.db_user():
        abort(404)

    verifier = request.args.get("oauth_verifier")
    handler = BuildTriggerHandler.get_handler(trigger)
    result = handler.exchange_verifier(verifier)
    if not result:
        trigger.delete_instance()
        return "Token has expired"

    namespace = trigger.repository.namespace_user.username
    repository = trigger.repository.name

    repo_path = "%s/%s" % (namespace, repository)
    full_url = url_for("web.buildtrigger", path=repo_path, trigger=trigger.uuid)

    logger.debug("Redirecting to full url: %s", full_url)
    return redirect(full_url)
