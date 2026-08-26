import datetime
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie

import pytest
from flask import session

from app import configure_app_session_lifetime
from endpoints.common import common_login
from endpoints.common_models_pre_oci import pre_oci_model as model
from endpoints.csrf import QUAY_CSRF_UPDATED_HEADER_NAME
from endpoints.test.shared import toggle_feature
from test.fixtures import *


def _save_session_cookie(app):
    response = app.response_class()
    app.session_interface.save_session(app, session, response)

    cookies = SimpleCookie()
    for header in response.headers.getlist("Set-Cookie"):
        cookies.load(header)

    return cookies[app.config["SESSION_COOKIE_NAME"]]


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
    with app.test_request_context():
        success, headers = common_login(uuid)
        assert success == expect_success
        if success:
            assert QUAY_CSRF_UPDATED_HEADER_NAME in headers


def test_configure_app_session_lifetime_uses_session_timeout(app):
    app.config["SESSION_TIMEOUT"] = "45m"

    configure_app_session_lifetime(app)

    assert app.permanent_session_lifetime == datetime.timedelta(minutes=45)


def test_common_login_sets_configured_permanent_session_expiration(app):
    app.config["SESSION_TIMEOUT"] = "2h"
    configure_app_session_lifetime(app)
    uuid = model.get_namespace_uuid("devtable")
    start_time = datetime.datetime.now(datetime.timezone.utc)

    with app.test_request_context():
        success, _ = common_login(uuid)

        assert success
        assert session.permanent

        session_cookie = _save_session_cookie(app)

    expires_at = parsedate_to_datetime(session_cookie["expires"])
    session_lifetime = expires_at - start_time

    assert datetime.timedelta(hours=2) - datetime.timedelta(seconds=5) <= session_lifetime
    assert session_lifetime <= datetime.timedelta(hours=2) + datetime.timedelta(seconds=5)


def test_common_login_uses_browser_session_when_permanent_sessions_disabled(app):
    app.config["SESSION_TIMEOUT"] = "2h"
    uuid = model.get_namespace_uuid("devtable")

    with toggle_feature("PERMANENT_SESSIONS", False):
        with app.test_request_context():
            session.permanent = True

            success, _ = common_login(uuid)

            assert success
            assert not session.permanent

            session_cookie = _save_session_cookie(app)

    assert session_cookie["expires"] == ""
