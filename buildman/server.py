import logging
import json

from datetime import timedelta
from threading import Event

import asyncio

from aiowsgi import create_server as create_wsgi_server
from autobahn.asyncio.wamp import RouterFactory, RouterSessionFactory
from autobahn.asyncio.websocket import WampWebSocketServerFactory
from autobahn.wamp import types
from flask import Flask

from app import app
from buildman.enums import BuildJobResult, BuildServerStatus, RESULT_PHASES
from buildman.jobutil.buildjob import BuildJob, BuildJobLoadException
from buildman.jobutil.buildstatus import StatusHandler
from data import database, model


logger = logging.getLogger(__name__)

WORK_CHECK_TIMEOUT = 10
TIMEOUT_PERIOD_MINUTES = 20
JOB_TIMEOUT_SECONDS = 300
SETUP_LEEWAY_SECONDS = 30
MINIMUM_JOB_EXTENSION = timedelta(minutes=1)

HEARTBEAT_PERIOD_SEC = 30


class BuilderServer(object):
    """
    Server which handles both HTTP and WAMP requests, managing the full state of the build
    controller.
    """

    def __init__(
        self,
        registry_hostname,
        queue,
        build_logs,
        user_files,
        lifecycle_manager_klass,
        lifecycle_manager_config,
        manager_hostname,
    ):
        self._loop = None
        self._current_status = BuildServerStatus.STARTING
        self._current_components = []
        self._realm_map = {}
        self._job_count = 0

        self._session_factory = RouterSessionFactory(RouterFactory())
        self._registry_hostname = registry_hostname
        self._queue = queue
        self._build_logs = build_logs
        self._user_files = user_files
        self._lifecycle_manager = lifecycle_manager_klass(
            self._register_component,
            self._unregister_component,
            self._job_heartbeat,
            self._job_complete,
            manager_hostname,
            HEARTBEAT_PERIOD_SEC,
        )
        self._lifecycle_manager_config = lifecycle_manager_config

        self._shutdown_event = Event()
        self._current_status = BuildServerStatus.RUNNING

        self._register_controller()

    def _register_controller(self):
        controller_app = Flask("controller")
        server = self

        @controller_app.route("/status")
        def status():
            (
                running_count,
                available_not_running_count,
                available_count,
            ) = server._queue.get_metrics()

            workers = [
                component
                for component in server._current_components
                if component.kind() == "builder"
            ]

            data = {
                "status": server._current_status,
                "running_local": server._job_count,
                "running_total": running_count,
                "workers": len(workers),
                "job_total": available_count + running_count,
            }

            return json.dumps(data)

        self._controller_app = controller_app

    def run(self, host, websocket_port, controller_port, ssl=None):
        logger.debug("Initializing the lifecycle manager")
        self._lifecycle_manager.initialize(self._lifecycle_manager_config)

        logger.debug("Initializing all members of the event loop")
        loop = asyncio.get_event_loop()

        logger.debug(
            "Starting server on port %s, with controller on port %s",
            websocket_port,
            controller_port,
        )

        try:
            loop.run_until_complete(
                self._initialize(loop, host, websocket_port, controller_port, ssl)
            )
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    def close(self):
        logger.debug("Requested server shutdown")
        self._current_status = BuildServerStatus.SHUTDOWN
        self._lifecycle_manager.shutdown()
        self._shutdown_event.wait()
        logger.debug("Shutting down server")

    def _register_component(self, realm, component_klass, **kwargs):
        """
        Registers a component with the server.

        The component_klass must derive from BaseComponent.
        """
        logger.debug("Registering component with realm %s", realm)
        if realm in self._realm_map:
            logger.debug("Component with realm %s already registered", realm)
            return self._realm_map[realm]

        component = component_klass(types.ComponentConfig(realm=realm), realm=realm, **kwargs)
        component.server = self
        component.parent_manager = self._lifecycle_manager
        component.build_logs = self._build_logs
        component.user_files = self._user_files
        component.registry_hostname = self._registry_hostname

        self._realm_map[realm] = component
        self._current_components.append(component)
        self._session_factory.add(component)
        return component

    def _unregister_component(self, component):
        logger.debug(
            "Unregistering component with realm %s and token %s",
            component.builder_realm,
            component.expected_token,
        )

        self._realm_map.pop(component.builder_realm, None)

        if component in self._current_components:
            self._current_components.remove(component)
            self._session_factory.remove(component)

    def _job_heartbeat(self, build_job):
        self._queue.extend_processing(
            build_job.job_item,
            seconds_from_now=JOB_TIMEOUT_SECONDS,
            minimum_extension=MINIMUM_JOB_EXTENSION,
        )

    async def _job_complete(self, build_job, job_status, executor_name=None, update_phase=False):
        if job_status == BuildJobResult.INCOMPLETE:
            logger.warning(
                "[BUILD INCOMPLETE: job complete] Build ID: %s. No retry restore.",
                build_job.repo_build.uuid,
            )
            self._queue.incomplete(build_job.job_item, restore_retry=False, retry_after=30)
        else:
            self._queue.complete(build_job.job_item)

        # Update the trigger failure tracking (if applicable).
        if build_job.repo_build.trigger is not None:
            model.build.update_trigger_disable_status(
                build_job.repo_build.trigger, RESULT_PHASES[job_status]
            )

        if update_phase:
            status_handler = StatusHandler(self._build_logs, build_job.repo_build.uuid)
            await status_handler.set_phase(RESULT_PHASES[job_status])

        self._job_count = self._job_count - 1

        if self._current_status == BuildServerStatus.SHUTDOWN and not self._job_count:
            self._shutdown_event.set()

    async def _work_checker(self):
        logger.debug("Initializing work checker")
        while self._current_status == BuildServerStatus.RUNNING:
            with database.CloseForLongOperation(app.config):
                await asyncio.sleep(WORK_CHECK_TIMEOUT)

            logger.debug(
                "Checking for more work for %d active workers",
                self._lifecycle_manager.num_workers(),
            )

            processing_time = self._lifecycle_manager.overall_setup_time() + SETUP_LEEWAY_SECONDS
            job_item = self._queue.get(processing_time=processing_time, ordering_required=True)
            if job_item is None:
                logger.debug(
                    "No additional work found. Going to sleep for %s seconds", WORK_CHECK_TIMEOUT
                )
                continue

            try:
                build_job = BuildJob(job_item)
            except BuildJobLoadException as irbe:
                logger.warning(
                    "[BUILD INCOMPLETE: job load exception] Job data: %s. No retry restore.",
                    job_item.body,
                )
                logger.exception(irbe)
                self._queue.incomplete(job_item, restore_retry=False)
                continue

            logger.debug(
                "Checking for an avaliable worker for build job %s", build_job.repo_build.uuid
            )

            try:
                schedule_success, retry_timeout = await self._lifecycle_manager.schedule(build_job)
            except:
                logger.warning(
                    "[BUILD INCOMPLETE: scheduling] Build ID: %s. Retry restored.",
                    build_job.repo_build.uuid,
                )
                logger.exception("Exception when scheduling job: %s", build_job.repo_build.uuid)
                self._current_status = BuildServerStatus.EXCEPTION
                self._queue.incomplete(job_item, restore_retry=True, retry_after=WORK_CHECK_TIMEOUT)
                return

            if schedule_success:
                logger.debug("Marking build %s as scheduled", build_job.repo_build.uuid)
                status_handler = StatusHandler(self._build_logs, build_job.repo_build.uuid)
                await status_handler.set_phase(database.BUILD_PHASE.BUILD_SCHEDULED)

                self._job_count = self._job_count + 1
                logger.debug(
                    "Build job %s scheduled. Running: %s",
                    build_job.repo_build.uuid,
                    self._job_count,
                )
            else:
                logger.warning(
                    "[BUILD INCOMPLETE: no schedule] Build ID: %s. Retry restored.",
                    build_job.repo_build.uuid,
                )
                logger.debug(
                    "All workers are busy for job %s Requeuing after %s seconds.",
                    build_job.repo_build.uuid,
                    retry_timeout,
                )
                self._queue.incomplete(job_item, restore_retry=True, retry_after=retry_timeout)

    async def _queue_metrics_updater(self):
        logger.debug("Initializing queue metrics updater")
        while self._current_status == BuildServerStatus.RUNNING:
            logger.debug("Writing metrics")
            self._queue.update_metrics()

            logger.debug("Metrics going to sleep for 30 seconds")
            await asyncio.sleep(30)

    async def _initialize(self, loop, host, websocket_port, controller_port, ssl=None):
        self._loop = loop

        # Create the WAMP server.
        transport_factory = WampWebSocketServerFactory(self._session_factory, debug_wamp=False)
        transport_factory.setProtocolOptions(failByDrop=True)

        # Initialize the controller server and the WAMP server
        create_wsgi_server(
            self._controller_app, loop=loop, host=host, port=controller_port, ssl=ssl
        )
        await loop.create_server(transport_factory, host, websocket_port, ssl=ssl)

        # Initialize the metrics updater
        asyncio.create_task(self._queue_metrics_updater())

        # Initialize the work queue checker.
        await self._work_checker()
