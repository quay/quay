import endpoints.decorated  # Note: We need to import this module to make sure the decorators are registered.
import features
from app import app as application
from endpoints.v2 import v2_bp

application.register_blueprint(v2_bp, url_prefix="/v2")
