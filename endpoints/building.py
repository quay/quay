import logging
import json

from datetime import datetime, timedelta

from flask import request

from app import app, dockerfile_build_queue
from data import model
from data.logs_model import logs_model
from data.database import db, RepositoryState
from auth.auth_context import get_authenticated_user
from notifications import spawn_notification
from util.names import escape_tag
from util.morecollections import AttrDict
from util.request import get_request_ip


logger = logging.getLogger(__name__)


class MaximumBuildsQueuedException(Exception):
    """
    This exception is raised when a build is requested, but the incoming build would exceed the
    configured maximum build rate.
    """

    pass


class BuildTriggerDisabledException(Exception):
    """
    This exception is raised when a build is required, but the build trigger has been disabled.
    """

    pass


def start_build(repository, prepared_build, pull_robot_name=None):
    # Ensure that builds are only run in image repositories.
    if repository.kind.name != "image":
        raise Exception("Attempt to start a build for application repository %s" % repository.id)

    # Ensure the repository isn't in mirror or read-only mode.
    if repository.state != RepositoryState.NORMAL:
        raise Exception(
            (
                "Attempt to start a build for a non-normal repository: %s %s"
                % (repository.id, repository.state)
            )
        )

    # Ensure that disabled triggers are not run.
    if prepared_build.trigger is not None and not prepared_build.trigger.enabled:
        raise BuildTriggerDisabledException

    if repository.namespace_user.maximum_queued_builds_count is not None:
        queue_item_canonical_name = [repository.namespace_user.username]
        alive_builds = dockerfile_build_queue.num_alive_jobs(queue_item_canonical_name)
        if alive_builds >= repository.namespace_user.maximum_queued_builds_count:
            logger.debug(
                "Prevented queueing of build under namespace %s due to reaching max: %s",
                repository.namespace_user.username,
                repository.namespace_user.maximum_queued_builds_count,
            )
            raise MaximumBuildsQueuedException()

    host = app.config["SERVER_HOSTNAME"]
    repo_path = "%s/%s/%s" % (host, repository.namespace_user.username, repository.name)

    new_token = model.token.create_access_token(
        repository, "write", kind="build-worker", friendly_name="Repository Build Token"
    )
    logger.debug(
        "Creating build %s with repo %s tags %s",
        prepared_build.build_name,
        repo_path,
        prepared_build.tags,
    )

    job_config = {
        "docker_tags": prepared_build.tags,
        "registry": host,
        "build_subdir": prepared_build.subdirectory,
        "context": prepared_build.context,
        "trigger_metadata": prepared_build.metadata or {},
        "is_manual": prepared_build.is_manual,
        "manual_user": get_authenticated_user().username if get_authenticated_user() else None,
        "archive_url": prepared_build.archive_url,
    }

    with app.config["DB_TRANSACTION_FACTORY"](db):
        build_request = model.build.create_repository_build(
            repository,
            new_token,
            job_config,
            prepared_build.dockerfile_id,
            prepared_build.build_name,
            prepared_build.trigger,
            pull_robot_name=pull_robot_name,
        )

        pull_creds = model.user.get_pull_credentials(pull_robot_name) if pull_robot_name else None

        json_data = json.dumps({"build_uuid": build_request.uuid, "pull_credentials": pull_creds})

        queue_id = dockerfile_build_queue.put(
            [repository.namespace_user.username, repository.name], json_data, retries_remaining=3
        )

        build_request.queue_id = queue_id
        build_request.save()

    # Add the build to the repo's log and spawn the build_queued notification.
    event_log_metadata = {
        "build_id": build_request.uuid,
        "docker_tags": prepared_build.tags,
        "repo": repository.name,
        "namespace": repository.namespace_user.username,
        "is_manual": prepared_build.is_manual,
        "manual_user": get_authenticated_user().username if get_authenticated_user() else None,
    }

    if prepared_build.trigger:
        event_log_metadata["trigger_id"] = prepared_build.trigger.uuid
        event_log_metadata["trigger_kind"] = prepared_build.trigger.service.name
        event_log_metadata["trigger_metadata"] = prepared_build.metadata or {}

    logs_model.log_action(
        "build_dockerfile",
        repository.namespace_user.username,
        ip=get_request_ip(),
        metadata=event_log_metadata,
        repository=repository,
    )

    # TODO: remove when more endpoints have been converted to using interfaces
    repo = AttrDict(
        {"namespace_name": repository.namespace_user.username, "name": repository.name,}
    )

    spawn_notification(
        repo,
        "build_queued",
        event_log_metadata,
        subpage="build/%s" % build_request.uuid,
        pathargs=["build", build_request.uuid],
    )

    return build_request


class PreparedBuild(object):
    """
    Class which holds all the information about a prepared build.

    The build queuing service will use this result to actually invoke the build.
    """

    def __init__(self, trigger=None):
        self._dockerfile_id = None
        self._archive_url = None
        self._tags = None
        self._build_name = None
        self._subdirectory = None
        self._context = None
        self._metadata = None
        self._trigger = trigger
        self._is_manual = None

    @staticmethod
    def get_display_name(sha):
        return sha[0:7]

    def name_from_sha(self, sha):
        self.build_name = PreparedBuild.get_display_name(sha)

    @property
    def is_manual(self):
        if self._is_manual is None:
            raise Exception("Property is_manual not set")

        return self._is_manual

    @is_manual.setter
    def is_manual(self, value):
        if self._is_manual is not None:
            raise Exception("Property is_manual already set")

        self._is_manual = value

    @property
    def trigger(self):
        return self._trigger

    @property
    def archive_url(self):
        return self._archive_url

    @archive_url.setter
    def archive_url(self, value):
        if self._archive_url:
            raise Exception("Property archive_url already set")

        self._archive_url = value

    @property
    def dockerfile_id(self):
        return self._dockerfile_id

    @dockerfile_id.setter
    def dockerfile_id(self, value):
        if self._dockerfile_id:
            raise Exception("Property dockerfile_id already set")

        self._dockerfile_id = value

    @property
    def tags(self):
        if not self._tags:
            raise Exception("Missing property tags")

        return self._tags

    @tags.setter
    def tags(self, value):
        if self._tags:
            raise Exception("Property tags already set")

        self._tags = [escape_tag(tag, default="latest") for tag in value]

    @property
    def build_name(self):
        if not self._build_name:
            raise Exception("Missing property build_name")

        return self._build_name

    @build_name.setter
    def build_name(self, value):
        if self._build_name:
            raise Exception("Property build_name already set")

        self._build_name = value

    @property
    def subdirectory(self):
        if self._subdirectory is None:
            raise Exception("Missing property subdirectory")

        return self._subdirectory

    @subdirectory.setter
    def subdirectory(self, value):
        if self._subdirectory:
            raise Exception("Property subdirectory already set")

        self._subdirectory = value

    @property
    def context(self):
        if self._context is None:
            raise Exception("Missing property context")

        return self._context

    @context.setter
    def context(self, value):
        if self._context:
            raise Exception("Property context already set")

        self._context = value

    @property
    def metadata(self):
        if self._metadata is None:
            raise Exception("Missing property metadata")

        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if self._metadata:
            raise Exception("Property metadata already set")

        self._metadata = value
