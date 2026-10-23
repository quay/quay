import datetime
from unittest.mock import MagicMock, patch

import pytest

from endpoints.api import require_fresh_login
from endpoints.exception import FreshLoginRequired, Unauthorized
from test.fixtures import *


@pytest.fixture
def dummy_func():
    func = MagicMock(return_value="success")
    func.__name__ = "dummy_func"
    func.__module__ = "test"
    return func


class TestRequireFreshLogin:
    def test_unauthenticated_user_rejected(self, app, dummy_func):
        wrapped = require_fresh_login(dummy_func)
        with app.test_request_context("/"):
            with patch("endpoints.api.get_authenticated_user", return_value=None):
                with pytest.raises(Unauthorized):
                    wrapped()
        dummy_func.assert_not_called()

    def test_robot_account_passes_through(self, app, dummy_func):
        mock_user = MagicMock()
        mock_user.robot = True
        wrapped = require_fresh_login(dummy_func)
        with app.test_request_context("/"):
            with patch("endpoints.api.get_authenticated_user", return_value=mock_user):
                result = wrapped()
        assert result == "success"
        dummy_func.assert_called_once()

    def test_fresh_login_passes(self, app, dummy_func):
        mock_user = MagicMock()
        mock_user.robot = False
        wrapped = require_fresh_login(dummy_func)
        with app.test_request_context("/"):
            with (
                patch("endpoints.api.get_authenticated_user", return_value=mock_user),
                patch("endpoints.api.get_validated_oauth_token", return_value=None),
                patch("endpoints.api.get_sso_token", return_value=None),
            ):
                from flask import session

                session["login_time"] = datetime.datetime.now(tz=datetime.timezone.utc)
                result = wrapped()
        assert result == "success"

    def test_stale_login_raises_fresh_login_required(self, app, dummy_func):
        mock_user = MagicMock()
        mock_user.robot = False
        mock_user.username = "testuser"
        wrapped = require_fresh_login(dummy_func)
        with app.test_request_context("/"):
            with (
                patch("endpoints.api.get_authenticated_user", return_value=mock_user),
                patch("endpoints.api.get_validated_oauth_token", return_value=None),
                patch("endpoints.api.get_sso_token", return_value=None),
                patch("endpoints.api.authentication") as mock_auth,
            ):
                mock_auth.supports_fresh_login = True
                mock_auth.has_password_set.return_value = True
                from flask import session

                session["login_time"] = datetime.datetime.min
                with pytest.raises(FreshLoginRequired):
                    wrapped()
        dummy_func.assert_not_called()
