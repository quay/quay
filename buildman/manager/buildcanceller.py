import logging

from buildman.manager.orchestrator_canceller import OrchestratorCanceller
from buildman.manager.noop_canceller import NoopCanceller

logger = logging.getLogger(__name__)

CANCELLERS = {"ephemeral": OrchestratorCanceller}


class BuildCanceller(object):
    """
    A class to manage cancelling a build.
    """

    def __init__(self, app=None):
        self.build_manager_config = app.config.get("BUILD_MANAGER")
        if app is None or self.build_manager_config is None:
            self.handler = NoopCanceller()
        else:
            self.handler = None

    def try_cancel_build(self, uuid):
        """
        A method to kill a running build.
        """
        if self.handler is None:
            canceller = CANCELLERS.get(self.build_manager_config[0], NoopCanceller)
            self.handler = canceller(self.build_manager_config[1])

        return self.handler.try_cancel_build(uuid)
