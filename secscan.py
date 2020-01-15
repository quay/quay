from app import app as application
from endpoints.secscan import secscan


application.register_blueprint(secscan, url_prefix="/secscan")
