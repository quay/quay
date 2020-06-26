import os
import logging
import urllib.parse

from uuid import uuid4
from _pyio import BufferedReader

import magic

from flask import url_for, request, send_file, make_response, abort
from flask.views import View
from util import get_app_url


logger = logging.getLogger(__name__)


class UserfilesHandlers(View):
    methods = ["GET", "PUT"]

    def __init__(self, distributed_storage, location, files):
        self._storage = distributed_storage
        self._files = files
        self._locations = {location}
        self._magic = magic.Magic(mime=True)

    def get(self, file_id):
        path = self._files.get_file_id_path(file_id)
        try:
            file_stream = self._storage.stream_read_file(self._locations, path)
            buffered = BufferedReader(file_stream)
            file_header_bytes = buffered.peek(1024)
            buffered.seek(0)
            return send_file(
                buffered,
                mimetype=self._magic.from_buffer(file_header_bytes),
                as_attachment=True,
                attachment_filename=file_id,
            )
        except IOError:
            logger.exception("Error reading user file")
            abort(404)

    def put(self, file_id):
        input_stream = request.stream
        if request.headers.get("transfer-encoding") == "chunked":
            # Careful, might work only with WSGI servers supporting chunked
            # encoding (Gunicorn)
            input_stream = request.environ["wsgi.input"]

        c_type = request.headers.get("Content-Type", None)

        path = self._files.get_file_id_path(file_id)
        self._storage.stream_write(self._locations, path, input_stream, c_type)

        return make_response("Okay")

    def dispatch_request(self, file_id):
        if request.method == "GET":
            return self.get(file_id)
        elif request.method == "PUT":
            return self.put(file_id)


class MissingHandlerException(Exception):
    pass


class DelegateUserfiles(object):
    def __init__(self, app, distributed_storage, location, path, handler_name=None):
        self._app = app
        self._storage = distributed_storage
        self._locations = {location}
        self._prefix = path
        self._handler_name = handler_name

    def _build_url_adapter(self):
        return self._app.url_map.bind(
            self._app.config["SERVER_HOSTNAME"],
            script_name=self._app.config["APPLICATION_ROOT"] or "/",
            url_scheme=self._app.config["PREFERRED_URL_SCHEME"],
        )

    def get_file_id_path(self, file_id):
        # Note: We use basename here to prevent paths with ..'s and absolute paths.
        return os.path.join(self._prefix or "", os.path.basename(file_id))

    def prepare_for_drop(self, mime_type, requires_cors=True):
        """
        Returns a signed URL to upload a file to our bucket.
        """
        logger.debug("Requested upload url with content type: %s" % mime_type)
        file_id = str(uuid4())
        path = self.get_file_id_path(file_id)
        url = self._storage.get_direct_upload_url(self._locations, path, mime_type, requires_cors)

        if url is None:
            if self._handler_name is None:
                raise MissingHandlerException()

            with self._app.app_context() as ctx:
                ctx.url_adapter = self._build_url_adapter()
                file_relative_url = url_for(self._handler_name, file_id=file_id)
                file_url = urllib.parse.urljoin(get_app_url(self._app.config), file_relative_url)
                return (file_url, file_id)

        return (url, file_id)

    def store_file(self, file_like_obj, content_type, content_encoding=None, file_id=None):
        if file_id is None:
            file_id = str(uuid4())

        path = self.get_file_id_path(file_id)
        self._storage.stream_write(
            self._locations, path, file_like_obj, content_type, content_encoding
        )
        return file_id

    def get_file_url(self, file_id, remote_ip, expires_in=300, requires_cors=False):
        path = self.get_file_id_path(file_id)
        url = self._storage.get_direct_download_url(
            self._locations, path, remote_ip, expires_in, requires_cors
        )

        if url is None:
            if self._handler_name is None:
                raise MissingHandlerException()

            with self._app.app_context() as ctx:
                ctx.url_adapter = self._build_url_adapter()
                file_relative_url = url_for(self._handler_name, file_id=file_id)
                return urllib.parse.urljoin(get_app_url(self._app.config), file_relative_url)

        return url

    def get_file_checksum(self, file_id):
        path = self.get_file_id_path(file_id)
        return self._storage.get_checksum(self._locations, path)


class Userfiles(object):
    def __init__(
        self, app=None, distributed_storage=None, path="userfiles", handler_name="userfiles_handler"
    ):
        self.app = app
        if app is not None:
            self.state = self.init_app(
                app, distributed_storage, path=path, handler_name=handler_name
            )
        else:
            self.state = None

    def init_app(
        self, app, distributed_storage, path="userfiles", handler_name="userfiles_handler"
    ):
        location = app.config.get("USERFILES_LOCATION")
        userfiles_path = app.config.get("USERFILES_PATH", None)

        if userfiles_path is not None:
            userfiles = DelegateUserfiles(
                app, distributed_storage, location, userfiles_path, handler_name=handler_name
            )

            app.add_url_rule(
                '/%s/<regex("[0-9a-zA-Z-]+"):file_id>' % path,
                view_func=UserfilesHandlers.as_view(
                    handler_name,
                    distributed_storage=distributed_storage,
                    location=location,
                    files=userfiles,
                ),
            )

            # register extension with app
            app.extensions = getattr(app, "extensions", {})
            app.extensions["userfiles"] = userfiles

        return userfiles

    def __getattr__(self, name):
        return getattr(self.state, name, None)
