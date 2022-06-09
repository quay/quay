from _init import TEMPLATE_DIR
from flask import Flask

# _app is a bare Flask object. Please don't use it directly from this package
# unless you need an uninitialized object.
_app = Flask(__name__, template_folder=TEMPLATE_DIR)


def app_context():
    return _app.app_context()
