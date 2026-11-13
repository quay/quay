from app import app as application
from endpoints.blobstream import blobstream_bp

application.register_blueprint(blobstream_bp, url_prefix="/_upstream_proxy")
