import logging

from .constants import PLUGIN_NAME
from .npm_routes import bp as npm_bp
from artifacts.plugins_base import BaseArtifactPlugin

logger = logging.getLogger(__name__)


class NpmPlugin(BaseArtifactPlugin):
    def __init__(self, name):
        super().__init__(name)

    def register_routes(self, app):
        app.register_blueprint(npm_bp, url_prefix="/npm")

    def register_workers(self):
        pass

    def __str__(self):
        return self.name


plugin = NpmPlugin(PLUGIN_NAME)
