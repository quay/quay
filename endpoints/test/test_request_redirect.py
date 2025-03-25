import json
import unittest

from werkzeug.routing.exceptions import RequestRedirect

import endpoints.decorated
from app import app


class TestRequestRedirect(unittest.TestCase):
    def setUp(self):

        self.app = app.test_client()
        self.app.application.config["PROPAGATE_EXCEPTIONS"] = True
        self.app.application.config["TRAP_HTTP_EXCEPTIONS"] = True
        self.app.base_url = "localhost:8080"
        self.ctx = app.test_request_context()
        self.ctx.__enter__()

    def tearDown(self):
        self.app.application.config["TRAP_HTTP_EXCEPTIONS"] = False
        self.ctx.__exit__(True, None, None)

    def test_handle_request_redirect(self):
        # add a fake route to raise exception
        @self.app.application.route("/raise-request-redirect")
        def raise_request_redirect():
            raise RequestRedirect("somepath")

        # add error handler to test client
        @self.app.application.errorhandler(RequestRedirect)
        def handle_request_redirect(e):
            return endpoints.decorated.handle_bad_redirect(e)

        path = "/raise-request-redirect"
        response = self.app.get(path)
        self.assertEqual(response.status_code, 308)
