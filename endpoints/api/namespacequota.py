import logging

from flask import request

import features
from auth.permissions import (
    AdministerOrganizationPermission,
    SuperUserPermission,
    OrganizationMemberPermission,
    UserReadPermission,
)
from auth.auth_context import get_authenticated_user
from data import model
from data.model import config
from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    validate_json_request,
    request_error,
    require_user_admin,
    require_scope,
    show_if,
    log_action,
)
from endpoints.exception import InvalidToken, Unauthorized, NotFound
from auth import scopes


logger = logging.getLogger(__name__)


def quota_view(quota, default_config=False):
    quota_limits = []

    if quota:
        quota_limits = list(model.namespacequota.get_namespace_quota_limit_list(quota))
    else:
        # If no quota is defined for the org, return systems default quota if set
        if config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") != 0:
            quota = model.namespacequota.get_system_default_quota()
            default_config = True

    return {
        "id": quota.id,
        "limit_bytes": quota.limit_bytes,
        "default_config": default_config,
        "limits": [limit_view(limit) for limit in quota_limits],
        "default_config_exists": True
        if config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") != 0
        else False,
    }


def limit_view(limit):
    return {
        "id": limit.id,
        "type": limit.quota_type.name,
        "limit_percent": limit.percent_of_limit,
    }


def get_quota(namespace_name, quota_id):
    quota = model.namespacequota.get_namespace_quota(namespace_name, quota_id)
    if quota is None:
        raise NotFound()
    return quota


@resource("/v1/organization/<orgname>/quota")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class OrganizationQuotaList(ApiResource):
    schemas = {
        "NewOrgQuota": {
            "type": "object",
            "description": "Description of a new organization quota",
            "required": ["limit_bytes"],
            "properties": {
                "limit_bytes": {
                    "type": "integer",
                    "description": "Number of bytes the organization is allowed",
                },
            },
        },
    }

    @nickname("listOrganizationQuota")
    def get(self, orgname):
        orgperm = OrganizationMemberPermission(orgname)
        if not orgperm.can() and not SuperUserPermission().can():
            raise Unauthorized()

        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        default_config = False
        quotas = model.namespacequota.get_namespace_quota_list(orgname)

        # If no quota is defined for the org, return systems default quota
        if not quotas and config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") != 0:
            quotas = [model.namespacequota.get_system_default_quota(orgname)]
            default_config = True

        return [quota_view(quota, default_config) for quota in quotas]

    @nickname("createOrganizationQuota")
    @validate_json_request("NewOrgQuota")
    @require_scope(scopes.SUPERUSER)
    def post(self, orgname):
        """
        Create a new organization quota.
        """
        if not SuperUserPermission().can():
            raise Unauthorized()

        quota_data = request.get_json()
        limit_bytes = quota_data["limit_bytes"]

        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        # Currently only supporting one quota definition per namespace
        quotas = model.namespacequota.get_namespace_quota_list(orgname)
        if quotas:
            raise request_error(message="Organization quota for '%s' already exists" % orgname)

        try:
            model.namespacequota.create_namespace_quota(org, limit_bytes)
            return "Created", 201
        except model.DataModelException as ex:
            raise request_error(exception=ex)


@resource("/v1/organization/<orgname>/quota/<quota_id>")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class OrganizationQuota(ApiResource):
    schemas = {
        "UpdateOrgQuota": {
            "type": "object",
            "description": "Description of a new organization quota",
            "properties": {
                "limit_bytes": {
                    "type": "integer",
                    "description": "Number of bytes the organization is allowed",
                },
            },
        },
    }

    @nickname("getOrganizationQuota")
    def get(self, orgname, quota_id):
        orgperm = OrganizationMemberPermission(orgname)
        if not orgperm.can() and not SuperUserPermission().can():
            raise Unauthorized()

        quota = get_quota(orgname, quota_id)

        return quota_view(quota)

    @nickname("changeOrganizationQuota")
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("UpdateOrgQuota")
    def put(self, orgname, quota_id):
        if not SuperUserPermission().can():
            raise Unauthorized()

        quota_data = request.get_json()
        quota = get_quota(orgname, quota_id)

        try:
            if "limit_bytes" in quota_data:
                limit_bytes = quota_data["limit_bytes"]
                model.namespacequota.update_namespace_quota_size(quota, limit_bytes)
        except model.DataModelException as ex:
            raise request_error(exception=ex)

        return quota_view(quota)

    @nickname("deleteOrganizationQuota")
    @require_scope(scopes.SUPERUSER)
    def delete(self, orgname, quota_id):
        if not SuperUserPermission().can():
            raise Unauthorized()

        quota = get_quota(orgname, quota_id)

        # Exceptions by`delete_instance` are unexpected and raised
        model.namespacequota.delete_namespace_quota(quota)

        return "", 204


@resource("/v1/organization/<orgname>/quota/<quota_id>/limit")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class OrganizationQuotaLimitList(ApiResource):
    schemas = {
        "NewOrgQuotaLimit": {
            "type": "object",
            "description": "Description of a new organization quota limit",
            "required": ["type", "threshold_percent"],
            "properties": {
                "type": {
                    "type": "string",
                    "description": 'Type of quota limit: "Warning" or "Reject"',
                },
                "threshold_percent": {
                    "type": "integer",
                    "description": "Quota threshold, in percent of quota",
                },
            },
        },
    }

    @nickname("listOrganizationQuotaLimit")
    def get(self, orgname, quota_id):
        orgperm = OrganizationMemberPermission(orgname)
        if not orgperm.can():
            raise Unauthorized()

        quota = get_quota(orgname, quota_id)
        return [
            limit_view(limit)
            for limit in model.namespacequota.get_namespace_quota_limit_list(quota)
        ]

    @nickname("createOrganizationQuotaLimit")
    @validate_json_request("NewOrgQuotaLimit")
    @require_scope(scopes.SUPERUSER)
    def post(self, orgname, quota_id):
        if not SuperUserPermission().can():
            raise Unauthorized()

        quota_limit_data = request.get_json()
        quota_type = quota_limit_data["type"]
        quota_limit_threshold = quota_limit_data["threshold_percent"]

        quota = get_quota(orgname, quota_id)

        quota_limit = model.namespacequota.get_namespace_quota_limit_list(
            quota,
            quota_type=quota_type,
            percent_of_limit=quota_limit_threshold,
        )

        if quota_limit:
            msg = "Quota limit already exists"
            raise request_error(message=msg)

        if quota_limit_data["type"].lower() == "reject" and quota_limit:
            raise request_error(message="Only one quota limit of type 'Reject' allowed.")

        try:
            model.namespacequota.create_namespace_quota_limit(
                quota,
                quota_type,
                quota_limit_threshold,
            )
            return "Created", 201
        except model.DataModelException as ex:
            raise request_error(exception=ex)


@resource("/v1/organization/<orgname>/quota/<quota_id>/limit/<limit_id>")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class OrganizationQuotaLimit(ApiResource):
    schemas = {
        "UpdateOrgQuotaLimit": {
            "type": "object",
            "description": "Description of changing organization quota limit",
            "properties": {
                "type": {
                    "type": "string",
                    "description": 'Type of quota limit: "Warning" or "Reject"',
                },
                "threshold_percent": {
                    "type": "integer",
                    "description": "Quota threshold, in percent of quota",
                },
            },
        },
    }

    @nickname("getOrganizationQuotaLimit")
    def get(self, orgname, quota_id, limit_id):
        orgperm = OrganizationMemberPermission(orgname)
        if not orgperm.can():
            raise Unauthorized()

        quota = get_quota(orgname, quota_id)
        quota_limit = model.namespacequota.get_namespace_quota_limit(quota, limit_id)
        if quota_limit is None:
            raise NotFound()

        return limit_view(quota_limit)

    @nickname("changeOrganizationQuotaLimit")
    @validate_json_request("UpdateOrgQuotaLimit")
    @require_scope(scopes.SUPERUSER)
    def put(self, orgname, quota_id, limit_id):
        if not SuperUserPermission().can():
            raise Unauthorized()

        quota_limit_data = request.get_json()

        quota = get_quota(orgname, quota_id)
        quota_limit = model.namespacequota.get_namespace_quota_limit(quota, limit_id)
        if quota_limit is None:
            raise NotFound()

        if "type" in quota_limit_data:
            new_type = quota_limit_data["type"]
            model.namespacequota.update_namespace_quota_limit_type(quota_limit, new_type)
        if "threshold_percent" in quota_limit_data:
            new_threshold = quota_limit_data["threshold_percent"]
            model.namespacequota.update_namespace_quota_limit_threshold(quota_limit, new_threshold)

        return quota_view(quota)

    @nickname("deleteOrganizationQuotaLimit")
    @require_scope(scopes.SUPERUSER)
    def delete(self, orgname, quota_id, limit_id):
        if not SuperUserPermission().can():
            raise Unauthorized()

        quota = get_quota(orgname, quota_id)
        quota_limit = model.namespacequota.get_namespace_quota_limit(quota, limit_id)
        if quota_limit is None:
            raise NotFound()

        try:
            # Exceptions by`delete_instance` are unexpected and raised
            model.namespacequota.delete_namespace_quota_limit(quota_limit)
            return "", 204
        except model.DataModelException as ex:
            raise request_error(exception=ex)


@resource("/v1/user/quota")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class UserQuotaList(ApiResource):
    @require_user_admin()
    @nickname("listUserQuota")
    def get(self):
        parent = get_authenticated_user()
        user_quotas = model.namespacequota.get_namespace_quota_list(parent.username)

        return [quota_view(quota) for quota in user_quotas]


@resource("/v1/user/quota/<quota_id>")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class UserQuota(ApiResource):
    @require_user_admin()
    @nickname("getUserQuota")
    def get(self, quota_id):
        parent = get_authenticated_user()
        quota = get_quota(parent.username, quota_id)

        return quota_view(quota)


@resource("/v1/user/quota/<quota_id>/limit")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class UserQuotaLimitList(ApiResource):
    @require_user_admin()
    @nickname("listUserQuotaLimit")
    def get(self, quota_id):
        parent = get_authenticated_user()
        quota = get_quota(parent.username, quota_id)

        return [
            limit_view(limit)
            for limit in model.namespacequota.get_namespace_quota_limit_list(quota)
        ]


@resource("/v1/user/quota/<quota_id>/limit/<limit_id>")
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT)
class UserQuotaLimit(ApiResource):
    @require_user_admin()
    @nickname("getUserQuotaLimit")
    def get(self, quota_id, limit_id):
        parent = get_authenticated_user()
        quota = get_quota(parent.username, quota_id)
        quota_limit = model.namespacequota.get_namespace_quota_limit(quota, limit_id)
        if quota_limit is None:
            raise NotFound()

        return quota_view(quota)
