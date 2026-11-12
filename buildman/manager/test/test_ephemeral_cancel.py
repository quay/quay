import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from buildman.interface import BuildJobResult
from buildman.manager.ephemeral import CANCEL_PREFIX, EphemeralBuilderManager
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
