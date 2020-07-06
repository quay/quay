import datetime
import os
import time
import logging
import json
import asyncio

from autobahn.wamp.exception import ApplicationError

from buildman.server import BuildJobResult
from buildman.component.basecomponent import BaseComponent
from buildman.component.buildparse import extract_current_step
from buildman.jobutil.buildjob import BuildJobLoadException
from buildman.jobutil.buildstatus import StatusHandler
from buildman.jobutil.workererror import WorkerError

from app import app
from data.database import BUILD_PHASE, UseThenDisconnect
from data.model import InvalidRepositoryBuildException
from data.registry_model import registry_model
from util import slash_join

HEARTBEAT_DELTA = datetime.timedelta(seconds=60)
BUILD_HEARTBEAT_DELAY = datetime.timedelta(seconds=30)
HEARTBEAT_TIMEOUT = 10
INITIAL_TIMEOUT = 25

SUPPORTED_WORKER_VERSIONS = ["0.3"]

# Label which marks a manifest with its source build ID.
INTERNAL_LABEL_BUILD_UUID = "quay.build.uuid"

logger = logging.getLogger(__name__)


class ComponentStatus(object):
    """
    ComponentStatus represents the possible states of a component.
    """

    JOINING = "joining"
    WAITING = "waiting"
    RUNNING = "running"
    BUILDING = "building"
    TIMED_OUT = "timeout"


class BuildComponent(BaseComponent):
    """
    An application session component which conducts one (or more) builds.
    """

    def __init__(self, config, realm=None, token=None, **kwargs):
        self.expected_token = token
        self.builder_realm = realm

        self.parent_manager = None
        self.registry_hostname = None

        self._component_status = ComponentStatus.JOINING
        self._last_heartbeat = None
        self._current_job = None
        self._build_status = None
        self._image_info = None
        self._worker_version = None

        BaseComponent.__init__(self, config, **kwargs)

    def kind(self):
        return "builder"

    def onConnect(self):
        self.join(self.builder_realm)

    async def onJoin(self, details):
        logger.debug("Registering methods and listeners for component %s", self.builder_realm)
        await self.register(self._on_ready, "io.quay.buildworker.ready")
        await (self.register(self._determine_cache_tag, "io.quay.buildworker.determinecachetag"))
        await self.register(self._ping, "io.quay.buildworker.ping")
        await self.register(self._on_log_message, "io.quay.builder.logmessagesynchronously")

        await self.subscribe(self._on_heartbeat, "io.quay.builder.heartbeat")

        await self._set_status(ComponentStatus.WAITING)

    async def start_build(self, build_job):
        """
        Starts a build.
        """
        if self._component_status not in (ComponentStatus.WAITING, ComponentStatus.RUNNING):
            logger.debug(
                "Could not start build for component %s (build %s, worker version: %s): %s",
                self.builder_realm,
                build_job.repo_build.uuid,
                self._worker_version,
                self._component_status,
            )
            return

        logger.debug(
            "Starting build for component %s (build %s, worker version: %s)",
            self.builder_realm,
            build_job.repo_build.uuid,
            self._worker_version,
        )

        self._current_job = build_job
        self._build_status = StatusHandler(self.build_logs, build_job.repo_build.uuid)
        self._image_info = {}

        await self._set_status(ComponentStatus.BUILDING)

        # Send the notification that the build has started.
        build_job.send_notification("build_start")

        # Parse the build configuration.
        try:
            build_config = build_job.build_config
        except BuildJobLoadException as irbe:
            await self._build_failure("Could not load build job information", irbe)
            return

        base_image_information = {}

        # Add the pull robot information, if any.
        if build_job.pull_credentials:
            base_image_information["username"] = build_job.pull_credentials.get("username", "")
            base_image_information["password"] = build_job.pull_credentials.get("password", "")

        # Retrieve the repository's fully qualified name.
        repo = build_job.repo_build.repository
        repository_name = repo.namespace_user.username + "/" + repo.name

        # Parse the build queue item into build arguments.
        #  build_package: URL to the build package to download and untar/unzip.
        #                 defaults to empty string to avoid requiring a pointer on the builder.
        #  sub_directory: The location within the build package of the Dockerfile and the build context.
        #  repository: The repository for which this build is occurring.
        #  registry: The registry for which this build is occuring (e.g. 'quay.io').
        #  pull_token: The token to use when pulling the cache for building.
        #  push_token: The token to use to push the built image.
        #  tag_names: The name(s) of the tag(s) for the newly built image.
        #  base_image: The image name and credentials to use to conduct the base image pull.
        #   username: The username for pulling the base image (if any).
        #   password: The password for pulling the base image (if any).
        context, dockerfile_path = self.extract_dockerfile_args(build_config)
        build_arguments = {
            "build_package": build_job.get_build_package_url(self.user_files),
            "context": context,
            "dockerfile_path": dockerfile_path,
            "repository": repository_name,
            "registry": self.registry_hostname,
            "pull_token": build_job.repo_build.access_token.get_code(),
            "push_token": build_job.repo_build.access_token.get_code(),
            "tag_names": build_config.get("docker_tags", ["latest"]),
            "base_image": base_image_information,
        }

        # If the trigger has a private key, it's using git, thus we should add
        # git data to the build args.
        #  url: url used to clone the git repository
        #  sha: the sha1 identifier of the commit to check out
        #  private_key: the key used to get read access to the git repository

        private_key = None
        if (
            build_job.repo_build.trigger is not None
            and build_job.repo_build.trigger.secure_private_key is not None
        ):
            private_key = build_job.repo_build.trigger.secure_private_key.decrypt()

        if private_key is not None:
            build_arguments["git"] = {
                "url": build_config["trigger_metadata"].get("git_url", ""),
                "sha": BuildComponent._commit_sha(build_config),
                "private_key": private_key or "",
            }

        # If the build args have no buildpack, mark it as a failure before sending
        # it to a builder instance.
        if not build_arguments["build_package"] and not build_arguments["git"]:
            logger.error(
                "%s: insufficient build args: %s",
                self._current_job.repo_build.uuid,
                build_arguments,
            )
            await self._build_failure("Insufficient build arguments. No buildpack available.")
            return

        # Invoke the build.
        logger.debug("Invoking build: %s", self.builder_realm)
        logger.debug("With Arguments: %s", build_arguments)

        def build_complete_callback(result):
            """
            This function is used to execute a coroutine as the callback.
            """
            asyncio.create_task(self._build_complete(result))

        self.call("io.quay.builder.build", **build_arguments).add_done_callback(
            build_complete_callback
        )

        # Set the heartbeat for the future. If the builder never receives the build call,
        # then this will cause a timeout after 30 seconds. We know the builder has registered
        # by this point, so it makes sense to have a timeout.
        self._last_heartbeat = datetime.datetime.utcnow() + BUILD_HEARTBEAT_DELAY

    @staticmethod
    def extract_dockerfile_args(build_config):
        dockerfile_path = build_config.get("build_subdir", "")
        context = build_config.get("context", "")
        if not (dockerfile_path == "" or context == ""):
            # This should not happen and can be removed when we centralize validating build_config
            dockerfile_abspath = slash_join("", dockerfile_path)
            if ".." in os.path.relpath(dockerfile_abspath, context):
                return os.path.split(dockerfile_path)
            dockerfile_path = os.path.relpath(dockerfile_abspath, context)

        return context, dockerfile_path

    @staticmethod
    def _commit_sha(build_config):
        """
        Determines whether the metadata is using an old schema or not and returns the commit.
        """
        commit_sha = build_config["trigger_metadata"].get("commit", "")
        old_commit_sha = build_config["trigger_metadata"].get("commit_sha", "")
        return commit_sha or old_commit_sha

    @staticmethod
    def name_and_path(subdir):
        """
        Returns the dockerfile path and name.
        """
        if subdir.endswith("/"):
            subdir += "Dockerfile"
        elif not subdir.endswith("Dockerfile"):
            subdir += "/Dockerfile"
        return os.path.split(subdir)

    @staticmethod
    def _total_completion(statuses, total_images):
        """
        Returns the current amount completion relative to the total completion of a build.
        """
        percentage_with_sizes = float(len(statuses.values())) / total_images
        sent_bytes = sum([status["current"] for status in statuses.values()])
        total_bytes = sum([status["total"] for status in statuses.values()])
        return float(sent_bytes) / total_bytes * percentage_with_sizes

    @staticmethod
    def _process_pushpull_status(status_dict, current_phase, docker_data, images):
        """
        Processes the status of a push or pull by updating the provided status_dict and images.
        """
        if not docker_data:
            return

        num_images = 0
        status_completion_key = ""

        if current_phase == "pushing":
            status_completion_key = "push_completion"
            num_images = status_dict["total_commands"]
        elif current_phase == "pulling":
            status_completion_key = "pull_completion"
        elif current_phase == "priming-cache":
            status_completion_key = "cache_completion"
        else:
            return

        if "progressDetail" in docker_data and "id" in docker_data:
            image_id = docker_data["id"]
            detail = docker_data["progressDetail"]

            if "current" in detail and "total" in detail:
                images[image_id] = detail
                status_dict[status_completion_key] = BuildComponent._total_completion(
                    images, max(len(images), num_images)
                )

    async def _on_log_message(self, phase, json_data):
        """
        Tails log messages and updates the build status.
        """
        # Update the heartbeat.
        self._last_heartbeat = datetime.datetime.utcnow()

        # Parse any of the JSON data logged.
        log_data = {}
        if json_data:
            try:
                log_data = json.loads(json_data)
            except ValueError:
                pass

        # Extract the current status message (if any).
        fully_unwrapped = ""
        keys_to_extract = ["error", "status", "stream"]
        for key in keys_to_extract:
            if key in log_data:
                fully_unwrapped = log_data[key]
                break

        # Determine if this is a step string.
        current_step = None
        current_status_string = str(fully_unwrapped.encode("utf-8"))

        if current_status_string and phase == BUILD_PHASE.BUILDING:
            current_step = extract_current_step(current_status_string)

        # Parse and update the phase and the status_dict. The status dictionary contains
        # the pull/push progress, as well as the current step index.
        with self._build_status as status_dict:
            try:
                changed_phase = await (
                    self._build_status.set_phase(phase, log_data.get("status_data"))
                )
                if changed_phase:
                    logger.debug("Build %s has entered a new phase: %s", self.builder_realm, phase)
                elif self._current_job.repo_build.phase == BUILD_PHASE.CANCELLED:
                    build_id = self._current_job.repo_build.uuid
                    logger.debug(
                        "Trying to move cancelled build into phase: %s with id: %s", phase, build_id
                    )
                    return False
            except InvalidRepositoryBuildException:
                build_id = self._current_job.repo_build.uuid
                logger.warning("Build %s was not found; repo was probably deleted", build_id)
                return False

            BuildComponent._process_pushpull_status(status_dict, phase, log_data, self._image_info)

            # If the current message represents the beginning of a new step, then update the
            # current command index.
            if current_step is not None:
                status_dict["current_command"] = current_step

            # If the json data contains an error, then something went wrong with a push or pull.
            if "error" in log_data:
                await self._build_status.set_error(log_data["error"])

        if current_step is not None:
            await self._build_status.set_command(current_status_string)
        elif phase == BUILD_PHASE.BUILDING:
            await self._build_status.append_log(current_status_string)
        return True

    async def _determine_cache_tag(
        self, command_comments, base_image_name, base_image_tag, base_image_id
    ):
        with self._build_status as status_dict:
            status_dict["total_commands"] = len(command_comments) + 1

        logger.debug(
            "Checking cache on realm %s. Base image: %s:%s (%s)",
            self.builder_realm,
            base_image_name,
            base_image_tag,
            base_image_id,
        )

        tag_found = self._current_job.determine_cached_tag(base_image_id, command_comments)
        return tag_found or ""

    async def _build_failure(self, error_message, exception=None):
        """
        Handles and logs a failed build.
        """
        await (
            self._build_status.set_error(
                error_message, {"internal_error": str(exception) if exception else None}
            )
        )

        build_id = self._current_job.repo_build.uuid
        logger.warning("Build %s failed with message: %s", build_id, error_message)

        # Mark that the build has finished (in an error state)
        await self._build_finished(BuildJobResult.ERROR)

    async def _build_complete(self, result):
        """
        Wraps up a completed build.

        Handles any errors and calls self._build_finished.
        """
        build_id = self._current_job.repo_build.uuid

        try:
            # Retrieve the result. This will raise an ApplicationError on any error that occurred.
            result_value = result.result()
            kwargs = {}

            # Note: If we are hitting an older builder that didn't return ANY map data, then the result
            # value will be a bool instead of a proper CallResult object.
            # Therefore: we have a try-except guard here to ensure we don't hit this pitfall.
            try:
                kwargs = result_value.kwresults
            except:
                pass

            try:
                await self._build_status.set_phase(BUILD_PHASE.COMPLETE)
            except InvalidRepositoryBuildException:
                logger.warning("Build %s was not found; repo was probably deleted", build_id)
                return

            await self._build_finished(BuildJobResult.COMPLETE)

            # Label the pushed manifests with the build metadata.
            manifest_digests = kwargs.get("digests") or []
            repository = registry_model.lookup_repository(
                self._current_job.namespace, self._current_job.repo_name
            )
            if repository is not None:
                for digest in manifest_digests:
                    with UseThenDisconnect(app.config):
                        manifest = registry_model.lookup_manifest_by_digest(
                            repository, digest, require_available=True
                        )
                        if manifest is None:
                            continue

                        registry_model.create_manifest_label(
                            manifest, INTERNAL_LABEL_BUILD_UUID, build_id, "internal", "text/plain"
                        )

            # Send the notification that the build has completed successfully.
            self._current_job.send_notification(
                "build_success", image_id=kwargs.get("image_id"), manifest_digests=manifest_digests
            )
        except ApplicationError as aex:
            worker_error = WorkerError(aex.error, aex.kwargs.get("base_error"))

            # Write the error to the log.
            await (
                self._build_status.set_error(
                    worker_error.public_message(),
                    worker_error.extra_data(),
                    internal_error=worker_error.is_internal_error(),
                    requeued=self._current_job.has_retries_remaining(),
                )
            )

            # Send the notification that the build has failed.
            self._current_job.send_notification(
                "build_failure", error_message=worker_error.public_message()
            )

            # Mark the build as completed.
            if worker_error.is_internal_error():
                logger.exception(
                    "[BUILD INTERNAL ERROR: Remote] Build ID: %s: %s",
                    build_id,
                    worker_error.public_message(),
                )
                await self._build_finished(BuildJobResult.INCOMPLETE)
            else:
                logger.debug("Got remote failure exception for build %s: %s", build_id, aex)
                await self._build_finished(BuildJobResult.ERROR)

        # Remove the current job.
        self._current_job = None

    async def _build_finished(self, job_status):
        """
        Alerts the parent that a build has completed and sets the status back to running.
        """
        await self.parent_manager.job_completed(self._current_job, job_status, self)

        # Set the component back to a running state.
        await self._set_status(ComponentStatus.RUNNING)

    @staticmethod
    def _ping():
        """
        Ping pong.
        """
        return "pong"

    async def _on_ready(self, token, version):
        logger.debug('On ready called (token "%s")', token)
        self._worker_version = version

        if not version in SUPPORTED_WORKER_VERSIONS:
            logger.warning(
                'Build component (token "%s") is running an out-of-date version: %s', token, version
            )
            return False

        if self._component_status != ComponentStatus.WAITING:
            logger.warning('Build component (token "%s") is already connected', self.expected_token)
            return False

        if token != self.expected_token:
            logger.warning(
                'Builder token mismatch. Expected: "%s". Found: "%s"', self.expected_token, token
            )
            return False

        await self._set_status(ComponentStatus.RUNNING)

        # Start the heartbeat check and updating loop.
        loop = asyncio.get_event_loop()
        loop.create_task(self._heartbeat())
        logger.debug("Build worker %s is connected and ready", self.builder_realm)
        return True

    async def _set_status(self, phase):
        if phase == ComponentStatus.RUNNING:
            await self.parent_manager.build_component_ready(self)

        self._component_status = phase

    def _on_heartbeat(self):
        """
        Updates the last known heartbeat.
        """
        if self._component_status == ComponentStatus.TIMED_OUT:
            return

        logger.debug("Got heartbeat on realm %s", self.builder_realm)
        self._last_heartbeat = datetime.datetime.utcnow()

    async def _heartbeat(self):
        """
        Coroutine that runs every HEARTBEAT_TIMEOUT seconds, both checking the worker's heartbeat
        and updating the heartbeat in the build status dictionary (if applicable).

        This allows the build system to catch crashes from either end.
        """
        await asyncio.sleep(INITIAL_TIMEOUT)

        while True:
            # If the component is no longer running or actively building, nothing more to do.
            if (
                self._component_status != ComponentStatus.RUNNING
                and self._component_status != ComponentStatus.BUILDING
            ):
                return

            # If there is an active build, write the heartbeat to its status.
            if self._build_status is not None:
                with self._build_status as status_dict:
                    status_dict["heartbeat"] = int(time.time())

            # Mark the build item.
            current_job = self._current_job
            if current_job is not None:
                await self.parent_manager.job_heartbeat(current_job)

            # Check the heartbeat from the worker.
            logger.debug("Checking heartbeat on realm %s", self.builder_realm)
            if (
                self._last_heartbeat
                and self._last_heartbeat < datetime.datetime.utcnow() - HEARTBEAT_DELTA
            ):
                logger.debug(
                    "Heartbeat on realm %s has expired: %s",
                    self.builder_realm,
                    self._last_heartbeat,
                )

                await self._timeout()
                return

            logger.debug(
                "Heartbeat on realm %s is valid: %s (%s).",
                self.builder_realm,
                self._last_heartbeat,
                self._component_status,
            )

            await asyncio.sleep(HEARTBEAT_TIMEOUT)

    async def _timeout(self):
        if self._component_status == ComponentStatus.TIMED_OUT:
            return

        await self._set_status(ComponentStatus.TIMED_OUT)
        logger.warning("Build component with realm %s has timed out", self.builder_realm)

        # If we still have a running job, then it has not completed and we need to tell the parent
        # manager.
        if self._current_job is not None:
            await (
                self._build_status.set_error(
                    "Build worker timed out",
                    internal_error=True,
                    requeued=self._current_job.has_retries_remaining(),
                )
            )

            build_id = self._current_job.build_uuid
            logger.error("[BUILD INTERNAL ERROR: Timeout] Build ID: %s", build_id)
            await (
                self.parent_manager.job_completed(
                    self._current_job, BuildJobResult.INCOMPLETE, self
                )
            )

        # Unregister the current component so that it cannot be invoked again.
        self.parent_manager.build_component_disposed(self, True)

        # Remove the job reference.
        self._current_job = None

    async def cancel_build(self):
        self.parent_manager.build_component_disposed(self, True)
        self._current_job = None
        await self._set_status(ComponentStatus.RUNNING)
