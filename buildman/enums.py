from data.database import BUILD_PHASE


class BuildJobResult(object):
    """
    Build job result enum.
    """

    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    ERROR = "error"


class BuildServerStatus(object):
    """
    Build server status enum.
    """

    STARTING = "starting"
    RUNNING = "running"
    SHUTDOWN = "shutting_down"
    EXCEPTION = "exception"


RESULT_PHASES = {
    BuildJobResult.INCOMPLETE: BUILD_PHASE.INTERNAL_ERROR,
    BuildJobResult.COMPLETE: BUILD_PHASE.COMPLETE,
    BuildJobResult.ERROR: BUILD_PHASE.ERROR,
}
