import pytest

from endpoints.common import common_login
from endpoints.csrf import QUAY_CSRF_UPDATED_HEADER_NAME

from test.fixtures import *
from endpoints.common_models_pre_oci import pre_oci_model as model


@pytest.mark.parametrize(
    "username, expect_success",
    [
        # Valid users.
        ("devtable", True),
        ("public", True),
        # Org.
        ("buynlarge", False),
        # Robot.
        ("devtable+dtrobot", False),
        # Unverified user.
        ("unverified", False),
    ],
)
def test_common_login(username, expect_success, app):
    uuid = model.get_namespace_uuid(username)
    with app.app_context():
        success, headers = common_login(uuid)
        assert success == expect_success
        if success:
            assert QUAY_CSRF_UPDATED_HEADER_NAME in headers
