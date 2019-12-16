import unittest
import endpoints.decorated
import json

from app import app
from util.names import parse_namespace_repository
from initdb import setup_database_for_testing, finished_database_for_testing
from .specs import build_v1_index_specs

from endpoints.v1 import v1_bp

app.register_blueprint(v1_bp, url_prefix="/v1")

NO_ACCESS_USER = "freshuser"
READ_ACCESS_USER = "reader"
CREATOR_ACCESS_USER = "creator"
ADMIN_ACCESS_USER = "devtable"


class EndpointTestCase(unittest.TestCase):
    def setUp(self):
        setup_database_for_testing(self)

    def tearDown(self):
        finished_database_for_testing(self)


class _SpecTestBuilder(type):
    @staticmethod
    def _test_generator(url, expected_status, open_kwargs, session_var_list):
        def test(self):
            with app.test_client() as c:
                if session_var_list:
                    # Temporarily remove the teardown functions
                    teardown_funcs = []
                    if None in app.teardown_request_funcs:
                        teardown_funcs = app.teardown_request_funcs[None]
                        app.teardown_request_funcs[None] = []

                    with c.session_transaction() as sess:
                        for sess_key, sess_val in session_var_list:
                            sess[sess_key] = sess_val

                    # Restore the teardown functions
                    app.teardown_request_funcs[None] = teardown_funcs

                rv = c.open(url, **open_kwargs)
                msg = "%s %s: %s expected: %s" % (
                    open_kwargs["method"],
                    url,
                    rv.status_code,
                    expected_status,
                )
                self.assertEqual(rv.status_code, expected_status, msg)

        return test

    def __new__(cls, name, bases, attrs):
        with app.test_request_context() as ctx:
            specs = attrs["spec_func"]()
            for test_spec in specs:
                url, open_kwargs = test_spec.get_client_args()

                if attrs["auth_username"]:
                    basic_auth = test_spec.gen_basic_auth(attrs["auth_username"], "password")
                    open_kwargs["headers"] = [("authorization", "%s" % basic_auth)]

                session_vars = []
                if test_spec.sess_repo:
                    ns, repo = parse_namespace_repository(test_spec.sess_repo, "library")
                    session_vars.append(("namespace", ns))
                    session_vars.append(("repository", repo))

                expected_status = getattr(test_spec, attrs["result_attr"])
                test = _SpecTestBuilder._test_generator(
                    url, expected_status, open_kwargs, session_vars
                )

                test_name_url = url.replace("/", "_").replace("-", "_")
                sess_repo = str(test_spec.sess_repo).replace("/", "_")
                test_name = "test_%s%s_%s_%s" % (
                    open_kwargs["method"].lower(),
                    test_name_url,
                    sess_repo,
                    attrs["result_attr"],
                )
                attrs[test_name] = test

        return type(name, bases, attrs)


class TestAnonymousAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v1_index_specs
    result_attr = "anon_code"
    auth_username = None


class TestNoAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v1_index_specs
    result_attr = "no_access_code"
    auth_username = NO_ACCESS_USER


class TestReadAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v1_index_specs
    result_attr = "read_code"
    auth_username = READ_ACCESS_USER


class TestCreatorAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v1_index_specs
    result_attr = "creator_code"
    auth_username = CREATOR_ACCESS_USER


class TestAdminAccess(EndpointTestCase, metaclass=_SpecTestBuilder):
    spec_func = build_v1_index_specs
    result_attr = "admin_code"
    auth_username = ADMIN_ACCESS_USER


if __name__ == "__main__":
    unittest.main()
