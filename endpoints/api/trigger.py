"""
Create, list and manage build triggers.
"""

import logging
from urllib.parse import urlunparse

from flask import request, url_for

from app import app
from auth.permissions import (
    UserAdminPermission,
    AdministerOrganizationPermission,
    AdministerRepositoryPermission,
)
from buildtrigger.basehandler import BuildTriggerHandler
from buildtrigger.triggerutil import TriggerException, EmptyRepositoryException
from data import model
from data.fields import DecryptedValue
from data.model.build import update_build_trigger
from endpoints.api import (
    RepositoryParamResource,
    nickname,
    resource,
    require_repo_admin,
    log_action,
    request_error,
    query_param,
    parse_args,
    internal_only,
    validate_json_request,
    api,
    path_param,
    abort,
    disallow_for_app_repositories,
    disallow_for_non_normal_repositories,
)
from endpoints.api.build import build_status_view, trigger_view, RepositoryBuildStatus
from endpoints.api.trigger_analyzer import TriggerAnalyzer
from endpoints.building import (
    start_build,
    MaximumBuildsQueuedException,
    BuildTriggerDisabledException,
)
from endpoints.exception import NotFound, Unauthorized, InvalidRequest
from util.names import parse_robot_username

logger = logging.getLogger(__name__)


def _prepare_webhook_url(scheme, username, password, hostname, path):
    auth_hostname = "%s:%s@%s" % (username, password, hostname)
    return urlunparse((scheme, auth_hostname, path, "", "", ""))


def get_trigger(trigger_uuid):
    try:
        trigger = model.build.get_build_trigger(trigger_uuid)
    except model.InvalidBuildTriggerException:
        raise NotFound()
    return trigger


@resource("/v1/repository/<apirepopath:repository>/trigger/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class BuildTriggerList(RepositoryParamResource):
    """
    Resource for listing repository build triggers.
    """

    @require_repo_admin
    @disallow_for_app_repositories
    @nickname("listBuildTriggers")
    def get(self, namespace_name, repo_name):
        """
        List the triggers for the specified repository.
        """
        triggers = model.build.list_build_triggers(namespace_name, repo_name)
        return {"triggers": [trigger_view(trigger, can_admin=True) for trigger in triggers]}


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
class BuildTrigger(RepositoryParamResource):
    """
    Resource for managing specific build triggers.
    """

    schemas = {
        "UpdateTrigger": {
            "type": "object",
            "description": "Options for updating a build trigger",
            "required": [
                "enabled",
            ],
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Whether the build trigger is enabled",
                },
            },
        },
    }

    @require_repo_admin
    @disallow_for_app_repositories
    @nickname("getBuildTrigger")
    def get(self, namespace_name, repo_name, trigger_uuid):
        """
        Get information for the specified build trigger.
        """
        return trigger_view(get_trigger(trigger_uuid), can_admin=True)

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("updateBuildTrigger")
    @validate_json_request("UpdateTrigger")
    def put(self, namespace_name, repo_name, trigger_uuid):
        """
        Updates the specified build trigger.
        """
        trigger = get_trigger(trigger_uuid)

        handler = BuildTriggerHandler.get_handler(trigger)
        if not handler.is_active():
            raise InvalidRequest("Cannot update an unactivated trigger")

        enable = request.get_json()["enabled"]
        model.build.toggle_build_trigger(trigger, enable)
        log_action(
            "toggle_repo_trigger",
            namespace_name,
            {
                "repo": repo_name,
                "trigger_id": trigger_uuid,
                "service": trigger.service.name,
                "enabled": enable,
            },
            repo=model.repository.get_repository(namespace_name, repo_name),
        )

        return trigger_view(trigger)

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("deleteBuildTrigger")
    def delete(self, namespace_name, repo_name, trigger_uuid):
        """
        Delete the specified build trigger.
        """
        trigger = get_trigger(trigger_uuid)

        handler = BuildTriggerHandler.get_handler(trigger)
        if handler.is_active():
            try:
                handler.deactivate()
            except TriggerException as ex:
                # We are just going to eat this error
                logger.warning("Trigger deactivation problem: %s", ex)

            log_action(
                "delete_repo_trigger",
                namespace_name,
                {"repo": repo_name, "trigger_id": trigger_uuid, "service": trigger.service.name},
                repo=model.repository.get_repository(namespace_name, repo_name),
            )

        trigger.delete_instance(recursive=True)

        if trigger.write_token is not None:
            trigger.write_token.delete_instance()

        return "No Content", 204


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/subdir")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
@internal_only
class BuildTriggerSubdirs(RepositoryParamResource):
    """
    Custom verb for fetching the subdirs which are buildable for a trigger.
    """

    schemas = {
        "BuildTriggerSubdirRequest": {
            "type": "object",
            "description": "Arbitrary json.",
        },
    }

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("listBuildTriggerSubdirs")
    @validate_json_request("BuildTriggerSubdirRequest")
    def post(self, namespace_name, repo_name, trigger_uuid):
        """
        List the subdirectories available for the specified build trigger and source.
        """
        trigger = get_trigger(trigger_uuid)

        user_permission = UserAdminPermission(trigger.connected_user.username)
        if user_permission.can():
            new_config_dict = request.get_json()
            handler = BuildTriggerHandler.get_handler(trigger, new_config_dict)

            try:
                subdirs = handler.list_build_subdirs()
                context_map = {}
                for file in subdirs:
                    context_map = handler.get_parent_directory_mappings(file, context_map)

                return {
                    "dockerfile_paths": ["/" + subdir for subdir in subdirs],
                    "contextMap": context_map,
                    "status": "success",
                }
            except EmptyRepositoryException as exc:
                return {
                    "status": "success",
                    "contextMap": {},
                    "dockerfile_paths": [],
                }
            except TriggerException as exc:
                return {
                    "status": "error",
                    "message": str(exc),
                }
        else:
            raise Unauthorized()


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/activate")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
class BuildTriggerActivate(RepositoryParamResource):
    """
    Custom verb for activating a build trigger once all required information has been collected.
    """

    schemas = {
        "BuildTriggerActivateRequest": {
            "type": "object",
            "required": ["config"],
            "properties": {
                "config": {
                    "type": "object",
                    "description": "Arbitrary json.",
                },
                "pull_robot": {
                    "type": "string",
                    "description": "The name of the robot that will be used to pull images.",
                },
            },
        },
    }

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("activateBuildTrigger")
    @validate_json_request("BuildTriggerActivateRequest")
    def post(self, namespace_name, repo_name, trigger_uuid):
        """
        Activate the specified build trigger.
        """
        trigger = get_trigger(trigger_uuid)
        handler = BuildTriggerHandler.get_handler(trigger)
        if handler.is_active():
            raise InvalidRequest("Trigger config is not sufficient for activation.")

        user_permission = UserAdminPermission(trigger.connected_user.username)
        if user_permission.can():
            # Update the pull robot (if any).
            pull_robot_name = request.get_json().get("pull_robot", None)
            if pull_robot_name:
                try:
                    pull_robot = model.user.lookup_robot(pull_robot_name)
                except model.InvalidRobotException:
                    raise NotFound()

                # Make sure the user has administer permissions for the robot's namespace.
                (robot_namespace, _) = parse_robot_username(pull_robot_name)
                if not AdministerOrganizationPermission(robot_namespace).can():
                    raise Unauthorized()

                # Make sure the namespace matches that of the trigger.
                if robot_namespace != namespace_name:
                    raise Unauthorized()

                # Set the pull robot.
                trigger.pull_robot = pull_robot

            # Update the config.
            new_config_dict = request.get_json()["config"]

            write_token_name = "Build Trigger: %s" % trigger.service.name
            write_token = model.token.create_delegate_token(
                namespace_name, repo_name, write_token_name, "write"
            )

            try:
                path = url_for("webhooks.build_trigger_webhook", trigger_uuid=trigger.uuid)
                authed_url = _prepare_webhook_url(
                    app.config["PREFERRED_URL_SCHEME"],
                    "$token",
                    write_token.get_code(),
                    app.config["SERVER_HOSTNAME"],
                    path,
                )

                handler = BuildTriggerHandler.get_handler(trigger, new_config_dict)
                final_config, private_config = handler.activate(authed_url)

                if "private_key" in private_config:
                    trigger.secure_private_key = DecryptedValue(private_config["private_key"])

            except TriggerException as exc:
                write_token.delete_instance()
                raise request_error(message=str(exc))

            # Save the updated config.
            update_build_trigger(trigger, final_config, write_token=write_token)

            # Log the trigger setup.
            repo = model.repository.get_repository(namespace_name, repo_name)
            log_action(
                "setup_repo_trigger",
                namespace_name,
                {
                    "repo": repo_name,
                    "namespace": namespace_name,
                    "trigger_id": trigger.uuid,
                    "service": trigger.service.name,
                    "pull_robot": trigger.pull_robot.username if trigger.pull_robot else None,
                    "config": final_config,
                },
                repo=repo,
            )

            return trigger_view(trigger, can_admin=True)
        else:
            raise Unauthorized()


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/analyze")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
@internal_only
class BuildTriggerAnalyze(RepositoryParamResource):
    """
    Custom verb for analyzing the config for a build trigger and suggesting various changes (such as
    a robot account to use for pulling)
    """

    schemas = {
        "BuildTriggerAnalyzeRequest": {
            "type": "object",
            "required": ["config"],
            "properties": {
                "config": {
                    "type": "object",
                    "description": "Arbitrary json.",
                }
            },
        },
    }

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("analyzeBuildTrigger")
    @validate_json_request("BuildTriggerAnalyzeRequest")
    def post(self, namespace_name, repo_name, trigger_uuid):
        """
        Analyze the specified build trigger configuration.
        """
        trigger = get_trigger(trigger_uuid)

        if trigger.repository.namespace_user.username != namespace_name:
            raise NotFound()

        if trigger.repository.name != repo_name:
            raise NotFound()

        new_config_dict = request.get_json()["config"]
        handler = BuildTriggerHandler.get_handler(trigger, new_config_dict)
        server_hostname = app.config["SERVER_HOSTNAME"]
        try:
            trigger_analyzer = TriggerAnalyzer(
                handler,
                namespace_name,
                server_hostname,
                new_config_dict,
                AdministerOrganizationPermission(namespace_name).can(),
            )
            return trigger_analyzer.analyze_trigger()
        except TriggerException as rre:
            return {
                "status": "error",
                "message": "Could not analyze the repository: %s" % rre,
            }
        except NotImplementedError:
            return {
                "status": "notimplemented",
            }


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/start")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
class ActivateBuildTrigger(RepositoryParamResource):
    """
    Custom verb to manually activate a build trigger.
    """

    schemas = {
        "RunParameters": {
            "type": "object",
            "description": "Optional run parameters for activating the build trigger",
            "properties": {
                "branch_name": {
                    "type": "string",
                    "description": "(SCM only) If specified, the name of the branch to build.",
                },
                "commit_sha": {
                    "type": "string",
                    "description": "(Custom Only) If specified, the ref/SHA1 used to checkout a git repository.",
                },
                "refs": {
                    "type": ["object", "null"],
                    "description": "(SCM Only) If specified, the ref to build.",
                },
            },
            "additionalProperties": False,
        }
    }

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("manuallyStartBuildTrigger")
    @validate_json_request("RunParameters")
    def post(self, namespace_name, repo_name, trigger_uuid):
        """
        Manually start a build from the specified trigger.
        """
        trigger = get_trigger(trigger_uuid)
        if not trigger.enabled:
            raise InvalidRequest("Trigger is not enabled.")

        handler = BuildTriggerHandler.get_handler(trigger)
        if not handler.is_active():
            raise InvalidRequest("Trigger is not active.")

        try:
            repo = model.repository.get_repository(namespace_name, repo_name)
            pull_robot_name = model.build.get_pull_robot_name(trigger)

            run_parameters = request.get_json()
            prepared = handler.manual_start(run_parameters=run_parameters)
            build_request = start_build(repo, prepared, pull_robot_name=pull_robot_name)
        except TriggerException as tse:
            raise InvalidRequest(str(tse)) from tse
        except MaximumBuildsQueuedException:
            abort(429, message="Maximum queued build rate exceeded.")
        except BuildTriggerDisabledException:
            abort(400, message="Build trigger is disabled")

        resp = build_status_view(build_request)
        repo_string = "%s/%s" % (namespace_name, repo_name)
        headers = {
            "Location": api.url_for(
                RepositoryBuildStatus, repository=repo_string, build_uuid=build_request.uuid
            ),
        }
        return resp, 201, headers


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/builds")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
class TriggerBuildList(RepositoryParamResource):
    """
    Resource to represent builds that were activated from the specified trigger.
    """

    @require_repo_admin
    @disallow_for_app_repositories
    @parse_args()
    @query_param("limit", "The maximum number of builds to return", type=int, default=5)
    @nickname("listTriggerRecentBuilds")
    def get(self, namespace_name, repo_name, trigger_uuid, parsed_args):
        """
        List the builds started by the specified trigger.
        """
        limit = parsed_args["limit"]
        builds = model.build.list_trigger_builds(namespace_name, repo_name, trigger_uuid, limit)
        return {"builds": [build_status_view(bld) for bld in builds]}


FIELD_VALUE_LIMIT = 30


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/fields/<field_name>")
@internal_only
class BuildTriggerFieldValues(RepositoryParamResource):
    """
    Custom verb to fetch a values list for a particular field name.
    """

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("listTriggerFieldValues")
    def post(self, namespace_name, repo_name, trigger_uuid, field_name):
        """
        List the field values for a custom run field.
        """
        trigger = get_trigger(trigger_uuid)

        config = request.get_json() or None
        if AdministerRepositoryPermission(namespace_name, repo_name).can():
            handler = BuildTriggerHandler.get_handler(trigger, config)
            values = handler.list_field_values(field_name, limit=FIELD_VALUE_LIMIT)

            if values is None:
                raise NotFound()

            return {"values": values}
        else:
            raise Unauthorized()


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/sources")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
@internal_only
class BuildTriggerSources(RepositoryParamResource):
    """
    Custom verb to fetch the list of build sources for the trigger config.
    """

    schemas = {
        "BuildTriggerSourcesRequest": {
            "type": "object",
            "description": "Specifies the namespace under which to fetch sources",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "The namespace for which to fetch sources",
                },
            },
        }
    }

    @require_repo_admin
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("listTriggerBuildSources")
    @validate_json_request("BuildTriggerSourcesRequest")
    def post(self, namespace_name, repo_name, trigger_uuid):
        """
        List the build sources for the trigger configuration thus far.
        """
        namespace = request.get_json().get("namespace")
        if namespace is None:
            raise InvalidRequest()

        trigger = get_trigger(trigger_uuid)

        user_permission = UserAdminPermission(trigger.connected_user.username)
        if user_permission.can():
            handler = BuildTriggerHandler.get_handler(trigger)

            try:
                return {"sources": handler.list_build_sources_for_namespace(namespace)}
            except TriggerException as rre:
                raise InvalidRequest(str(rre)) from rre
        else:
            raise Unauthorized()


@resource("/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/namespaces")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("trigger_uuid", "The UUID of the build trigger")
@internal_only
class BuildTriggerSourceNamespaces(RepositoryParamResource):
    """
    Custom verb to fetch the list of namespaces (orgs, projects, etc) for the trigger config.
    """

    @require_repo_admin
    @disallow_for_app_repositories
    @nickname("listTriggerBuildSourceNamespaces")
    def get(self, namespace_name, repo_name, trigger_uuid):
        """
        List the build sources for the trigger configuration thus far.
        """
        trigger = get_trigger(trigger_uuid)

        user_permission = UserAdminPermission(trigger.connected_user.username)
        if user_permission.can():
            handler = BuildTriggerHandler.get_handler(trigger)

            try:
                return {"namespaces": handler.list_build_source_namespaces()}
            except TriggerException as rre:
                raise InvalidRequest(str(rre)) from rre
        else:
            raise Unauthorized()
