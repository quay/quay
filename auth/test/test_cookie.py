import uuid

from flask_login import login_user

from app import LoginWrappedDBUser
from data import model
from auth.cookie import validate_session_cookie
from test.fixtures import *


def test_anonymous_cookie(app):
    assert validate_session_cookie().missing


def test_invalidformatted_cookie(app):
    # "Login" with a non-UUID reference.
    someuser = model.user.get_user("devtable")
    login_user(LoginWrappedDBUser("somenonuuid", someuser))

    # Ensure we get an invalid session cookie format error.
    result = validate_session_cookie()
    assert result.authed_user is None
    assert result.context.identity is None
    assert not result.has_nonrobot_user
    assert result.error_message == "Invalid session cookie format"


def test_disabled_user(app):
    # "Login" with a disabled user.
    someuser = model.user.get_user("disabled")
    login_user(LoginWrappedDBUser(someuser.uuid, someuser))

    # Ensure we get an invalid session cookie format error.
    result = validate_session_cookie()
    assert result.authed_user is None
    assert result.context.identity is None
    assert not result.has_nonrobot_user
    assert result.error_message == "User account is disabled"


def test_valid_user(app):
    # Login with a valid user.
    someuser = model.user.get_user("devtable")
    login_user(LoginWrappedDBUser(someuser.uuid, someuser))

    result = validate_session_cookie()
    assert result.authed_user == someuser
    assert result.context.identity is not None
    assert result.has_nonrobot_user
    assert result.error_message is None


def test_valid_organization(app):
    # "Login" with a valid organization.
    someorg = model.user.get_namespace_user("buynlarge")
    someorg.uuid = str(uuid.uuid4())
    someorg.verified = True
    someorg.save()

    login_user(LoginWrappedDBUser(someorg.uuid, someorg))

    result = validate_session_cookie()
    assert result.authed_user is None
    assert result.context.identity is None
    assert not result.has_nonrobot_user
    assert result.error_message == "Cannot login to organization"
