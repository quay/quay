import json
import pytest

from buildtrigger.test.githubmock import get_github_trigger
from buildtrigger.triggerutil import (
    SkipRequestException,
    ValidationRequestException,
    InvalidPayloadException,
)
from endpoints.building import PreparedBuild
from util.morecollections import AttrDict


@pytest.fixture
def github_trigger():
    return get_github_trigger()


@pytest.mark.parametrize(
    "payload, expected_error, expected_message",
    [
        ('{"zen": true}', SkipRequestException, ""),
        ("{}", InvalidPayloadException, "Missing 'repository' on request"),
        ('{"repository": "foo"}', InvalidPayloadException, "Missing 'owner' on repository"),
        # Valid payload:
        (
            """{
    "repository": {
      "owner": {
        "name": "someguy"
      },
      "name": "somerepo",
      "ssh_url": "someurl"
    },
    "ref": "refs/tags/foo",
    "head_commit": {
      "id": "11d6fbc",
      "url": "http://some/url",
      "message": "some message",
      "timestamp": "NOW"
    }
  }""",
            None,
            None,
        ),
        # Skip message:
        (
            """{
    "repository": {
      "owner": {
        "name": "someguy"
      },
      "name": "somerepo",
      "ssh_url": "someurl"
    },
    "ref": "refs/tags/foo",
    "head_commit": {
      "id": "11d6fbc",
      "url": "http://some/url",
      "message": "[skip build]",
      "timestamp": "NOW"
    }
  }""",
            SkipRequestException,
            "",
        ),
    ],
)
def test_handle_trigger_request(github_trigger, payload, expected_error, expected_message):
    def get_payload():
        return json.loads(payload)

    request = AttrDict(dict(get_json=get_payload))

    if expected_error is not None:
        with pytest.raises(expected_error) as ipe:
            github_trigger.handle_trigger_request(request)
        assert str(ipe.value) == expected_message
    else:
        assert isinstance(github_trigger.handle_trigger_request(request), PreparedBuild)


@pytest.mark.parametrize(
    "dockerfile_path, contents",
    [
        ("/Dockerfile", "hello world"),
        ("somesubdir/Dockerfile", "hi universe"),
        ("unknownpath", None),
    ],
)
def test_load_dockerfile_contents(dockerfile_path, contents):
    trigger = get_github_trigger(dockerfile_path)
    assert trigger.load_dockerfile_contents() == contents


@pytest.mark.parametrize(
    "username, expected_response",
    [
        ("unknownuser", None),
        ("knownuser", {"html_url": "https://bitbucket.org/knownuser", "avatar_url": "avatarurl"}),
    ],
)
def test_lookup_user(username, expected_response, github_trigger):
    assert github_trigger.lookup_user(username) == expected_response


def test_list_build_subdirs(github_trigger):
    assert github_trigger.list_build_subdirs() == ["Dockerfile", "somesubdir/Dockerfile"]


def test_list_build_source_namespaces(github_trigger):
    namespaces_expected = [
        {
            "personal": True,
            "score": 1,
            "avatar_url": "avatarurl",
            "id": "knownuser",
            "title": "knownuser",
            "url": "https://bitbucket.org/knownuser",
        },
        {
            "score": 0,
            "title": "someorg",
            "personal": False,
            "url": "",
            "avatar_url": "avatarurl",
            "id": "someorg",
        },
    ]

    found = github_trigger.list_build_source_namespaces()
    sorted(found, key=lambda d: sorted(d.items()))

    sorted(namespaces_expected, key=lambda d: sorted(d.items()))
    assert found == namespaces_expected
