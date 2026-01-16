# -*- coding: utf-8 -*-
"""
Organization-level repository mirroring API endpoints.

Enables users to configure a single mirroring task to replicate all repositories
from a source namespace (e.g., Harbor project, Quay organization) into a target
Quay organization.
"""

import logging
from datetime import datetime

from flask import request

import features
from auth import scopes
from auth.permissions import AdministerOrganizationPermission
from data import model
from data.encryption import DecryptionFailureException
from data.model import InvalidOrganizationException
from endpoints.api import (
    allow_if_superuser_with_full_access,
    ApiResource,
    nickname,
    path_param,
    require_scope,
    resource,
    show_if,
    validate_json_request,
)
from flask_restful import abort

from endpoints.exception import InvalidRequest, NotFound, Unauthorized


def require_org_admin(orgname):
    """
    Check if the current user has admin permission on the organization.
    Raises Unauthorized if not.
    """
    permission = AdministerOrganizationPermission(orgname)
    if not (permission.can() or allow_if_superuser_with_full_access()):
        raise Unauthorized()

logger = logging.getLogger(__name__)


def _not_implemented():
    """Return 501 Not Implemented response."""
    abort(501, message="This endpoint is not yet implemented")


@resource("/v1/organization/<orgname>/mirror")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrgMirrorConfig(ApiResource):
    """
    Resource for managing organization-level mirror configuration.
    """

    schemas = {
        "CreateOrgMirrorConfig": {
            "type": "object",
            "description": "Create organization mirror configuration",
            "required": [
                "external_registry_type",
                "external_registry_url",
                "external_namespace",
                "robot_username",
                "visibility",
                "sync_interval",
                "sync_start_date",
            ],
            "properties": {
                "external_registry_type": {
                    "type": "string",
                    "description": "Type of source registry",
                    "enum": ["harbor", "quay"],
                },
                "external_registry_url": {
                    "type": "string",
                    "description": "URL of the source registry",
                },
                "external_namespace": {
                    "type": "string",
                    "description": "Source namespace/project name",
                    "maxLength": 255,
                },
                "robot_username": {
                    "type": "string",
                    "description": "Robot account for creating repos (format: orgname+robotname)",
                },
                "visibility": {
                    "type": "string",
                    "description": "Visibility for created repositories",
                    "enum": ["public", "private"],
                },
                "sync_interval": {
                    "type": "integer",
                    "description": "Seconds between syncs",
                    "minimum": 60,
                },
                "sync_start_date": {
                    "type": "string",
                    "description": "Initial sync time (ISO 8601 format)",
                },
                "is_enabled": {
                    "type": "boolean",
                    "description": "Enable or disable mirroring",
                    "default": True,
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
                    "description": "TLS and proxy settings",
                    "properties": {
                        "verify_tls": {
                            "type": "boolean",
                            "description": "Verify TLS certificates",
                        },
                        "proxy": {
                            "type": "object",
                            "properties": {
                                "https_proxy": {"type": ["string", "null"]},
                                "http_proxy": {"type": ["string", "null"]},
                                "no_proxy": {"type": ["string", "null"]},
                            },
                        },
                    },
                },
                "repository_filters": {
                    "type": "array",
                    "description": "Glob patterns for filtering repositories",
                    "items": {"type": "string"},
                },
                "skopeo_timeout": {
                    "type": "integer",
                    "description": "Timeout for Skopeo operations in seconds",
                    "minimum": 30,
                    "maximum": 3600,
                    "default": 300,
                },
            },
        },
        "UpdateOrgMirrorConfig": {
            "type": "object",
            "description": "Update organization mirror configuration",
            "properties": {
                "is_enabled": {"type": "boolean"},
                "external_registry_url": {"type": "string"},
                "external_namespace": {"type": "string", "maxLength": 255},
                "robot_username": {"type": "string"},
                "visibility": {"type": "string", "enum": ["public", "private"]},
                "sync_interval": {"type": "integer", "minimum": 60},
                "sync_start_date": {"type": "string"},
                "external_registry_username": {"type": ["string", "null"]},
                "external_registry_password": {"type": ["string", "null"]},
                "external_registry_config": {"type": "object"},
                "repository_filters": {"type": "array", "items": {"type": "string"}},
                "skopeo_timeout": {"type": "integer", "minimum": 30, "maximum": 3600},
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrgMirrorConfig")
    def get(self, orgname):
        """
        Get the organization-level mirror configuration.
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        mirror = model.org_mirror.get_org_mirror_config(org)
        if not mirror:
            raise NotFound()

        try:
            username = self._decrypt_username(mirror.external_registry_username)
        except DecryptionFailureException as dfe:
            logger.warning(
                "Failed to decrypt username for organization %s: %s",
                orgname,
                dfe,
            )
            username = "(invalid. please re-enter)"

        return {
            "is_enabled": mirror.is_enabled,
            "external_registry_type": mirror.external_registry_type.name.lower(),
            "external_registry_url": mirror.external_registry_url,
            "external_namespace": mirror.external_namespace,
            "external_registry_username": username,
            "external_registry_config": mirror.external_registry_config or {},
            "repository_filters": mirror.repository_filters or [],
            "robot_username": mirror.internal_robot.username if mirror.internal_robot else None,
            "visibility": mirror.visibility.name,
            "delete_stale_repos": mirror.delete_stale_repos,
            "sync_interval": mirror.sync_interval,
            "sync_start_date": self._dt_to_string(mirror.sync_start_date),
            "sync_expiration_date": self._dt_to_string(mirror.sync_expiration_date),
            "sync_status": mirror.sync_status.name,
            "sync_retries_remaining": mirror.sync_retries_remaining,
            "skopeo_timeout": mirror.skopeo_timeout,
            "creation_date": self._dt_to_string(mirror.creation_date),
        }

    def _decrypt_username(self, username):
        """Decrypt the external registry username."""
        if username is None:
            return None
        return username.decrypt()

    def _dt_to_string(self, dt):
        """Convert DateTime to ISO 8601 formatted String."""
        if dt is None:
            return None
        assert isinstance(dt, datetime)
        return dt.isoformat() + "Z"

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrgMirrorConfig")
    @validate_json_request("CreateOrgMirrorConfig")
    def post(self, orgname):
        """
        Create organization mirror configuration.
        """
        require_org_admin(orgname)
        _not_implemented()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrgMirrorConfig")
    @validate_json_request("UpdateOrgMirrorConfig")
    def put(self, orgname):
        """
        Update organization mirror configuration.
        """
        require_org_admin(orgname)
        _not_implemented()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrgMirrorConfig")
    def delete(self, orgname):
        """
        Delete organization mirror configuration.
        """
        require_org_admin(orgname)
        _not_implemented()


@resource("/v1/organization/<orgname>/mirror/sync-now")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrgMirrorSyncNow(ApiResource):
    """
    Resource for triggering immediate organization mirror sync.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("syncOrgMirrorNow")
    def post(self, orgname):
        """
        Trigger immediate discovery and sync for the organization.
        """
        require_org_admin(orgname)
        _not_implemented()


@resource("/v1/organization/<orgname>/mirror/sync-cancel")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrgMirrorSyncCancel(ApiResource):
    """
    Resource for cancelling ongoing organization mirror sync.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("cancelOrgMirrorSync")
    def post(self, orgname):
        """
        Cancel ongoing discovery or sync operation.
        """
        require_org_admin(orgname)
        _not_implemented()


@resource("/v1/organization/<orgname>/mirror/verify")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrgMirrorVerify(ApiResource):
    """
    Resource for verifying connection to source registry.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("verifyOrgMirrorConnection")
    def post(self, orgname):
        """
        Verify connection to source registry.
        """
        require_org_admin(orgname)
        _not_implemented()


@resource("/v1/organization/<orgname>/mirror/repositories")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrgMirrorRepositories(ApiResource):
    """
    Resource for listing discovered repositories.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("listOrgMirrorRepositories")
    def get(self, orgname):
        """
        List all discovered repositories from source namespace.
        """
        require_org_admin(orgname)
        _not_implemented()
