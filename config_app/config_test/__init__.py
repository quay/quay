import json as py_json
import unittest
from contextlib import contextmanager
from urllib.parse import urlencode
from urllib.parse import urlparse, parse_qs, urlunparse

from config_app.c_app import app, config_provider
from config_app.config_endpoints.api import api
from initdb import setup_database_for_testing, finished_database_for_testing


CSRF_TOKEN_KEY = "_csrf_token"
CSRF_TOKEN = "123csrfforme"

READ_ACCESS_USER = "reader"
ADMIN_ACCESS_USER = "devtable"
ADMIN_ACCESS_EMAIL = "jschorr@devtable.com"

# OVERRIDES FROM PORTING FROM OLD APP:
all_queues = []  # the config app doesn't have any queues


class ApiTestCase(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def _add_csrf(without_csrf):
        parts = urlparse(without_csrf)
        query = parse_qs(parts[4])
        query[CSRF_TOKEN_KEY] = CSRF_TOKEN
        return urlunparse(list(parts[0:4]) + [urlencode(query)] + list(parts[5:]))

    def url_for(self, resource_name, params=None, skip_csrf=False):
        params = params or {}
        url = api.url_for(resource_name, **params)
        if not skip_csrf:
            url = ApiTestCase._add_csrf(url)
        return url

    def setUp(self):
        setup_database_for_testing(self)
        self.app = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.__enter__()
        self.setCsrfToken(CSRF_TOKEN)

    def tearDown(self):
        finished_database_for_testing(self)
        config_provider.clear()
        self.ctx.__exit__(True, None, None)

    def setCsrfToken(self, token):
        with self.app.session_transaction() as sess:
            sess[CSRF_TOKEN_KEY] = token

    @contextmanager
    def toggleFeature(self, name, enabled):
        import features

        previous_value = getattr(features, name)
        setattr(features, name, enabled)
        yield
        setattr(features, name, previous_value)

    def getJsonResponse(self, resource_name, params={}, expected_code=200):
        rv = self.app.get(api.url_for(resource_name, **params))
        self.assertEqual(expected_code, rv.status_code)
        data = rv.data
        parsed = py_json.loads(data)
        return parsed

    def postResponse(
        self, resource_name, params={}, data={}, file=None, headers=None, expected_code=200
    ):
        data = py_json.dumps(data)

        headers = headers or {}
        headers.update({"Content-Type": "application/json"})

        if file is not None:
            data = {"file": file}
            headers = None

        rv = self.app.post(self.url_for(resource_name, params), data=data, headers=headers)
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def getResponse(self, resource_name, params={}, expected_code=200):
        rv = self.app.get(api.url_for(resource_name, **params))
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def putResponse(self, resource_name, params={}, data={}, expected_code=200):
        rv = self.app.put(
            self.url_for(resource_name, params),
            data=py_json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def deleteResponse(self, resource_name, params={}, expected_code=204):
        rv = self.app.delete(self.url_for(resource_name, params))

        if rv.status_code != expected_code:
            print("Mismatch data for resource DELETE %s: %s" % (resource_name, rv.data))

        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def deleteEmptyResponse(self, resource_name, params={}, expected_code=204):
        rv = self.app.delete(self.url_for(resource_name, params))
        self.assertEqual(rv.status_code, expected_code)
        self.assertEqual(rv.data, "")  # ensure response body empty
        return

    def postJsonResponse(self, resource_name, params={}, data={}, expected_code=200):
        rv = self.app.post(
            self.url_for(resource_name, params),
            data=py_json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

        if rv.status_code != expected_code:
            print("Mismatch data for resource POST %s: %s" % (resource_name, rv.data))

        self.assertEqual(rv.status_code, expected_code)
        data = rv.data
        parsed = py_json.loads(data)
        return parsed

    def putJsonResponse(
        self, resource_name, params={}, data={}, expected_code=200, skip_csrf=False
    ):
        rv = self.app.put(
            self.url_for(resource_name, params, skip_csrf),
            data=py_json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

        if rv.status_code != expected_code:
            print("Mismatch data for resource PUT %s: %s" % (resource_name, rv.data))

        self.assertEqual(rv.status_code, expected_code)
        data = rv.data
        parsed = py_json.loads(data)
        return parsed

    def assertNotInTeam(self, data, membername):
        for memberData in data["members"]:
            if memberData["name"] == membername:
                self.fail(membername + " found in team: " + data["name"])

    def assertInTeam(self, data, membername):
        for member_data in data["members"]:
            if member_data["name"] == membername:
                return

        self.fail(membername + " not found in team: " + data["name"])
