import json
import logging
import os

from app import app
from cachetools.func import lru_cache
from notifications import spawn_notification
from data import model
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from data.database import UseThenDisconnect
from util import slash_join
from util.morecollections import AttrDict

logger = logging.getLogger(__name__)


class BuildJobLoadException(Exception):
    """
    Exception raised if a build job could not be instantiated for some reason.
    """

    pass


class BuildJob(object):
    """
    Represents a single in-progress build job.
    """

    def __init__(self, job_item):
        self.job_item = job_item

        try:
            self.job_details = json.loads(job_item.body)
            self.build_notifier = BuildJobNotifier(self.build_uuid)
        except ValueError:
            raise BuildJobLoadException(
                "Could not parse build queue item config with ID %s"
                % self.job_details["build_uuid"]
            )

    @property
    def retries_remaining(self):
        return self.job_item.retries_remaining

    def has_retries_remaining(self):
        return self.job_item.retries_remaining > 0

    def send_notification(self, kind, error_message=None, image_id=None, manifest_digests=None):
        self.build_notifier.send_notification(kind, error_message, image_id, manifest_digests)

    @lru_cache(maxsize=1)
    def _load_repo_build(self):
        with UseThenDisconnect(app.config):
            try:
                return model.build.get_repository_build(self.build_uuid)
            except model.InvalidRepositoryBuildException:
                raise BuildJobLoadException(
                    "Could not load repository build with ID %s" % self.build_uuid
                )

    @property
    def build_uuid(self):
        """
        Returns the unique UUID for this build job.
        """
        return self.job_details["build_uuid"]

    @property
    def namespace(self):
        """
        Returns the namespace under which this build is running.
        """
        return self.repo_build.repository.namespace_user.username

    @property
    def repo_name(self):
        """
        Returns the name of the repository under which this build is running.
        """
        return self.repo_build.repository.name

    @property
    def repo_build(self):
        return self._load_repo_build()

    def get_build_package_url(self, user_files):
        """
        Returns the URL of the build package for this build, if any or empty string if none.
        """
        archive_url = self.build_config.get("archive_url", None)
        if archive_url:
            return archive_url

        if not self.repo_build.resource_key:
            return ""

        return user_files.get_file_url(
            self.repo_build.resource_key, "127.0.0.1", requires_cors=False
        )

    @property
    def pull_credentials(self):
        """
        Returns the pull credentials for this job, or None if none.
        """
        return self.job_details.get("pull_credentials")

    @property
    def build_config(self):
        try:
            return json.loads(self.repo_build.job_config)
        except ValueError:
            raise BuildJobLoadException(
                "Could not parse repository build job config with ID %s"
                % self.job_details["build_uuid"]
            )

    def determine_cached_tag(self, base_image_id=None):
        """
        Returns the tag to pull to prime the cache or None if none.
        """
        cached_tag = self._determine_cached_tag_by_tag()
        logger.debug("Determined cached tag %s for %s: %s", cached_tag, base_image_id)
        return cached_tag

    def _determine_cached_tag_by_tag(self):
        """
        Determines the cached tag by looking for one of the tags being built, and seeing if it
        exists in the repository.

        This is a fallback for when no comment information is available.
        """
        with UseThenDisconnect(app.config):
            tags = self.build_config.get("docker_tags", ["latest"])
            repository = RepositoryReference.for_repo_obj(self.repo_build.repository)
            matching_tag = registry_model.find_matching_tag(repository, tags)
            if matching_tag is not None:
                return matching_tag.name

            most_recent_tag = registry_model.get_most_recent_tag(repository)
            if most_recent_tag is not None:
                return most_recent_tag.name

            return None

    def extract_dockerfile_args(self):
        dockerfile_path = self.build_config.get("build_subdir", "")
        context = self.build_config.get("context", "")
        if not (dockerfile_path == "" or context == ""):
            # This should not happen and can be removed when we centralize validating build_config
            dockerfile_abspath = slash_join("", dockerfile_path)
            if ".." in os.path.relpath(dockerfile_abspath, context):
                return os.path.split(dockerfile_path)
            dockerfile_path = os.path.relpath(dockerfile_abspath, context)

        return context, dockerfile_path

    def commit_sha(self):
        """
        Determines whether the metadata is using an old schema or not and returns the commit.
        """
        commit_sha = self.build_config["trigger_metadata"].get("commit", "")
        old_commit_sha = self.build_config["trigger_metadata"].get("commit_sha", "")
        return commit_sha or old_commit_sha


class BuildJobNotifier(object):
    """
    A class for sending notifications to a job that only relies on the build_uuid.
    """

    def __init__(self, build_uuid):
        self.build_uuid = build_uuid

    @property
    def repo_build(self):
        return self._load_repo_build()

    @lru_cache(maxsize=1)
    def _load_repo_build(self):
        try:
            return model.build.get_repository_build(self.build_uuid)
        except model.InvalidRepositoryBuildException:
            raise BuildJobLoadException(
                "Could not load repository build with ID %s" % self.build_uuid
            )

    @property
    def build_config(self):
        try:
            return json.loads(self.repo_build.job_config)
        except ValueError:
            raise BuildJobLoadException(
                "Could not parse repository build job config with ID %s" % self.repo_build.uuid
            )

    def send_notification(self, kind, error_message=None, image_id=None, manifest_digests=None):
        with UseThenDisconnect(app.config):
            tags = self.build_config.get("docker_tags", ["latest"])
            trigger = self.repo_build.trigger
            if trigger is not None and trigger.id is not None:
                trigger_kind = trigger.service.name
            else:
                trigger_kind = None

            event_data = {
                "build_id": self.repo_build.uuid,
                "build_name": self.repo_build.display_name,
                "docker_tags": tags,
                "trigger_id": trigger.uuid if trigger is not None else None,
                "trigger_kind": trigger_kind,
                "trigger_metadata": self.build_config.get("trigger_metadata", {}),
            }

            if image_id is not None:
                event_data["image_id"] = image_id

            if manifest_digests:
                event_data["manifest_digests"] = manifest_digests

            if error_message is not None:
                event_data["error_message"] = error_message

            # TODO: remove when more endpoints have been converted to using
            # interfaces
            repo = AttrDict(
                {
                    "namespace_name": self.repo_build.repository.namespace_user.username,
                    "name": self.repo_build.repository.name,
                }
            )
            spawn_notification(
                repo,
                kind,
                event_data,
                subpage="build/%s" % self.repo_build.uuid,
                pathargs=["build", self.repo_build.uuid],
            )
