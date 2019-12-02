import pytest

from werkzeug.exceptions import HTTPException

from data import model
from endpoints.appr import require_app_repo_read

from test.fixtures import *


def test_require_app_repo_read(app):
    called = [False]

    # Ensure that trying to read an *image* repository fails.
    @require_app_repo_read
    def empty(**kwargs):
        called[0] = True

    with pytest.raises(HTTPException):
        empty(namespace="devtable", package_name="simple")
        assert not called[0]
