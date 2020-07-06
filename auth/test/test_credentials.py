# -*- coding: utf-8 -*-

from auth.credentials import validate_credentials, CredentialKind
from auth.credential_consts import (
    ACCESS_TOKEN_USERNAME,
    OAUTH_TOKEN_USERNAME,
    APP_SPECIFIC_TOKEN_USERNAME,
)
from auth.validateresult import AuthKind, ValidateResult
from data import model

from test.fixtures import *


def test_valid_user(app):
    result, kind = validate_credentials("devtable", "password")
    assert kind == CredentialKind.user
    assert result == ValidateResult(AuthKind.credentials, user=model.user.get_user("devtable"))


def test_valid_robot(app):
    robot, password = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    result, kind = validate_credentials(robot.username, password)
    assert kind == CredentialKind.robot
    assert result == ValidateResult(AuthKind.credentials, robot=robot)


def test_valid_robot_for_disabled_user(app):
    user = model.user.get_user("devtable")
    user.enabled = False
    user.save()

    robot, password = model.user.create_robot("somerobot", user)
    result, kind = validate_credentials(robot.username, password)
    assert kind == CredentialKind.robot

    err = "This user has been disabled. Please contact your administrator."
    assert result == ValidateResult(AuthKind.credentials, error_message=err)


def test_valid_token(app):
    access_token = model.token.create_delegate_token("devtable", "simple", "sometoken")
    result, kind = validate_credentials(ACCESS_TOKEN_USERNAME, access_token.get_code())
    assert kind == CredentialKind.token
    assert result == ValidateResult(AuthKind.credentials, token=access_token)


def test_valid_oauth(app):
    user = model.user.get_user("devtable")
    app = model.oauth.list_applications_for_org(model.user.get_user_or_org("buynlarge"))[0]
    oauth_token, code = model.oauth.create_access_token_for_testing(
        user, app.client_id, "repo:read"
    )
    result, kind = validate_credentials(OAUTH_TOKEN_USERNAME, code)
    assert kind == CredentialKind.oauth_token
    assert result == ValidateResult(AuthKind.oauth, oauthtoken=oauth_token)


def test_invalid_user(app):
    result, kind = validate_credentials("devtable", "somepassword")
    assert kind == CredentialKind.user
    assert result == ValidateResult(
        AuthKind.credentials, error_message="Invalid Username or Password"
    )


def test_valid_app_specific_token(app):
    user = model.user.get_user("devtable")
    app_specific_token = model.appspecifictoken.create_token(user, "some token")
    full_token = model.appspecifictoken.get_full_token_string(app_specific_token)
    result, kind = validate_credentials(APP_SPECIFIC_TOKEN_USERNAME, full_token)
    assert kind == CredentialKind.app_specific_token
    assert result == ValidateResult(AuthKind.credentials, appspecifictoken=app_specific_token)


def test_valid_app_specific_token_for_disabled_user(app):
    user = model.user.get_user("devtable")
    user.enabled = False
    user.save()

    app_specific_token = model.appspecifictoken.create_token(user, "some token")
    full_token = model.appspecifictoken.get_full_token_string(app_specific_token)
    result, kind = validate_credentials(APP_SPECIFIC_TOKEN_USERNAME, full_token)
    assert kind == CredentialKind.app_specific_token

    err = "This user has been disabled. Please contact your administrator."
    assert result == ValidateResult(AuthKind.credentials, error_message=err)


def test_invalid_app_specific_token(app):
    result, kind = validate_credentials(APP_SPECIFIC_TOKEN_USERNAME, "somecode")
    assert kind == CredentialKind.app_specific_token
    assert result == ValidateResult(AuthKind.credentials, error_message="Invalid token")


def test_invalid_app_specific_token_code(app):
    user = model.user.get_user("devtable")
    app_specific_token = model.appspecifictoken.create_token(user, "some token")
    full_token = app_specific_token.token_name + "something"
    result, kind = validate_credentials(APP_SPECIFIC_TOKEN_USERNAME, full_token)
    assert kind == CredentialKind.app_specific_token
    assert result == ValidateResult(AuthKind.credentials, error_message="Invalid token")


def test_unicode(app):
    result, kind = validate_credentials("someusername", "some₪code")
    assert kind == CredentialKind.user
    assert not result.auth_valid
    assert result == ValidateResult(
        AuthKind.credentials, error_message="Invalid Username or Password"
    )


def test_unicode_robot(app):
    robot, _ = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    result, kind = validate_credentials(robot.username, "some₪code")

    assert kind == CredentialKind.robot
    assert not result.auth_valid

    msg = "Could not find robot with username: devtable+somerobot and supplied password."
    assert result == ValidateResult(AuthKind.credentials, error_message=msg)


def test_invalid_user(app):
    result, kind = validate_credentials("someinvaliduser", "password")
    assert kind == CredentialKind.user
    assert not result.authed_user
    assert not result.auth_valid


def test_invalid_user_password(app):
    result, kind = validate_credentials("devtable", "somepassword")
    assert kind == CredentialKind.user
    assert not result.authed_user
    assert not result.auth_valid


def test_invalid_robot(app):
    result, kind = validate_credentials("devtable+doesnotexist", "password")
    assert kind == CredentialKind.robot
    assert not result.authed_user
    assert not result.auth_valid


def test_invalid_robot_token(app):
    robot, _ = model.user.create_robot("somerobot", model.user.get_user("devtable"))
    result, kind = validate_credentials(robot.username, "invalidpassword")
    assert kind == CredentialKind.robot
    assert not result.authed_user
    assert not result.auth_valid


def test_invalid_unicode_robot(app):
    token = "“4JPCOLIVMAY32Q3XGVPHC4CBF8SKII5FWNYMASOFDIVSXTC5I5NBU”"
    result, kind = validate_credentials("devtable+somerobot", token)
    assert kind == CredentialKind.robot
    assert not result.auth_valid
    msg = "Could not find robot with username: devtable+somerobot and supplied password."
    assert result == ValidateResult(AuthKind.credentials, error_message=msg)


def test_invalid_unicode_robot_2(app):
    user = model.user.get_user("devtable")
    robot, password = model.user.create_robot("somerobot", user)

    token = "“4JPCOLIVMAY32Q3XGVPHC4CBF8SKII5FWNYMASOFDIVSXTC5I5NBU”"
    result, kind = validate_credentials("devtable+somerobot", token)
    assert kind == CredentialKind.robot
    assert not result.auth_valid
    msg = "Could not find robot with username: devtable+somerobot and supplied password."
    assert result == ValidateResult(AuthKind.credentials, error_message=msg)
