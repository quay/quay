"""
Manage organizations, members and OAuth applications.
"""

import logging

from flask import request

import features
from auth.permissions import (
    AdministerOrganizationPermission,
    SuperUserPermission,
    OrganizationMemberPermission,
    UserReadPermission,
)
from data import model
from data.model import config
from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    validate_json_request,
    request_error,
    require_user_admin,
    show_if,
)
from endpoints.exception import InvalidToken, Unauthorized

logger = logging.getLogger(__name__)


def quota_view(orgname: str, quota, quota_limit_types):
    return {
        "orgname": orgname,
        "limit_bytes": quota.limit_bytes if quota else None,
        "quota_limit_types": quota_limit_types,
    }


def quota_limit_view(orgname: str, quota_limit):
    return {
        "percent_of_limit": quota_limit["percent_of_limit"],
        "limit_type": {
            "name": quota_limit["name"],
            "quota_limit_id": quota_limit["id"],
            "quota_type_id": quota_limit["type_id"],
        },
    }


def namespace_size_view(orgname: str, repo):
    return {
        "orgname": orgname,
        "repository_name": repo.name,
        "repository_size": repo.repositorysize.size_bytes,
        "repository_id": repo.id,
    }


@resource("/v1/namespacequota/<namespace>/quota")
@show_if(features.QUOTA_MANAGEMENT)
class OrganizationQuota(ApiResource):

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

    @nickname("getNamespaceQuota")
    def get(self, namespace):
        orgperm = OrganizationMemberPermission(namespace)
        userperm = UserReadPermission(namespace)

        if not orgperm.can() and not userperm.can():
            raise Unauthorized()

        quota = model.namespacequota.get_namespace_quota(namespace)
        quota_limit_types = model.namespacequota.get_namespace_limit_types()
        quota = quota.get() if quota else None

        return quota_view(namespace, quota, quota_limit_types)

    @nickname("createNamespaceQuota")
    @validate_json_request("NewOrgQuota")
    def post(self, namespace):
        """
        Create a new organization quota.
        """
        orgperm = AdministerOrganizationPermission(namespace)
        superperm = SuperUserPermission()

        if not superperm.can():
            if orgperm.can():
                if config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") != 0:
                    raise Unauthorized()
            else:
                raise Unauthorized()

        quota_data = request.get_json()

        quota = model.namespacequota.get_namespace_quota(namespace)

        if quota is not None:
            msg = "quota already exists"
            raise request_error(message=msg)

        try:
            model.namespacequota.create_namespace_quota(
                name=namespace, limit_bytes=quota_data["limit_bytes"]
            )
            return "Created", 201
        except model.DataModelException as ex:
            raise request_error(exception=ex)

    @nickname("changeOrganizationQuota")
    @validate_json_request("NewOrgQuota")
    def put(self, namespace):

        superperm = SuperUserPermission()

        if not superperm.can():
            raise Unauthorized()

        quota_data = request.get_json()

        quota = model.namespacequota.get_namespace_quota(namespace)

        if quota is None:
            msg = "quota does not exist"
            raise request_error(message=msg)

        try:
            model.namespacequota.change_namespace_quota(namespace, quota_data["limit_bytes"])
            return "Updated", 201
        except model.DataModelException as ex:
            raise request_error(exception=ex)

    @nickname("deleteOrganizationQuota")
    def delete(self, namespace):
        superperm = SuperUserPermission()

        if not superperm.can():
            raise Unauthorized()

        quota = model.namespacequota.get_namespace_quota(namespace)

        if quota is None:
            msg = "quota does not exist"
            raise request_error(message=msg)

        try:
            success = model.namespacequota.delete_namespace_quota(namespace)
            if success == 1:
                return "Deleted", 201

            msg = "quota failed to delete"
            raise request_error(message=msg)
        except model.DataModelException as ex:
            raise request_error(exception=ex)


@resource("/v1/namespacequota/<namespace>/quotalimits")
@show_if(features.QUOTA_MANAGEMENT)
class OrganizationQuotaLimits(ApiResource):

    schemas = {
        "NewOrgQuotaLimit": {
            "type": "object",
            "description": "Description of a new organization quota limit threshold",
            "required": ["percent_of_limit", "quota_type_id"],
            "properties": {
                "percent_of_limit": {
                    "type": "integer",
                    "description": "Percentage of quota at which to do something",
                },
                "quota_type_id": {
                    "type": "integer",
                    "description": "Quota type Id",
                },
            },
        },
    }

    @nickname("getOrganizationQuotaLimit")
    def get(self, namespace):
        orgperm = OrganizationMemberPermission(namespace)
        userperm = UserReadPermission(namespace)

        if not orgperm.can() and not userperm.can():
            raise Unauthorized()

        quota_limits = list(model.namespacequota.get_namespace_limits(namespace))

        return {"quota_limits": [quota_limit_view(namespace, limit) for limit in quota_limits]}, 200

    @nickname("createOrganizationQuotaLimit")
    @validate_json_request("NewOrgQuotaLimit")
    def post(self, namespace):
        """
        Create a new organization quota.
        """

        orgperm = AdministerOrganizationPermission(namespace)
        superperm = SuperUserPermission()

        if not superperm.can():
            if orgperm.can():
                if config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") != 0:
                    raise Unauthorized()
            else:
                raise Unauthorized()

        quota_limit_data = request.get_json()
        quota = model.namespacequota.get_namespace_limit(
            namespace, quota_limit_data["quota_type_id"], quota_limit_data["percent_of_limit"]
        )

        if quota is not None:
            msg = "quota limit already exists"
            raise request_error(message=msg)

        reject_quota = model.namespacequota.get_namespace_reject_limit(namespace)
        if reject_quota is not None and model.namespacequota.is_reject_limit_type(
            quota_limit_data["quota_type_id"]
        ):
            msg = "You can only have one Reject type of quota limit"
            raise request_error(message=msg)

        try:
            model.namespacequota.create_namespace_limit(
                orgname=namespace,
                percent_of_limit=quota_limit_data["percent_of_limit"],
                quota_type_id=quota_limit_data["quota_type_id"],
            )
            return "Created", 201
        except model.DataModelException as ex:
            raise request_error(exception=ex)

    @nickname("changeOrganizationQuotaLimit")
    @validate_json_request("NewOrgQuotaLimit")
    def put(self, namespace):

        superperm = SuperUserPermission()

        if not superperm.can():
            raise Unauthorized()

        quota_limit_data = request.get_json()

        try:
            quota_limit_id = quota_limit_data["quota_limit_id"]
        except KeyError:
            msg = "Must supply quota_limit_id for updates"
            raise request_error(message=msg)

        quota = model.namespacequota.get_namespace_limit_from_id(namespace, quota_limit_id)

        if quota is None:
            msg = "quota limit does not exist"
            raise request_error(message=msg)

        try:
            model.namespacequota.change_namespace_quota_limit(
                namespace,
                quota_limit_data["percent_of_limit"],
                quota_limit_data["quota_type_id"],
                quota_limit_data["quota_limit_id"],
            )
            return "Updated", 201
        except model.DataModelException as ex:
            raise request_error(exception=ex)

    @nickname("deleteOrganizationQuotaLimit")
    def delete(self, namespace):

        superperm = SuperUserPermission()

        if not superperm.can():
            raise Unauthorized()

        quota_limit_id = request.args.get("quota_limit_id", None)
        if quota_limit_id is None:
            msg = "Bad request to delete quota limit. Missing quota limit identifier."
            raise request_error(message=msg)

        quota = model.namespacequota.get_namespace_limit_from_id(namespace, quota_limit_id)

        if quota is None:
            msg = "quota does not exist"
            raise request_error(message=msg)

        try:
            success = model.namespacequota.delete_namespace_quota_limit(namespace, quota_limit_id)
            if success == 1:
                return "Deleted", 201

            msg = "quota failed to delete"
            raise request_error(message=msg)
        except model.DataModelException as ex:
            raise request_error(exception=ex)


@resource("/v1/namespacequota/<namespace>/quotareport")
@show_if(features.QUOTA_MANAGEMENT)
class OrganizationQuotaReport(ApiResource):
    @nickname("getOrganizationSizeReporting")
    def get(self, namespace):
        orgperm = OrganizationMemberPermission(namespace)
        userperm = UserReadPermission(namespace)

        if not orgperm.can() and not userperm.can():
            raise Unauthorized()

        return {
            "response": model.namespacequota.get_namespace_repository_sizes_and_cache(namespace)
        }, 200
