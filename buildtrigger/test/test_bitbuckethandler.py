import json
import pytest

from buildtrigger.test.bitbucketmock import get_bitbucket_trigger
from buildtrigger.triggerutil import (
    SkipRequestException,
    ValidationRequestException,
    InvalidPayloadException,
)
from endpoints.building import PreparedBuild
from util.morecollections import AttrDict


@pytest.fixture
def bitbucket_trigger():
    return get_bitbucket_trigger()


def test_list_build_subdirs(bitbucket_trigger):
    assert bitbucket_trigger.list_build_subdirs() == ["/Dockerfile"]


@pytest.mark.parametrize(
    "dockerfile_path, contents",
    [
        ("/Dockerfile", "hello world"),
        ("somesubdir/Dockerfile", "hi universe"),
        ("unknownpath", None),
    ],
)
def test_load_dockerfile_contents(dockerfile_path, contents):
    trigger = get_bitbucket_trigger(dockerfile_path)
    assert trigger.load_dockerfile_contents() == contents


@pytest.mark.parametrize(
    "payload, expected_error, expected_message",
    [
        ("{}", InvalidPayloadException, "'push' is a required property"),
        # Valid payload:
        (
            """{
    "push": {
        "changes": [{
            "new": {
                "name": "somechange",
                "target": {
                    "hash": "aaaaaaa",
                    "message": "foo",
                    "date": "now",
                    "links": {
                        "html": {
                            "href": "somelink"
                        }
                    }
                }
            }
        }]
    },
    "repository": {
        "full_name": "foo/bar"
    }
   }""",
            None,
            None,
        ),
        # Skip message:
        (
            """{
    "push": {
        "changes": [{
            "new": {
                "name": "somechange",
                "target": {
                    "hash": "aaaaaaa",
                    "message": "[skip build] foo",
                    "date": "now",
                    "links": {
                        "html": {
                            "href": "somelink"
                        }
                    }
                }
            }
        }]
    },
    "repository": {
        "full_name": "foo/bar"
    }
   }""",
            SkipRequestException,
            "",
        ),
    ],
)
def test_handle_trigger_request(bitbucket_trigger, payload, expected_error, expected_message):
    def get_payload():
        return json.loads(payload)

    request = AttrDict(dict(get_json=get_payload))

    if expected_error is not None:
        with pytest.raises(expected_error) as ipe:
            bitbucket_trigger.handle_trigger_request(request)
        assert str(ipe.value) == expected_message
    else:
        assert isinstance(bitbucket_trigger.handle_trigger_request(request), PreparedBuild)
