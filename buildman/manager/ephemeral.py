import asyncio
import logging
import uuid
import calendar
import json
import time

from collections import namedtuple
from datetime import datetime, timedelta
from six import iteritems

from prometheus_client import Counter, Histogram

from buildman.orchestrator import (
    orchestrator_from_config,
    KeyEvent,
    OrchestratorError,
    OrchestratorConnectionError,
    ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION,
)
from buildman.manager.basemanager import BaseManager
from buildman.manager.executor import PopenExecutor, EC2Executor, KubernetesExecutor
from buildman.component.buildcomponent import BuildComponent
from buildman.jobutil.buildjob import BuildJob
from buildman.server import BuildJobResult
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
    labelnames=["executor", "job_status"],
)


JOB_PREFIX = "building/"
LOCK_PREFIX = "lock/"
REALM_PREFIX = "realm/"
CANCEL_PREFIX = "cancel/"
METRIC_PREFIX = "metric/"

CANCELED_LOCK_PREFIX = slash_join(LOCK_PREFIX, "job-cancelled")
EXPIRED_LOCK_PREFIX = slash_join(LOCK_PREFIX, "job-expired")

EPHEMERAL_API_TIMEOUT = 20
EPHEMERAL_SETUP_TIMEOUT = 500

RETRY_IMMEDIATELY_SLEEP_DURATION = 0
TOO_MANY_WORKERS_SLEEP_DURATION = 10


BuildInfo = namedtuple("BuildInfo", ["component", "build_job", "execution_id", "executor_name"])


class EphemeralBuilderManager(BaseManager):
    """
    Build manager implementation for the Enterprise Registry.
    """

    EXECUTORS = {
        "popen": PopenExecutor,
        "ec2": EC2Executor,
        "kubernetes": KubernetesExecutor,
    }

    def __init__(self, *args, **kwargs):
        super(EphemeralBuilderManager, self).__init__(*args, **kwargs)

        self._shutting_down = False

        self._manager_config = None
        self._orchestrator = None

        # The registered executors available for running jobs, in order.
        self._ordered_executors = []

        # The registered executors, mapped by their unique name.
        self._executor_name_to_executor = {}

        # Map from builder component to its associated job.
        self._component_to_job = {}

        # Map from build UUID to a BuildInfo tuple with information about the build.
        self._build_uuid_to_info = {}

    def overall_setup_time(self):
        return EPHEMERAL_SETUP_TIMEOUT

    async def _mark_job_incomplete(self, build_job, build_info):
        """
        Marks a job as incomplete, in response to a failure to start or a timeout.
        """
        executor_name = build_info.executor_name
        execution_id = build_info.execution_id

        logger.warning(
            "Build executor failed to successfully boot with execution id %s", execution_id
        )

        # Take a lock to ensure that only one manager reports the build as incomplete for this
        # execution.
        lock_key = slash_join(self._expired_lock_prefix, build_job.build_uuid, execution_id)
        acquired_lock = await self._orchestrator.lock(lock_key)
        if acquired_lock:
            try:
                # Clean up the bookkeeping for the job.
                await self._orchestrator.delete_key(self._job_key(build_job))
            except KeyError:
                logger.debug(
                    "Could not delete job key %s; might have been removed already",
                    build_job.build_uuid,
                )

            logger.error(
                "[BUILD INTERNAL ERROR] Build ID: %s. Exec name: %s. Exec ID: %s",
                build_job.build_uuid,
                executor_name,
                execution_id,
            )
            await (
                self.job_complete_callback(
                    build_job, BuildJobResult.INCOMPLETE, executor_name, update_phase=True
                )
            )
        else:
            logger.debug("Did not get lock for job-expiration for job %s", build_job.build_uuid)

    async def _job_callback(self, key_change):
        """
        This is the callback invoked when keys related to jobs are changed. It ignores all events
        related to the creation of new jobs. Deletes or expirations cause checks to ensure they've
        been properly marked as completed.

        :param key_change: the event and value produced by a key changing in the orchestrator
        :type key_change: :class:`KeyChange`
        """
        if key_change.event in (KeyEvent.CREATE, KeyEvent.SET):
            return

        elif key_change.event in (KeyEvent.DELETE, KeyEvent.EXPIRE):
            # Handle the expiration/deletion.
            job_metadata = json.loads(key_change.value)
            build_job = BuildJob(AttrDict(job_metadata["job_queue_item"]))
            logger.debug('Got "%s" of job %s', key_change.event, build_job.build_uuid)

            # Get the build info.
            build_info = self._build_uuid_to_info.get(build_job.build_uuid, None)
            if build_info is None:
                logger.debug(
                    'No build info for "%s" job %s (%s); probably already deleted by this manager',
                    key_change.event,
                    build_job.build_uuid,
                    job_metadata,
                )
                return

            if key_change.event != KeyEvent.EXPIRE:
                # If the etcd action was not an expiration, then it was already deleted by some manager and
                # the execution was therefore already shutdown. All that's left is to remove the build info.
                self._build_uuid_to_info.pop(build_job.build_uuid, None)
                return

            logger.debug(
                "got expiration for job %s with metadata: %s", build_job.build_uuid, job_metadata
            )

            if not job_metadata.get("had_heartbeat", False):
                # If we have not yet received a heartbeat, then the node failed to boot in some way.
                # We mark the job as incomplete here.
                await self._mark_job_incomplete(build_job, build_info)

            # Finally, we terminate the build execution for the job. We don't do this under a lock as
            # terminating a node is an atomic operation; better to make sure it is terminated than not.
            logger.debug(
                "Terminating expired build executor for job %s with execution id %s",
                build_job.build_uuid,
                build_info.execution_id,
            )
            await self.kill_builder_executor(build_job.build_uuid)
        else:
            logger.warning(
                "Unexpected KeyEvent (%s) on job key: %s", key_change.event, key_change.key
            )

    async def _realm_callback(self, key_change):
        logger.debug("realm callback for key: %s", key_change.key)
        if key_change.event == KeyEvent.CREATE:
            # Listen on the realm created by ourselves or another worker.
            realm_spec = json.loads(key_change.value)
            self._register_realm(realm_spec)

        elif key_change.event in (KeyEvent.DELETE, KeyEvent.EXPIRE):
            # Stop listening for new connections on the realm, if we did not get the connection.
            realm_spec = json.loads(key_change.value)
            realm_id = realm_spec["realm"]

            build_job = BuildJob(AttrDict(realm_spec["job_queue_item"]))
            build_uuid = build_job.build_uuid

            logger.debug("Realm key %s for build %s was %s", realm_id, build_uuid, key_change.event)
            build_info = self._build_uuid_to_info.get(build_uuid, None)
            if build_info is not None:
                # Pop off the component and if we find one, then the build has not connected to this
                # manager, so we can safely unregister its component.
                component = self._component_to_job.pop(build_info.component, None)
                if component is not None:
                    # We were not the manager which the worker connected to, remove the bookkeeping for it
                    logger.debug("Unregistering unused component for build %s", build_uuid)
                    self.unregister_component(build_info.component)

            # If the realm has expired, then perform cleanup of the executor.
            if key_change.event == KeyEvent.EXPIRE:
                execution_id = realm_spec.get("execution_id", None)
                executor_name = realm_spec.get("executor_name", "EC2Executor")

                # Cleanup the job, since it never started.
                logger.debug("Job %s for incomplete marking: %s", build_uuid, build_info)
                if build_info is not None:
                    await self._mark_job_incomplete(build_job, build_info)

                # Cleanup the executor.
                logger.debug(
                    "Realm %s expired for job %s, terminating executor %s with execution id %s",
                    realm_id,
                    build_uuid,
                    executor_name,
                    execution_id,
                )
                await self.terminate_executor(executor_name, execution_id)

        else:
            logger.warning(
                "Unexpected action (%s) on realm key: %s", key_change.event, key_change.key
            )

    def _register_realm(self, realm_spec):
        logger.debug("Got call to register realm %s with manager", realm_spec["realm"])

        # Create the build information block for the registered realm.
        build_job = BuildJob(AttrDict(realm_spec["job_queue_item"]))
        execution_id = realm_spec.get("execution_id", None)
        executor_name = realm_spec.get("executor_name", "EC2Executor")

        logger.debug("Registering realm %s with manager: %s", realm_spec["realm"], realm_spec)
        component = self.register_component(
            realm_spec["realm"], BuildComponent, token=realm_spec["token"]
        )

        build_info = BuildInfo(
            component=component,
            build_job=build_job,
            execution_id=execution_id,
            executor_name=executor_name,
        )

        self._component_to_job[component] = build_job
        self._build_uuid_to_info[build_job.build_uuid] = build_info

        logger.debug("Registered realm %s with manager", realm_spec["realm"])
        return component

    @property
    def registered_executors(self):
        return self._ordered_executors

    async def _register_existing_realms(self):
        try:
            all_realms = await self._orchestrator.get_prefixed_keys(self._realm_prefix)

            # Register all existing realms found.
            encountered = {
                self._register_realm(json.loads(realm_data)) for _realm, realm_data in all_realms
            }

            # Remove any components not encountered so we can clean up.
            for component, job in iteritems(self._component_to_job):
                if not component in encountered:
                    self._component_to_job.pop(component, None)
                    self._build_uuid_to_info.pop(job.build_uuid, None)

        except KeyError:
            pass

    def _load_executor(self, executor_kind_name, executor_config):
        executor_klass = EphemeralBuilderManager.EXECUTORS.get(executor_kind_name)
        if executor_klass is None:
            logger.error("Unknown executor %s; skipping install", executor_kind_name)
            return

        executor = executor_klass(executor_config, self.manager_hostname)
        if executor.name in self._executor_name_to_executor:
            raise Exception("Executor with name %s already registered" % executor.name)

        self._ordered_executors.append(executor)
        self._executor_name_to_executor[executor.name] = executor

    def _config_prefix(self, key):
        if self._manager_config.get("ORCHESTRATOR") is None:
            return key

        prefix = self._manager_config.get("ORCHESTRATOR_PREFIX", "")
        return slash_join(prefix, key).lstrip("/") + "/"

    @property
    def _job_prefix(self):
        return self._config_prefix(JOB_PREFIX)

    @property
    def _realm_prefix(self):
        return self._config_prefix(REALM_PREFIX)

    @property
    def _cancel_prefix(self):
        return self._config_prefix(CANCEL_PREFIX)

    @property
    def _metric_prefix(self):
        return self._config_prefix(METRIC_PREFIX)

    @property
    def _expired_lock_prefix(self):
        return self._config_prefix(EXPIRED_LOCK_PREFIX)

    @property
    def _canceled_lock_prefix(self):
        return self._config_prefix(CANCELED_LOCK_PREFIX)

    def _metric_key(self, realm):
        """
        Create a key which is used to track a job in the Orchestrator.

        :param realm: realm for the build
        :type realm: str
        :returns: key used to track jobs
        :rtype: str
        """
        return slash_join(self._metric_prefix, realm)

    def _job_key(self, build_job):
        """
        Creates a key which is used to track a job in the Orchestrator.

        :param build_job: unique job identifier for a build
        :type build_job: str
        :returns: key used to track the job
        :rtype: str
        """
        return slash_join(self._job_prefix, build_job.job_details["build_uuid"])

    def _realm_key(self, realm):
        """
        Create a key which is used to track an incoming connection on a realm.

        :param realm: realm for the build
        :type realm: str
        :returns: key used to track the connection to the realm
        :rtype: str
        """
        return slash_join(self._realm_prefix, realm)

    def initialize(self, manager_config):
        logger.debug("Calling initialize")
        self._manager_config = manager_config

        # Note: Executor config can be defined either as a single block of EXECUTOR_CONFIG (old style)
        # or as a new set of executor configurations, with the order determining how we fallback. We
        # check for both here to ensure backwards compatibility.
        if manager_config.get("EXECUTORS"):
            for executor_config in manager_config["EXECUTORS"]:
                self._load_executor(executor_config.get("EXECUTOR"), executor_config)
        else:
            self._load_executor(
                manager_config.get("EXECUTOR"), manager_config.get("EXECUTOR_CONFIG")
            )

        logger.debug("calling orchestrator_from_config")
        self._orchestrator = orchestrator_from_config(manager_config)

        logger.debug("setting on_key_change callbacks for job, cancel, realm")
        self._orchestrator.on_key_change(self._job_prefix, self._job_callback)
        self._orchestrator.on_key_change(self._cancel_prefix, self._cancel_callback)
        self._orchestrator.on_key_change(
            self._realm_prefix, self._realm_callback, restarter=self._register_existing_realms
        )

        # Load components for all realms currently known to the cluster
        asyncio.create_task(self._register_existing_realms())

    def shutdown(self):
        logger.debug("Shutting down worker.")
        if self._orchestrator is not None:
            self._orchestrator.shutdown()

    async def schedule(self, build_job):
        build_uuid = build_job.job_details["build_uuid"]
        logger.debug("Calling schedule with job: %s", build_uuid)

        # Check if there are worker slots available by checking the number of jobs in the orchestrator
        allowed_worker_count = self._manager_config.get("ALLOWED_WORKER_COUNT", 1)
        try:
            active_jobs = await self._orchestrator.get_prefixed_keys(self._job_prefix)
            workers_alive = len(active_jobs)
        except KeyError:
            workers_alive = 0
        except OrchestratorConnectionError:
            logger.exception(
                "Could not read job count from orchestrator for job due to orchestrator being down"
            )
            return False, ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION
        except OrchestratorError:
            logger.exception(
                "Exception when reading job count from orchestrator for job: %s", build_uuid
            )
            return False, RETRY_IMMEDIATELY_SLEEP_DURATION

        logger.debug("Total jobs (scheduling job %s): %s", build_uuid, workers_alive)

        if workers_alive >= allowed_worker_count:
            logger.debug(
                "Too many workers alive, unable to start new worker for build job: %s. %s >= %s",
                build_uuid,
                workers_alive,
                allowed_worker_count,
            )
            return False, TOO_MANY_WORKERS_SLEEP_DURATION

        job_key = self._job_key(build_job)

        # First try to take a lock for this job, meaning we will be responsible for its lifeline
        realm = str(uuid.uuid4())
        token = str(uuid.uuid4())
        nonce = str(uuid.uuid4())

        machine_max_expiration = self._manager_config.get("MACHINE_MAX_TIME", 7200)
        max_expiration = datetime.utcnow() + timedelta(seconds=machine_max_expiration)

        payload = {
            "max_expiration": calendar.timegm(max_expiration.timetuple()),
            "nonce": nonce,
            "had_heartbeat": False,
            "job_queue_item": build_job.job_item,
        }

        lock_payload = json.dumps(payload)
        logger.debug(
            "Writing key for job %s with expiration in %s seconds",
            build_uuid,
            EPHEMERAL_SETUP_TIMEOUT,
        )

        try:
            await (
                self._orchestrator.set_key(
                    job_key, lock_payload, overwrite=False, expiration=EPHEMERAL_SETUP_TIMEOUT
                )
            )
        except KeyError:
            logger.warning(
                "Job: %s already exists in orchestrator, timeout may be misconfigured. Removing key %s from Redis.", build_uuid, job_key
            )
            await self._orchestrator.delete_key(job_key)
            return False, EPHEMERAL_API_TIMEOUT
        except OrchestratorConnectionError:
            logger.exception(
                "Exception when writing job %s to orchestrator; could not connect", build_uuid
            )
            return False, ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION
        except OrchestratorError:
            logger.exception("Exception when writing job %s to orchestrator", build_uuid)
            return False, RETRY_IMMEDIATELY_SLEEP_DURATION

        # Got a lock, now lets boot the job via one of the registered executors.
        started_with_executor = None
        execution_id = None

        logger.debug("Registered executors are: %s", [ex.name for ex in self._ordered_executors])
        for executor in self._ordered_executors:
            # Check if we can use this executor based on its whitelist, by namespace.
            namespace = build_job.namespace
            if not executor.allowed_for_namespace(namespace):
                logger.debug(
                    "Job %s (namespace: %s) cannot use executor %s",
                    build_uuid,
                    namespace,
                    executor.name,
                )
                continue

            # Check if we can use this executor based on the retries remaining.
            if executor.minimum_retry_threshold > build_job.retries_remaining:
                build_fallback.labels(executor.name).inc()
                logger.warning(
                    "Job %s cannot use executor %s as it is below retry threshold %s (retry #%s) - Falling back to next configured executor",
                    build_uuid,
                    executor.name,
                    executor.minimum_retry_threshold,
                    build_job.retries_remaining,
                )
                continue

            logger.debug(
                "Starting builder for job %s with selected executor: %s", build_uuid, executor.name
            )

            try:
                execution_id = await executor.start_builder(realm, token, build_uuid)
            except:
                logger.exception("Exception when starting builder for job: %s", build_uuid)
                continue

            started_with_executor = executor

            # Break out of the loop now that we've started a builder successfully.
            break

        # If we didn't start the job, cleanup and return it to the queue.
        if started_with_executor is None:
            logger.error("Could not start ephemeral worker for build %s", build_uuid)

            # Delete the associated build job record.
            await self._orchestrator.delete_key(job_key)
            return False, EPHEMERAL_API_TIMEOUT

        # Job was started!
        logger.debug(
            "Started execution with ID %s for job: %s with executor: %s",
            execution_id,
            build_uuid,
            started_with_executor.name,
        )

        # Store metric data
        metric_spec = json.dumps(
            {"executor_name": started_with_executor.name, "start_time": time.time(),}
        )

        try:
            await (
                self._orchestrator.set_key(
                    self._metric_key(realm),
                    metric_spec,
                    overwrite=False,
                    expiration=machine_max_expiration + 10,
                )
            )
        except KeyError:
            logger.error(
                "Realm %s already exists in orchestrator for job %s "
                + "UUID collision or something is very very wrong.",
                realm,
                build_uuid,
            )
        except OrchestratorError:
            logger.exception(
                "Exception when writing realm %s to orchestrator for job %s", realm, build_uuid
            )

        # Store the realm spec which will allow any manager to accept this builder when it connects
        realm_spec = json.dumps(
            {
                "realm": realm,
                "token": token,
                "execution_id": execution_id,
                "executor_name": started_with_executor.name,
                "job_queue_item": build_job.job_item,
            }
        )

        try:
            setup_time = started_with_executor.setup_time or self.overall_setup_time()
            logger.debug(
                "Writing job key for job %s using executor %s with ID %s and ttl %s",
                build_uuid,
                started_with_executor.name,
                execution_id,
                setup_time,
            )
            await (
                self._orchestrator.set_key(
                    self._realm_key(realm), realm_spec, expiration=setup_time
                )
            )
        except OrchestratorConnectionError:
            logger.exception(
                "Exception when writing realm %s to orchestrator for job %s", realm, build_uuid
            )
            return False, ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION
        except OrchestratorError:
            logger.exception(
                "Exception when writing realm %s to orchestrator for job %s", realm, build_uuid
            )
            return False, setup_time

        logger.debug(
            "Builder spawn complete for job %s using executor %s with ID %s ",
            build_uuid,
            started_with_executor.name,
            execution_id,
        )
        return True, None

    async def build_component_ready(self, build_component):
        logger.debug(
            "Got component ready for component with realm %s", build_component.builder_realm
        )

        # Pop off the job for the component.
        # We do so before we send out the watch below, as it will also remove this mapping.
        job = self._component_to_job.pop(build_component, None)
        if job is None:
            # This will occur once the build finishes, so no need to worry about it.
            # We log in case it happens outside of the expected flow.
            logger.debug(
                "Could not find job for the build component on realm %s; component is ready",
                build_component.builder_realm,
            )
            return

        # Start the build job.
        logger.debug(
            "Sending build %s to newly ready component on realm %s",
            job.build_uuid,
            build_component.builder_realm,
        )
        await build_component.start_build(job)

        await self._write_duration_metric(build_ack_duration, build_component.builder_realm)

        # Clean up the bookkeeping for allowing any manager to take the job.
        try:
            await (self._orchestrator.delete_key(self._realm_key(build_component.builder_realm)))
        except KeyError:
            logger.warning("Could not delete realm key %s", build_component.builder_realm)

    def build_component_disposed(self, build_component, timed_out):
        logger.debug("Calling build_component_disposed.")
        self.unregister_component(build_component)

    async def job_completed(self, build_job, job_status, build_component):
        logger.debug(
            "Calling job_completed for job %s with status: %s", build_job.build_uuid, job_status
        )

        await (
            self._write_duration_metric(
                build_duration, build_component.builder_realm, job_status=job_status
            )
        )

        # Mark the job as completed. Since this is being invoked from the component, we don't need
        # to ask for the phase to be updated as well.
        build_info = self._build_uuid_to_info.get(build_job.build_uuid, None)
        executor_name = build_info.executor_name if build_info else None
        await (self.job_complete_callback(build_job, job_status, executor_name, update_phase=False))

        # Kill the ephemeral builder.
        await self.kill_builder_executor(build_job.build_uuid)

        # Delete the build job from the orchestrator.
        try:
            job_key = self._job_key(build_job)
            await self._orchestrator.delete_key(job_key)
        except KeyError:
            logger.debug("Builder is asking for job to be removed, but work already completed")
        except OrchestratorConnectionError:
            logger.exception("Could not remove job key as orchestrator is not available")
            await asyncio.sleep(ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION)
            return

        # Delete the metric from the orchestrator.
        try:
            metric_key = self._metric_key(build_component.builder_realm)
            await self._orchestrator.delete_key(metric_key)
        except KeyError:
            logger.debug("Builder is asking for metric to be removed, but key not found")
        except OrchestratorConnectionError:
            logger.exception("Could not remove metric key as orchestrator is not available")
            await asyncio.sleep(ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION)
            return

        logger.debug("job_completed for job %s with status: %s", build_job.build_uuid, job_status)

    async def kill_builder_executor(self, build_uuid):
        logger.debug("Starting termination of executor for job %s", build_uuid)
        build_info = self._build_uuid_to_info.pop(build_uuid, None)
        if build_info is None:
            logger.debug(
                "Build information not found for build %s; skipping termination", build_uuid
            )
            return

        # Remove the build's component.
        self._component_to_job.pop(build_info.component, None)

        # Stop the build node/executor itself.
        await self.terminate_executor(build_info.executor_name, build_info.execution_id)

    async def terminate_executor(self, executor_name, execution_id):
        executor = self._executor_name_to_executor.get(executor_name)
        if executor is None:
            logger.error("Could not find registered executor %s", executor_name)
            return

        # Terminate the executor's execution.
        logger.debug("Terminating executor %s with execution id %s", executor_name, execution_id)
        await executor.stop_builder(execution_id)

    async def job_heartbeat(self, build_job):
        """
    :param build_job: the identifier for the build
    :type build_job: str
    """
        self.job_heartbeat_callback(build_job)
        self._extend_job_in_orchestrator(build_job)

    async def _extend_job_in_orchestrator(self, build_job):
        try:
            job_data = await self._orchestrator.get_key(self._job_key(build_job))
        except KeyError:
            logger.debug("Job %s no longer exists in the orchestrator", build_job.build_uuid)
            return
        except OrchestratorConnectionError:
            logger.exception("failed to connect when attempted to extend job")

        build_job_metadata = json.loads(job_data)

        max_expiration = datetime.utcfromtimestamp(build_job_metadata["max_expiration"])
        max_expiration_remaining = max_expiration - datetime.utcnow()
        max_expiration_sec = max(0, int(max_expiration_remaining.total_seconds()))

        ttl = min(self.heartbeat_period_sec * 2, max_expiration_sec)
        payload = {
            "job_queue_item": build_job.job_item,
            "max_expiration": build_job_metadata["max_expiration"],
            "had_heartbeat": True,
        }

        try:
            await (
                self._orchestrator.set_key(
                    self._job_key(build_job), json.dumps(payload), expiration=ttl
                )
            )
        except OrchestratorConnectionError:
            logger.exception(
                "Could not update heartbeat for job as the orchestrator is not available"
            )
            await asyncio.sleep(ORCHESTRATOR_UNAVAILABLE_SLEEP_DURATION)

    async def _write_duration_metric(self, metric, realm, job_status=None):
        """ :returns: True if the metric was written, otherwise False
            :rtype: bool
        """
        try:
            metric_data = await self._orchestrator.get_key(self._metric_key(realm))
            parsed_metric_data = json.loads(metric_data)
            start_time = parsed_metric_data["start_time"]
            executor = parsed_metric_data.get("executor_name", "unknown")
            if job_status is not None:
                metric.labels(executor, str(job_status)).observe(time.time() - start_time)
            else:
                metric.labels(executor).observe(time.time() - start_time)
        except Exception:
            logger.exception("Could not write metric for realm %s", realm)

    def num_workers(self):
        """
        The number of workers we're managing locally.

        :returns: the number of the workers locally managed
        :rtype: int
        """
        return len(self._component_to_job)

    async def _cancel_callback(self, key_change):
        if key_change.event not in (KeyEvent.CREATE, KeyEvent.SET):
            return

        build_uuid = key_change.value
        build_info = self._build_uuid_to_info.get(build_uuid, None)
        if build_info is None:
            logger.debug('No build info for "%s" job %s', key_change.event, build_uuid)
            return False

        lock_key = slash_join(self._canceled_lock_prefix, build_uuid, build_info.execution_id)
        lock_acquired = await self._orchestrator.lock(lock_key)
        if lock_acquired:
            builder_realm = build_info.component.builder_realm
            await self.kill_builder_executor(build_uuid)
            await self._orchestrator.delete_key(self._realm_key(builder_realm))
            await self._orchestrator.delete_key(self._metric_key(builder_realm))
            await self._orchestrator.delete_key(slash_join(self._job_prefix, build_uuid))

        # This is outside the lock so we can un-register the component wherever it is registered to.
        await build_info.component.cancel_build()
