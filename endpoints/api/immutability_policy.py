import logging
from typing import Any

from flask import request

import features
from auth import scopes
from auth.permissions import (
    AdministerOrganizationPermission,
    AdministerRepositoryPermission,
)
from data import model
from data.model import immutability
from data.registry_model import registry_model
from endpoints.api import (
    ApiResource,
    RepositoryParamResource,
    allow_if_global_readonly_superuser,
    allow_if_superuser,
    allow_if_superuser_with_full_access,
    log_action,
    nickname,
    path_param,
    request_error,
    require_repo_admin,
    require_scope,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.exception import NotFound, Unauthorized

logger = logging.getLogger(__name__)

IMMUTABILITY_POLICY_SCHEMA = {
    "ImmutabilityPolicyConfig": {
        "type": "object",
        "description": "The immutability policy configuration",
        "required": ["tagPattern"],
        "properties": {
            "tagPattern": {
                "type": "string",
                "description": "Regex pattern to match tag names",
            },
            "tagPatternMatches": {
                "type": "boolean",
                "description": "If true, matching tags are immutable. If false, non-matching tags are immutable.",
            },
        },
    },
}


def _parse_policy_config(app_data: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate policy config from request."""
    tag_pattern = app_data.get("tagPattern")
    if tag_pattern and isinstance(tag_pattern, str):
        tag_pattern = tag_pattern.strip()
    tag_pattern_matches = app_data.get("tagPatternMatches", True)
    return {"tag_pattern": tag_pattern, "tag_pattern_matches": tag_pattern_matches}


# Organization endpoints


@resource("/v1/organization/<orgname>/immutabilitypolicy/")
@path_param("orgname", "The name of the organization")
@show_if(features.IMMUTABLE_TAGS)
class OrgImmutabilityPolicies(ApiResource):
    schemas = IMMUTABILITY_POLICY_SCHEMA

    @require_scope(scopes.ORG_ADMIN)
    @nickname("listOrgImmutabilityPolicies")
    def get(self, orgname):
        permission = AdministerOrganizationPermission(orgname)
        if (
            not permission.can()
            and not allow_if_global_readonly_superuser()
            and not (features.SUPERUSERS_FULL_ACCESS and allow_if_superuser())
        ):
            raise Unauthorized()

        policies = immutability.get_namespace_immutability_policies(orgname)
        return {"policies": [p.get_view() for p in policies]}

    @require_scope(scopes.ORG_ADMIN)
    @validate_json_request("ImmutabilityPolicyConfig")
    @nickname("createOrgImmutabilityPolicy")
    def post(self, orgname):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser_with_full_access():
            raise Unauthorized()

        policy_config = _parse_policy_config(request.get_json())

        try:
            policy = immutability.create_namespace_immutability_policy(orgname, policy_config)
        except model.InvalidImmutabilityPolicy as ex:
            request_error(ex)
        except model.DuplicateImmutabilityPolicy as ex:
            request_error(ex)

        log_action("create_immutability_policy", orgname, {"namespace": orgname, **policy_config})
        return {"uuid": policy.uuid}, 201


@resource("/v1/organization/<orgname>/immutabilitypolicy/<policy_uuid>")
@path_param("orgname", "The name of the organization")
@path_param("policy_uuid", "The unique ID of the policy")
@show_if(features.IMMUTABLE_TAGS)
class OrgImmutabilityPolicy(ApiResource):
    schemas = IMMUTABILITY_POLICY_SCHEMA

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrgImmutabilityPolicy")
    def get(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if (
            not permission.can()
            and not allow_if_global_readonly_superuser()
            and not (features.SUPERUSERS_FULL_ACCESS and allow_if_superuser())
        ):
            raise Unauthorized()

        policy = immutability.get_namespace_immutability_policy(orgname, policy_uuid)
        if policy is None:
            raise NotFound()
        return policy.get_view()

    @require_scope(scopes.ORG_ADMIN)
    @validate_json_request("ImmutabilityPolicyConfig")
    @nickname("updateOrgImmutabilityPolicy")
    def put(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser_with_full_access():
            raise Unauthorized()

        policy_config = _parse_policy_config(request.get_json())

        try:
            immutability.update_namespace_immutability_policy(orgname, policy_uuid, policy_config)
        except model.InvalidImmutabilityPolicy as ex:
            request_error(ex)
        except model.DuplicateImmutabilityPolicy as ex:
            request_error(ex)
        except model.ImmutabilityPolicyDoesNotExist:
            raise NotFound()

        log_action("update_immutability_policy", orgname, {"namespace": orgname, **policy_config})
        return {"uuid": policy_uuid}, 204

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrgImmutabilityPolicy")
    def delete(self, orgname, policy_uuid):
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can() and not allow_if_superuser_with_full_access():
            raise Unauthorized()

        try:
            immutability.delete_namespace_immutability_policy(orgname, policy_uuid)
        except model.ImmutabilityPolicyDoesNotExist:
            raise NotFound()

        log_action(
            "delete_immutability_policy",
            orgname,
            {"namespace": orgname, "policy_uuid": policy_uuid},
        )
        return {"uuid": policy_uuid}, 200


# Repository endpoints


@resource("/v1/repository/<apirepopath:repository>/immutabilitypolicy/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@show_if(features.IMMUTABLE_TAGS)
class RepositoryImmutabilityPolicies(RepositoryParamResource):
    schemas = IMMUTABILITY_POLICY_SCHEMA

    @require_repo_admin(allow_for_global_readonly_superuser=True, allow_for_superuser=True)
    @nickname("listRepositoryImmutabilityPolicies")
    def get(self, namespace, repository):
        permission = AdministerRepositoryPermission(namespace, repository)
        if (
            not permission.can()
            and not allow_if_global_readonly_superuser()
            and not (features.SUPERUSERS_FULL_ACCESS and allow_if_superuser())
        ):
            raise Unauthorized()

        if registry_model.lookup_repository(namespace, repository) is None:
            raise NotFound()

        policies = immutability.get_repository_immutability_policies(namespace, repository)
        return {"policies": [p.get_view() for p in policies]}

    @require_repo_admin(allow_for_superuser=True)
    @validate_json_request("ImmutabilityPolicyConfig")
    @nickname("createRepositoryImmutabilityPolicy")
    def post(self, namespace, repository):
        permission = AdministerRepositoryPermission(namespace, repository)
        if not permission.can() and not allow_if_superuser_with_full_access():
            raise Unauthorized()

        if registry_model.lookup_repository(namespace, repository) is None:
            raise NotFound()

        policy_config = _parse_policy_config(request.get_json())

        try:
            policy = immutability.create_repository_immutability_policy(
                namespace, repository, policy_config
            )
        except model.InvalidImmutabilityPolicy as ex:
            request_error(ex)
        except model.DuplicateImmutabilityPolicy as ex:
            request_error(ex)
        except model.InvalidRepositoryException:
            raise NotFound()

        log_action(
            "create_immutability_policy",
            namespace,
            {"namespace": namespace, "repo": repository, **policy_config},
            repo_name=repository,
        )
        return {"uuid": policy.uuid}, 201


@resource("/v1/repository/<apirepopath:repository>/immutabilitypolicy/<policy_uuid>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("policy_uuid", "The unique ID of the policy")
@show_if(features.IMMUTABLE_TAGS)
class RepositoryImmutabilityPolicy(RepositoryParamResource):
    schemas = IMMUTABILITY_POLICY_SCHEMA

    @require_repo_admin(allow_for_global_readonly_superuser=True, allow_for_superuser=True)
    @nickname("getRepositoryImmutabilityPolicy")
    def get(self, namespace, repository, policy_uuid):
        permission = AdministerRepositoryPermission(namespace, repository)
        if (
            not permission.can()
            and not allow_if_global_readonly_superuser()
            and not (features.SUPERUSERS_FULL_ACCESS and allow_if_superuser())
        ):
            raise Unauthorized()

        policy = immutability.get_repository_immutability_policy(namespace, repository, policy_uuid)
        if policy is None:
            raise NotFound()
        return policy.get_view()

    @require_repo_admin(allow_for_superuser=True)
    @validate_json_request("ImmutabilityPolicyConfig")
    @nickname("updateRepositoryImmutabilityPolicy")
    def put(self, namespace, repository, policy_uuid):
        permission = AdministerRepositoryPermission(namespace, repository)
        if not permission.can() and not allow_if_superuser_with_full_access():
            raise Unauthorized()

        policy_config = _parse_policy_config(request.get_json())

        try:
            immutability.update_repository_immutability_policy(
                namespace, repository, policy_uuid, policy_config
            )
        except model.InvalidImmutabilityPolicy as ex:
            request_error(ex)
        except model.DuplicateImmutabilityPolicy as ex:
            request_error(ex)
        except model.ImmutabilityPolicyDoesNotExist:
            raise NotFound()
        except model.InvalidRepositoryException:
            raise NotFound()

        log_action(
            "update_immutability_policy",
            namespace,
            {"namespace": namespace, "repo": repository, **policy_config},
            repo_name=repository,
        )
        return {"uuid": policy_uuid}, 204

    @require_repo_admin(allow_for_superuser=True)
    @nickname("deleteRepositoryImmutabilityPolicy")
    def delete(self, namespace, repository, policy_uuid):
        permission = AdministerRepositoryPermission(namespace, repository)
        if not permission.can() and not allow_if_superuser_with_full_access():
            raise Unauthorized()

        try:
            immutability.delete_repository_immutability_policy(namespace, repository, policy_uuid)
        except model.ImmutabilityPolicyDoesNotExist:
            raise NotFound()
        except model.InvalidRepositoryException:
            raise NotFound()

        log_action(
            "delete_immutability_policy",
            namespace,
            {"namespace": namespace, "repo": repository, "policy_uuid": policy_uuid},
            repo_name=repository,
        )
        return {"uuid": policy_uuid}, 200
