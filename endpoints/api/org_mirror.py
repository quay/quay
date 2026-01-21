# -*- coding: utf-8 -*-
"""
Organization-level repository mirroring API endpoints.

Enables users to configure a single mirroring task to replicate all repositories
from a source namespace (e.g., Harbor project, Quay organization) into a target
Quay organization.
"""

import logging
from datetime import datetime

import requests
from flask import request

import features
from auth import scopes
from auth.permissions import AdministerOrganizationPermission
from data import model
from data.database import SourceRegistryType, Visibility
from data.encryption import DecryptionFailureException
from data.model import DataModelException, InvalidOrganizationException
from endpoints.api import (
    ApiResource,
    allow_if_superuser_with_full_access,
    log_action,
    nickname,
    path_param,
    require_scope,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.exception import InvalidRequest, NotFound, Unauthorized
from util.names import parse_robot_username
from util.orgmirror import get_registry_adapter


def require_org_admin(orgname):
    """
    Check if the current user has admin permission on the organization.
    Raises Unauthorized if not.
    """
    permission = AdministerOrganizationPermission(orgname)
    if not (permission.can() or allow_if_superuser_with_full_access()):
        raise Unauthorized()


logger = logging.getLogger(__name__)


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

    def _string_to_dt(self, string):
        """Convert ISO 8601 string to datetime."""
        if string is None:
            return None
        assert isinstance(string, str)
        return datetime.strptime(string, "%Y-%m-%dT%H:%M:%SZ")

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrgMirrorConfig")
    @validate_json_request("CreateOrgMirrorConfig")
    def post(self, orgname):
        """
        Create organization mirror configuration.
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        # Check if mirror config already exists
        existing = model.org_mirror.get_org_mirror_config(org)
        if existing:
            raise InvalidRequest("Mirror configuration already exists for this organization")

        data = request.get_json()

        # Validate and look up robot account
        robot_username = data.get("robot_username")
        try:
            robot = model.user.lookup_robot(robot_username)
        except model.InvalidRobotException:
            raise InvalidRequest(f"Invalid robot account: {robot_username}")

        # Verify robot belongs to the organization
        namespace, _ = parse_robot_username(robot_username)
        if namespace != orgname:
            raise InvalidRequest("Robot account must belong to the organization")

        # Parse external registry type
        registry_type_str = data.get("external_registry_type", "").upper()
        try:
            external_registry_type = SourceRegistryType[registry_type_str]
        except KeyError:
            raise InvalidRequest(
                f"Invalid external_registry_type: {data.get('external_registry_type')}"
            )

        # Parse visibility
        visibility_str = data.get("visibility", "").lower()
        try:
            visibility = Visibility.get(name=visibility_str)
        except Visibility.DoesNotExist:
            raise InvalidRequest(f"Invalid visibility: {data.get('visibility')}")

        # Parse sync_start_date
        try:
            sync_start_date = self._string_to_dt(data.get("sync_start_date"))
        except (ValueError, AssertionError):
            raise InvalidRequest(
                "Invalid sync_start_date format. Use ISO 8601: YYYY-MM-DDTHH:MM:SSZ"
            )

        # Validate sync_interval
        sync_interval = data.get("sync_interval")
        if sync_interval < 60:
            raise InvalidRequest("sync_interval must be at least 60 seconds")

        # Validate skopeo_timeout
        skopeo_timeout = data.get("skopeo_timeout", 300)
        if skopeo_timeout < 30 or skopeo_timeout > 3600:
            raise InvalidRequest("skopeo_timeout must be between 30 and 3600 seconds")

        # Create the mirror config
        try:
            mirror = model.org_mirror.create_org_mirror_config(
                organization=org,
                internal_robot=robot,
                external_registry_type=external_registry_type,
                external_registry_url=data.get("external_registry_url"),
                external_namespace=data.get("external_namespace"),
                visibility=visibility,
                sync_interval=sync_interval,
                sync_start_date=sync_start_date,
                is_enabled=data.get("is_enabled", True),
                external_registry_username=data.get("external_registry_username"),
                external_registry_password=data.get("external_registry_password"),
                external_registry_config=data.get("external_registry_config", {}),
                repository_filters=data.get("repository_filters", []),
                skopeo_timeout=skopeo_timeout,
            )
        except DataModelException as e:
            raise InvalidRequest(str(e))

        # Log the action
        log_action(
            "org_mirror_enabled",
            orgname,
            {
                "external_registry_type": registry_type_str.lower(),
                "external_registry_url": data.get("external_registry_url"),
                "external_namespace": data.get("external_namespace"),
            },
        )

        return "", 201

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrgMirrorConfig")
    @validate_json_request("UpdateOrgMirrorConfig")
    def put(self, orgname):
        """
        Update organization mirror configuration.
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        # Check if mirror config exists
        existing = model.org_mirror.get_org_mirror_config(org)
        if not existing:
            raise NotFound()

        data = request.get_json()

        # Build update kwargs with validated values
        update_kwargs = {}

        # Handle is_enabled
        if "is_enabled" in data:
            update_kwargs["is_enabled"] = data["is_enabled"]

        # Handle external_registry_url
        if "external_registry_url" in data:
            update_kwargs["external_registry_url"] = data["external_registry_url"]

        # Handle external_namespace
        if "external_namespace" in data:
            update_kwargs["external_namespace"] = data["external_namespace"]

        # Handle robot_username
        if "robot_username" in data:
            robot_username = data["robot_username"]
            try:
                robot = model.user.lookup_robot(robot_username)
            except model.InvalidRobotException:
                raise InvalidRequest(f"Invalid robot account: {robot_username}")

            # Verify robot belongs to the organization
            namespace, _ = parse_robot_username(robot_username)
            if namespace != orgname:
                raise InvalidRequest("Robot account must belong to the organization")
            update_kwargs["internal_robot"] = robot

        # Handle visibility
        if "visibility" in data:
            visibility_str = data["visibility"].lower()
            try:
                visibility = Visibility.get(name=visibility_str)
            except Visibility.DoesNotExist:
                raise InvalidRequest(f"Invalid visibility: {data['visibility']}")
            update_kwargs["visibility"] = visibility

        # Handle sync_interval
        if "sync_interval" in data:
            sync_interval = data["sync_interval"]
            if sync_interval < 60:
                raise InvalidRequest("sync_interval must be at least 60 seconds")
            update_kwargs["sync_interval"] = sync_interval

        # Handle sync_start_date
        if "sync_start_date" in data:
            try:
                sync_start_date = self._string_to_dt(data["sync_start_date"])
            except (ValueError, AssertionError):
                raise InvalidRequest(
                    "Invalid sync_start_date format. Use ISO 8601: YYYY-MM-DDTHH:MM:SSZ"
                )
            update_kwargs["sync_start_date"] = sync_start_date

        # Handle external_registry_username
        if "external_registry_username" in data:
            update_kwargs["external_registry_username"] = data["external_registry_username"]

        # Handle external_registry_password
        if "external_registry_password" in data:
            update_kwargs["external_registry_password"] = data["external_registry_password"]

        # Handle external_registry_config
        if "external_registry_config" in data:
            update_kwargs["external_registry_config"] = data["external_registry_config"]

        # Handle repository_filters
        if "repository_filters" in data:
            update_kwargs["repository_filters"] = data["repository_filters"]

        # Handle skopeo_timeout
        if "skopeo_timeout" in data:
            skopeo_timeout = data["skopeo_timeout"]
            if skopeo_timeout < 30 or skopeo_timeout > 3600:
                raise InvalidRequest("skopeo_timeout must be between 30 and 3600 seconds")
            update_kwargs["skopeo_timeout"] = skopeo_timeout

        # Update the mirror config
        try:
            model.org_mirror.update_org_mirror_config(org, **update_kwargs)
        except DataModelException as e:
            raise InvalidRequest(str(e))

        # Log the action
        log_action(
            "org_mirror_config_changed",
            orgname,
            {"updated_fields": list(data.keys())},
        )

        return "", 200

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrgMirrorConfig")
    def delete(self, orgname):
        """
        Delete organization mirror configuration.
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        deleted = model.org_mirror.delete_org_mirror_config(org)
        if not deleted:
            raise NotFound()

        # Log the action
        log_action("org_mirror_disabled", orgname, {})

        return "", 204


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

        Sets sync_status to SYNC_NOW and sync_start_date to now for
        immediate pickup by the repomirrorworker.

        Returns 204 on success, 404 if config not found or already syncing.
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        mirror = model.org_mirror.get_org_mirror_config(org)
        if not mirror:
            raise NotFound()

        updated = model.org_mirror.update_sync_status_to_sync_now(mirror)
        if not updated:
            raise InvalidRequest("Cannot trigger sync: mirror is currently syncing")

        log_action(
            "org_mirror_sync_now_requested",
            orgname,
            {},
        )

        return "", 204


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

        Sets sync_status to CANCEL on the config and all in-progress
        repository syncs. The worker will stop processing on next check.

        Returns 204 on success, 404 if config not found or not syncing.
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        mirror = model.org_mirror.get_org_mirror_config(org)
        if not mirror:
            raise NotFound()

        updated = model.org_mirror.update_sync_status_to_cancel(mirror)
        if not updated:
            raise InvalidRequest("Cannot cancel: mirror is not currently syncing")

        log_action(
            "org_mirror_sync_cancelled",
            orgname,
            {},
        )

        return "", 204


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

        Tests connectivity, authentication, and TLS configuration without
        triggering a full sync operation. Useful for validating configuration
        before enabling mirroring.

        Returns:
            JSON object with:
                - success: Boolean indicating if connection was successful
                - message: Human-readable status message
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        mirror = model.org_mirror.get_org_mirror_config(org)
        if not mirror:
            raise NotFound()

        # Decrypt credentials
        try:
            username = (
                mirror.external_registry_username.decrypt()
                if mirror.external_registry_username
                else None
            )
            password = (
                mirror.external_registry_password.decrypt()
                if mirror.external_registry_password
                else None
            )
        except DecryptionFailureException as e:
            logger.warning("Failed to decrypt credentials for mirror config: %s", e)
            return {"success": False, "message": "Failed to decrypt source registry credentials"}

        # Create adapter for the source registry type
        try:
            adapter = get_registry_adapter(
                registry_type=mirror.external_registry_type,
                url=mirror.external_registry_url,
                namespace=mirror.external_namespace,
                username=username,
                password=password,
                config=mirror.external_registry_config,
            )
        except ValueError as e:
            return {"success": False, "message": str(e)}

        # Test connection
        success, message = adapter.test_connection()

        return {"success": success, "message": message}


MAX_PAGE_LIMIT = 500
DEFAULT_PAGE_LIMIT = 100


@resource("/v1/organization/<orgname>/mirror/repositories")
@path_param("orgname", "The name of the organization")
@show_if(features.ORG_MIRROR)
class OrgMirrorRepositories(ApiResource):
    """
    Resource for listing discovered repositories from the source registry.

    This endpoint fetches repositories from the configured source registry,
    applies glob filters, persists them to the database, and returns a
    paginated list with sync status information.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("listOrgMirrorRepositories")
    def get(self, orgname):
        """
        List all discovered repositories from source namespace.

        Query Parameters:
            page (int): Page number, default 1
            limit (int): Items per page, default 100, max 500
            refresh (bool): If true, fetch fresh data from source registry

        Returns:
            JSON object with:
                - repositories: List of repository objects
                - page: Current page number
                - limit: Items per page
                - total: Total number of matching repositories
                - has_next: Whether there are more pages
        """
        require_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except InvalidOrganizationException:
            raise NotFound()

        mirror = model.org_mirror.get_org_mirror_config(org)
        if not mirror:
            raise NotFound()

        # Parse pagination parameters
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)
        limit = min(limit, MAX_PAGE_LIMIT)  # Cap at max
        refresh = request.args.get("refresh", "false").lower() == "true"

        if page < 1:
            page = 1
        if limit < 1:
            limit = DEFAULT_PAGE_LIMIT

        # Check if we need to refresh from source registry
        if refresh:
            self._refresh_from_source(mirror)

        # Fetch from database with pagination
        repos, total = model.org_mirror.get_org_mirror_repos(mirror, page, limit)

        return {
            "repositories": [
                {
                    "name": r.repository_name,
                    "sync_status": r.sync_status.name,
                    "discovery_date": self._dt_to_string(r.discovery_date),
                    "last_sync_date": self._dt_to_string(r.last_sync_date),
                    "status_message": r.status_message,
                    "quay_repository": (
                        f"{orgname}/{r.repository_name}" if r.repository_id else None
                    ),
                }
                for r in repos
            ],
            "page": page,
            "limit": limit,
            "total": total,
            "has_next": (page * limit) < total,
        }

    def _refresh_from_source(self, mirror):
        """
        Fetch repositories from source registry and update the database.

        Args:
            mirror: OrgMirrorConfig instance

        Raises:
            InvalidRequest: On connection or API errors
        """
        # Decrypt credentials
        try:
            username = (
                mirror.external_registry_username.decrypt()
                if mirror.external_registry_username
                else None
            )
            password = (
                mirror.external_registry_password.decrypt()
                if mirror.external_registry_password
                else None
            )
        except DecryptionFailureException as e:
            logger.warning("Failed to decrypt credentials for mirror config: %s", e)
            raise InvalidRequest("Failed to decrypt source registry credentials")

        # Create adapter for the source registry type
        try:
            adapter = get_registry_adapter(
                registry_type=mirror.external_registry_type,
                url=mirror.external_registry_url,
                namespace=mirror.external_namespace,
                username=username,
                password=password,
                config=mirror.external_registry_config,
            )
        except ValueError as e:
            raise InvalidRequest(str(e))

        # Fetch repositories from source
        try:
            all_repos = adapter.list_repositories()
        except requests.exceptions.Timeout:
            raise InvalidRequest("Connection to source registry timed out")
        except requests.exceptions.SSLError as e:
            raise InvalidRequest(f"SSL error connecting to source registry: {e}")
        except requests.exceptions.ConnectionError as e:
            raise InvalidRequest(f"Failed to connect to source registry: {e}")
        except requests.exceptions.HTTPError as e:
            raise InvalidRequest(f"Source registry returned error: {e}")
        except requests.exceptions.RequestException as e:
            raise InvalidRequest(f"Failed to fetch repositories: {e}")

        # Apply glob filters
        filters = mirror.repository_filters
        if filters:
            all_repos = [
                r for r in all_repos if model.org_mirror.matches_repository_filter(r, filters)
            ]

        # Sync to database
        model.org_mirror.sync_discovered_repos(mirror, all_repos)

        logger.info(
            "Refreshed %d repositories from source registry for org %s",
            len(all_repos),
            mirror.organization.username,
        )

    def _dt_to_string(self, dt):
        """Convert DateTime to ISO 8601 formatted string."""
        if dt is None:
            return None
        return dt.isoformat() + "Z"
