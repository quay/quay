"""
Manage OAuth tokens for an organization's application.
"""

import logging

from flask import request

from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.permissions import AdministerOrganizationPermission
from data import model
from data.database import User
from data.model import oauth as oauth_model
from data.model.oauth import (
    MAX_TOKENS_PER_APPLICATION,
    normalize_scope,
    validate_expiration,
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


def token_view(token, include_secret=False, secret=None):
    view = {
        "uuid": token.uuid,
        "scope": token.scope,
        "expires_at": token.expires_at.isoformat() + "Z" if token.expires_at else None,
        "created": token.created.isoformat() + "Z" if token.created else None,
        "created_by": None,
        "last_accessed": token.last_accessed.isoformat() + "Z" if token.last_accessed else None,
    }

    try:
        if token.created_by:
            view["created_by"] = token.created_by.username
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
            "description": "Description of a new OAuth token.",
            "required": ["scope"],
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "Space- or comma-separated scope string",
                },
                "expiration": {
                    "type": "number",
                    "description": "Token lifetime in seconds (default 10 years)",
                    "minimum": 1,
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

        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        application = oauth_model.lookup_application(org, client_id)
        if not application:
            raise NotFound()

        tokens, next_page_token = oauth_model.list_application_tokens(
            application, page_token=page_token
        )

        return {"tokens": [token_view(t) for t in tokens]}, next_page_token

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

        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        application = oauth_model.lookup_application(org, client_id)
        if not application:
            raise NotFound()

        body = request.get_json()
        scope_string = body["scope"]

        normalized_scope = normalize_scope(scope_string)
        if not scopes.validate_scope_string(normalized_scope):
            return {"message": "Invalid scope: %s" % scope_string}, 400

        try:
            expiration = validate_expiration(body.get("expiration", 315576000))
        except ValueError as e:
            return {"message": str(e)}, 400

        active_count = oauth_model.count_active_tokens(application)
        if active_count >= MAX_TOKENS_PER_APPLICATION:
            return {
                "message": "Token limit reached: maximum %d non-expired tokens per application"
                % MAX_TOKENS_PER_APPLICATION
            }, 400

        user = get_authenticated_user()

        token_record, access_token = oauth_model.create_oauth_api_token(
            application=application,
            user=user,
            scope=normalized_scope,
            expiration_seconds=expiration,
        )

        log_action(
            "create_oauth_api_token",
            orgname,
            metadata={
                "oauth_token_uuid": token_record.uuid,
                "scope": normalized_scope,
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

        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        application = oauth_model.lookup_application(org, client_id)
        if not application:
            raise NotFound()

        deleted = oauth_model.delete_application_token(application, token_uuid)
        if not deleted:
            raise NotFound()

        log_action(
            "revoke_oauth_api_token",
            orgname,
            metadata={
                "oauth_token_uuid": token_uuid,
                "client_id": application.client_id,
            },
        )

        return "", 204
