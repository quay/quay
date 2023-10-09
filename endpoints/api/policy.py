import logging

from flask import request

import features
from auth.auth_context import get_authenticated_user
from auth.permissions import AdministerOrganizationPermission
from data import model
from data.model.autoprune import AutoPruneMethod, valid_value
from endpoints.api import (
    ApiResource,
    allow_if_superuser,
    path_param,
    request_error,
    require_user_admin,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.exception import InvalidRequest, NotFound, Unauthorized

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

        policies = model.autoprune.get_namespace_autoprune_policies_by_orgname(orgname)

        return {"policies": [policy.get_view() for policy in policies]}

    @validate_json_request("AutoPrunePolicyConfig")
    def post(self, orgname):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)

        if method is None or value is None:
            request_error(message="Missing the following parameters: method, value")

        policy_config = {
            "method": method,
            "value": value,
        }

        try:
            policy = model.autoprune.create_namespace_autoprune_policy(
                orgname, policy_config, create_task=True
            )
        except model.InvalidNamespaceException:
            raise NotFound()
        except model.InvalidNamespaceAutoPrunePolicy as ex:
            request_error(ex)
        except model.NamespaceAutoPrunePolicyAlreadyExists as ex:
            request_error(ex)

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

        policy = model.autoprune.get_namespace_autoprune_policy(orgname, policy_uuid)
        if policy is None:
            raise NotFound()

        return policy.get_view()

    @validate_json_request("AutoPrunePolicyConfig")
    def put(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)

        if method is None or value is None:
            request_error(message="Missing the following parameters: method, value")

        policy_config = {
            "method": method,
            "value": value,
        }

        try:
            updated = model.autoprune.update_namespace_autoprune_policy(
                orgname, policy_uuid, policy_config
            )
            if not updated:
                request_error(message="could not update policy")
        except model.InvalidNamespaceException:
            raise NotFound()
        except model.InvalidNamespaceAutoPrunePolicy as ex:
            request_error(ex)
        except model.NamespaceAutoPrunePolicyDoesNotExist as ex:
            raise NotFound()

        return {"uuid": policy_uuid}, 204

    def delete(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser():
            raise Unauthorized()

        try:
            updated = model.autoprune.delete_namespace_autoprune_policy(orgname, policy_uuid)
            if not updated:
                raise InvalidRequest("could not delete policy")
        except model.InvalidNamespaceException as ex:
            raise NotFound()
        except model.NamespaceAutoPrunePolicyDoesNotExist as ex:
            raise NotFound()

        return {"uuid": policy_uuid}, 200


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

        return {"policies": [policy.get_view() for policy in policies]}

    @require_user_admin()
    @validate_json_request("AutoPrunePolicyConfig")
    def post(self):
        user = get_authenticated_user()

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)

        if method is None or value is None:
            request_error(message="Missing the following parameters: method, value")

        policy_config = {
            "method": method,
            "value": value,
        }
        try:
            policy = model.autoprune.create_namespace_autoprune_policy(
                user.username, policy_config, create_task=True
            )
        except model.InvalidNamespaceException:
            raise NotFound()
        except model.InvalidNamespaceAutoPrunePolicy as ex:
            request_error(ex)
        except model.NamespaceAutoPrunePolicyAlreadyExists as ex:
            request_error(ex)

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

        app_data = request.get_json()
        method = app_data.get("method", None)
        value = app_data.get("value", None)

        if method is None or value is None:
            request_error(message="Missing the following parameters: method, value")

        policy_config = {
            "method": method,
            "value": value,
        }

        try:
            updated = model.autoprune.update_namespace_autoprune_policy(
                user.username, policy_uuid, policy_config
            )
            if not updated:
                raise InvalidRequest("could not update policy")
        except model.InvalidNamespaceException:
            raise NotFound()
        except model.InvalidNamespaceAutoPrunePolicy as ex:
            request_error(ex)
        except model.NamespaceAutoPrunePolicyDoesNotExist as ex:
            raise NotFound()

        return {"uuid": policy_uuid}, 204

    @require_user_admin()
    def delete(self, policy_uuid):
        user = get_authenticated_user()

        try:
            updated = model.autoprune.delete_namespace_autoprune_policy(user.username, policy_uuid)
            if not updated:
                raise InvalidRequest("could not delete policy")
        except model.InvalidNamespaceException as ex:
            raise NotFound()
        except model.NamespaceAutoPrunePolicyDoesNotExist as ex:
            raise NotFound()

        return {"uuid": policy_uuid}, 200
