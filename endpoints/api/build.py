"""
Create, list, cancel and get status/logs of repository builds.
"""
import datetime
import hashlib
import json
import logging
import os

from flask import request
from urllib.parse import urlparse

import features

from app import userfiles as user_files, build_logs, log_archive, dockerfile_build_queue
from auth.permissions import (
    ReadRepositoryPermission,
    ModifyRepositoryPermission,
    AdministerRepositoryPermission,
    AdministerOrganizationPermission,
    SuperUserPermission,
)
from buildtrigger.basehandler import BuildTriggerHandler
from data import database
from data import model
from data.buildlogs import BuildStatusRetrievalError
from endpoints.api import (
    RepositoryParamResource,
    parse_args,
    query_param,
    nickname,
    resource,
    require_repo_read,
    require_repo_write,
    validate_json_request,
    ApiResource,
    internal_only,
    format_date,
    api,
    path_param,
    require_repo_admin,
    abort,
    disallow_for_app_repositories,
    disallow_for_non_normal_repositories,
)
from endpoints.building import (
    start_build,
    PreparedBuild,
    MaximumBuildsQueuedException,
    BuildTriggerDisabledException,
)
from endpoints.exception import Unauthorized, NotFound, InvalidRequest
from util.names import parse_robot_username
from util.request import get_request_ip

logger = logging.getLogger(__name__)


def get_trigger_config(trigger):
    try:
        return json.loads(trigger.config)
    except:
        return {}


def get_job_config(build_obj):
    try:
        return json.loads(build_obj.job_config)
    except:
        return {}


def user_view(user):
    return {
        "name": user.username,
        "kind": "user",
        "is_robot": user.robot,
    }


def trigger_view(trigger, can_read=False, can_admin=False, for_build=False):
    if trigger and trigger.uuid:
        build_trigger = BuildTriggerHandler.get_handler(trigger)
        build_source = build_trigger.config.get("build_source")

        repo_url = build_trigger.get_repository_url() if build_source else None
        can_read = can_read or can_admin

        trigger_data = {
            "id": trigger.uuid,
            "service": trigger.service.name,
            "is_active": build_trigger.is_active(),
            "build_source": build_source if can_read else None,
            "repository_url": repo_url if can_read else None,
            "config": build_trigger.config if can_admin else {},
            "can_invoke": can_admin,
            "enabled": trigger.enabled,
            "disabled_reason": trigger.disabled_reason.name if trigger.disabled_reason else None,
        }

        if not for_build and can_admin and trigger.pull_robot:
            trigger_data["pull_robot"] = user_view(trigger.pull_robot)

        return trigger_data

    return None


def _get_build_status(build_obj):
    """
    Returns the updated build phase, status and (if any) error for the build object.
    """
    phase = build_obj.phase
    status = {}
    error = None

    # If the build is currently running, then load its "real-time" status from Redis.
    if not database.BUILD_PHASE.is_terminal_phase(phase):
        try:
            status = build_logs.get_status(build_obj.uuid)
        except BuildStatusRetrievalError as bsre:
            phase = "cannot_load"
            if SuperUserPermission().can():
                error = str(bsre)
            else:
                error = "Redis may be down. Please contact support."

        if phase != "cannot_load":
            # If the status contains a heartbeat, then check to see if has been written in the last few
            # minutes. If not, then the build timed out.
            if status is not None and "heartbeat" in status and status["heartbeat"]:
                heartbeat = datetime.datetime.utcfromtimestamp(status["heartbeat"])
                if datetime.datetime.utcnow() - heartbeat > datetime.timedelta(minutes=1):
                    phase = database.BUILD_PHASE.INTERNAL_ERROR

    # If the phase is internal error, return 'expired' instead if the number of retries
    # on the queue item is 0.
    if phase == database.BUILD_PHASE.INTERNAL_ERROR:
        retry = build_obj.queue_id and dockerfile_build_queue.has_retries_remaining(
            build_obj.queue_id
        )
        if not retry:
            phase = "expired"

    return (phase, status, error)


def build_status_view(build_obj):
    phase, status, error = _get_build_status(build_obj)
    repo_namespace = build_obj.repository.namespace_user.username
    repo_name = build_obj.repository.name

    can_read = ReadRepositoryPermission(repo_namespace, repo_name).can()
    can_write = ModifyRepositoryPermission(repo_namespace, repo_name).can()
    can_admin = AdministerRepositoryPermission(repo_namespace, repo_name).can()

    job_config = get_job_config(build_obj)

    resp = {
        "id": build_obj.uuid,
        "phase": phase,
        "started": format_date(build_obj.started),
        "display_name": build_obj.display_name,
        "status": status or {},
        "subdirectory": job_config.get("build_subdir", ""),
        "dockerfile_path": job_config.get("build_subdir", ""),
        "context": job_config.get("context", ""),
        "tags": job_config.get("docker_tags", []),
        "manual_user": job_config.get("manual_user", None),
        "is_writer": can_write,
        "trigger": trigger_view(build_obj.trigger, can_read, can_admin, for_build=True),
        "trigger_metadata": job_config.get("trigger_metadata", None) if can_read else None,
        "resource_key": build_obj.resource_key,
        "pull_robot": user_view(build_obj.pull_robot) if build_obj.pull_robot else None,
        "repository": {"namespace": repo_namespace, "name": repo_name},
        "error": error,
    }

    if can_write or features.READER_BUILD_LOGS:
        if build_obj.resource_key is not None:
            resp["archive_url"] = user_files.get_file_url(
                build_obj.resource_key, get_request_ip(), requires_cors=True
            )
        elif job_config.get("archive_url", None):
            resp["archive_url"] = job_config["archive_url"]

    return resp


@resource("/v1/repository/<apirepopath:repository>/build/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryBuildList(RepositoryParamResource):
    """
    Resource related to creating and listing repository builds.
    """

    schemas = {
        "RepositoryBuildRequest": {
            "type": "object",
            "description": "Description of a new repository build.",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The file id that was generated when the build spec was uploaded",
                },
                "archive_url": {
                    "type": "string",
                    "description": 'The URL of the .tar.gz to build. Must start with "http" or "https".',
                },
                "subdirectory": {
                    "type": "string",
                    "description": "Subdirectory in which the Dockerfile can be found. You can only specify this or dockerfile_path",
                },
                "dockerfile_path": {
                    "type": "string",
                    "description": "Path to a dockerfile. You can only specify this or subdirectory.",
                },
                "context": {
                    "type": "string",
                    "description": "Pass in the context for the dockerfile. This is optional.",
                },
                "pull_robot": {
                    "type": "string",
                    "description": "Username of a Quay robot account to use as pull credentials",
                },
                "docker_tags": {
                    "type": "array",
                    "description": "The tags to which the built images will be pushed. "
                    + 'If none specified, "latest" is used.',
                    "items": {"type": "string"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
            },
        },
    }

    @require_repo_read
    @parse_args()
    @query_param("limit", "The maximum number of builds to return", type=int, default=5)
    @query_param(
        "since", "Returns all builds since the given unix timecode", type=int, default=None
    )
    @nickname("getRepoBuilds")
    @disallow_for_app_repositories
    def get(self, namespace, repository, parsed_args):
        """
        Get the list of repository builds.
        """
        limit = parsed_args.get("limit", 5)
        since = parsed_args.get("since", None)

        if since is not None:
            since = datetime.datetime.utcfromtimestamp(since)

        builds = model.build.list_repository_builds(namespace, repository, limit, since=since)
        return {"builds": [build_status_view(build) for build in builds]}

    @require_repo_write
    @nickname("requestRepoBuild")
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @validate_json_request("RepositoryBuildRequest")
    def post(self, namespace, repository):
        """
        Request that a repository be built and pushed from the specified input.
        """
        logger.debug("User requested repository initialization.")
        request_json = request.get_json()

        dockerfile_id = request_json.get("file_id", None)
        archive_url = request_json.get("archive_url", None)

        if not dockerfile_id and not archive_url:
            raise InvalidRequest("file_id or archive_url required")

        if archive_url:
            archive_match = None
            try:
                archive_match = urlparse(archive_url)
            except ValueError:
                pass

            if not archive_match:
                raise InvalidRequest("Invalid Archive URL: Must be a valid URI")

            scheme = archive_match.scheme
            if scheme != "http" and scheme != "https":
                raise InvalidRequest("Invalid Archive URL: Must be http or https")

        context, subdir = self.get_dockerfile_context(request_json)
        tags = request_json.get("docker_tags", ["latest"])
        pull_robot_name = request_json.get("pull_robot", None)

        # Verify the security behind the pull robot.
        if pull_robot_name:
            result = parse_robot_username(pull_robot_name)
            if result:
                try:
                    model.user.lookup_robot(pull_robot_name)
                except model.InvalidRobotException:
                    raise NotFound()

                # Make sure the user has administer permissions for the robot's namespace.
                (robot_namespace, _) = result
                if not AdministerOrganizationPermission(robot_namespace).can():
                    raise Unauthorized()
            else:
                raise Unauthorized()

        # Check if the dockerfile resource has already been used. If so, then it
        # can only be reused if the user has access to the repository in which the
        # dockerfile was previously built.
        if dockerfile_id:
            associated_repository = model.build.get_repository_for_resource(dockerfile_id)
            if associated_repository:
                if not ModifyRepositoryPermission(
                    associated_repository.namespace_user.username, associated_repository.name
                ):
                    raise Unauthorized()

        # Start the build.
        repo = model.repository.get_repository(namespace, repository)
        if repo is None:
            raise NotFound()

        try:
            build_name = (
                user_files.get_file_checksum(dockerfile_id)
                if dockerfile_id
                else hashlib.sha224(archive_url.encode("ascii")).hexdigest()[0:7]
            )
        except IOError:
            raise InvalidRequest("File %s could not be found or is invalid" % dockerfile_id)

        prepared = PreparedBuild()
        prepared.build_name = build_name
        prepared.dockerfile_id = dockerfile_id
        prepared.archive_url = archive_url
        prepared.tags = tags
        prepared.subdirectory = subdir
        prepared.context = context
        prepared.is_manual = True
        prepared.metadata = {}
        try:
            build_request = start_build(repo, prepared, pull_robot_name=pull_robot_name)
        except MaximumBuildsQueuedException:
            abort(429, message="Maximum queued build rate exceeded.")
        except BuildTriggerDisabledException:
            abort(400, message="Build trigger is disabled")

        resp = build_status_view(build_request)
        repo_string = "%s/%s" % (namespace, repository)
        headers = {
            "Location": api.url_for(
                RepositoryBuildStatus, repository=repo_string, build_uuid=build_request.uuid
            ),
        }
        return resp, 201, headers

    @staticmethod
    def get_dockerfile_context(request_json):
        context = request_json["context"] if "context" in request_json else os.path.sep
        if "dockerfile_path" in request_json:
            subdir = request_json["dockerfile_path"]
            if "context" not in request_json:
                context = os.path.dirname(subdir)
            return context, subdir

        if "subdirectory" in request_json:
            subdir = request_json["subdirectory"]
            context = subdir
            if not subdir.endswith(os.path.sep):
                subdir += os.path.sep

            subdir += "Dockerfile"
        else:
            if context.endswith(os.path.sep):
                subdir = context + "Dockerfile"
            else:
                subdir = context + os.path.sep + "Dockerfile"

        return context, subdir


@resource("/v1/repository/<apirepopath:repository>/build/<build_uuid>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("build_uuid", "The UUID of the build")
class RepositoryBuildResource(RepositoryParamResource):
    """
    Resource for dealing with repository builds.
    """

    @require_repo_read
    @nickname("getRepoBuild")
    @disallow_for_app_repositories
    def get(self, namespace, repository, build_uuid):
        """
        Returns information about a build.
        """
        try:
            build = model.build.get_repository_build(build_uuid)
        except model.build.InvalidRepositoryBuildException:
            raise NotFound()

        if (
            build.repository.name != repository
            or build.repository.namespace_user.username != namespace
        ):
            raise NotFound()

        return build_status_view(build)

    @require_repo_admin
    @nickname("cancelRepoBuild")
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    def delete(self, namespace, repository, build_uuid):
        """
        Cancels a repository build.
        """
        try:
            build = model.build.get_repository_build(build_uuid)
        except model.build.InvalidRepositoryBuildException:
            raise NotFound()

        if (
            build.repository.name != repository
            or build.repository.namespace_user.username != namespace
        ):
            raise NotFound()

        if model.build.cancel_repository_build(build, dockerfile_build_queue):
            return "Okay", 201
        else:
            raise InvalidRequest("Build is currently running or has finished")


@resource("/v1/repository/<apirepopath:repository>/build/<build_uuid>/status")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("build_uuid", "The UUID of the build")
class RepositoryBuildStatus(RepositoryParamResource):
    """
    Resource for dealing with repository build status.
    """

    @require_repo_read
    @nickname("getRepoBuildStatus")
    @disallow_for_app_repositories
    def get(self, namespace, repository, build_uuid):
        """
        Return the status for the builds specified by the build uuids.
        """
        build = model.build.get_repository_build(build_uuid)
        if (
            not build
            or build.repository.name != repository
            or build.repository.namespace_user.username != namespace
        ):
            raise NotFound()

        return build_status_view(build)


def get_logs_or_log_url(build):
    # If the logs have been archived, just return a URL of the completed archive
    if build.logs_archived:
        return {
            "logs_url": log_archive.get_file_url(build.uuid, get_request_ip(), requires_cors=True)
        }
    start = int(request.args.get("start", 0))

    try:
        count, logs = build_logs.get_log_entries(build.uuid, start)
    except BuildStatusRetrievalError:
        count, logs = (0, [])

    response_obj = {}
    response_obj.update(
        {
            "start": start,
            "total": count,
            "logs": [log for log in logs],
        }
    )

    return response_obj


@resource("/v1/repository/<apirepopath:repository>/build/<build_uuid>/logs")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("build_uuid", "The UUID of the build")
class RepositoryBuildLogs(RepositoryParamResource):
    """
    Resource for loading repository build logs.
    """

    @require_repo_read
    @nickname("getRepoBuildLogs")
    @disallow_for_app_repositories
    def get(self, namespace, repository, build_uuid):
        """
        Return the build logs for the build specified by the build uuid.
        """
        can_write = ModifyRepositoryPermission(namespace, repository).can()
        if not features.READER_BUILD_LOGS and not can_write:
            raise Unauthorized()

        build = model.build.get_repository_build(build_uuid)
        if (
            not build
            or build.repository.name != repository
            or build.repository.namespace_user.username != namespace
        ):
            raise NotFound()

        return get_logs_or_log_url(build)


@resource("/v1/filedrop/")
@internal_only
class FileDropResource(ApiResource):
    """
    Custom verb for setting up a client side file transfer.
    """

    schemas = {
        "FileDropRequest": {
            "type": "object",
            "description": "Description of the file that the user wishes to upload.",
            "required": [
                "mimeType",
            ],
            "properties": {
                "mimeType": {
                    "type": "string",
                    "description": "Type of the file which is about to be uploaded",
                },
            },
        },
    }

    @nickname("getFiledropUrl")
    @validate_json_request("FileDropRequest")
    def post(self):
        """
        Request a URL to which a file may be uploaded.
        """
        mime_type = request.get_json()["mimeType"]
        (url, file_id) = user_files.prepare_for_drop(mime_type, requires_cors=True)
        return {
            "url": url,
            "file_id": str(file_id),
        }
