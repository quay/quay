import logging

from util.registry.gzipinputstream import GzipInputStream
from flask import send_file, abort

from data.userfiles import DelegateUserfiles, UserfilesHandlers


JSON_MIMETYPE = "application/json"


logger = logging.getLogger(__name__)


class LogArchive(object):
    def __init__(self, app=None, distributed_storage=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app, distributed_storage)
        else:
            self.state = None

    def init_app(self, app, distributed_storage):
        location = app.config.get("LOG_ARCHIVE_LOCATION")
        path = app.config.get("LOG_ARCHIVE_PATH", None)

        handler_name = "web.logarchive"

        log_archive = DelegateUserfiles(
            app, distributed_storage, location, path, handler_name=handler_name
        )
        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["log_archive"] = log_archive
        return log_archive

    def __getattr__(self, name):
        return getattr(self.state, name, None)
