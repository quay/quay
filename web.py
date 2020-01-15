from app import app as application
from endpoints.api import api_bp
from endpoints.bitbuckettrigger import bitbuckettrigger
from endpoints.githubtrigger import githubtrigger
from endpoints.gitlabtrigger import gitlabtrigger
from endpoints.keyserver import key_server
from endpoints.oauth.login import oauthlogin
from endpoints.realtime import realtime
from endpoints.web import web
from endpoints.webhooks import webhooks
from endpoints.wellknown import wellknown


application.register_blueprint(web)
application.register_blueprint(githubtrigger, url_prefix="/oauth2")
application.register_blueprint(gitlabtrigger, url_prefix="/oauth2")
application.register_blueprint(oauthlogin, url_prefix="/oauth2")
application.register_blueprint(bitbuckettrigger, url_prefix="/oauth1")
application.register_blueprint(api_bp, url_prefix="/api")
application.register_blueprint(webhooks, url_prefix="/webhooks")
application.register_blueprint(realtime, url_prefix="/realtime")
application.register_blueprint(key_server, url_prefix="/keys")
application.register_blueprint(wellknown, url_prefix="/.well-known")
