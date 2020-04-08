# NOTE: Must be before we import or call anything that may be synchronous.
from gevent import monkey

monkey.patch_all()

from app import app as application
from endpoints.healthy import healthy


application.register_blueprint(healthy, url_prefix="/health")
