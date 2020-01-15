import endpoints.decorated  # Note: We need to import this module to make sure the decorators are registered.
import features

from app import app as application

from endpoints.appr import appr_bp, registry  # registry needed to ensure routes registered
from endpoints.v1 import v1_bp
from endpoints.v2 import v2_bp


application.register_blueprint(v1_bp, url_prefix="/v1")
application.register_blueprint(v2_bp, url_prefix="/v2")

if features.APP_REGISTRY:
    application.register_blueprint(appr_bp, url_prefix="/cnr")
