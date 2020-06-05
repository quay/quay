import datetime
import logging

from redis import RedisError

from data.database import BUILD_PHASE
from data import model
from buildman.asyncutil import AsyncWrapper


logger = logging.getLogger(__name__)


class StatusHandler(object):
    """
    Context wrapper for writing status to build logs.
    """

    def __init__(self, build_logs, repository_build_uuid):
        self._current_phase = None
        self._current_command = None
        self._uuid = repository_build_uuid
        self._build_logs = AsyncWrapper(build_logs)
        self._sync_build_logs = build_logs
        self._build_model = AsyncWrapper(model.build)

        self._status = {
            "total_commands": 0,
            "current_command": None,
            "push_completion": 0.0,
            "pull_completion": 0.0,
        }

        # Write the initial status.
        self.__exit__(None, None, None)

    async def _append_log_message(self, log_message, log_type=None, log_data=None):
        log_data = log_data or {}
        log_data["datetime"] = str(datetime.datetime.now())

        try:
            await (self._build_logs.append_log_message(self._uuid, log_message, log_type, log_data))
        except RedisError:
            logger.exception("Could not save build log for build %s: %s", self._uuid, log_message)

    async def append_log(self, log_message, extra_data=None):
        if log_message is None:
            return

        await self._append_log_message(log_message, log_data=extra_data)

    async def set_command(self, command, extra_data=None):
        if self._current_command == command:
            return

        self._current_command = command
        await self._append_log_message(command, self._build_logs.COMMAND, extra_data)

    async def set_error(self, error_message, extra_data=None, internal_error=False, requeued=False):
        error_phase = (
            BUILD_PHASE.INTERNAL_ERROR if internal_error and requeued else BUILD_PHASE.ERROR
        )
        await self.set_phase(error_phase)

        extra_data = extra_data or {}
        extra_data["internal_error"] = internal_error
        await self._append_log_message(error_message, self._build_logs.ERROR, extra_data)

    async def set_phase(self, phase, extra_data=None):
        if phase == self._current_phase:
            return False

        self._current_phase = phase
        await self._append_log_message(phase, self._build_logs.PHASE, extra_data)

        # Update the repository build with the new phase
        return self._build_model.update_phase_then_close(self._uuid, phase)

    def __enter__(self):
        return self._status

    def __exit__(self, exc_type, value, traceback):
        try:
            self._sync_build_logs.set_status(self._uuid, self._status)
        except RedisError:
            logger.exception("Could not set status of build %s to %s", self._uuid, self._status)
