# NOTE: Must be before we import or call anything that may be synchronous.
from gevent import monkey

monkey.patch_all()

from app import app as application
from endpoints.secscan import secscan

if not application.config.get("ACCOUNT_RECOVERY_MODE", False):
    application.register_blueprint(secscan, url_prefix="/secscan")
