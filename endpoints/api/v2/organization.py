import logging

from auth.permissions import (
    UserAdminPermission,
    UserReadPermission,
    AdministerOrganizationPermission,
    CreateRepositoryPermission,
    SuperUserPermission,
)
from endpoints.api import resource, ApiResource, nickname, allow_if_superuser, require_scope
from auth.auth_context import get_authenticated_user
from endpoints.decorators import anon_allowed
from endpoints.exception import InvalidToken
from endpoints.api import query_param, parse_args
from data.database import User
from util.parsing import truthy_bool
from data import model
from auth import scopes
from app import app, avatar, authentication

logger = logging.getLogger(__name__)

API_V2_ORG_PATH = app.config.get("V2_API_PATH", "/v2")


@resource(f"{API_V2_ORG_PATH}/organization/")
class OrganizationResource(ApiResource):
    @require_scope(scopes.READ_USER)
    @nickname("getOrganizationForUser")
    @parse_args()
    @query_param(
        "robot_permissions",
        "Whether to include repostories and teams in which the robots have permission.",
        type=truthy_bool,
        default=False,
    )
    @query_param(
        "page_number",
        "Page number for the response",
        type=int,
        default=1,
    )
    @query_param(
        "per_page",
        "Items per page for the response",
        type=int,
        default=10,
    )
    @query_param(
        "sort_by",
        "Field to sort the response",
        type=str,
        default=User.creation_date,  # By default sort by org creation_date TODO: Build a str to field map for supported fields
    )
    @query_param(
        "sort_type",
        "Sort type - asc/desc",
        type=str,
        default=None,
    )
    @query_param(
        "filter",  # ?search_key=name,search_value=org1
        "Field(s) to filter response",
        type=str,
        default=None,
    )
    @anon_allowed
    def get(self, parsed_args):
        user = get_authenticated_user()
        if user is None or user.organization or not UserReadPermission(user.username).can():
            raise InvalidToken("Requires authentication", payload={"session_required": False})

        username = user.username
        user_response = model.user.get_default_user_response(user, avatar)

        # User perms
        is_admin = UserAdminPermission(username).can()
        user_read = UserReadPermission(username)

        if is_admin:
            user_response.update(model.user.get_admin_user_response(user, authentication))

        org_query = model.organization.get_user_organizations_base_query(username)
        query_obj = model.querybuilder.QueryBuilder(
            query=org_query
        )  # provides a cursor, does not execute the query

        if user_read.can():
            # Retrieve the organizations only if user has read permissions
            public_namespaces = app.config.get("PUBLIC_NAMESPACES", [])

            query_cursor = (
                query_obj.sort(
                    field=parsed_args.get("sort_by"), sort_type=parsed_args.get("sort_type", None)
                )
                .paginate(
                    page_number=parsed_args.get("page_number", 1),
                    items_per_page=parsed_args.get("per_page", 10),
                )
                .execute()
            )

            user_response["organizations"] = model.organization.get_paginated_user_organizations(
                query_cursor,
                public_namespaces,
                is_admin,
                AdministerOrganizationPermission,
                CreateRepositoryPermission,
                allow_if_superuser,
                avatar,
            )

        # Do we check for user_view_perms here?
        user_response["orgs_count"] = query_obj.count()

        # Update response based on feature flags
        user_response.update(model.user.feature_data(user, SuperUserPermission))
        return user_response
