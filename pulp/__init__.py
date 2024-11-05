import logging

from flask import Blueprint

from app import app
from pulp.client import PulpClient
from util.metrics.prometheus import timed_blueprint

logger = logging.getLogger(__name__)
pulp_bp = timed_blueprint(Blueprint("_pulp", __name__))

pulp_client = PulpClient(app.config.get("PULP_PLUGIN_CONFIG"))

from pulp import rpm
