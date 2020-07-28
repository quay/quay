import logging

from flask import make_response, Blueprint
from endpoints.decorators import anon_allowed

logger = logging.getLogger(__name__)
secscan = Blueprint("secscan", __name__)


@secscan.route("/_internal_ping")
@anon_allowed
def internal_ping():
    return make_response("true", 200)
