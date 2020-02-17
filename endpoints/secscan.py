import logging
import json

import features

from app import secscan_notification_queue
from flask import request, make_response, Blueprint, abort
from endpoints.decorators import route_show_if, anon_allowed

logger = logging.getLogger(__name__)
secscan = Blueprint("secscan", __name__)


@route_show_if(features.SECURITY_SCANNER)
@secscan.route("/notify", methods=["POST"])
def secscan_notification():
    data = request.get_json()
    logger.debug("Got notification from Security Scanner: %s", data)
    if "Notification" not in data:
        abort(400)

    notification = data["Notification"]
    name = ["named", notification["Name"]]

    if not secscan_notification_queue.alive(name):
        secscan_notification_queue.put(name, json.dumps(notification))

    return make_response("Okay")


@secscan.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)
