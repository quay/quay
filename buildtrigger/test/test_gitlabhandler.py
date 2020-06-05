import json
import pytest

from mock import Mock

from buildtrigger.test.gitlabmock import get_gitlab_trigger
from buildtrigger.triggerutil import (
    SkipRequestException,
    ValidationRequestException,
    InvalidPayloadException,
    TriggerStartException,
)
from endpoints.building import PreparedBuild
from util.morecollections import AttrDict


@pytest.fixture()
def gitlab_trigger():
    with get_gitlab_trigger() as t:
        yield t


def test_list_build_subdirs(gitlab_trigger):
    assert gitlab_trigger.list_build_subdirs() == ["Dockerfile"]


@pytest.mark.parametrize(
    "dockerfile_path, contents",
    [
        ("/Dockerfile", b"hello world"),
        ("somesubdir/Dockerfile", b"hi universe"),
        ("unknownpath", None),
    ],
)
def test_load_dockerfile_contents(dockerfile_path, contents):
    with get_gitlab_trigger(dockerfile_path=dockerfile_path) as trigger:
        assert trigger.load_dockerfile_contents() == contents


@pytest.mark.parametrize(
    "email, expected_response",
    [
        ("unknown@email.com", None),
        (
            "knownuser",
            {
                "username": "knownuser",
                "html_url": "https://bitbucket.org/knownuser",
                "avatar_url": "avatarurl",
            },
        ),
    ],
)
def test_lookup_user(email, expected_response, gitlab_trigger):
    assert gitlab_trigger.lookup_user(email) == expected_response


def test_null_permissions():
    with get_gitlab_trigger(add_permissions=False) as trigger:
        sources = trigger.list_build_sources_for_namespace("someorg")
        source = sources[0]
        assert source["has_admin_permissions"]


def test_list_build_sources():
    with get_gitlab_trigger() as trigger:
        sources = trigger.list_build_sources_for_namespace("someorg")
        assert sources == [
            {
                "last_updated": 1380548762,
                "name": "someproject",
                "url": "http://example.com/someorg/someproject",
                "private": True,
                "full_name": "someorg/someproject",
                "has_admin_permissions": False,
                "description": "",
            },
            {
                "last_updated": 1380548762,
                "name": "anotherproject",
                "url": "http://example.com/someorg/anotherproject",
                "private": False,
                "full_name": "someorg/anotherproject",
                "has_admin_permissions": True,
                "description": "",
            },
        ]


def test_null_avatar():
    with get_gitlab_trigger(missing_avatar_url=True) as trigger:
        namespace_data = trigger.list_build_source_namespaces()
        expected = {
            "avatar_url": None,
            "personal": False,
            "title": "someorg",
            "url": "http://gitlab.com/groups/someorg",
            "score": 1,
            "id": "2",
        }

        assert namespace_data == [expected]


@pytest.mark.parametrize(
    "payload, expected_error, expected_message",
    [
        ("{}", InvalidPayloadException, ""),
        # Valid payload:
        (
            """{
    "object_kind": "push",
    "ref": "refs/heads/master",
    "checkout_sha": "aaaaaaa",
    "repository": {
      "git_ssh_url": "foobar"
    },
    "commits": [
      {
        "id": "aaaaaaa",
        "url": "someurl",
        "message": "hello there!",
        "timestamp": "now"
      }
    ]
  }""",
            None,
            None,
        ),
        # Skip message:
        (
            """{
    "object_kind": "push",
    "ref": "refs/heads/master",
    "checkout_sha": "aaaaaaa",
    "repository": {
      "git_ssh_url": "foobar"
    },
    "commits": [
      {
        "id": "aaaaaaa",
        "url": "someurl",
        "message": "[skip build] hello there!",
        "timestamp": "now"
      }
    ]
  }""",
            SkipRequestException,
            "",
        ),
    ],
)
def test_handle_trigger_request(gitlab_trigger, payload, expected_error, expected_message):
    def get_payload():
        return json.loads(payload)

    request = AttrDict(dict(get_json=get_payload))

    if expected_error is not None:
        with pytest.raises(expected_error) as ipe:
            gitlab_trigger.handle_trigger_request(request)
        assert str(ipe.value) == expected_message
    else:
        assert isinstance(gitlab_trigger.handle_trigger_request(request), PreparedBuild)


@pytest.mark.parametrize(
    "run_parameters, expected_error, expected_message",
    [
        # No branch or tag specified: use the commit of the default branch.
        ({}, None, None),
        # Invalid branch.
        (
            {"refs": {"kind": "branch", "name": "invalid"}},
            TriggerStartException,
            "Could not find branch in repository",
        ),
        # Invalid tag.
        (
            {"refs": {"kind": "tag", "name": "invalid"}},
            TriggerStartException,
            "Could not find tag in repository",
        ),
        # Valid branch.
        ({"refs": {"kind": "branch", "name": "master"}}, None, None),
        # Valid tag.
        ({"refs": {"kind": "tag", "name": "sometag"}}, None, None),
    ],
)
def test_manual_start(run_parameters, expected_error, expected_message, gitlab_trigger):
    if expected_error is not None:
        with pytest.raises(expected_error) as ipe:
            gitlab_trigger.manual_start(run_parameters)
        assert str(ipe.value) == expected_message
    else:
        assert isinstance(gitlab_trigger.manual_start(run_parameters), PreparedBuild)


def test_activate_and_deactivate(gitlab_trigger):
    _, private_key = gitlab_trigger.activate("http://some/url")
    assert "private_key" in private_key

    gitlab_trigger.deactivate()


@pytest.mark.parametrize(
    "name, expected",
    [
        (
            "refs",
            [
                {"kind": "branch", "name": "master"},
                {"kind": "branch", "name": "otherbranch"},
                {"kind": "tag", "name": "sometag"},
                {"kind": "tag", "name": "someothertag"},
            ],
        ),
        ("tag_name", set(["sometag", "someothertag"])),
        ("branch_name", set(["master", "otherbranch"])),
        ("invalid", None),
    ],
)
def test_list_field_values(name, expected, gitlab_trigger):
    if expected is None:
        assert gitlab_trigger.list_field_values(name) is None
    elif isinstance(expected, set):
        assert set(gitlab_trigger.list_field_values(name)) == set(expected)
    else:
        assert gitlab_trigger.list_field_values(name) == expected


@pytest.mark.parametrize(
    "namespace, expected",
    [
        ("", []),
        ("unknown", []),
        (
            "knownuser",
            [
                {
                    "last_updated": 1380548762,
                    "name": "anotherproject",
                    "url": "http://example.com/knownuser/anotherproject",
                    "private": False,
                    "full_name": "knownuser/anotherproject",
                    "has_admin_permissions": True,
                    "description": "",
                },
            ],
        ),
        (
            "someorg",
            [
                {
                    "last_updated": 1380548762,
                    "name": "someproject",
                    "url": "http://example.com/someorg/someproject",
                    "private": True,
                    "full_name": "someorg/someproject",
                    "has_admin_permissions": False,
                    "description": "",
                },
                {
                    "last_updated": 1380548762,
                    "name": "anotherproject",
                    "url": "http://example.com/someorg/anotherproject",
                    "private": False,
                    "full_name": "someorg/anotherproject",
                    "has_admin_permissions": True,
                    "description": "",
                },
            ],
        ),
    ],
)
def test_list_build_sources_for_namespace(namespace, expected, gitlab_trigger):
    assert gitlab_trigger.list_build_sources_for_namespace(namespace) == expected
