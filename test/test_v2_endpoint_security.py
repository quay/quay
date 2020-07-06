import unittest
import json

import endpoints.decorated  # Register the various exceptions via decorators.

from app import app
from endpoints.v2 import v2_bp
from initdb import setup_database_for_testing, finished_database_for_testing
from test.specs import build_v2_index_specs

app.register_blueprint(v2_bp, url_prefix="/v2")

NO_ACCESS_USER = "freshuser"
READ_ACCESS_USER = "reader"
ADMIN_ACCESS_USER = "devtable"
CREATOR_ACCESS_USER = "creator"


class EndpointTestCase(unittest.TestCase):
    def setUp(self):
        setup_database_for_testing(self)

    def tearDown(self):
        finished_database_for_testing(self)


class _SpecTestBuilder(type):
    @staticmethod
    def _test_generator(url, test_spec, attrs):
        def test(self):
            with app.test_client() as c:
                headers = []
                expected_index_status = getattr(test_spec, attrs["result_attr"])

                if attrs["auth_username"]:

                    # Get a signed JWT.
                    username = attrs["auth_username"]
                    password = "password"

                    jwt_scope = test_spec.get_scope_string()
                    query_string = (
                        "service=" + app.config["SERVER_HOSTNAME"] + "&scope=" + jwt_scope
                    )

                    arv = c.open(
                        "/v2/auth",
                        headers=[("authorization", test_spec.gen_basic_auth(username, password))],
                        query_string=query_string,
                    )

                    msg = "Auth failed for %s %s: got %s, expected: 200" % (
                        test_spec.method_name,
                        test_spec.index_name,
                        arv.status_code,
                    )
                    self.assertEqual(arv.status_code, 200, msg)

                    headers = [("authorization", "Bearer " + json.loads(arv.data)["token"])]

                rv = c.open(url, headers=headers, method=test_spec.method_name)
                msg = "%s %s: got %s, expected: %s (auth: %s | headers %s)" % (
                    test_spec.method_name,
                    test_spec.index_name,
                    rv.status_code,
                    expected_index_status,
                    attrs["auth_username"],
                    len(headers),
                )

                self.assertEqual(rv.status_code, expected_index_status, msg)

        return test

    def __new__(cls, name, bases, attrs):
        with app.test_request_context() as ctx:
            specs = attrs["spec_func"]()
            for test_spec in specs:
                test_name = "%s_%s_%s_%s_%s" % (
                    test_spec.index_name,
                    test_spec.method_name,
                    test_spec.repo_name,
                    attrs["auth_username"] or "anon",
                    attrs["result_attr"],
                )
                test_name = test_name.replace("/", "_").replace("-", "_")

                test_name = "test_" + test_name.lower().replace("v2.", "v2_")
                url = test_spec.get_url()
                attrs[test_name] = _SpecTestBuilder._test_generator(url, test_spec, attrs)

        return type(name, bases, attrs)


class TestAnonymousAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v2_index_specs
    result_attr = "anon_code"
    auth_username = None


class TestNoAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v2_index_specs
    result_attr = "no_access_code"
    auth_username = NO_ACCESS_USER


class TestReadAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v2_index_specs
    result_attr = "read_code"
    auth_username = READ_ACCESS_USER


class TestCreatorAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v2_index_specs
    result_attr = "creator_code"
    auth_username = CREATOR_ACCESS_USER


class TestAdminAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v2_index_specs
    result_attr = "admin_code"
    auth_username = ADMIN_ACCESS_USER


if __name__ == "__main__":
    unittest.main()
