import logging

from flask import request
from auth.auth_context import get_authenticated_user
from data.model.autoprune import AutoPruneMethod, valid_value

import features
from auth.permissions import AdministerOrganizationPermission
from data import model
from endpoints.api import (
    ApiResource,
    allow_if_superuser,
    path_param,
    request_error,
    resource,
    show_if,
    validate_json_request,
    require_user_admin,
)
from endpoints.exception import NotFound, Unauthorized

logger = logging.getLogger(__name__)


@resource("/v1/organization/<orgname>/autoprunepolicy/")
@path_param("orgname", "The name of the organization")
@show_if(features.AUTO_PRUNE)
class OrgAutoPrunePolicies(ApiResource):
    """"""

    schemas = {
        "AutoPrunePolicyConfig": {
            "type": "object",
            "description": "",
            "required": ["method"],
            "properties": {
                "method": {
                    "type": "string",
                    "description": "",
                },
                "value": {
                    "type": ["integer", "string"],
                    "description": "",
                },
            },
        },
    }

    def get(self, orgname):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        # TODO: We can use org here to get the policies by Id instead of name
        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        policies = model.autoprune.get_namespace_autoprune_policies_by_orgname(orgname)

        # TODO: should this be paginated? Probably shouldn't allow 50+ policies anyway
        return {"policies": [policy.get_view() for policy in policies]}

    @validate_json_request("AutoPrunePolicyConfig")
    def post(self, orgname):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        # TODO: We can use org here to get the policies by Id instead of name
        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)

        try:
            method = AutoPruneMethod(method)
        except ValueError:
            request_error(message="Invalid method")

        if not valid_value(method, value):
            request_error(message="Invalid type given for parameter value")

        policy_config = {
            "method": method.value,
            "value": value,
        }
        policy = model.autoprune.create_namespace_autoprune_policy(
            orgname, policy_config, create_task=True
        )
        return {"uuid": policy.uuid}, 201


@resource("/v1/organization/<orgname>/autoprunepolicy/<policy_uuid>")
@path_param("orgname", "The name of the organization")
@path_param("policy_uuid", "The unique ID of the policy")
@show_if(features.AUTO_PRUNE)
class OrgAutoPrunePolicy(ApiResource):
    """"""

    schemas = {
        "AutoPrunePolicyConfig": {
            "type": "object",
            "description": "",
            "required": ["method"],
            "properties": {
                "method": {
                    "type": "string",
                    "description": "",
                },
                "value": {
                    "type": ["integer", "string"],
                    "description": "",
                },
            },
        },
    }

    def get(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        # TODO: We can use org here to get the policies by Id instead of name
        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        policy = model.autoprune.get_namespace_autoprune_policy(orgname, policy_uuid)
        if policy is None:
            raise NotFound()

        return policy.get_view()

    @validate_json_request("AutoPrunePolicyConfig")
    def put(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        # TODO: We can use org here to get the policies by Id instead of name
        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        policy = model.autoprune.get_namespace_autoprune_policy(orgname, policy_uuid)
        if policy is None:
            raise NotFound()

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)

        try:
            method = AutoPruneMethod(method)
        except ValueError:
            request_error(message="Invalid method")

        if not valid_value(method, value):
            request_error(message="Invalid type given for parameter value")

        policy_config = {
            "method": method.value,
            "value": value,
        }
        policy = model.autoprune.update_namespace_autoprune_policy(
            orgname, policy_uuid, policy_config
        )
        if policy is None:
            raise NotFound()
        return policy_uuid, 204

    def delete(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        # TODO: We can use org here to get the policies by Id instead of name
        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        policy = model.autoprune.delete_namespace_autoprune_policy(orgname, policy_uuid)
        if policy is None:
            raise NotFound()

        return policy_uuid, 200


@resource("/v1/user/autoprunepolicy/")
@show_if(features.AUTO_PRUNE)
class UserAutoPrunePolicies(ApiResource):
    """"""

    schemas = {
        "AutoPrunePolicyConfig": {
            "type": "object",
            "description": "",
            "required": ["method"],
            "properties": {
                "method": {
                    "type": "string",
                    "description": "",
                },
                "value": {
                    "type": ["integer", "string"],
                    "description": "",
                },
            },
        },
    }

    @require_user_admin()
    def get(self):
        user = get_authenticated_user()

        policies = model.autoprune.get_namespace_autoprune_policies_by_orgname(user.username)

        # TODO: should this be paginated? Probably shouldn't allow 50+ policies anyway
        return {"policies": [policy.get_view() for policy in policies]}

    @require_user_admin()
    @validate_json_request("AutoPrunePolicyConfig")
    def post(self):
        user = get_authenticated_user()

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)
        try:
            method = AutoPruneMethod(method)
        except ValueError:
            request_error(message="Invalid method")

        if not valid_value(method, value):
            request_error(message="Invalid type given for parameter value")

        policy_config = {
            "method": method.value,
            "value": value,
        }
        policy = model.autoprune.create_namespace_autoprune_policy(
            user.username, policy_config, create_task=True
        )
        return {"uuid": policy.uuid}, 201


@resource("/v1/user/autoprunepolicy/<policy_uuid>")
@path_param("policy_uuid", "The unique ID of the policy")
@show_if(features.AUTO_PRUNE)
class UserAutoPrunePolicy(ApiResource):
    """"""

    schemas = {
        "AutoPrunePolicyConfig": {
            "type": "object",
            "description": "",
            "required": ["method"],
            "properties": {
                "method": {
                    "type": "string",
                    "description": "",
                },
                "value": {
                    "type": ["integer", "string"],
                    "description": "",
                },
            },
        },
    }

    @require_user_admin()
    def get(self, policy_uuid):
        user = get_authenticated_user()

        policy = model.autoprune.get_namespace_autoprune_policy(user.username, policy_uuid)
        if policy is None:
            raise NotFound()

        return policy.get_view()

    @require_user_admin()
    @validate_json_request("AutoPrunePolicyConfig")
    def put(self, policy_uuid):
        user = get_authenticated_user()

        policy = model.autoprune.get_namespace_autoprune_policy(user.username, policy_uuid)
        if policy is None:
            raise NotFound()

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)

        try:
            method = AutoPruneMethod(method)
        except ValueError:
            request_error(message="Invalid method")

        if not valid_value(method, value):
            request_error(message="Invalid type given for parameter value")

        policy_config = {
            "method": method.value,
            "value": value,
        }
        policy = model.autoprune.update_namespace_autoprune_policy(
            user.username, policy_uuid, policy_config
        )
        if policy is None:
            raise NotFound()
        return policy_uuid, 204

    @require_user_admin()
    def delete(self, policy_uuid):
        user = get_authenticated_user()

        policy = model.autoprune.delete_namespace_autoprune_policy(user.username, policy_uuid)
        if policy is None:
            raise NotFound()

        return policy_uuid, 200
