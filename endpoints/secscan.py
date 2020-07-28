import logging

from flask import make_response, Blueprint, jsonify
from data.database import ManifestSecurityStatus, Manifest
from endpoints.decorators import anon_allowed

logger = logging.getLogger(__name__)
secscan = Blueprint("secscan", __name__)


@secscan.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)


@secscan.route("/_backfill_status")
@anon_allowed
def manifest_security_backfill_status():
    manifest_count = Manifest.select().count()
    mss_count = ManifestSecurityStatus.select().count()
    return jsonify({"backfill_percent": mss_count / float(manifest_count)})
