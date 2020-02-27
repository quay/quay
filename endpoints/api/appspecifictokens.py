"""
Manages app specific tokens for the current user.
"""

import logging
import math

from datetime import timedelta
from flask import request

import features

from app import app
from auth.auth_context import get_authenticated_user
from data import model
from endpoints.api import (
    ApiResource,
    nickname,
    resource,
    validate_json_request,
    log_action,
    require_user_admin,
    require_fresh_login,
    path_param,
    NotFound,
    format_date,
    show_if,
    query_param,
    parse_args,
)
from util.parsing import truthy_bool
from util.timedeltastring import convert_to_timedelta


logger = logging.getLogger(__name__)


def token_view(token, include_code=False):
    data = {
        "uuid": token.uuid,
        "title": token.title,
        "last_accessed": format_date(token.last_accessed),
        "created": format_date(token.created),
        "expiration": format_date(token.expiration),
    }

    if include_code:
        data.update(
            {"token_code": model.appspecifictoken.get_full_token_string(token),}
        )

    return data


# The default window to use when looking up tokens that will be expiring.
_DEFAULT_TOKEN_EXPIRATION_WINDOW = "4w"


@resource("/v1/user/apptoken")
@show_if(features.APP_SPECIFIC_TOKENS)
class AppTokens(ApiResource):
    """
    Lists all app specific tokens for a user.
    """

    schemas = {
        "NewToken": {
            "type": "object",
            "required": ["title",],
            "properties": {
                "title": {"type": "string", "description": "The user-defined title for the token",},
            },
        },
    }

    @require_user_admin
    @nickname("listAppTokens")
    @parse_args()
    @query_param("expiring", "If true, only returns those tokens expiring soon", type=truthy_bool)
    def get(self, parsed_args):
        """
        Lists the app specific tokens for the user.
        """
        expiring = parsed_args["expiring"]
        if expiring:
            expiration = app.config.get("APP_SPECIFIC_TOKEN_EXPIRATION")
            token_expiration = convert_to_timedelta(expiration or _DEFAULT_TOKEN_EXPIRATION_WINDOW)
            seconds = math.ceil(token_expiration.total_seconds() * 0.1) or 1
            soon = timedelta(seconds=seconds)
            tokens = model.appspecifictoken.get_expiring_tokens(get_authenticated_user(), soon)
        else:
            tokens = model.appspecifictoken.list_tokens(get_authenticated_user())

        return {
            "tokens": [token_view(token, include_code=False) for token in tokens],
            "only_expiring": expiring,
        }

    @require_user_admin
    @require_fresh_login
    @nickname("createAppToken")
    @validate_json_request("NewToken")
    def post(self):
        """
        Create a new app specific token for user.
        """
        title = request.get_json()["title"]
        token = model.appspecifictoken.create_token(get_authenticated_user(), title)

        log_action(
            "create_app_specific_token",
            get_authenticated_user().username,
            {"app_specific_token_title": token.title, "app_specific_token": token.uuid},
        )

        return {
            "token": token_view(token, include_code=True),
        }


@resource("/v1/user/apptoken/<token_uuid>")
@show_if(features.APP_SPECIFIC_TOKENS)
@path_param("token_uuid", "The uuid of the app specific token")
class AppToken(ApiResource):
    """
    Provides operations on an app specific token.
    """

    @require_user_admin
    @require_fresh_login
    @nickname("getAppToken")
    def get(self, token_uuid):
        """
        Returns a specific app token for the user.
        """
        token = model.appspecifictoken.get_token_by_uuid(token_uuid, owner=get_authenticated_user())
        if token is None:
            raise NotFound()

        return {
            "token": token_view(token, include_code=True),
        }

    @require_user_admin
    @require_fresh_login
    @nickname("revokeAppToken")
    def delete(self, token_uuid):
        """
        Revokes a specific app token for the user.
        """
        token = model.appspecifictoken.revoke_token_by_uuid(
            token_uuid, owner=get_authenticated_user()
        )
        if token is None:
            raise NotFound()

        log_action(
            "revoke_app_specific_token",
            get_authenticated_user().username,
            {"app_specific_token_title": token.title, "app_specific_token": token.uuid},
        )

        return "", 204
