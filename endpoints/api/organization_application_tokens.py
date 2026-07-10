"""
Manage OAuth tokens for an organization's application.
"""

import logging

from flask import request

from auth import scopes
from auth.auth_context import get_authenticated_user, get_validated_oauth_token
from auth.permissions import (
    AdministerOrganizationPermission,
    AdministerRepositoryPermission,
    CreateRepositoryPermission,
    ModifyRepositoryPermission,
    ReadRepositoryPermission,
    SuperUserPermission,
    UserAdminPermission,
    UserReadPermission,
)
from data import model
from data.database import User
from data.model import oauth as oauth_model
from data.model.oauth import (
    DEFAULT_TOKEN_EXPIRATION_SECONDS,
    MAX_TOKEN_DISPLAY_NAME_LENGTH,
    normalize_scope,
    validate_expiration,
    validate_token_display_name,
)
from endpoints.api import (
    ApiResource,
    allow_if_global_readonly_superuser,
    allow_if_superuser_with_full_access,
    log_action,
    nickname,
    page_support,
    parse_args,
    path_param,
    require_scope,
    resource,
    validate_json_request,
)
from endpoints.exception import NotFound, Unauthorized

logger = logging.getLogger(__name__)


MINTABLE_SCOPE_PERMISSION_FACTORIES = {
    scopes.READ_REPO: lambda orgname, user: ReadRepositoryPermission(orgname, ""),
    scopes.WRITE_REPO: lambda orgname, user: ModifyRepositoryPermission(orgname, ""),
    scopes.ADMIN_REPO: lambda orgname, user: AdministerRepositoryPermission(orgname, ""),
    scopes.CREATE_REPO: lambda orgname, user: CreateRepositoryPermission(orgname),
    scopes.READ_USER: lambda orgname, user: UserReadPermission(user.username),
    scopes.ADMIN_USER: lambda orgname, user: UserAdminPermission(user.username),
    scopes.ORG_ADMIN: lambda orgname, user: AdministerOrganizationPermission(orgname),
    scopes.SUPERUSER: lambda orgname, user: SuperUserPermission(),
}


def _permission_for_scope(scope, orgname, user):
    permission_factory = MINTABLE_SCOPE_PERMISSION_FACTORIES.get(scope)
    if permission_factory is None:
        return None

    return permission_factory(orgname, user)


def _can_mint_scope(orgname, normalized_scope, user):
    current_oauth_token = get_validated_oauth_token()
    if current_oauth_token is not None and not scopes.is_subset_string(
        current_oauth_token.scope, normalized_scope
    ):
        return False

    requested_scopes = scopes.scopes_from_scope_string(normalized_scope)
    for scope in requested_scopes:
        permission = _permission_for_scope(scope, orgname, user)
        if permission is None or not permission.can():
            return False

    return True


def _lookup_application_or_raise(orgname, client_id):
    try:
        org = model.organization.get_organization(orgname)
    except model.InvalidOrganizationException:
        raise NotFound()

    application = oauth_model.lookup_application(org, client_id)
    if not application:
        raise NotFound()

    return application


def token_view(token, include_secret=False, secret=None):
    view = {
        "uuid": token.uuid,
        "name": token.display_name,
        "scope": token.scope,
        "expires_at": token.expires_at.isoformat() + "Z" if token.expires_at else None,
        "created": token.created.isoformat() + "Z" if token.created else None,
        "created_by": None,
        "last_accessed": token.last_accessed.isoformat() + "Z" if token.last_accessed else None,
    }

    try:
        if token.authorized_user:
            view["created_by"] = token.authorized_user.username
    except (AttributeError, User.DoesNotExist):
        pass

    if include_secret and secret is not None:
        view["token"] = secret

    return view


@resource("/v1/organization/<orgname>/applications/<client_id>/tokens")
@path_param("orgname", "The name of the organization")
@path_param("client_id", "The OAuth client ID")
class OrganizationApplicationTokens(ApiResource):
    """
    Resource for listing and creating tokens for an organization's OAuth application.
    """

    schemas = {
        "NewToken": {
            "type": "object",
            "description": "Description of a new OAuth API token. Duplicate names are allowed within an application.",
            "required": ["name", "scope"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "User-facing token name. Leading and trailing whitespace is trimmed before storage.",
                    "minLength": 1,
                    "maxLength": MAX_TOKEN_DISPLAY_NAME_LENGTH,
                },
                "scope": {
                    "type": "string",
                    "description": "Space- or comma-separated scope string",
                },
                "expiration": {
                    "type": "number",
                    "description": "Token lifetime in seconds. Must be positive and is capped at the maximum supported lifetime.",
                    "minimum": 1,
                },
            },
        },
        "OAuthApplicationToken": {
            "type": "object",
            "description": "OAuth API token metadata. The bearer token secret is only returned when the token is created.",
            "properties": {
                "uuid": {"type": "string"},
                "name": {
                    "type": ["string", "null"],
                    "description": "User-facing token name. Null indicates a legacy unnamed token.",
                },
                "scope": {"type": "string"},
                "expires_at": {"type": ["string", "null"]},
                "created": {"type": ["string", "null"]},
                "created_by": {"type": ["string", "null"]},
                "last_accessed": {"type": ["string", "null"]},
                "token": {
                    "type": "string",
                    "description": "Bearer token secret, present only in create responses.",
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("listOrganizationApplicationTokens")
    @parse_args()
    @page_support()
    def get(self, orgname, client_id, parsed_args, page_token):
        """
        List all tokens for the specified application.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not (
            permission.can()
            or allow_if_global_readonly_superuser()
            or allow_if_superuser_with_full_access()
        ):
            raise Unauthorized()

        application = _lookup_application_or_raise(orgname, client_id)

        tokens, next_page_token = oauth_model.list_application_tokens(
            application, page_token=page_token
        )

        return {"tokens": [token_view(token) for token in tokens]}, next_page_token

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrganizationApplicationToken")
    @validate_json_request("NewToken")
    def post(self, orgname, client_id):
        """
        Create a new token for the specified application.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not (permission.can() or allow_if_superuser_with_full_access()):
            raise Unauthorized()

        application = _lookup_application_or_raise(orgname, client_id)

        body = request.get_json()
        try:
            display_name = validate_token_display_name(body.get("name"))
        except ValueError as e:
            return {"message": str(e)}, 400

        scope_string = body["scope"]
        normalized_scope = normalize_scope(scope_string)
        if not scopes.validate_scope_string(normalized_scope):
            return {"message": "Invalid scope: %s" % scope_string}, 400

        user = get_authenticated_user()
        if user is None:
            raise Unauthorized()

        if not _can_mint_scope(orgname, normalized_scope, user):
            raise Unauthorized()

        try:
            expiration = validate_expiration(
                body.get("expiration", DEFAULT_TOKEN_EXPIRATION_SECONDS)
            )
        except ValueError as e:
            return {"message": str(e)}, 400

        try:
            token_record, access_token = oauth_model.create_oauth_api_token_under_limit(
                application=application,
                user_obj=user,
                scope=normalized_scope,
                expiration_seconds=expiration,
                display_name=display_name,
            )
        except oauth_model.TokenLimitExceeded as e:
            return {
                "message": "Token limit reached: maximum %d non-expired tokens per application"
                % e.max_active_tokens
            }, 400

        log_action(
            "create_oauth_api_token",
            orgname,
            metadata={
                "oauth_token_uuid": token_record.uuid,
                "scope": normalized_scope,
                "token_display_name": display_name,
                "application_name": application.name,
                "auth_method": "OAuth",
                "client_id": application.client_id,
            },
        )

        return token_view(token_record, include_secret=True, secret=access_token)


@resource("/v1/organization/<orgname>/applications/<client_id>/tokens/<token_uuid>")
@path_param("orgname", "The name of the organization")
@path_param("client_id", "The OAuth client ID")
@path_param("token_uuid", "The UUID of the token")
class OrganizationApplicationToken(ApiResource):
    """
    Resource for managing a single token of an organization's OAuth application.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrganizationApplicationToken")
    def delete(self, orgname, client_id, token_uuid):
        """
        Revoke a specific token for the specified application.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not (permission.can() or allow_if_superuser_with_full_access()):
            raise Unauthorized()

        application = _lookup_application_or_raise(orgname, client_id)

        deleted = oauth_model.delete_application_token(application, token_uuid)
        if not deleted:
            raise NotFound()

        log_action(
            "revoke_oauth_api_token",
            orgname,
            metadata={
                "oauth_token_uuid": token_uuid,
                "application_name": application.name,
                "client_id": application.client_id,
            },
        )

        return "", 204
