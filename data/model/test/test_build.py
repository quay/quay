import pytest

from mock import patch

from data.database import BUILD_PHASE, RepositoryBuildTrigger, RepositoryBuild
from data.model.build import (
    update_trigger_disable_status,
    create_repository_build,
    get_repository_build,
    update_phase_then_close,
)
from test.fixtures import *

TEST_FAIL_THRESHOLD = 5
TEST_INTERNAL_ERROR_THRESHOLD = 2


@pytest.mark.parametrize(
    "starting_failure_count, starting_error_count, status, expected_reason",
    [
        (0, 0, BUILD_PHASE.COMPLETE, None),
        (10, 10, BUILD_PHASE.COMPLETE, None),
        (TEST_FAIL_THRESHOLD - 1, TEST_INTERNAL_ERROR_THRESHOLD - 1, BUILD_PHASE.COMPLETE, None),
        (TEST_FAIL_THRESHOLD - 1, 0, BUILD_PHASE.ERROR, "successive_build_failures"),
        (
            0,
            TEST_INTERNAL_ERROR_THRESHOLD - 1,
            BUILD_PHASE.INTERNAL_ERROR,
            "successive_build_internal_errors",
        ),
    ],
)
def test_update_trigger_disable_status(
    starting_failure_count, starting_error_count, status, expected_reason, initialized_db
):
    test_config = {
        "SUCCESSIVE_TRIGGER_FAILURE_DISABLE_THRESHOLD": TEST_FAIL_THRESHOLD,
        "SUCCESSIVE_TRIGGER_INTERNAL_ERROR_DISABLE_THRESHOLD": TEST_INTERNAL_ERROR_THRESHOLD,
    }

    trigger = model.build.list_build_triggers("devtable", "building")[0]
    trigger.successive_failure_count = starting_failure_count
    trigger.successive_internal_error_count = starting_error_count
    trigger.enabled = True
    trigger.save()

    with patch("data.model.config.app_config", test_config):
        update_trigger_disable_status(trigger, status)
        updated_trigger = RepositoryBuildTrigger.get(uuid=trigger.uuid)

        assert updated_trigger.enabled == (expected_reason is None)

        if expected_reason is not None:
            assert updated_trigger.disabled_reason.name == expected_reason
        else:
            assert updated_trigger.disabled_reason is None
            assert updated_trigger.successive_failure_count == 0
            assert updated_trigger.successive_internal_error_count == 0


def test_archivable_build_logs(initialized_db):
    # Make sure there are no archivable logs.
    result = model.build.get_archivable_build()
    assert result is None

    # Add a build that cannot (yet) be archived.
    repo = model.repository.get_repository("devtable", "simple")
    token = model.token.create_access_token(repo, "write")
    created = RepositoryBuild.create(
        repository=repo,
        access_token=token,
        phase=model.build.BUILD_PHASE.WAITING,
        logs_archived=False,
        job_config="{}",
        display_name="",
    )

    # Make sure there are no archivable logs.
    result = model.build.get_archivable_build()
    assert result is None

    # Change the build to being complete.
    created.phase = model.build.BUILD_PHASE.COMPLETE
    created.save()

    # Make sure we now find an archivable build.
    result = model.build.get_archivable_build()
    assert result.id == created.id


def test_update_build_phase(initialized_db):
    build = create_build(model.repository.get_repository("devtable", "building"))

    repo_build = get_repository_build(build.uuid)

    assert repo_build.phase == BUILD_PHASE.WAITING
    assert update_phase_then_close(build.uuid, BUILD_PHASE.COMPLETE)

    repo_build = get_repository_build(build.uuid)
    assert repo_build.phase == BUILD_PHASE.COMPLETE

    repo_build.delete_instance()
    assert not update_phase_then_close(repo_build.uuid, BUILD_PHASE.PULLING)


def create_build(repository):
    new_token = model.token.create_access_token(repository, "write", "build-worker")
    repo = "ci.devtable.com:5000/%s/%s" % (repository.namespace_user.username, repository.name)
    job_config = {
        "repository": repo,
        "docker_tags": ["latest"],
        "build_subdir": "",
        "trigger_metadata": {
            "commit": "3482adc5822c498e8f7db2e361e8d57b3d77ddd9",
            "ref": "refs/heads/master",
            "default_branch": "master",
        },
    }
    build = create_repository_build(
        repository, new_token, job_config, "68daeebd-a5b9-457f-80a0-4363b882f8ea", "build_name"
    )
    build.save()
    return build
