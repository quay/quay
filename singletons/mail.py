from flask_mail import Mail
from singletons.app import _app

mail = Mail(_app)
