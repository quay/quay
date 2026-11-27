import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from buildman.interface import BuildJobResult
from buildman.manager.ephemeral import (
    CANCEL_PREFIX,
    EPHEMERAL_API_TIMEOUT,
    EphemeralBuilderManager,
)
from util import slash_join


@pytest.fixture
def manager():
    manager = EphemeralBuilderManager("registry", "manager", MagicMock(), MagicMock(), None, None)
    manager.initialize({"ORCHESTRATOR": {"MEM_CONFIG": None}})
    return manager


def _set_job(manager, build_uuid):
    job_queue_item = {"id": 1, "body": json.dumps({"build_uuid": build_uuid})}
    job_data = {
        "job_queue_item": job_queue_item,
        "executor_name": "kubernetes",
        "execution_id": "builder-1",
    }
    manager._orchestrator.set_key(manager._job_key(build_uuid), json.dumps(job_data))


def _cancel(manager, build_uuid):
    # Same write as OrchestratorCanceller.try_cancel_build.
    manager._orchestrator.set_key(slash_join(CANCEL_PREFIX, build_uuid), build_uuid, expiration=60)


def test_cancel_running_job_completes_it(manager):
    build_uuid = str(uuid.uuid4())
    _set_job(manager, build_uuid)

    with patch.object(manager, "on_job_complete") as on_job_complete:
        _cancel(manager, build_uuid)

    on_job_complete.assert_called_once()
    build_job, job_result, executor_name, execution_id = on_job_complete.call_args.args
    assert build_job.build_uuid == build_uuid
    assert job_result == BuildJobResult.CANCELLED
    assert executor_name == "kubernetes"
    assert execution_id == "builder-1"


def test_cancel_without_job_is_ignored(manager):
    with patch.object(manager, "on_job_complete") as on_job_complete:
        _cancel(manager, str(uuid.uuid4()))

    on_job_complete.assert_not_called()


def test_cancel_build_without_job_returns_true(manager):
    with patch("buildman.manager.ephemeral.model.build") as build_model:
        build_model.get_repository_build.return_value = MagicMock(phase="building")
        build_model.update_phase_then_close.return_value = True
        with patch.object(manager, "on_job_complete") as on_job_complete:
            assert manager.cancel_build(str(uuid.uuid4()))

    on_job_complete.assert_not_called()


def test_cancel_does_not_raise_when_completion_fails(manager):
    build_uuid = str(uuid.uuid4())
    _set_job(manager, build_uuid)

    with patch.object(manager, "on_job_complete", side_effect=RuntimeError("boom")):
        _cancel(manager, build_uuid)


def _schedule_with_cancel_during_start(manager, build_uuid, stop_side_effect=None):
    _set_job(manager, build_uuid)
    job_key = manager._job_key(build_uuid)

    executor = MagicMock(minimum_retry_threshold=0, setup_time=60, running_builders_count=0)
    executor.name = "kubernetes"

    def start_builder(*_):
        manager._orchestrator.delete_key(job_key)  # cancel lands mid-start
        return "builder-1"

    executor.start_builder.side_effect = start_builder
    executor.stop_builder.side_effect = stop_side_effect
    manager._ordered_executors = [executor]

    build_job = MagicMock(build_uuid=build_uuid, namespace="ns", retries_remaining=1)
    with (
        patch.object(manager, "_build_job_from_job_id", return_value=build_job),
        patch.object(manager, "generate_build_token", return_value="token"),
    ):
        return manager.schedule(build_uuid), executor


def test_schedule_stops_builder_when_job_cancelled_during_start(manager):
    result, executor = _schedule_with_cancel_during_start(manager, str(uuid.uuid4()))

    assert result == (False, EPHEMERAL_API_TIMEOUT)
    executor.stop_builder.assert_called_once_with("builder-1")


def test_schedule_returns_when_stopping_builder_fails(manager):
    result, executor = _schedule_with_cancel_during_start(
        manager, str(uuid.uuid4()), stop_side_effect=RuntimeError("boom")
    )

    assert result == (False, EPHEMERAL_API_TIMEOUT)
    executor.stop_builder.assert_called_once_with("builder-1")
