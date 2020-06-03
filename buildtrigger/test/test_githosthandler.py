import copy

import pytest

from buildtrigger.triggerutil import TriggerStartException
from buildtrigger.test.bitbucketmock import get_bitbucket_trigger
from buildtrigger.test.githubmock import get_github_trigger, GithubBuildTrigger
from endpoints.building import PreparedBuild

# Note: This test suite executes a common set of tests against all the trigger types specified
# in this fixture. Each trigger's mock is expected to return the same data for all of these calls.
@pytest.fixture(params=[get_github_trigger(), get_bitbucket_trigger()])
def githost_trigger(request):
    return request.param


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
def test_manual_start(run_parameters, expected_error, expected_message, githost_trigger):
    if expected_error is not None:
        with pytest.raises(expected_error) as ipe:
            githost_trigger.manual_start(run_parameters)
        assert str(ipe.value) == expected_message
    else:
        assert isinstance(githost_trigger.manual_start(run_parameters), PreparedBuild)


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
def test_list_field_values(name, expected, githost_trigger):
    if expected is None:
        assert githost_trigger.list_field_values(name) is None
    elif isinstance(expected, set):
        assert set(githost_trigger.list_field_values(name)) == set(expected)
    else:
        assert githost_trigger.list_field_values(name) == expected


def test_list_build_source_namespaces():
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
            "score": 2,
            "title": "someorg",
            "personal": False,
            "url": "https://bitbucket.org/someorg",
            "avatar_url": "avatarurl",
            "id": "someorg",
        },
    ]

    found = get_bitbucket_trigger().list_build_source_namespaces()
    found = sorted(found, key=lambda d: sorted(d.items()))

    namespaces_expected = sorted(namespaces_expected, key=lambda d: sorted(d.items()))
    assert found == namespaces_expected


@pytest.mark.parametrize(
    "namespace, expected",
    [
        ("", []),
        ("unknown", []),
        (
            "knownuser",
            [
                {
                    "last_updated": 0,
                    "name": "somerepo",
                    "url": "https://bitbucket.org/knownuser/somerepo",
                    "private": True,
                    "full_name": "knownuser/somerepo",
                    "has_admin_permissions": True,
                    "description": "some somerepo repo",
                }
            ],
        ),
        (
            "someorg",
            [
                {
                    "last_updated": 0,
                    "name": "somerepo",
                    "url": "https://bitbucket.org/someorg/somerepo",
                    "private": True,
                    "full_name": "someorg/somerepo",
                    "has_admin_permissions": False,
                    "description": "some somerepo repo",
                },
                {
                    "last_updated": 0,
                    "name": "anotherrepo",
                    "url": "https://bitbucket.org/someorg/anotherrepo",
                    "private": False,
                    "full_name": "someorg/anotherrepo",
                    "has_admin_permissions": False,
                    "description": "some anotherrepo repo",
                },
            ],
        ),
    ],
)
def test_list_build_sources_for_namespace(namespace, expected, githost_trigger):
    if isinstance(githost_trigger, GithubBuildTrigger):
        # NOTE: We've disabled the permissions check for GitHub, so cancel them here.
        expected = copy.deepcopy(expected)
        for item in expected:
            item["has_admin_permissions"] = True

    assert githost_trigger.list_build_sources_for_namespace(namespace) == expected


def test_activate_and_deactivate(githost_trigger):
    _, private_key = githost_trigger.activate("http://some/url")
    assert "private_key" in private_key
    githost_trigger.deactivate()
