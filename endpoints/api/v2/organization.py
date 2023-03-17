import logging

from auth.permissions import (
    UserAdminPermission,
    UserReadPermission,
    AdministerOrganizationPermission,
    CreateRepositoryPermission,
)
from endpoints.api import resource, ApiResource, nickname, allow_if_superuser, require_scope
from data.database import User as UserTable
from auth.auth_context import get_authenticated_user
from endpoints.decorators import anon_allowed
from endpoints.exception import InvalidToken
from endpoints.api import query_param, parse_args, page_support
from endpoints.api.v2 import API_V2_ORG_PATH
from util.parsing import truthy_bool
from data import model
from auth import scopes
from app import app, avatar

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
    @page_support()
    def get(self, page_token, parsed_args):
        user = get_authenticated_user()
        username = user.username
        if user is None or user.organization or not UserReadPermission(username).can():
            raise InvalidToken("Requires authentication", payload={"session_required": False})

        org_query = model.organization.get_user_organizations_base_query(
            username,
            search_key=parsed_args.get("search_key", None),
            search_value=parsed_args.get("search_value", None),
        )

        public_namespaces = app.config.get("PUBLIC_NAMESPACES", [])
        descending_order = False if parsed_args.get("sort_type", "") == "asc" else True

        orgs, next_page_token = model.modelutil.paginate(
            org_query,
            UserTable,
            descending=descending_order,
            page_token=page_token,
            limit=parsed_args.get("per_page", 10),
            sort_field_name=parsed_args.get("search_key", None),
        )

        response = {
            "organizations": model.organization.get_paginated_user_organizations(
                orgs,
                public_namespaces,
                UserAdminPermission(username).can(),
                AdministerOrganizationPermission,
                CreateRepositoryPermission,
                allow_if_superuser,
                avatar,
            ),
        }

        return response, next_page_token
