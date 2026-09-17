"""Manage expiring Management API tokens owned by robot accounts."""

from flask import request

import features
from app import app, instance_keys
from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.decorators import require_session_login
from auth.permissions import AdministerOrganizationPermission
from data.model import api_token as api_token_model
from data.model.api_token import (
    API_TOKEN_DEFAULT_EXPIRATION_SECONDS,
    MAX_API_TOKEN_DISPLAY_NAME_LENGTH,
    normalize_scope,
    validate_api_scope_string,
    validate_expiration,
    validate_token_display_name,
)
from data.model.user import lookup_robot
from endpoints.api import (
    ApiResource,
    allow_if_superuser_with_full_access,
    log_action,
    path_param,
    require_fresh_login,
    require_scope,
    require_user_admin,
    resource,
    validate_json_request,
)
from endpoints.api.organization_application_tokens import _can_mint_scope
from endpoints.exception import NotFound, Unauthorized
from util.names import format_robot_username

NEW_ROBOT_TOKEN_SCHEMA = {
    "type": "object",
    "required": ["name", "scope"],
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": MAX_API_TOKEN_DISPLAY_NAME_LENGTH},
        "scope": {"type": "string"},
        "expiration": {"type": "number", "minimum": 1},
    },
}


def _token_view(token, secret=None):
    result = {
        "uuid": token.uuid,
        "name": token.display_name,
        "scope": token.scope,
        "expires_at": token.expires_at.isoformat() + "Z",
        "created": token.created.isoformat() + "Z" if token.created else None,
        "created_by": token.creator.username if token.creator else None,
        "last_accessed": token.last_accessed.isoformat() + "Z" if token.last_accessed else None,
    }
    if secret is not None:
        result["token"] = secret
    return result


def _create_token(robot, namespace):
    body = request.get_json()
    try:
        name = validate_token_display_name(body["name"])
        expiration = validate_expiration(
            body.get("expiration", API_TOKEN_DEFAULT_EXPIRATION_SECONDS)
        )
    except ValueError as error:
        return {"message": str(error)}, 400

    scope = normalize_scope(body["scope"])
    if not validate_api_scope_string(scope):
        return {"message": "Invalid scope: %s" % body["scope"]}, 400
    if scopes.SUPERUSER in scopes.scopes_from_scope_string(scope) and not features.SUPER_USERS:
        return {"message": "super:user scope is disabled"}, 400

    creator = get_authenticated_user()
    if creator is None or not _can_mint_scope(namespace, scope, creator):
        raise Unauthorized()

    try:
        token = api_token_model.create_token_under_limit(robot, creator, scope, expiration, name)
        secret = api_token_model.mint_jwt(token, instance_keys, app.config["SERVER_HOSTNAME"])
    except api_token_model.TokenLimitExceeded as error:
        return {
            "message": "Token limit reached: maximum %d non-expired tokens per robot"
            % error.max_active_tokens
        }, 400

    log_action(
        "create_robot_api_token",
        namespace,
        {
            "robot": robot.username,
            "api_token_uuid": token.uuid,
            "scope": scope,
            "token_display_name": name,
            "expiration": expiration,
        },
    )
    return _token_view(token, secret)


def _delete_token(robot, namespace, token_uuid):
    if not api_token_model.revoke_token(robot, token_uuid):
        raise NotFound()
    log_action(
        "revoke_robot_api_token",
        namespace,
        {"robot": robot.username, "api_token_uuid": token_uuid},
    )
    return "", 204


@resource("/v1/user/robots/<robot_shortname>/tokens")
@path_param("robot_shortname", "The short robot name")
class UserRobotTokens(ApiResource):
    schemas = {"NewRobotToken": NEW_ROBOT_TOKEN_SCHEMA}

    @require_session_login
    @require_fresh_login
    @require_user_admin(disallow_for_restricted_users=True)
    def get(self, robot_shortname):
        parent = get_authenticated_user()
        robot = lookup_robot(format_robot_username(parent.username, robot_shortname))
        return {"tokens": [_token_view(token) for token in api_token_model.list_tokens(robot)]}

    @require_session_login
    @require_fresh_login
    @require_user_admin(disallow_for_restricted_users=True)
    @validate_json_request("NewRobotToken")
    def post(self, robot_shortname):
        parent = get_authenticated_user()
        robot = lookup_robot(format_robot_username(parent.username, robot_shortname))
        return _create_token(robot, parent.username)


@resource("/v1/user/robots/<robot_shortname>/tokens/<token_uuid>")
class UserRobotToken(ApiResource):
    @require_session_login
    @require_fresh_login
    @require_user_admin(disallow_for_restricted_users=True)
    def delete(self, robot_shortname, token_uuid):
        parent = get_authenticated_user()
        robot = lookup_robot(format_robot_username(parent.username, robot_shortname))
        return _delete_token(robot, parent.username, token_uuid)


def _organization_robot(orgname, robot_shortname):
    if not (
        AdministerOrganizationPermission(orgname).can() or allow_if_superuser_with_full_access()
    ):
        raise Unauthorized()
    return lookup_robot(format_robot_username(orgname, robot_shortname))


@resource("/v1/organization/<orgname>/robots/<robot_shortname>/tokens")
class OrganizationRobotTokens(ApiResource):
    schemas = {"NewRobotToken": NEW_ROBOT_TOKEN_SCHEMA}

    @require_session_login
    @require_fresh_login
    @require_scope(scopes.ORG_ADMIN)
    def get(self, orgname, robot_shortname):
        robot = _organization_robot(orgname, robot_shortname)
        return {"tokens": [_token_view(token) for token in api_token_model.list_tokens(robot)]}

    @require_session_login
    @require_fresh_login
    @require_scope(scopes.ORG_ADMIN)
    @validate_json_request("NewRobotToken")
    def post(self, orgname, robot_shortname):
        return _create_token(_organization_robot(orgname, robot_shortname), orgname)


@resource("/v1/organization/<orgname>/robots/<robot_shortname>/tokens/<token_uuid>")
class OrganizationRobotToken(ApiResource):
    @require_session_login
    @require_fresh_login
    @require_scope(scopes.ORG_ADMIN)
    def delete(self, orgname, robot_shortname, token_uuid):
        return _delete_token(_organization_robot(orgname, robot_shortname), orgname, token_uuid)
