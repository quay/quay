import logging

from buildman.orchestrator import orchestrator_from_config, OrchestratorError
from util import slash_join


logger = logging.getLogger(__name__)


CANCEL_PREFIX = "cancel/"


class OrchestratorCanceller(object):
    """
    An asynchronous way to cancel a build with any Orchestrator.
    """

    def __init__(self, config):
        self._orchestrator = orchestrator_from_config(config, canceller_only=True)

    def try_cancel_build(self, build_uuid):
        logger.debug("Cancelling build %s", build_uuid)
        cancel_key = slash_join(CANCEL_PREFIX, build_uuid)
        try:
            self._orchestrator.set_key_sync(cancel_key, build_uuid, expiration=60)
            return True
        except OrchestratorError:
            logger.exception("Failed to write cancel action to redis with uuid %s", build_uuid)
            return False
