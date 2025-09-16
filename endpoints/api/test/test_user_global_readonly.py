from unittest.mock import patch

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import Signout, User
from endpoints.test.shared import client_with_identity
from test.fixtures import *  # noqa: F401,F403


def test_signout_allowed_for_global_readonly(app):
    with client_with_identity("reader", app) as cl:
        conduct_api_call(cl, Signout, "POST", None, None, 200)


def test_update_user_blocked_for_global_readonly(app):
    with patch("endpoints.api.user.allow_if_global_readonly_superuser", return_value=True):
        with client_with_identity("reader", app) as cl:
            conduct_api_call(
                cl,
                User,
                "PUT",
                None,
                {"password": "newpass"},
                403,
            )
