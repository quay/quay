import logging
import features
import json

from flask import make_response, Blueprint, jsonify, abort, request

from app import secscan_notification_queue
from data.database import ManifestSecurityStatus, Manifest
from endpoints.decorators import anon_allowed, route_show_if

logger = logging.getLogger(__name__)
secscan = Blueprint("secscan", __name__)


@secscan.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)


@route_show_if(features.SECURITY_SCANNER)
@route_show_if(features.SECURITY_NOTIFICATIONS)
@secscan.route("/notification", methods=["POST"])
@anon_allowed
def secscan_notification():
    # TODO(alecmerdler): verify the JWT header is signed by the security scanner

    data = request.get_json()
    logger.debug("Got notification from V4 Security Scanner: %s", data)
    if "notification_id" not in data or "callback" not in data:
        abort(400)

    notification_id = data["notification_id"]
    name = ["with_id", notification_id]
    if not secscan_notification_queue.alive(name):
        secscan_notification_queue.put(
            name, json.dumps({"notification_id": notification_id}),
        )

    return make_response("Okay")


@secscan.route("/_backfill_status")
@anon_allowed
def manifest_security_backfill_status():
    manifest_count = Manifest.select().count()
    mss_count = ManifestSecurityStatus.select().count()

    return jsonify({"backfill_percent": mss_count / float(manifest_count)})
