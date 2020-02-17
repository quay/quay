import pytest

from data import model
from buildtrigger.triggerutil import raise_if_skipped_build, SkipRequestException
from endpoints.building import (
    start_build,
    PreparedBuild,
    MaximumBuildsQueuedException,
    BuildTriggerDisabledException,
)

from test.fixtures import *


def test_maximum_builds(app):
    # Change the maximum number of builds to 1.
    user = model.user.create_user("foobar", "password", "foo@example.com")
    user.maximum_queued_builds_count = 1
    user.save()

    repo = model.repository.create_repository("foobar", "somerepo", user)

    # Try to queue a build; should succeed.
    prepared_build = PreparedBuild()
    prepared_build.build_name = "foo"
    prepared_build.is_manual = True
    prepared_build.dockerfile_id = "foobar"
    prepared_build.archive_url = "someurl"
    prepared_build.tags = ["latest"]
    prepared_build.subdirectory = "/"
    prepared_build.context = "/"
    prepared_build.metadata = {}

    start_build(repo, prepared_build)

    # Try to queue a second build; should fail.
    with pytest.raises(MaximumBuildsQueuedException):
        start_build(repo, prepared_build)


def test_start_build_disabled_trigger(app):
    trigger = model.build.list_build_triggers("devtable", "building")[0]
    trigger.enabled = False
    trigger.save()

    build = PreparedBuild(trigger=trigger)

    with pytest.raises(BuildTriggerDisabledException):
        start_build(trigger.repository, build)


@pytest.mark.parametrize(
    "metadata, config",
    [
        ({}, {}),
        pytest.param(
            {"ref": "ref/heads/master"}, {"branchtag_regex": "nothing"}, id="branchtag regex"
        ),
        pytest.param(
            {"ref": "ref/heads/master", "commit_info": {"message": "[skip build]",},},
            {},
            id="commit message",
        ),
    ],
)
def test_skip(metadata, config):
    prepared = PreparedBuild()
    prepared.metadata = metadata
    config = config

    with pytest.raises(SkipRequestException):
        raise_if_skipped_build(prepared, config)


def test_does_not_skip():
    prepared = PreparedBuild()
    prepared.metadata = {
        "ref": "ref/heads/master",
        "commit_info": {"message": "some cool message",},
    }

    config = {
        "branchtag_regex": "(master)|(heads/master)",
    }

    raise_if_skipped_build(prepared, config)
