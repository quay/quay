# -*- coding: utf-8 -*-
import logging

from email.utils import parsedate_tz, mktime_tz
from datetime import datetime

from jsonschema import ValidationError
from flask import request

import features

from auth.auth_context import get_authenticated_user
from data import model
from data.database import RepoMirrorRuleType
from data.encryption import DecryptionFailureException
from endpoints.api import (
    RepositoryParamResource,
    nickname,
    path_param,
    require_repo_admin,
    resource,
    validate_json_request,
    define_json_response,
    show_if,
    format_date,
)
from endpoints.exception import NotFound
from util.audit import track_and_log, wrap_repository
from util.names import parse_robot_username


common_properties = {
    "is_enabled": {
        "type": "boolean",
        "description": "Used to enable or disable synchronizations.",
    },
    "external_reference": {"type": "string", "description": "Location of the external repository."},
    "external_registry_username": {
        "type": ["string", "null"],
        "description": "Username used to authenticate with external registry.",
    },
    "external_registry_password": {
        "type": ["string", "null"],
        "description": "Password used to authenticate with external registry.",
    },
    "sync_start_date": {
        "type": "string",
        "description": "Determines the next time this repository is ready for synchronization.",
    },
    "sync_interval": {
        "type": "integer",
        "minimum": 0,
        "description": "Number of seconds after next_start_date to begin synchronizing.",
    },
    "robot_username": {
        "type": "string",
        "description": "Username of robot which will be used for image pushes.",
    },
    "root_rule": {
        "type": "object",
        "description": "Tag mirror rule",
        "required": ["rule_kind", "rule_value"],
        "properties": {
            "rule_kind": {
                "type": "string",
                "description": "The kind of rule type",
                "enum": ["tag_glob_csv"],
            },
            "rule_value": {
                "type": "array",
                "description": "Array of tag patterns",
                "items": {"type": "string"},
            },
        },
        "description": "A list of glob-patterns used to determine which tags should be synchronized.",
    },
    "external_registry_config": {
        "type": "object",
        "properties": {
            "verify_tls": {
                "type": "boolean",
                "description": (
                    "Determines whether HTTPs is required and the certificate is verified when "
                    "communicating with the external repository."
                ),
            },
            "proxy": {
                "type": "object",
                "description": "Proxy configuration for use during synchronization.",
                "properties": {
                    "https_proxy": {
                        "type": ["string", "null"],
                        "description": "Value for HTTPS_PROXY environment variable during sync.",
                    },
                    "http_proxy": {
                        "type": ["string", "null"],
                        "description": "Value for HTTP_PROXY environment variable during sync.",
                    },
                    "no_proxy": {
                        "type": ["string", "null"],
                        "description": "Value for NO_PROXY environment variable during sync.",
                    },
                },
            },
        },
    },
}


@resource("/v1/repository/<apirepopath:repository>/mirror/sync-now")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@show_if(features.REPO_MIRROR)
class RepoMirrorSyncNowResource(RepositoryParamResource):
    """
    A resource for managing RepoMirrorConfig.sync_status.
    """

    @require_repo_admin
    @nickname("syncNow")
    def post(self, namespace_name, repository_name):
        """
        Update the sync_status for a given Repository's mirroring configuration.
        """
        repo = model.repository.get_repository(namespace_name, repository_name)
        if not repo:
            raise NotFound()

        mirror = model.repo_mirror.get_mirror(repository=repo)
        if not mirror:
            raise NotFound()

        if mirror and model.repo_mirror.update_sync_status_to_sync_now(mirror):
            track_and_log(
                "repo_mirror_config_changed",
                wrap_repository(repo),
                changed="sync_status",
                to="SYNC_NOW",
            )
            return "", 204

        raise NotFound()


@resource("/v1/repository/<apirepopath:repository>/mirror/sync-cancel")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@show_if(features.REPO_MIRROR)
class RepoMirrorSyncCancelResource(RepositoryParamResource):
    """
    A resource for managing RepoMirrorConfig.sync_status.
    """

    @require_repo_admin
    @nickname("syncCancel")
    def post(self, namespace_name, repository_name):
        """
        Update the sync_status for a given Repository's mirroring configuration.
        """
        repo = model.repository.get_repository(namespace_name, repository_name)
        if not repo:
            raise NotFound()

        mirror = model.repo_mirror.get_mirror(repository=repo)
        if not mirror:
            raise NotFound()

        if mirror and model.repo_mirror.update_sync_status_to_cancel(mirror):
            track_and_log(
                "repo_mirror_config_changed",
                wrap_repository(repo),
                changed="sync_status",
                to="SYNC_CANCEL",
            )
            return "", 204

        raise NotFound()


@resource("/v1/repository/<apirepopath:repository>/mirror")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@show_if(features.REPO_MIRROR)
class RepoMirrorResource(RepositoryParamResource):
    """
    Resource for managing repository mirroring.
    """

    schemas = {
        "CreateMirrorConfig": {
            "description": "Create the repository mirroring configuration.",
            "type": "object",
            "required": ["external_reference", "sync_interval", "sync_start_date", "root_rule"],
            "properties": common_properties,
        },
        "UpdateMirrorConfig": {
            "description": "Update the repository mirroring configuration.",
            "type": "object",
            "properties": common_properties,
        },
        "ViewMirrorConfig": {
            "description": "View the repository mirroring configuration.",
            "type": "object",
            "required": [
                "is_enabled",
                "mirror_type",
                "external_reference",
                "external_registry_username",
                "external_registry_config",
                "sync_interval",
                "sync_start_date",
                "sync_expiration_date",
                "sync_retries_remaining",
                "sync_status",
                "root_rule",
                "robot_username",
            ],
            "properties": common_properties,
        },
    }

    @require_repo_admin
    @define_json_response("ViewMirrorConfig")
    @nickname("getRepoMirrorConfig")
    def get(self, namespace_name, repository_name):
        """
        Return the Mirror configuration for a given Repository.
        """
        repo = model.repository.get_repository(namespace_name, repository_name)
        if not repo:
            raise NotFound()

        mirror = model.repo_mirror.get_mirror(repo)
        if not mirror:
            raise NotFound()

        try:
            username = self._decrypt_username(mirror.external_registry_username)
        except DecryptionFailureException as dfe:
            logger.warning(
                "Failed to decrypt username for repository %s/%s: %s",
                namespace_name,
                repository_name,
                dfe,
            )
            username = "(invalid. please re-enter)"

        # Transformations
        rules = mirror.root_rule.rule_value
        sync_start_date = self._dt_to_string(mirror.sync_start_date)
        sync_expiration_date = self._dt_to_string(mirror.sync_expiration_date)
        robot = mirror.internal_robot.username if mirror.internal_robot is not None else None

        return {
            "is_enabled": mirror.is_enabled,
            "mirror_type": mirror.mirror_type.name,
            "external_reference": mirror.external_reference,
            "external_registry_username": username,
            "external_registry_config": mirror.external_registry_config or {},
            "sync_interval": mirror.sync_interval,
            "sync_start_date": sync_start_date,
            "sync_expiration_date": sync_expiration_date,
            "sync_retries_remaining": mirror.sync_retries_remaining,
            "sync_status": mirror.sync_status.name,
            "root_rule": {"rule_kind": "tag_glob_csv", "rule_value": rules},
            "robot_username": robot,
        }

    @require_repo_admin
    @nickname("createRepoMirrorConfig")
    @validate_json_request("CreateMirrorConfig")
    def post(self, namespace_name, repository_name):
        """
        Create a RepoMirrorConfig for a given Repository.
        """
        # TODO: Tidy up this function
        # TODO: Specify only the data we want to pass on when creating the RepoMirrorConfig. Avoid
        #       the possibility of data injection.

        repo = model.repository.get_repository(namespace_name, repository_name)
        if not repo:
            raise NotFound()

        if model.repo_mirror.get_mirror(repo):
            return (
                {
                    "detail": "Mirror configuration already exits for repository %s/%s"
                    % (namespace_name, repository_name)
                },
                409,
            )

        data = request.get_json()

        data["sync_start_date"] = self._string_to_dt(data["sync_start_date"])

        rule = model.repo_mirror.create_rule(repo, data["root_rule"]["rule_value"])
        del data["root_rule"]

        # Verify the robot is part of the Repository's namespace
        robot = self._setup_robot_for_mirroring(
            namespace_name, repository_name, data["robot_username"]
        )
        del data["robot_username"]

        mirror = model.repo_mirror.enable_mirroring_for_repository(
            repo, root_rule=rule, internal_robot=robot, **data
        )
        if mirror:
            track_and_log(
                "repo_mirror_config_changed",
                wrap_repository(repo),
                changed="external_reference",
                to=data["external_reference"],
            )
            return "", 201
        else:
            # TODO: Determine appropriate Response
            return {"detail": "RepoMirrorConfig already exists for this repository."}, 409

    @require_repo_admin
    @validate_json_request("UpdateMirrorConfig")
    @nickname("changeRepoMirrorConfig")
    def put(self, namespace_name, repository_name):
        """
        Allow users to modifying the repository's mirroring configuration.
        """
        values = request.get_json()

        repo = model.repository.get_repository(namespace_name, repository_name)
        if not repo:
            raise NotFound()

        mirror = model.repo_mirror.get_mirror(repo)
        if not mirror:
            raise NotFound()

        if "is_enabled" in values:
            if values["is_enabled"] == True:
                if model.repo_mirror.enable_mirror(repo):
                    track_and_log(
                        "repo_mirror_config_changed",
                        wrap_repository(repo),
                        changed="is_enabled",
                        to=True,
                    )
            if values["is_enabled"] == False:
                if model.repo_mirror.disable_mirror(repo):
                    track_and_log(
                        "repo_mirror_config_changed",
                        wrap_repository(repo),
                        changed="is_enabled",
                        to=False,
                    )

        if "external_reference" in values:
            if values["external_reference"] == "":
                return {"detail": "Empty string is an invalid repository location."}, 400
            if model.repo_mirror.change_remote(repo, values["external_reference"]):
                track_and_log(
                    "repo_mirror_config_changed",
                    wrap_repository(repo),
                    changed="external_reference",
                    to=values["external_reference"],
                )

        if "robot_username" in values:
            robot_username = values["robot_username"]
            robot = self._setup_robot_for_mirroring(namespace_name, repository_name, robot_username)
            if model.repo_mirror.set_mirroring_robot(repo, robot):
                track_and_log(
                    "repo_mirror_config_changed",
                    wrap_repository(repo),
                    changed="robot_username",
                    to=robot_username,
                )

        if "sync_start_date" in values:
            try:
                sync_start_date = self._string_to_dt(values["sync_start_date"])
            except ValueError as e:
                return {"detail": "Incorrect DateTime format for sync_start_date."}, 400
            if model.repo_mirror.change_sync_start_date(repo, sync_start_date):
                track_and_log(
                    "repo_mirror_config_changed",
                    wrap_repository(repo),
                    changed="sync_start_date",
                    to=sync_start_date,
                )

        if "sync_interval" in values:
            if model.repo_mirror.change_sync_interval(repo, values["sync_interval"]):
                track_and_log(
                    "repo_mirror_config_changed",
                    wrap_repository(repo),
                    changed="sync_interval",
                    to=values["sync_interval"],
                )

        if "external_registry_username" in values and "external_registry_password" in values:
            username = values["external_registry_username"]
            password = values["external_registry_password"]
            if username is None and password is not None:
                return {"detail": "Unable to delete username while setting a password."}, 400
            if model.repo_mirror.change_credentials(repo, username, password):
                track_and_log(
                    "repo_mirror_config_changed",
                    wrap_repository(repo),
                    changed="external_registry_username",
                    to=username,
                )
                if password is None:
                    track_and_log(
                        "repo_mirror_config_changed",
                        wrap_repository(repo),
                        changed="external_registry_password",
                        to=None,
                    )
                else:
                    track_and_log(
                        "repo_mirror_config_changed",
                        wrap_repository(repo),
                        changed="external_registry_password",
                        to="********",
                    )

        elif "external_registry_username" in values:
            username = values["external_registry_username"]
            if model.repo_mirror.change_username(repo, username):
                track_and_log(
                    "repo_mirror_config_changed",
                    wrap_repository(repo),
                    changed="external_registry_username",
                    to=username,
                )

        # Do not allow specifying a password without setting a username
        if "external_registry_password" in values and "external_registry_username" not in values:
            return (
                {"detail": "Unable to set a new password without also specifying a username."},
                400,
            )

        if "external_registry_config" in values:
            external_registry_config = values.get("external_registry_config", {})

            if "verify_tls" in external_registry_config:
                updates = {"verify_tls": external_registry_config["verify_tls"]}
                if model.repo_mirror.change_external_registry_config(repo, updates):
                    track_and_log(
                        "repo_mirror_config_changed",
                        wrap_repository(repo),
                        changed="verify_tls",
                        to=external_registry_config["verify_tls"],
                    )

            if "proxy" in external_registry_config:
                proxy_values = external_registry_config.get("proxy", {})

                if "http_proxy" in proxy_values:
                    updates = {"proxy": {"http_proxy": proxy_values["http_proxy"]}}
                    if model.repo_mirror.change_external_registry_config(repo, updates):
                        track_and_log(
                            "repo_mirror_config_changed",
                            wrap_repository(repo),
                            changed="http_proxy",
                            to=proxy_values["http_proxy"],
                        )

                if "https_proxy" in proxy_values:
                    updates = {"proxy": {"https_proxy": proxy_values["https_proxy"]}}
                    if model.repo_mirror.change_external_registry_config(repo, updates):
                        track_and_log(
                            "repo_mirror_config_changed",
                            wrap_repository(repo),
                            changed="https_proxy",
                            to=proxy_values["https_proxy"],
                        )

                if "no_proxy" in proxy_values:
                    updates = {"proxy": {"no_proxy": proxy_values["no_proxy"]}}
                    if model.repo_mirror.change_external_registry_config(repo, updates):
                        track_and_log(
                            "repo_mirror_config_changed",
                            wrap_repository(repo),
                            changed="no_proxy",
                            to=proxy_values["no_proxy"],
                        )

        if "root_rule" in values:

            if values["root_rule"]["rule_kind"] != "tag_glob_csv":
                raise ValidationError('validation failed: rule_kind must be "tag_glob_csv"')

            if model.repo_mirror.change_rule(
                repo, RepoMirrorRuleType.TAG_GLOB_CSV, values["root_rule"]["rule_value"]
            ):
                track_and_log(
                    "repo_mirror_config_changed",
                    wrap_repository(repo),
                    changed="mirror_rule",
                    to=values["root_rule"]["rule_value"],
                )

        return "", 201

    def _setup_robot_for_mirroring(self, namespace_name, repo_name, robot_username):
        """
        Validate robot exists and give write permissions.
        """
        robot = model.user.lookup_robot(robot_username)
        assert robot.robot

        namespace, _ = parse_robot_username(robot_username)
        if namespace != namespace_name:
            raise model.DataModelException("Invalid robot")

        # Ensure the robot specified has access to the repository. If not, grant it.
        permissions = model.permission.get_user_repository_permissions(
            robot, namespace_name, repo_name
        )
        if not permissions or permissions[0].role.name == "read":
            model.permission.set_user_repo_permission(
                robot.username, namespace_name, repo_name, "write"
            )

        return robot

    def _string_to_dt(self, string):
        """
        Convert String to correct DateTime format.
        """
        if string is None:
            return None

        """
    # TODO: Use RFC2822. This doesn't work consistently.
    # TODO: Move this to same module as `format_date` once fixed.
    tup = parsedate_tz(string)
    if len(tup) == 8:
      tup = tup + (0,)  # If TimeZone is omitted, assume UTC
    ts = mktime_tz(tup)
    dt = datetime.fromtimestamp(ts, pytz.UTC)
    return dt
    """
        assert isinstance(string, str)
        dt = datetime.strptime(string, "%Y-%m-%dT%H:%M:%SZ")
        return dt

    def _dt_to_string(self, dt):
        """
        Convert DateTime to correctly formatted String.
        """
        if dt is None:
            return None

        """
    # TODO: Use RFC2822. Need to make it work bi-directionally.
    return format_date(dt)
    """

        assert isinstance(dt, datetime)
        string = dt.isoformat() + "Z"
        return string

    def _decrypt_username(self, username):
        if username is None:
            return None
        return username.decrypt()
