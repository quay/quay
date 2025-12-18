# -*- coding: utf-8 -*-
"""
API endpoints for managing organization-level repository mirroring.

Provides CRUD operations for organization mirror configurations and endpoints
for querying discovered repositories and triggering syncs.
"""

import logging
from datetime import datetime

from flask import request

import features
from auth.permissions import AdministerOrganizationPermission
from data.database import OrgMirrorRepoStatus, OrgMirrorStatus, RepoMirrorRuleType
from data.fields import DecryptedValue
from data.model.org_mirror import (
    create_org_mirror,
    delete_org_mirror,
    get_discovered_repos,
    get_org_mirror_config,
    trigger_sync_now,
    update_org_mirror_config,
)
from data.model.organization import get_organization
from data.model.user import get_user
from endpoints.api import (
    ApiResource,
    define_json_response,
    format_date,
    nickname,
    path_param,
    require_scope,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.exception import InvalidRequest, NotFound, Unauthorized
from util.audit import track_and_log
from util.parsing import truthy_bool

logger = logging.getLogger(__name__)


# JSON Schemas
common_properties = {
    "is_enabled": {
        "type": "boolean",
        "description": "Enable or disable the organization mirror",
    },
    "external_reference": {
        "type": "string",
        "description": "Source organization/project (e.g., 'harbor.example.com/my-project')",
    },
    "external_registry_username": {
        "type": ["string", "null"],
        "description": "Username for source registry authentication",
    },
    "external_registry_password": {
        "type": ["string", "null"],
        "description": "Password for source registry authentication",
    },
    "external_registry_config": {
        "type": "object",
        "description": "Additional registry configuration (verify_tls, etc.)",
    },
    "sync_interval": {
        "type": "integer",
        "description": "Sync interval in seconds",
        "minimum": 0,
    },
    "sync_start_date": {
        "type": "string",
        "description": "Date and time of next sync start",
    },
    "sync_status": {
        "type": "string",
        "enum": ["NEVER_RUN", "SUCCESS", "FAIL", "SYNCING", "SYNC_NOW", "CANCEL"],
        "description": "Current sync status",
    },
    "internal_robot": {
        "type": "string",
        "description": "Robot account username for repository creation",
    },
    "root_rule": {
        "type": ["object", "null"],
        "description": "Repository filtering rules",
    },
    "skopeo_timeout": {
        "type": "integer",
        "description": "Timeout for skopeo operations in seconds",
        "minimum": 0,
    },
}


def _mirror_to_dict(mirror):
    """
    Convert OrgMirrorConfig to API dict representation.

    Args:
        mirror: OrgMirrorConfig instance

    Returns:
        Dict with mirror configuration
    """
    # Decrypt credentials if present
    username = None
    if mirror.external_registry_username:
        try:
            username_value = mirror.external_registry_username.decrypt()
            if isinstance(username_value, DecryptedValue):
                username = username_value.value
            else:
                username = username_value
        except Exception:
            logger.exception("Failed to decrypt external_registry_username")

    password = None
    if mirror.external_registry_password:
        try:
            password_value = mirror.external_registry_password.decrypt()
            if isinstance(password_value, DecryptedValue):
                password = password_value.value
            else:
                password = password_value
        except Exception:
            logger.exception("Failed to decrypt external_registry_password")

    return {
        "is_enabled": mirror.is_enabled,
        "external_reference": mirror.external_reference,
        "external_registry_username": username,
        "external_registry_password": password,
        "external_registry_config": mirror.external_registry_config or {},
        "sync_interval": mirror.sync_interval,
        "sync_start_date": format_date(mirror.sync_start_date) if mirror.sync_start_date else None,
        "sync_expiration_date": format_date(mirror.sync_expiration_date)
        if mirror.sync_expiration_date
        else None,
        "sync_retries_remaining": mirror.sync_retries_remaining,
        "sync_status": mirror.sync_status.name,
        "internal_robot": mirror.internal_robot.username,
        "root_rule": _rule_to_dict(mirror.root_rule) if mirror.root_rule else None,
        "skopeo_timeout": mirror.skopeo_timeout,
    }


def _rule_to_dict(rule):
    """
    Convert RepoMirrorRule to API dict representation.

    Args:
        rule: RepoMirrorRule instance

    Returns:
        Dict with rule structure
    """
    if not rule:
        return None

    result = {
        "rule_type": rule.rule_type.name,
        "rule_value": rule.rule_value,
    }

    if rule.left_child or rule.right_child:
        result["left_child"] = _rule_to_dict(rule.left_child) if rule.left_child else None
        result["right_child"] = _rule_to_dict(rule.right_child) if rule.right_child else None

    return result


def _parse_rule(rule_dict):
    """
    Parse rule dict from API request into RepoMirrorRule.

    Args:
        rule_dict: Dict with rule structure

    Returns:
        RepoMirrorRule instance or None
    """
    from data.database import RepoMirrorRule

    if not rule_dict:
        return None

    # Get rule type
    rule_type_name = rule_dict.get("rule_type")
    if not rule_type_name:
        raise InvalidRequest("Missing rule_type in rule definition")

    try:
        rule_type = RepoMirrorRuleType[rule_type_name]
    except KeyError:
        raise InvalidRequest(f"Invalid rule_type: {rule_type_name}")

    # Parse children recursively
    left_child = _parse_rule(rule_dict.get("left_child")) if rule_dict.get("left_child") else None
    right_child = (
        _parse_rule(rule_dict.get("right_child")) if rule_dict.get("right_child") else None
    )

    # Create rule
    rule = RepoMirrorRule.create(
        rule_type=rule_type,
        rule_value=rule_dict.get("rule_value", {}),
        left_child=left_child,
        right_child=right_child,
    )

    return rule


@resource("/v1/organization/<orgname>/mirror")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrganizationMirrorResource(ApiResource):
    """
    Resource for managing organization-level repository mirroring.
    """

    schemas = {
        "CreateOrgMirror": {
            "type": "object",
            "required": [
                "external_reference",
                "sync_interval",
                "internal_robot",
                "skopeo_timeout",
            ],
            "properties": common_properties,
        },
        "UpdateOrgMirror": {
            "type": "object",
            "properties": common_properties,
        },
        "ViewOrgMirror": {
            "type": "object",
            "properties": common_properties,
        },
    }

    @require_scope(AdministerOrganizationPermission)
    @nickname("getOrgMirrorConfig")
    @define_json_response("ViewOrgMirror")
    def get(self, orgname):
        """
        Get organization mirror configuration.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can():
            raise Unauthorized()

        mirror = get_org_mirror_config(orgname)
        if not mirror:
            raise NotFound()

        return _mirror_to_dict(mirror), 200

    @require_scope(AdministerOrganizationPermission)
    @nickname("createOrgMirrorConfig")
    @validate_json_request("CreateOrgMirror")
    def post(self, orgname):
        """
        Create organization mirror configuration.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can():
            raise Unauthorized()

        # Check if already exists
        existing = get_org_mirror_config(orgname)
        if existing:
            raise InvalidRequest("Organization mirror already exists")

        data = request.get_json()

        # Get robot account
        robot_username = data["internal_robot"]
        robot = get_user(robot_username)
        if not robot or not robot.robot:
            raise InvalidRequest("Invalid robot account")

        # Validate robot belongs to organization
        if robot.username.split("+")[0] != orgname:
            raise InvalidRequest("Robot must belong to the organization")

        # Parse root_rule if provided
        root_rule = None
        if "root_rule" in data and data["root_rule"]:
            root_rule = _parse_rule(data["root_rule"])

        try:
            mirror = create_org_mirror(
                org_name=orgname,
                external_reference=data["external_reference"],
                sync_interval=data["sync_interval"],
                internal_robot=robot,
                skopeo_timeout=data["skopeo_timeout"],
                external_registry_username=data.get("external_registry_username"),
                external_registry_password=data.get("external_registry_password"),
                external_registry_config=data.get("external_registry_config", {}),
                root_rule=root_rule,
                is_enabled=data.get("is_enabled", True),
            )

            # Log audit event
            track_and_log(
                "org_mirror_config_created",
                namespace_name=orgname,
                metadata={
                    "external_reference": mirror.external_reference,
                    "sync_interval": mirror.sync_interval,
                    "robot": robot.username,
                },
            )

            return _mirror_to_dict(mirror), 201

        except Exception as e:
            logger.exception("Failed to create organization mirror")
            raise InvalidRequest(str(e))

    @require_scope(AdministerOrganizationPermission)
    @nickname("updateOrgMirrorConfig")
    @validate_json_request("UpdateOrgMirror")
    def put(self, orgname):
        """
        Update organization mirror configuration.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can():
            raise Unauthorized()

        mirror = get_org_mirror_config(orgname)
        if not mirror:
            raise NotFound()

        data = request.get_json()

        # Parse updates
        updates = {}

        if "is_enabled" in data:
            updates["is_enabled"] = data["is_enabled"]

        if "external_reference" in data:
            updates["external_reference"] = data["external_reference"]

        if "external_registry_username" in data:
            updates["external_registry_username"] = data["external_registry_username"]

        if "external_registry_password" in data:
            updates["external_registry_password"] = data["external_registry_password"]

        if "external_registry_config" in data:
            updates["external_registry_config"] = data["external_registry_config"]

        if "sync_interval" in data:
            updates["sync_interval"] = data["sync_interval"]

        if "skopeo_timeout" in data:
            updates["skopeo_timeout"] = data["skopeo_timeout"]

        if "internal_robot" in data:
            robot_username = data["internal_robot"]
            robot = get_user(robot_username)
            if not robot or not robot.robot:
                raise InvalidRequest("Invalid robot account")
            if robot.username.split("+")[0] != orgname:
                raise InvalidRequest("Robot must belong to the organization")
            updates["internal_robot"] = robot

        if "root_rule" in data:
            if data["root_rule"]:
                updates["root_rule"] = _parse_rule(data["root_rule"])
            else:
                updates["root_rule"] = None

        try:
            updated_mirror = update_org_mirror_config(orgname, **updates)

            # Log audit event
            track_and_log(
                "org_mirror_config_changed",
                namespace_name=orgname,
                metadata={
                    "changed": list(data.keys()),
                    "external_reference": updated_mirror.external_reference,
                },
            )

            return _mirror_to_dict(updated_mirror), 200

        except Exception as e:
            logger.exception("Failed to update organization mirror")
            raise InvalidRequest(str(e))

    @require_scope(AdministerOrganizationPermission)
    @nickname("deleteOrgMirrorConfig")
    def delete(self, orgname):
        """
        Delete organization mirror configuration.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can():
            raise Unauthorized()

        mirror = get_org_mirror_config(orgname)
        if not mirror:
            raise NotFound()

        # Capture external reference before deletion
        external_ref = mirror.external_reference

        try:
            delete_org_mirror(orgname)

            # Log audit event
            track_and_log(
                "org_mirror_config_deleted",
                namespace_name=orgname,
                metadata={
                    "external_reference": external_ref,
                },
            )

            return "", 204

        except Exception as e:
            logger.exception("Failed to delete organization mirror")
            raise InvalidRequest(str(e))


@resource("/v1/organization/<orgname>/mirror/repositories")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrganizationMirrorRepositoriesResource(ApiResource):
    """
    Resource for querying discovered repositories for an organization mirror.
    """

    schemas = {
        "ViewDiscoveredRepositories": {
            "type": "object",
            "properties": {
                "repositories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "repository_name": {"type": "string"},
                            "external_repo_name": {"type": "string"},
                            "status": {"type": "string"},
                            "message": {"type": ["string", "null"]},
                            "created_repository": {"type": ["string", "null"]},
                        },
                    },
                },
            },
        },
    }

    @require_scope(AdministerOrganizationPermission)
    @nickname("getOrgMirrorRepositories")
    @define_json_response("ViewDiscoveredRepositories")
    def get(self, orgname):
        """
        Get list of discovered repositories for organization mirror.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can():
            raise Unauthorized()

        mirror = get_org_mirror_config(orgname)
        if not mirror:
            raise NotFound()

        # Get status filter from query params
        status_filter = request.args.get("status")
        status_enum = None
        if status_filter:
            try:
                status_enum = OrgMirrorRepoStatus[status_filter.upper()]
            except KeyError:
                raise InvalidRequest(f"Invalid status: {status_filter}")

        discovered = get_discovered_repos(mirror, status=status_enum)

        repositories = []
        for repo in discovered:
            repositories.append(
                {
                    "repository_name": repo.repository_name,
                    "external_repo_name": repo.external_repo_name,
                    "status": repo.status.name,
                    "message": repo.message,
                    "created_repository": f"{orgname}/{repo.repository_name}"
                    if repo.repository
                    else None,
                }
            )

        return {"repositories": repositories}, 200


@resource("/v1/organization/<orgname>/mirror/sync-now")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrganizationMirrorSyncNowResource(ApiResource):
    """
    Resource for triggering immediate sync of organization mirror.
    """

    @require_scope(AdministerOrganizationPermission)
    @nickname("triggerOrgMirrorSyncNow")
    def post(self, orgname):
        """
        Trigger immediate sync for organization mirror.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can():
            raise Unauthorized()

        mirror = get_org_mirror_config(orgname)
        if not mirror:
            raise NotFound()

        if not mirror.is_enabled:
            raise InvalidRequest("Cannot sync disabled mirror")

        try:
            trigger_sync_now(mirror)

            # Log audit event
            track_and_log(
                "org_mirror_sync_requested",
                namespace_name=orgname,
                metadata={
                    "sync_status": "SYNC_NOW",
                },
            )

            return {"status": "sync_triggered"}, 200

        except Exception as e:
            logger.exception("Failed to trigger sync")
            raise InvalidRequest(str(e))
