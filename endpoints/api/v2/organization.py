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
from endpoints.api.v2 import API_V2_ORG_PATH
from data.database import User
from util.parsing import truthy_bool
from data import model
from auth import scopes
from app import app, avatar, authentication

logger = logging.getLogger(__name__)


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
    @query_param("sort_by", "Field to sort the response", type=str, default="creation_date")
    @query_param(
        "sort_type",
        "Sort type - asc/desc",
        type=str,
        default=None,
    )
    @query_param(
        "search_key",
        "Field key to filter response",
        type=str,
        default=None,
    )
    @query_param(
        "search_value",
        "Field value to filter response",
        type=str,
        default=None,
    )
    @anon_allowed
    def get(self, parsed_args):
        user = get_authenticated_user()
        username = user.username
        if user is None or user.organization or not UserReadPermission(username).can():
            raise InvalidToken("Requires authentication", payload={"session_required": False})

        org_query = model.organization.get_user_organizations_base_query(
            username,
            search_key=parsed_args.get("search_key", None),
            search_value=parsed_args.get("search_value", None),
        )
        query_obj = model.querybuilder.QueryBuilder(
            query=org_query
        )  # provides a cursor, does not execute the query

        # Retrieve the organizations only if user has read permissions
        public_namespaces = app.config.get("PUBLIC_NAMESPACES", [])
        sort_by = model.user.UserFieldMapping[parsed_args.get("sort_by")].value
        query_cursor = (
            query_obj.sort(field=sort_by, sort_type=parsed_args.get("sort_type", None))
            .paginate(
                page_number=parsed_args.get("page_number", 1),
                items_per_page=parsed_args.get("per_page", 10),
            )
            .execute()
        )

        response = {
            "organizations": model.organization.get_paginated_user_organizations(
                query_cursor,
                public_namespaces,
                UserAdminPermission(username).can(),
                AdministerOrganizationPermission,
                CreateRepositoryPermission,
                allow_if_superuser,
                avatar,
            ),
            "count": query_obj.count(),
        }

        return response
