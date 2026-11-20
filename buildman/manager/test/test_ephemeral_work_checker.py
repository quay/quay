import json
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest

from buildman.jobutil.buildjob import BuildJob
from buildman.manager import ephemeral
from buildman.manager.ephemeral import EphemeralBuilderManager
from buildman.orchestrator import MemoryOrchestrator, OrchestratorConnectionError
from util.morecollections import AttrDict

BUILD_UUID = "deadbeef-dead-beef-dead-beefdeadbeef"


class StopWorkChecker(Exception):
    pass


@pytest.fixture
def job_item():
    return AttrDict(body=json.dumps({"build_uuid": BUILD_UUID}), retries_remaining=1)


@pytest.fixture
def manager(job_item):
    queue = Mock()
    # The second dequeue ends the otherwise infinite work checker loop.
    queue.get.side_effect = [job_item, StopWorkChecker()]

    manager = EphemeralBuilderManager("registry", "manager", queue, None, None, None)
    manager._orchestrator = MemoryOrchestrator()

    with (
        patch.object(ephemeral.time, "sleep"),
        patch.object(ephemeral.database, "CloseForLongOperation", MagicMock()),
        patch.object(BuildJob, "repo_build", new_callable=PropertyMock),
    ):
        yield manager


def test_work_checker_survives_unschedulable_job(manager, job_item):
    with (
        patch.object(manager, "schedule", return_value=(False, 30)),
        patch.object(ephemeral, "build_queue_duration") as queue_duration,
    ):
        with pytest.raises(StopWorkChecker):
            manager._work_checker()

    manager._queue.incomplete.assert_called_once_with(job_item, restore_retry=False, retry_after=30)
    queue_duration.labels.assert_called_once_with(False)
    queue_duration.labels.return_value.observe.assert_called_once()


def test_work_checker_observes_queue_duration_on_schedule(manager):
    with (
        patch.object(manager, "schedule", return_value=(True, None)),
        patch.object(ephemeral, "build_queue_duration") as queue_duration,
    ):
        with pytest.raises(StopWorkChecker):
            manager._work_checker()

    manager._queue.incomplete.assert_not_called()
    queue_duration.labels.assert_called_once_with(True)
    queue_duration.labels.return_value.observe.assert_called_once()


def test_work_checker_reads_created_at_before_schedule_deletes_key(manager):
    # No executors: the real schedule() deletes the job key before returning.
    manager._ordered_executors = []
    with (
        patch.object(manager, "_running_workers", return_value=0),
        patch.object(manager, "generate_build_token", return_value="token"),
        patch.object(ephemeral, "build_queue_duration") as queue_duration,
    ):
        with pytest.raises(StopWorkChecker):
            manager._work_checker()

    queue_duration.labels.assert_called_once_with(False)


def test_work_checker_skips_queue_duration_when_job_key_missing(manager, job_item):
    with (
        patch.object(manager, "create_job"),
        patch.object(manager, "schedule", return_value=(False, 30)),
        patch.object(ephemeral, "build_queue_duration") as queue_duration,
    ):
        with pytest.raises(StopWorkChecker):
            manager._work_checker()

    manager._queue.incomplete.assert_called_once_with(job_item, restore_retry=False, retry_after=30)
    queue_duration.labels.assert_not_called()


def test_work_checker_schedules_when_job_key_read_fails(manager, job_item):
    with (
        patch.object(manager._orchestrator, "get_key", side_effect=OrchestratorConnectionError()),
        patch.object(manager, "schedule", return_value=(True, None)) as schedule,
        patch.object(ephemeral, "build_queue_duration") as queue_duration,
    ):
        with pytest.raises(StopWorkChecker):
            manager._work_checker()

    schedule.assert_called_once_with(BUILD_UUID)
    queue_duration.labels.assert_not_called()
