import calendar
import logging
import json
import re
import time
import uuid
from datetime import datetime, timedelta
import dateutil.parser

import jwt
from prometheus_client import Counter, Histogram

from app import app
from buildman.build_token import (
    build_token,
    verify_build_token,
    InvalidBearerTokenException,
    BUILD_JOB_REGISTRATION_TYPE,
    BUILD_JOB_TOKEN_TYPE,
)
from buildman.interface import (
    BuildStateInterface,
    BuildJobAlreadyExistsError,
    BuildJobDoesNotExistsError,
    BuildJobError,
    BuildJobResult,
    RESULT_PHASES,
)
from buildman.jobutil.buildjob import BuildJob, BuildJobLoadException
from buildman.manager.executor import PopenExecutor, EC2Executor, KubernetesExecutor
from buildman.orchestrator import (
    orchestrator_from_config,
    KeyEvent,
    OrchestratorError,
    OrchestratorConnectionError,
    ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION,
)

from app import instance_keys
from data import database
from data.database import BUILD_PHASE
from data import model
from util import slash_join
from util.morecollections import AttrDict


logger = logging.getLogger(__name__)


build_fallback = Counter(
    "quay_build_fallback_total", "number of times a build has been retried", labelnames=["executor"]
)
build_ack_duration = Histogram(
    "quay_build_ack_duration_seconds",
    "seconds taken for the builder to acknowledge a queued build",
    labelnames=["executor"],
)
build_duration = Histogram(
    "quay_build_duration_seconds",
    "seconds taken for a build's execution",
    labelnames=["executor", "job_status"],  # status in (COMPLETE, INCOMPLETE, ERROR)
)

JOB_PREFIX = "building/"
LOCK_PREFIX = "lock/"
CANCEL_PREFIX = "cancel/"
METRIC_PREFIX = "metric/"

EPHEMERAL_API_TIMEOUT = 20
EPHEMERAL_SETUP_TIMEOUT = 500
WORK_CHECK_TIMEOUT = 10
SETUP_LEEWAY_SECONDS = 30

# Schedule retry durations
RETRY_IMMEDIATELY_SLEEP_DURATION = 0
TOO_MANY_WORKERS_SLEEP_DURATION = 10
CREATED_JOB_TIMEOUT_SLEEP_DURATION = 10

CREATED_JOB_TIMEOUT = 15
JOB_TIMEOUT_SECONDS = 300
MINIMUM_JOB_EXTENSION = timedelta(minutes=1)

HEARTBEAT_PERIOD_SECONDS = 30
HEARTBEAT_DELTA = timedelta(seconds=60)


logger = logging.getLogger(__name__)


class EphemeralBuilderManager(BuildStateInterface):
    PHASES_NOT_ALLOWED_TO_CANCEL_FROM = (
        BUILD_PHASE.PUSHING,
        BUILD_PHASE.COMPLETE,
        BUILD_PHASE.ERROR,
        BUILD_PHASE.INTERNAL_ERROR,
        BUILD_PHASE.CANCELLED,
    )
    ARCHIVABLE_BUILD_PHASES = (BUILD_PHASE.COMPLETE, BUILD_PHASE.ERROR, BUILD_PHASE.CANCELLED)
    COMPLETED_PHASES = ARCHIVABLE_BUILD_PHASES + (BUILD_PHASE.INTERNAL_ERROR,)

    EXECUTORS = {
        "popen": PopenExecutor,
        "ec2": EC2Executor,
        "kubernetes": KubernetesExecutor,
    }

    def __init__(
        self, registry_hostname, manager_hostname, queue, build_logs, user_files, instance_keys
    ):
        self._registry_hostname = registry_hostname
        self._manager_hostname = manager_hostname
        self._queue = queue
        self._build_logs = build_logs
        self._user_files = user_files
        self._instance_keys = instance_keys

        self._ordered_executors = []
        self._executor_name_to_executor = {}

        self._manager_config = {}
        self._orchestrator = None

    def initialize(self, manager_config):
        self._manager_config = manager_config
        if manager_config.get("EXECUTORS"):
            for executor_config in manager_config["EXECUTORS"]:
                self._load_executor(executor_config.get("EXECUTOR"), executor_config)
        else:
            self._load_executor(
                manager_config.get("EXECUTOR"), manager_config.get("EXECUTOR_CONFIG")
            )

        logger.debug("calling orchestrator_from_config")
        self._orchestrator = orchestrator_from_config(manager_config)

        logger.debug("setting on_key_change callbacks for job expiry, cancel")
        self._orchestrator.on_key_change(self._job_prefix, self._job_expired_callback)
        self._orchestrator.on_key_change(self._cancel_prefix, self._job_cancelled_callback)

    def _load_executor(self, executor_kind_name, executor_config):
        executor_klass = EphemeralBuilderManager.EXECUTORS.get(executor_kind_name)
        if executor_klass is None:
            logger.error("Unknown executor %s; skipping install", executor_kind_name)
            return

        executor = executor_klass(executor_config, self._manager_hostname)
        if executor.name in self._executor_name_to_executor:
            raise Exception("Executor with name %s already registered" % executor.name)

        self._ordered_executors.append(executor)
        self._executor_name_to_executor[executor.name] = executor

    def generate_build_token(self, token_type, build_id, job_id, expiration):
        return build_token(
            self._manager_hostname, token_type, build_id, job_id, expiration, self._instance_keys
        )

    def verify_build_token(self, token, token_type):
        return verify_build_token(token, self._manager_hostname, token_type, self._instance_keys)

    def _config_prefix(self, key):
        if self._manager_config.get("ORCHESTRATOR") is None:
            return key

        prefix = self._manager_config.get("ORCHESTRATOR_PREFIX", "")
        return slash_join(prefix, key).lstrip("/") + "/"

    @property
    def _job_prefix(self):
        return self._config_prefix(JOB_PREFIX)

    @property
    def _cancel_prefix(self):
        return self._config_prefix(CANCEL_PREFIX)

    @property
    def _metric_prefix(self):
        return self._config_prefix(METRIC_PREFIX)

    @property
    def _lock_prefix(self):
        return self._config_prefix(LOCK_PREFIX)

    @property
    def machine_max_expiration(self):
        return self._manager_config.get("MACHINE_MAX_TIME", 7200)

    def _lock_key(self, build_id):
        """Create a key which is used to get a lock on a job in the Orchestrator."""
        return slash_join(self._lock_prefix, build_id)

    def _metric_key(self, build_id):
        """Create a key which is used to track a job's metrics in the Orchestrator."""
        return slash_join(self._metric_prefix, build_id)

    def _job_key(self, build_id):
        """Creates a key which is used to track a job in the Orchestrator."""
        return slash_join(self._job_prefix, build_id)

    def _build_job_from_job_id(self, job_id):
        """Return the BuildJob from the job id."""
        try:
            job_data = self._orchestrator.get_key(job_id)
        except KeyError:
            raise BuildJobDoesNotExistsError(job_id)
        except (OrchestratorConnectionError, OrchestratorError) as oe:
            raise BuildJobError(oe)

        job_metadata = json.loads(job_data)
        build_job = BuildJob(AttrDict(job_metadata["job_queue_item"]))
        return build_job

    def create_job(self, build_id, build_metadata):
        """Create the job in the orchestrator.
        The job will expire if it is not scheduled within CREATED_JOB_TIMEOUT.
        """
        # Sets max threshold for build heartbeats. i.e max total running time of the build (default: 2h)
        # This is separate from the redis key expiration, which is kept alive with heartbeats from the worker.
        max_expiration = datetime.utcnow() + timedelta(seconds=self.machine_max_expiration)
        build_metadata["max_expiration"] = calendar.timegm(max_expiration.timetuple())
        build_metadata["last_heartbeat"] = None

        job_key = self._job_key(build_id)
        try:
            self._orchestrator.set_key(
                job_key,
                json.dumps(build_metadata),
                overwrite=False,
                expiration=CREATED_JOB_TIMEOUT,
            )
        except KeyError:
            raise BuildJobAlreadyExistsError(job_key)
        except (OrchestratorConnectionError, OrchestratorError) as je:
            raise BuildJobError(je)

        return job_key

    def job_scheduled(self, job_id, control_plane, execution_id, max_startup_time):
        """Mark the given job as scheduled with execution id, with max_startup_time.
        A job is considered scheduled once a worker is started with a given registration token.
        """
        # Get job to schedule
        try:
            job_data = self._orchestrator.get_key(job_id)
            job_data_json = json.loads(job_data)
        except KeyError:
            logger.warning(
                "Failed to mark job %s as scheduled. Job no longer exists in the orchestrator",
                job_id,
            )
            return False
        except Exception as e:
            logger.warning("Exception loading job %s from orchestrator: %s", job_id, e)
            return False

        # Update build context
        job_data_json["executor_name"] = control_plane
        job_data_json["execution_id"] = execution_id
        try:
            self._orchestrator.set_key(
                job_id, json.dumps(job_data_json), overwrite=True, expiration=max_startup_time
            )
        except Exception as e:
            logger.warning("Exception updating job %s in orchestrator: %s", job_id, e)
            return False

        build_job = BuildJob(AttrDict(job_data_json["job_queue_item"]))
        updated = self.update_job_phase(job_id, BUILD_PHASE.BUILD_SCHEDULED)
        if updated:
            self._queue.extend_processing(
                build_job.job_item,
                seconds_from_now=max_startup_time
                + 60,  # Add some leeway to allow the expiry event to complete
                minimum_extension=MINIMUM_JOB_EXTENSION,
            )

            logger.debug(
                "Job scheduled for job %s with execution with ID %s on control plane %s with max startup time of %s",
                job_id,
                execution_id,
                control_plane,
                max_startup_time,
            )
        else:
            logger.warning("Job %s not scheduled. Unable update build phase to SCHEDULED")

        return updated

    def job_unschedulable(self, job_id):
        """Stop tracking the given unschedulable job.
        Deletes any states that might have previously been stored in the orchestrator.
        """
        try:
            build_job = self._build_job_from_job_id(job_id)
            self._cleanup_job_from_orchestrator(build_job)
        except Exception as e:
            logger.warning(
                "Exception trying to mark job %s as unschedulable. Some state may not have been cleaned/updated: %s",
                job_id,
                e,
            )

    def on_job_complete(self, build_job, job_result, executor_name, execution_id):
        """Handle a completed job by updating the queue, job metrics, and cleaning up
        any remaining state.

        If the job result is INCOMPLETE, the job is requeued with its retry restored.
        If a job result is in EXPIRED or ERROR, the job is requeued, but it retry is not restored.

        If the job is cancelled, it is not requeued.

        If the job is completed, it is marked as such in the queue.

        Also checks the disable threshold on the build trigger if the phase is in (INTERNAL_ERROR, ERROR)
        """
        job_id = self._job_key(build_job.build_uuid)
        logger.debug("Calling job complete callback for job %s with result %s", job_id, job_result)

        self._write_duration_metric(build_duration, build_job.build_uuid, job_status=job_result)

        # Build timeout. No retry restored
        if job_result == BuildJobResult.EXPIRED:
            self._queue.incomplete(build_job.job_item, restore_retry=False, retry_after=30)
            logger.warning(
                "Job %s completed with result %s. Requeuing build without restoring retry.",
                job_id,
                job_result,
            )

        # Unfinished build due to internal error. Restore retry.
        elif job_result == BuildJobResult.INCOMPLETE:
            logger.warning(
                "Job %s completed with result %s. Requeuing build with retry restored.",
                job_id,
                job_result,
            )
            self._queue.incomplete(build_job.job_item, restore_retry=True, retry_after=30)

        elif job_result in (
            BuildJobResult.ERROR,
            BuildJobResult.COMPLETE,
            BuildJobResult.CANCELLED,
        ):
            logger.warning(
                "Job %s completed with result %s. Marking build done in queue.", job_id, job_result
            )
            self._queue.complete(build_job.job_item)

        # Disable trigger if needed
        if build_job.repo_build.trigger is not None:
            model.build.update_trigger_disable_status(
                build_job.repo_build.trigger, RESULT_PHASES[job_result]
            )

        # Cleanup job from executors
        if executor_name and execution_id:
            self._terminate_executor(executor_name, execution_id)

        # Cleanup job from orchestrator
        self._cleanup_job_from_orchestrator(build_job)

        logger.debug("Job completed for job %s with result %s", job_id, job_result)

    def start_job(self, job_id, max_build_time):
        """Starts the build job. This is invoked by the worker once the job has been created and
        scheduled, returing the buildpack needed to start the actual build.
        """
        try:
            job_data = self._orchestrator.get_key(job_id)
            job_data_json = json.loads(job_data)
            build_job = BuildJob(AttrDict(job_data_json["job_queue_item"]))
        except KeyError:
            logger.warning("Failed to start job %s. Job does not exists in orchestrator", job_id)
            return None, None
        except Exception as e:
            logger.error("Exception loading job %s from orchestrator: %s", job_id, e)
            return None, None

        # Construct the buildpack
        repo = build_job.repo_build.repository
        repository_name = repo.namespace_user.username + "/" + repo.name
        context, dockerfile_path = build_job.extract_dockerfile_args()
        base_image_information = {}
        if build_job.pull_credentials:
            base_image_information["username"] = build_job.pull_credentials.get("username", "")
            base_image_information["password"] = build_job.pull_credentials.get("password", "")

        build_args = {
            "build_package": build_job.get_build_package_url(self._user_files),
            "context": context,
            "dockerfile_path": dockerfile_path,
            "repository": repository_name,
            "registry": self._registry_hostname,
            "pull_token": build_job.repo_build.access_token.get_code(),
            "push_token": build_job.repo_build.access_token.get_code(),
            "tag_names": build_job.build_config.get("docker_tags", ["latest"]),
            "base_image": base_image_information,
        }

        private_key = None
        if (
            build_job.repo_build.trigger is not None
            and build_job.repo_build.trigger.secure_private_key is not None
        ):
            private_key = build_job.repo_build.trigger.secure_private_key.decrypt()

        if private_key is not None:
            build_args["git"] = {
                "url": build_job.build_config["trigger_metadata"].get("git_url", ""),
                "sha": build_job.commit_sha(build_job.build_config),
                "private_key": private_key or "",
            }

        # If the build args have no buildpack, mark it as a failure before sending
        # it to a builder instance.
        if not build_args["build_package"] and not build_args["git"]:
            logger.error(
                "Failed to start job %s: insufficient build args - No package url or git",
                job_id,
            )
            self.update_job_phase(job_id, BUILD_PHASE.INTERNAL_ERROR)
            return (None, None)

        # Generate the build token
        token = self.generate_build_token(
            BUILD_JOB_TOKEN_TYPE, build_job.build_uuid, job_id, max_build_time
        )

        # Publish the time it took for a worker to ack the build
        self._write_duration_metric(build_ack_duration, build_job.build_uuid)

        logger.debug("Started build job %s with arguments %s", job_id, build_args)
        return (token, build_args)

    def update_job_phase(self, job_id, phase, phase_metadata=None):
        """Updates the given job's phase and append the phase change to the buildlogs, with the
        given phase metadata. If the job reaches a completed state, update_job_phase also update the
        queue and cleanups any existing state and executors.
        """
        try:
            job_data = self._orchestrator.get_key(job_id)
            job_data_json = json.loads(job_data)
            build_job = BuildJob(AttrDict(job_data_json["job_queue_item"]))
        except KeyError:
            logger.warning("Job %s no longer exists in the orchestrator, likely expired", job_id)
            return False
        except Exception as e:
            logger.error("Exception loading job %s from orchestrator: %s", job_id, e)
            return False

        # Check if the build has not already reached a final phase
        if build_job.repo_build.phase in EphemeralBuilderManager.ARCHIVABLE_BUILD_PHASES:
            logger.warning(
                "Job %s is already in a final completed phase (%s), cannot update to %s",
                job_id,
                build_job.repo_build.phase,
                phase,
            )
            return False

        # Update the build phase
        phase_metadata = phase_metadata or {}
        updated = model.build.update_phase_then_close(build_job.build_uuid, phase)
        if updated:
            self.append_log_message(
                build_job.build_uuid, phase, self._build_logs.PHASE, phase_metadata
            )

        # Check if on_job_complete needs to be called
        if updated and phase in EphemeralBuilderManager.COMPLETED_PHASES:
            executor_name = job_data_json.get("executor_name")
            execution_id = job_data_json.get("execution_id")

            if phase == BUILD_PHASE.ERROR:
                self.on_job_complete(build_job, BuildJobResult.ERROR, executor_name, execution_id)
            elif phase == BUILD_PHASE.COMPLETE:
                self.on_job_complete(
                    build_job, BuildJobResult.COMPLETE, executor_name, execution_id
                )
            elif phase == BUILD_PHASE.INTERNAL_ERROR:
                self.on_job_complete(
                    build_job, BuildJobResult.INCOMPLETE, executor_name, execution_id
                )
            elif phase == BUILD_PHASE.CANCELLED:
                self.on_job_complete(
                    build_job, BuildJobResult.CANCELLED, executor_name, execution_id
                )

        return updated

    def job_heartbeat(self, job_id):
        """Extend the processing time in the queue and updates the ttl of the job in the
        orchestrator.
        """
        try:
            job_data = self._orchestrator.get_key(job_id)
            job_data_json = json.loads(job_data)
            build_job = BuildJob(AttrDict(job_data_json["job_queue_item"]))
        except KeyError:
            logger.warning("Job %s no longer exists in the orchestrator, likely expired", job_id)
            return False
        except Exception as e:
            logger.error("Exception loading job %s from orchestrator: %s", job_id, e)
            return False

        max_expiration = datetime.utcfromtimestamp(job_data_json["max_expiration"])
        max_expiration_remaining = max_expiration - datetime.utcnow()
        max_expiration_sec = max(1, int(max_expiration_remaining.total_seconds()))
        ttl = min(HEARTBEAT_PERIOD_SECONDS * 2, max_expiration_sec)

        # Update job expirations
        if (
            job_data_json["last_heartbeat"]
            and dateutil.parser.isoparse(job_data_json["last_heartbeat"])
            < datetime.utcnow() - HEARTBEAT_DELTA
        ):
            logger.warning(
                "Heartbeat expired for job %s. Marking job as expired. Last heartbeat received at %s",
                job_data_json["last_heartbeat"],
            )
            self.update_job_phase(job_id, BUILD_PHASE.INTERNAL_ERROR)
            return False

        job_data_json["last_heartbeat"] = str(datetime.utcnow())

        self._queue.extend_processing(
            build_job.job_item,
            seconds_from_now=JOB_TIMEOUT_SECONDS,
            minimum_extension=MINIMUM_JOB_EXTENSION,
        )

        try:
            self._orchestrator.set_key(job_id, json.dumps(job_data_json), expiration=ttl)
        except OrchestratorConnectionError:
            logger.error(
                "Could not update heartbeat for job %s. Orchestrator is not available", job_id
            )
            return False

        return True

    def cancel_build(self, build_id):
        build = model.build.get_repository_build(build_id)
        if build.phase in EphemeralBuilderManager.PHASES_NOT_ALLOWED_TO_CANCEL_FROM:
            return False

        cancelled = model.build.update_phase_then_close(build_id, BUILD_PHASE.CANCELLED)
        if cancelled:
            try:
                job_data = self._orchestrator.get_key(self._job_key(build_id))
                job_data_json = json.loads(job_data)
                build_job = BuildJob(AttrDict(job_data_json["job_queue_item"]))
                self.on_job_complete(
                    build_job,
                    BuildJobResult.CANCELLED,
                    job_data_json.get("executor_name"),
                    job_data_json.get("execution_id"),
                )
            except KeyError:
                logger.warning(
                    "Could not cleanup cancelled job %s. Job does not exist in orchestrator", job_id
                )

        return cancelled

    def determine_cached_tag(self, build_id, base_image_id):
        job_id = self._job_key(build_id)
        try:
            job_data = self._orchestrator.get_key(job_id)
            job_data_json = json.loads(job_data)
            build_job = BuildJob(AttrDict(job_data_json["job_queue_item"]))
        except KeyError:
            logger.warning("Job %s does not exist in orchestrator: %s", job_id)
            return None
        except Exception as e:
            logger.warning("Exception loading job from orchestrator: %s", e)
            return None

        return build_job.determine_cached_tag(base_image_id)

    def schedule(self, build_id):
        """Schedule an existed job to be started on the configured control planes (executors)."""
        logger.debug("Scheduling build %s", build_id)

        allowed_worker_count = self._manager_config.get("ALLOWED_WORKER_COUNT", 1)
        if self._running_workers() >= allowed_worker_count:
            logger.warning(
                "Could not schedule build %s. Number of workers at capacity: %s.",
                build_id,
                self._running_workers(),
            )
            return False, TOO_MANY_WORKERS_SLEEP_DURATION

        job_id = self._job_key(build_id)
        try:
            build_job = self._build_job_from_job_id(job_id)
        except BuildJobDoesNotExistsError as bjne:
            logger.warning(
                "Failed to schedule job %s - Job no longer exists in the orchestrator, likely expired: %s",
                job_id,
                bjne,
            )
            return False, CREATED_JOB_TIMEOUT_SLEEP_DURATION
        except BuildJobError as bje:
            logger.warning(
                "Failed to schedule job %s - Could not get job from orchestrator: %s", job_id, bje
            )
            return False, ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION

        registration_token = self.generate_build_token(
            BUILD_JOB_REGISTRATION_TYPE, build_job.build_uuid, job_id, EPHEMERAL_SETUP_TIMEOUT
        )

        started_with_executor = None
        execution_id = None
        for executor in self._ordered_executors:
            namespace = build_job.namespace
            if not executor.allowed_for_namespace(namespace):
                logger.warning(
                    "Job %s (namespace: %s) cannot use executor %s",
                    job_id,
                    namespace,
                    executor.name,
                )
                continue

            # Check if we can use this executor based on the retries remaining.
            if executor.minimum_retry_threshold > build_job.retries_remaining:
                build_fallback.labels(executor.name).inc()
                logger.warning(
                    "Job %s cannot use executor %s as it is below retry threshold %s (retry #%s) - Falling back to next configured executor",
                    job_id,
                    executor.name,
                    executor.minimum_retry_threshold,
                    build_job.retries_remaining,
                )
                continue

            logger.debug(
                "Starting builder for job %s with selected executor: %s", job_id, executor.name
            )

            try:
                execution_id = executor.start_builder(registration_token, build_job.build_uuid)
            except:
                logger.exception(
                    "Exception when starting builder for job: %s - Falling back to next configured executor",
                    job_id,
                )
                continue

            started_with_executor = executor

            # Break out of the loop now that we've started a builder successfully.
            break

        # If we didn't start the job, cleanup and return it to the queue.
        if started_with_executor is None:
            logger.error("Could not start ephemeral worker for build %s", build_job.build_uuid)

            # Delete the associated build job record.
            self._orchestrator.delete_key(job_id)
            return False, EPHEMERAL_API_TIMEOUT

        # Store metric data tracking job
        metric_spec = json.dumps(
            {
                "executor_name": started_with_executor.name,
                "start_time": time.time(),
            }
        )

        # Mark the job as scheduled
        setup_time = started_with_executor.setup_time or EPHEMERAL_SETUP_TIMEOUT
        if not self.job_scheduled(job_id, started_with_executor.name, execution_id, setup_time):
            return False, EPHEMERAL_API_TIMEOUT

        self._write_metric_spec(build_job.build_uuid, metric_spec)

        return True, None

    def _job_expired_callback(self, key_change):
        """Callback invoked when job key is changed, except for CREATE, SET events.
        DELETE and EXPIRE exvents make sure the build is marked as completed and remove any
        state tracking, executors left.
        """
        if key_change.event == KeyEvent.EXPIRE:
            job_metadata = json.loads(key_change.value)
            build_job = BuildJob(AttrDict(job_metadata["job_queue_item"]))
            executor_name = job_metadata.get("executor_name")
            execution_id = job_metadata.get("execution_id")

            job_result = BuildJobResult.EXPIRED

            model.build.update_phase_then_close(build_job.build_uuid, RESULT_PHASES[job_result])
            self.on_job_complete(build_job, job_result, executor_name, execution_id)

    def _job_cancelled_callback(self, key_change):
        if key_change.event not in (KeyEvent.CREATE, KeyEvent.SET):
            return

        job_metadata = json.loads(key_change.value)
        build_job = BuildJob(AttrDict(job_metadata["job_queue_item"]))
        executor_name = job_metadata.get("executor_name")
        execution_id = job_metadata.get("execution_id")

        job_result = BuildJobResult.CANCELLED
        self.on_job_complete(build_job, job_result, executor_name, execution_id)

    def _cleanup_job_from_orchestrator(self, build_job):
        """Cleanup the given job from the orchestrator.
        This includes any keys related to that job: job keys, expiry keys, metric keys, ...
        """
        lock_key = self._lock_key(build_job.build_uuid)
        lock_acquired = self._orchestrator.lock(lock_key)
        if lock_acquired:
            try:
                self._orchestrator.delete_key(self._job_key(build_job.build_uuid))
                self._orchestrator.delete_key(self._metric_key(build_job.build_uuid))
            except KeyError:
                pass
            finally:
                self._orchestrator.delete_key(lock_key)  # Release lock

    def append_build_log(self, build_id, log_message):
        """
        Append the logs from Docker's build output.
        This checks if the given message is a "STEP" line from Docker's output,
        and set the log type to "COMMAND" if so.

        See https://github.com/quay/quay-builder/blob/master/docker/log_writer.go
        to get the serialized message structure
        """
        try:
            log_data = json.loads(log_message)
        except ValueError:
            raise

        fully_unwrapped = ""
        keys_to_extract = ["error", "status", "stream"]
        for key in keys_to_extract:
            if key in log_data:
                fully_unwrapped = log_data[key]
                break

        current_log_string = str(fully_unwrapped)
        current_step = _extract_current_step(current_log_string)
        if current_step:
            self.append_log_message(
                self, build_id, current_log_string, log_type=self._build_logs.COMMAND
            )
        else:
            self.append_log_message(self, build_id, current_log_string)

    def append_log_message(self, build_id, log_message, log_type=None, log_data=None):
        """
        Append the given message to the buildlogs.

        log_data adds additional context to the log message.

        log_type can be one of: "command", "phase", "error"
        If the log_message is an output line of Docker's build output, and not the first line of a RUN command,
        log_type should be set to None.

        For example, an entry for a phase change might have the following structure:
        {
          "type":    "phase"
          "message": "build-scheduled"
          "data": {
            "datetime": "2020-10-26 05:37:25.932196"
          }
        }
        """

        log_data = log_data or {}
        log_data["datetime"] = str(datetime.now())

        try:
            self._build_logs.append_log_message(build_id, log_message, log_type, log_data)
        except Exception as e:
            logger.exception("Could not append log to buildlogs for build %s - %s", e, build_id)

    def _running_workers(self):
        return sum([x.running_builders_count for x in self._ordered_executors])

    def _terminate_executor(self, executor_name, execution_id):
        """Cleanup existing running executor running on `executor_name` with `execution_id`."""
        executor = self._executor_name_to_executor.get(executor_name)
        if executor is None:
            logger.error(
                "Could not find registered executor %s to terminate %s", executor_name, execution_id
            )
            return

        # Terminate the executor's execution
        logger.debug("Terminating executor %s with execution id %s", executor_name, execution_id)
        executor.stop_builder(execution_id)

    def _write_metric_spec(self, build_id, payload):
        metric_key = self._metric_key(build_id)
        try:
            self._orchestrator.set_key(
                metric_key,
                payload,
                overwrite=False,
                expiration=self.machine_max_expiration + 60,
            )
        except KeyError:
            logger.warning(
                "Metric already exists in orchestrator for build %s. Build was likely started before and requeued.",
                build_id,
            )
        except (OrchestratorConnectionError, OrchestratorError) as oe:
            logger.error("Error when writing metric for build %s to orchestrator: %s", build_id, oe)

    def _write_duration_metric(self, metric, build_id, job_status=None):
        try:
            metric_data = self._orchestrator.get_key(self._metric_key(build_id))
            parsed_metric_data = json.loads(metric_data)
            start_time = parsed_metric_data["start_time"]
            executor = parsed_metric_data.get("executor_name", "unknown")
            if job_status is not None:
                metric.labels(executor, str(job_status)).observe(time.time() - start_time)
            else:
                metric.labels(executor).observe(time.time() - start_time)
        except Exception:
            logger.exception("Could not write metric for build %s", build_id)

    def _work_checker(self):
        logger.debug("Initializing work checker")
        while True:
            logger.debug("Writing queue metrics")
            self._queue.update_metrics()

            with database.CloseForLongOperation(app.config):
                time.sleep(WORK_CHECK_TIMEOUT)

            logger.debug("Checking for more work from the build queue")
            processing_time = EPHEMERAL_SETUP_TIMEOUT + SETUP_LEEWAY_SECONDS
            job_item = self._queue.get(processing_time=processing_time, ordering_required=True)

            if job_item is None:
                logger.debug(
                    "No additional work found. Going to sleep for %s seconds", WORK_CHECK_TIMEOUT
                )
                continue

            try:
                build_job = BuildJob(job_item)
            except BuildJobLoadException as bjle:
                logger.error(
                    "BuildJobLoadException. Job data: %s. No retry restore. - %s",
                    job_item.body,
                    bjle,
                )
                self._queue.incomplete(job_item, restore_retry=False)
                continue

            build_id = build_job.build_uuid
            job_id = self._job_key(build_id)

            try:
                logger.debug("Creating build job for build %s", build_id)
                self.create_job(build_id, {"job_queue_item": build_job.job_item})
            except BuildJobAlreadyExistsError:
                logger.warning(
                    "Attempted to create job %s that already exists. Cleaning up existing job and returning it to the queue.",
                    job_id,
                )
                self.job_unschedulable(job_id)
                self._queue.incomplete(job_item, restore_retry=True)
                continue
            except BuildJobError as je:
                logger.error("Create job exception. Build %s - %s", build_id, je)
                self._queue.incomplete(job_item, restore_retry=True)
                continue

            try:
                logger.debug("Scheduling build job %s", job_id)
                schedule_success, retry_timeout = self.schedule(build_id)
            except Exception as se:
                logger.exception("Exception when scheduling job %s: %s", build_job.build_uuid, se)
                self._queue.incomplete(job_item, restore_retry=True, retry_after=WORK_CHECK_TIMEOUT)
                continue

            if schedule_success:
                logger.debug("Build job %s scheduled.", job_id)
            else:
                logger.warning(
                    "Unsuccessful schedule. Build ID: %s. Retry restored.",
                    build_job.repo_build.uuid,
                )
                self.job_unschedulable(job_id)
                self._queue.incomplete(job_item, restore_retry=True, retry_after=retry_timeout)


def _extract_current_step(current_status_string):
    """
    Attempts to extract the current step numeric identifier from the given status string.

    Returns the step number or None if none.
    """
    # Older format: `Step 12 :`
    # Newer format: `Step 4/13 :`
    step_increment = re.search(r"Step ([0-9]+)/([0-9]+) :", current_status_string)
    if step_increment:
        return int(step_increment.group(1))

    step_increment = re.search(r"Step ([0-9]+) :", current_status_string)
    if step_increment:
        return int(step_increment.group(1))
