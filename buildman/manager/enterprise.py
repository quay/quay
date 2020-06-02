import logging
import uuid

from buildman.component.basecomponent import BaseComponent
from buildman.component.buildcomponent import BuildComponent
from buildman.manager.basemanager import BaseManager

REGISTRATION_REALM = "registration"
RETRY_TIMEOUT = 5
logger = logging.getLogger(__name__)


class DynamicRegistrationComponent(BaseComponent):
    """
    Component session that handles dynamic registration of the builder components.
    """

    def onConnect(self):
        self.join(REGISTRATION_REALM)

    async def onJoin(self, details):
        logger.debug("Registering registration method")
        await self.register(self._worker_register, "io.quay.buildworker.register")

    def _worker_register(self):
        realm = self.parent_manager.add_build_component()
        logger.debug("Registering new build component+worker with realm %s", realm)
        return realm

    def kind(self):
        return "registration"


class EnterpriseManager(BaseManager):
    """
    Build manager implementation for the Enterprise Registry.
    """

    def __init__(self, *args, **kwargs):
        self.ready_components = set()
        self.all_components = set()
        self.shutting_down = False

        super(EnterpriseManager, self).__init__(*args, **kwargs)

    def initialize(self, manager_config):
        # Add a component which is used by build workers for dynamic registration. Unlike
        # production, build workers in enterprise are long-lived and register dynamically.
        self.register_component(REGISTRATION_REALM, DynamicRegistrationComponent)

    def overall_setup_time(self):
        # Builders are already registered, so the setup time should be essentially instant. We therefore
        # only return a minute here.
        return 60

    def add_build_component(self):
        """
        Adds a new build component for an Enterprise Registry.
        """
        # Generate a new unique realm ID for the build worker.
        realm = str(uuid.uuid4())
        new_component = self.register_component(realm, BuildComponent, token="")
        self.all_components.add(new_component)
        return realm

    async def schedule(self, build_job):
        """
        Schedules a build for an Enterprise Registry.
        """
        if self.shutting_down or not self.ready_components:
            return False, RETRY_TIMEOUT

        component = self.ready_components.pop()

        await component.start_build(build_job)

        return True, None

    async def build_component_ready(self, build_component):
        self.ready_components.add(build_component)

    def shutdown(self):
        self.shutting_down = True

    async def job_completed(self, build_job, job_status, build_component):
        await self.job_complete_callback(build_job, job_status)

    def build_component_disposed(self, build_component, timed_out):
        self.all_components.remove(build_component)
        if build_component in self.ready_components:
            self.ready_components.remove(build_component)

        self.unregister_component(build_component)

    def num_workers(self):
        return len(self.all_components)
