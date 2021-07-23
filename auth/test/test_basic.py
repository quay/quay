# -*- coding: utf-8 -*-

import pytest

from base64 import b64encode

from auth.basic import validate_basic_auth
from auth.credentials import (
    ACCESS_TOKEN_USERNAME,
    OAUTH_TOKEN_USERNAME,
    APP_SPECIFIC_TOKEN_USERNAME,
)
from auth.validateresult import AuthKind, ValidateResult
from data import model

from test.fixtures import *


def _token(username, password):
    assert isinstance(username, str)
    assert isinstance(password, str)
    token_bytes = b"%s:%s" % (username.encode("utf-8"), password.encode("utf-8"))
    return "basic " + b64encode(token_bytes).decode("ascii")


@pytest.mark.parametrize(
    "token, expected_result",
    [
        ("", ValidateResult(AuthKind.basic, missing=True)),
        ("someinvalidtoken", ValidateResult(AuthKind.basic, missing=True)),
        ("somefoobartoken", ValidateResult(AuthKind.basic, missing=True)),
        ("basic ", ValidateResult(AuthKind.basic, missing=True)),
        ("basic some token", ValidateResult(AuthKind.basic, missing=True)),
        ("basic sometoken", ValidateResult(AuthKind.basic, missing=True)),
        (
            _token(APP_SPECIFIC_TOKEN_USERNAME, "invalid"),
            ValidateResult(AuthKind.basic, error_message="Invalid token"),
        ),
        (
            _token(ACCESS_TOKEN_USERNAME, "invalid"),
            ValidateResult(AuthKind.basic, error_message="Invalid access token"),
        ),
        (
            _token(OAUTH_TOKEN_USERNAME, "invalid"),
            ValidateResult(
                AuthKind.basic, error_message="OAuth access token could not be validated"
            ),
        ),
        (
            _token("devtable", "invalid"),
            ValidateResult(AuthKind.basic, error_message="Invalid Username or Password"),
        ),
        (
            _token("devtable+somebot", "invalid"),
            ValidateResult(
                AuthKind.basic, error_message="Could not find robot with specified username"
            ),
        ),
        (
            _token("disabled", "password"),
            ValidateResult(
                AuthKind.basic,
                error_message="This user has been disabled. Please contact your administrator.",
            ),
        ),
        (
            _token("usér", "passwôrd"),
            ValidateResult(AuthKind.basic, error_message="Invalid Username or Password"),
        ),
    ],
)
def test_validate_basic_auth_token(token, expected_result, app):
    result = validate_basic_auth(token)
    assert result == expected_result


def test_valid_user(app):
    token = _token("devtable", "password")
    result = validate_basic_auth(token)
    assert result == ValidateResult(AuthKind.basic, user=model.user.get_user("devtable"))


def test_valid_robot(app):
    robot, password = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    token = _token(robot.username, password)
    result = validate_basic_auth(token)
    assert result == ValidateResult(AuthKind.basic, robot=robot)


def test_valid_token(app):
    access_token = model.token.create_delegate_token("devtable", "simple", "sometoken")
    token = _token(ACCESS_TOKEN_USERNAME, access_token.get_code())
    result = validate_basic_auth(token)
    assert result == ValidateResult(AuthKind.basic, token=access_token)


def test_valid_oauth(app):
    user = model.user.get_user("devtable")
    app = model.oauth.list_applications_for_org(model.user.get_user_or_org("buynlarge"))[0]
    oauth_token, code = model.oauth.create_user_access_token(user, app.client_id, "repo:read")
    token = _token(OAUTH_TOKEN_USERNAME, code)
    result = validate_basic_auth(token)
    assert result == ValidateResult(AuthKind.basic, oauthtoken=oauth_token)


def test_valid_app_specific_token(app):
    user = model.user.get_user("devtable")
    app_specific_token = model.appspecifictoken.create_token(user, "some token")
    full_token = model.appspecifictoken.get_full_token_string(app_specific_token)
    token = _token(APP_SPECIFIC_TOKEN_USERNAME, full_token)
    result = validate_basic_auth(token)
    assert result == ValidateResult(AuthKind.basic, appspecifictoken=app_specific_token)


def test_invalid_unicode(app):
    token = b"\xebOH"
    header = "basic " + b64encode(token).decode("ascii")
    result = validate_basic_auth(header)
    assert result == ValidateResult(AuthKind.basic, missing=True)


def test_invalid_unicode_2(app):
    token = "“4JPCOLIVMAY32Q3XGVPHC4CBF8SKII5FWNYMASOFDIVSXTC5I5NBU”".encode("utf-8")
    header = "basic " + b64encode(b"devtable+somerobot:%s" % token).decode("ascii")
    result = validate_basic_auth(header)
    assert result == ValidateResult(
        AuthKind.basic,
        error_message="Could not find robot with username: devtable+somerobot and supplied password.",
    )


def test_invalid_unicode_3(app):
    token = "sometoken"
    auth = "“devtable+somerobot”:" + token
    auth = auth.encode("utf-8")
    header = "basic " + b64encode(auth).decode("ascii")
    result = validate_basic_auth(header)
    assert result == ValidateResult(
        AuthKind.basic,
        error_message="Could not find robot with specified username",
    )
