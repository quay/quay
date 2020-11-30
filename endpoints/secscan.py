import logging
import features
import json
import jwt
import base64

from flask import make_response, Blueprint, jsonify, abort, request

from app import secscan_notification_queue, app
from util.security.jwtutil import decode, TOKEN_REGEX
from data.database import ManifestSecurityStatus, Manifest
from endpoints.decorators import anon_allowed, route_show_if

logger = logging.getLogger(__name__)
secscan = Blueprint("secscan", __name__)

JWT_HEADER_NAME = "Authorization"


@secscan.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)


@route_show_if(features.SECURITY_SCANNER)
@route_show_if(features.SECURITY_NOTIFICATIONS)
@secscan.route("/notification", methods=["POST"])
@anon_allowed
def secscan_notification():
    # If Quay is configured with a Clair V4 PSK we assume
    # Clair will also sign JWT's with this PSK. Therefore,
    # attempt jwt verification.
    key = app.config.get("SECURITY_SCANNER_V4_PSK", None)
    if key:
        key = base64.b64decode(key)
        jwt_header = request.headers.get(JWT_HEADER_NAME, "")
        match = TOKEN_REGEX.match(jwt_header)
        if match is None:
            logger.error("Could not find matching bearer token")
            abort(401)
        token = match.group(1)
        try:
            decode(token, key=key, algorithms=["HS256"])
        except jwt.exceptions.InvalidTokenError as e:
            logger.error("Could not verify jwt {}".format(e))
            abort(401)
        logger.debug("Successfully verified jwt")

    data = request.get_json()
    if data is None:
        logger.error("expected json request")
        abort(400)

    logger.debug("Got notification from V4 Security Scanner: %s", data)
    if "notification_id" not in data or "callback" not in data:
        abort(400)

    notification_id = data["notification_id"]
    name = ["with_id", notification_id]
    if not secscan_notification_queue.alive(name):
        secscan_notification_queue.put(
            name,
            json.dumps({"notification_id": notification_id}),
        )

    return make_response("Okay")


@secscan.route("/_backfill_status")
@anon_allowed
def manifest_security_backfill_status():
    manifest_count = Manifest.select().count()
    mss_count = ManifestSecurityStatus.select().count()

    return jsonify({"backfill_percent": mss_count / float(manifest_count)})
