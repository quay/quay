import pytest

from auth.auth_context import get_authenticated_context
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.database import AppSpecificAuthToken
from test.fixtures import *


def get_user():
    return model.user.get_user("devtable")


def get_app_specific_token():
    return AppSpecificAuthToken.get()


def get_robot():
    robot, _ = model.user.create_robot("somebot", get_user())
    return robot


def get_token():
    return model.token.create_delegate_token("devtable", "simple", "sometoken")


def get_oauthtoken():
    user = model.user.get_user("devtable")
    return list(model.oauth.list_access_tokens_for_user(user))[0]


def get_signeddata():
    return {"grants": {"a": "b"}, "user_context": {"c": "d"}}


@pytest.mark.parametrize(
    "get_entity,entity_kind",
    [
        (get_user, "user"),
        (get_robot, "robot"),
        (get_token, "token"),
        (get_oauthtoken, "oauthtoken"),
        (get_signeddata, "signed_data"),
        (get_app_specific_token, "appspecifictoken"),
    ],
)
def test_apply_context(get_entity, entity_kind, app):
    assert get_authenticated_context() is None

    entity = get_entity()
    args = {}
    args[entity_kind] = entity

    result = ValidateResult(AuthKind.basic, **args)
    result.apply_to_context()

    expected_user = entity if entity_kind == "user" or entity_kind == "robot" else None
    if entity_kind == "oauthtoken":
        expected_user = entity.authorized_user

    if entity_kind == "appspecifictoken":
        expected_user = entity.user

    expected_token = entity if entity_kind == "token" else None
    expected_oauth = entity if entity_kind == "oauthtoken" else None
    expected_appspecifictoken = entity if entity_kind == "appspecifictoken" else None
    expected_grant = entity if entity_kind == "signed_data" else None

    assert get_authenticated_context().authed_user == expected_user
    assert get_authenticated_context().token == expected_token
    assert get_authenticated_context().oauthtoken == expected_oauth
    assert get_authenticated_context().appspecifictoken == expected_appspecifictoken
    assert get_authenticated_context().signed_data == expected_grant
