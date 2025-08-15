"""
Manages app specific tokens for the current user.
"""

import logging
import math
from datetime import timedelta

from flask import abort, request

import features
from app import app, usermanager
from auth.auth_context import get_authenticated_user
from auth.permissions import SuperUserPermission
from data import model
from endpoints.api import (
    ApiResource,
    NotFound,
    allow_if_global_readonly_superuser,
    allow_if_superuser,
    format_date,
    log_action,
    nickname,
    parse_args,
    path_param,
    query_param,
    require_fresh_login,
    require_user_admin,
    resource,
    show_if,
    validate_json_request,
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
            {
                "token_code": model.appspecifictoken.get_full_token_string(token),
            }
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
            "required": [
                "title",
            ],
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The user-defined title for the token",
                },
            },
        },
    }

    @require_user_admin()
    @nickname("listAppTokens")
    @parse_args()
    @query_param("expiring", "If true, only returns those tokens expiring soon", type=truthy_bool)
    def get(self, parsed_args):
        """
        Lists the app specific tokens accessible to the user.

        - Superusers: Can see all tokens across the application
        - Global Read-Only Superusers: Can see all tokens across the application (but not token secrets)
        - Regular Users: Can only see their own tokens
        """
        user = get_authenticated_user()
        # In API v1, allow_if_superuser() reflects the current request context's superuser status.
        # Use it directly to ensure tests and runtime align.
        is_superuser = bool(allow_if_superuser())
        expiring = parsed_args["expiring"]

        # Determine which tokens to retrieve based on user type
        if is_superuser or allow_if_global_readonly_superuser():
            # Superusers and global readonly superusers can see all tokens
            if expiring:
                expiration = app.config.get("APP_SPECIFIC_TOKEN_EXPIRATION")
                token_expiration = convert_to_timedelta(
                    expiration or _DEFAULT_TOKEN_EXPIRATION_WINDOW
                )
                seconds = math.ceil(token_expiration.total_seconds() * 0.1) or 1
                soon = timedelta(seconds=seconds)
                tokens = model.appspecifictoken.get_all_expiring_tokens(soon)
            else:
                tokens = model.appspecifictoken.list_all_tokens()
        else:
            # Regular users see only their tokens
            if expiring:
                expiration = app.config.get("APP_SPECIFIC_TOKEN_EXPIRATION")
                token_expiration = convert_to_timedelta(
                    expiration or _DEFAULT_TOKEN_EXPIRATION_WINDOW
                )
                seconds = math.ceil(token_expiration.total_seconds() * 0.1) or 1
                soon = timedelta(seconds=seconds)
                tokens = model.appspecifictoken.get_expiring_tokens(user, soon)
            else:
                tokens = model.appspecifictoken.list_tokens(user)

        return {
            "tokens": [token_view(token, include_code=False) for token in tokens],
            "only_expiring": expiring,
        }

    @require_user_admin()
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

    @require_user_admin()
    @require_fresh_login
    @nickname("getAppToken")
    def get(self, token_uuid):
        """
        Returns a specific app token for the user.
        """
        user = get_authenticated_user()
        is_superuser = bool(allow_if_superuser())

        # Superusers (both regular and global readonly) can see any user's app tokens, but must
        # never receive the secret token code unless they are the owner of the token.
        if is_superuser or allow_if_global_readonly_superuser():
            token = model.appspecifictoken.get_token_by_uuid(token_uuid, owner=None)
        else:
            # Regular users can only access their own tokens
            token = model.appspecifictoken.get_token_by_uuid(token_uuid, owner=user)
        if token is None:
            raise NotFound()

        # Include the token_code only if the authenticated user is the owner of the token.
        include_code = user is not None and token.user_id == user.id

        return {
            "token": token_view(token, include_code=include_code),
        }

    @require_user_admin()
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
