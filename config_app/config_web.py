from config_app.c_app import app as application
from config_app.config_endpoints.api import api_bp
from config_app.config_endpoints.setup_web import setup_web

application.register_blueprint(setup_web)
application.register_blueprint(api_bp, url_prefix="/api")
