"""
Manages app specific tokens for the current user.
"""

import datetime
import logging
import math
from datetime import timedelta

import pytz
from flask import request, session
from jsonschema import ValidationError, validate

import features
from app import app, authentication
from auth import scopes
from auth.auth_context import (
    get_authenticated_user,
    get_sso_token,
    get_validated_oauth_token,
)
from auth.bootstrap import BootstrapAuthError, validate_bootstrap_auth
from auth.permissions import UserAdminPermission
from data import model
from endpoints.api import (
    FRESH_LOGIN_TIMEOUT,
    ApiResource,
    NotFound,
    add_method_metadata,
    format_date,
    log_action,
    nickname,
    parse_args,
    path_param,
    query_param,
    require_fresh_login,
    require_scope,
    require_user_admin,
    resource,
    show_if,
)
from endpoints.exception import FreshLoginRequired, InvalidRequest, Unauthorized
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


def _has_fresh_login(user):
    """Check whether the current request has fresh login credentials (OAuth token, SSO, or recent session)."""
    if get_validated_oauth_token() or get_sso_token():
        return True

    last_login = session.get("login_time", datetime.datetime.min)
    valid_span = datetime.datetime.now() - FRESH_LOGIN_TIMEOUT

    if (
        last_login.replace(tzinfo=pytz.UTC) >= valid_span.replace(tzinfo=pytz.UTC)
        or not authentication.supports_fresh_login
        or not authentication.has_password_set(user.username)
    ):
        return True

    return False


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
        Lists the app specific tokens for the current user.

        All users (including superusers) see only their own tokens.
        For system-wide token auditing, superusers should use /v1/superuser/apptokens.
        """
        user = get_authenticated_user()
        expiring = parsed_args["expiring"]

        if expiring:
            expiration = app.config.get("APP_SPECIFIC_TOKEN_EXPIRATION")
            token_expiration = convert_to_timedelta(expiration or _DEFAULT_TOKEN_EXPIRATION_WINDOW)
            seconds = math.ceil(token_expiration.total_seconds() * 0.1) or 1
            soon = timedelta(seconds=seconds)
            tokens = model.appspecifictoken.get_expiring_tokens(user, soon)
        else:
            tokens = model.appspecifictoken.list_tokens(user)

        return {
            "tokens": [token_view(token, include_code=False) for token in tokens],
            "only_expiring": expiring,
        }

    @require_scope(scopes.ADMIN_USER)
    @add_method_metadata("requires_fresh_login", True)
    @add_method_metadata("request_schema", "NewToken")
    @nickname("createAppToken")
    def post(self):
        """
        Create a new app specific token for user.

        Supports two authentication methods:
        1. Standard session/OAuth auth with fresh login (existing behavior)
        2. Bootstrap auth (Basic Auth) when FEATURE_PROGRAMMATIC_BOOTSTRAP is enabled
        """
        user = get_authenticated_user()
        if user:
            if user.robot:
                raise Unauthorized()
            if not UserAdminPermission(user.username).can():
                raise Unauthorized()
            if not _has_fresh_login(user):
                raise FreshLoginRequired()
        elif features.PROGRAMMATIC_BOOTSTRAP:
            try:
                auth_result = validate_bootstrap_auth()
                user = auth_result.user
            except BootstrapAuthError:
                raise Unauthorized()
        else:
            raise Unauthorized()

        json_data = request.get_json()
        if json_data is None:
            raise InvalidRequest("Missing JSON body")
        try:
            validate(json_data, self.schemas["NewToken"])
        except ValidationError as ex:
            raise InvalidRequest(str(ex))

        title = json_data["title"]
        token = model.appspecifictoken.create_token(user, title)

        log_action(
            "create_app_specific_token",
            user.username,
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

        Users can only access their own tokens.
        """
        user = get_authenticated_user()
        token = model.appspecifictoken.get_token_by_uuid(token_uuid, owner=user)

        if token is None:
            raise NotFound()

        return {
            "token": token_view(token, include_code=True),
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
