# NOTE: We don't gevent patch here because `verbs` uses `sync` workers.

from app import app as application
from endpoints.verbs import verbs


application.register_blueprint(verbs, url_prefix="/c1")
