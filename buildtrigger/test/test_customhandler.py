import pytest

from buildtrigger.customhandler import CustomBuildTrigger
from buildtrigger.triggerutil import (
    InvalidPayloadException,
    SkipRequestException,
    TriggerStartException,
)
from endpoints.building import PreparedBuild
from util.morecollections import AttrDict


@pytest.mark.parametrize(
    "payload, expected_error, expected_message",
    [
        ("", InvalidPayloadException, "Missing expected payload"),
        ("{}", InvalidPayloadException, "'commit' is a required property"),
        (
            '{"commit": "foo", "ref": "refs/heads/something", "default_branch": "baz"}',
            InvalidPayloadException,
            "'foo' does not match '^([A-Fa-f0-9]{7,})$'",
        ),
        (
            '{"commit": "11d6fbc", "ref": "refs/heads/something", "default_branch": "baz"}',
            None,
            None,
        ),
        (
            """{
    "commit": "11d6fbc",
    "ref": "refs/heads/something",
    "default_branch": "baz",
    "commit_info": {
      "message": "[skip build]",
      "url": "http://foo.bar",
      "date": "NOW"
    }
  }""",
            SkipRequestException,
            "",
        ),
    ],
)
def test_handle_trigger_request(payload, expected_error, expected_message):
    trigger = CustomBuildTrigger(None, {"build_source": "foo"})
    request = AttrDict(dict(data=payload))

    if expected_error is not None:
        with pytest.raises(expected_error) as ipe:
            trigger.handle_trigger_request(request)

        assert str(ipe.value) == expected_message
    else:
        assert isinstance(trigger.handle_trigger_request(request), PreparedBuild)


@pytest.mark.parametrize(
    "run_parameters, expected_error, expected_message",
    [
        ({}, TriggerStartException, "missing required parameter"),
        (
            {"commit_sha": "foo"},
            TriggerStartException,
            "'foo' does not match '^([A-Fa-f0-9]{7,})$'",
        ),
        ({"commit_sha": "11d6fbc"}, None, None),
    ],
)
def test_manual_start(run_parameters, expected_error, expected_message):
    trigger = CustomBuildTrigger(None, {"build_source": "foo"})
    if expected_error is not None:
        with pytest.raises(expected_error) as ipe:
            trigger.manual_start(run_parameters)
        assert str(ipe.value) == expected_message
    else:
        assert isinstance(trigger.manual_start(run_parameters), PreparedBuild)
