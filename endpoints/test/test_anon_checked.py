import pytest

from app import app
from endpoints.v1 import v1_bp
from endpoints.v2 import v2_bp


@pytest.mark.parametrize("blueprint", [v2_bp, v1_bp,])
def test_verify_blueprint(blueprint):
    class Checker(object):
        def __init__(self):
            self.first_registration = True
            self.app = app

        def add_url_rule(self, rule, endpoint, view_function, methods=None):
            result = "__anon_protected" in dir(view_function) or "__anon_allowed" in dir(
                view_function
            )
            error_message = (
                "Missing anonymous access protection decorator on function "
                + "%s under blueprint %s" % (endpoint, blueprint.name)
            )
            assert result, error_message

    for deferred_function in blueprint.deferred_functions:
        deferred_function(Checker())
