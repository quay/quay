import pytest

from flask import session
from flask_login import login_user
from werkzeug.exceptions import HTTPException

from app import LoginWrappedDBUser
from auth.auth_context import get_authenticated_user
from auth.decorators import (
    extract_namespace_repo_from_session,
    require_session_login,
    process_auth_or_cookie,
)
from data import model
from test.fixtures import *


def test_extract_namespace_repo_from_session_missing(app):
    def emptyfunc():
        pass

    session.clear()
    with pytest.raises(HTTPException):
        extract_namespace_repo_from_session(emptyfunc)()


def test_extract_namespace_repo_from_session_present(app):
    encountered = []

    def somefunc(namespace, repository):
        encountered.append(namespace)
        encountered.append(repository)

    # Add the namespace and repository to the session.
    session.clear()
    session["namespace"] = "foo"
    session["repository"] = "bar"

    # Call the decorated method.
    extract_namespace_repo_from_session(somefunc)()

    assert encountered[0] == "foo"
    assert encountered[1] == "bar"


def test_require_session_login_missing(app):
    def emptyfunc():
        pass

    with pytest.raises(HTTPException):
        require_session_login(emptyfunc)()


def test_require_session_login_valid_user(app):
    def emptyfunc():
        pass

    # Login as a valid user.
    someuser = model.user.get_user("devtable")
    login_user(LoginWrappedDBUser(someuser.uuid, someuser))

    # Call the function.
    require_session_login(emptyfunc)()

    # Ensure the authenticated user was updated.
    assert get_authenticated_user() == someuser


def test_require_session_login_invalid_user(app):
    def emptyfunc():
        pass

    # "Login" as a disabled user.
    someuser = model.user.get_user("disabled")
    login_user(LoginWrappedDBUser(someuser.uuid, someuser))

    # Call the function.
    with pytest.raises(HTTPException):
        require_session_login(emptyfunc)()

    # Ensure the authenticated user was not updated.
    assert get_authenticated_user() is None


def test_process_auth_or_cookie_invalid_user(app):
    def emptyfunc():
        pass

    # Call the function.
    process_auth_or_cookie(emptyfunc)()

    # Ensure the authenticated user was not updated.
    assert get_authenticated_user() is None


def test_process_auth_or_cookie_valid_user(app):
    def emptyfunc():
        pass

    # Login as a valid user.
    someuser = model.user.get_user("devtable")
    login_user(LoginWrappedDBUser(someuser.uuid, someuser))

    # Call the function.
    process_auth_or_cookie(emptyfunc)()

    # Ensure the authenticated user was  updated.
    assert get_authenticated_user() == someuser
