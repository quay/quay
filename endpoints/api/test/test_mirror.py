from datetime import datetime

import pytest

from data import model
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.mirror import RepoMirrorResource
from endpoints.test.shared import client_with_identity

from test.fixtures import *


def _setup_mirror():
    repo = model.repository.get_repository("devtable", "simple")
    assert repo
    robot = model.user.lookup_robot("devtable+dtrobot")
    assert robot
    rule = model.repo_mirror.create_rule(repo, ["latest", "3.3*", "foo"])
    assert rule
    mirror_kwargs = {
        "is_enabled": True,
        "external_reference": "quay.io/redhat/quay",
        "sync_interval": 5000,
        "sync_start_date": datetime(2020, 0o1, 0o2, 6, 30, 0),
        "external_registry_username": "fakeUsername",
        "external_registry_password": "fakePassword",
        "external_registry_config": {
            "verify_tls": True,
            "proxy": {
                "http_proxy": "http://insecure.proxy.corp",
                "https_proxy": "https://secure.proxy.corp",
                "no_proxy": "mylocalhost",
            },
        },
    }
    mirror = model.repo_mirror.enable_mirroring_for_repository(
        repo, root_rule=rule, internal_robot=robot, **mirror_kwargs
    )
    assert mirror
    return mirror


@pytest.mark.parametrize(
    "existing_robot_permission, expected_permission",
    [
        (None, "write"),
        ("read", "write"),
        ("write", "write"),
        ("admin", "admin"),
    ],
)
def test_create_mirror_sets_permissions(existing_robot_permission, expected_permission, client):
    mirror_bot, _ = model.user.create_robot(
        "newmirrorbot", model.user.get_namespace_user("devtable")
    )

    if existing_robot_permission:
        model.permission.set_user_repo_permission(
            mirror_bot.username, "devtable", "simple", existing_robot_permission
        )

    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        request_body = {
            "external_reference": "quay.io/foobar/barbaz",
            "sync_interval": 100,
            "sync_start_date": "2019-08-20T17:51:00Z",
            "root_rule": {"rule_kind": "tag_glob_csv", "rule_value": ["latest", "foo", "bar"]},
            "robot_username": "devtable+newmirrorbot",
        }
        conduct_api_call(cl, RepoMirrorResource, "POST", params, request_body, 201)

    # Check the status of the robot.
    permissions = model.permission.get_user_repository_permissions(mirror_bot, "devtable", "simple")
    assert permissions[0].role.name == expected_permission

    config = model.repo_mirror.get_mirror(model.repository.get_repository("devtable", "simple"))
    assert config.root_rule.rule_value == ["latest", "foo", "bar"]


def test_get_mirror_does_not_exist(client):
    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        resp = conduct_api_call(cl, RepoMirrorResource, "GET", params, None, 404)


def test_get_repo_does_not_exist(client):
    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/unicorn"}
        resp = conduct_api_call(cl, RepoMirrorResource, "GET", params, None, 404)


def test_get_mirror(client):
    """
    Verify that performing a `GET` request returns expected and accurate data.
    """
    mirror = _setup_mirror()

    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        resp = conduct_api_call(cl, RepoMirrorResource, "GET", params, None, 200).json

    assert resp["is_enabled"] == True
    assert resp["external_reference"] == "quay.io/redhat/quay"
    assert resp["sync_interval"] == 5000
    assert resp["sync_start_date"] == "2020-01-02T06:30:00Z"
    assert resp["external_registry_username"] == "fakeUsername"
    assert "external_registry_password" not in resp
    assert "external_registry_config" in resp
    assert resp["external_registry_config"]["verify_tls"] == True
    assert "proxy" in resp["external_registry_config"]
    assert resp["external_registry_config"]["proxy"]["http_proxy"] == "http://insecure.proxy.corp"
    assert resp["external_registry_config"]["proxy"]["https_proxy"] == "https://secure.proxy.corp"
    assert resp["external_registry_config"]["proxy"]["no_proxy"] == "mylocalhost"


@pytest.mark.parametrize(
    "key, value, expected_status",
    [
        ("is_enabled", True, 201),
        ("is_enabled", False, 201),
        ("is_enabled", None, 400),
        ("is_enabled", "foo", 400),
        ("external_reference", "example.com/foo/bar", 201),
        ("external_reference", "example.com/foo", 201),
        ("external_reference", "example.com", 201),
        ("external_registry_username", "newTestUsername", 201),
        ("external_registry_username", None, 201),
        ("external_registry_username", 123, 400),
        ("external_registry_password", "newTestPassword", 400),
        ("external_registry_password", None, 400),
        ("external_registry_password", 41, 400),
        ("robot_username", "devtable+dtrobot", 201),
        ("robot_username", "devtable+doesntExist", 400),
        ("sync_start_date", "2020-01-01T00:00:00Z", 201),
        ("sync_start_date", "January 1 2020", 400),
        ("sync_start_date", "2020-01-01T00:00:00.00Z", 400),
        ("sync_start_date", "Wed, 01 Jan 2020 00:00:00 -0000", 400),
        ("sync_start_date", "Wed, 02 Oct 2002 08:00:00 EST", 400),
        ("sync_interval", 2000, 201),
        ("sync_interval", -5, 400),
        ("https_proxy", "https://proxy.corp.example.com", 201),
        ("https_proxy", None, 201),
        (
            "https_proxy",
            "proxy.example.com; rm -rf /",
            201,
        ),  # Safe; values only set in env, not eval'ed
        ("http_proxy", "http://proxy.corp.example.com", 201),
        ("http_proxy", None, 201),
        (
            "http_proxy",
            "proxy.example.com; rm -rf /",
            201,
        ),  # Safe; values only set in env, not eval'ed
        ("no_proxy", "quay.io", 201),
        ("no_proxy", None, 201),
        ("no_proxy", "quay.io; rm -rf /", 201),  # Safe because proxy values are not eval'ed
        ("verify_tls", True, 201),
        ("verify_tls", False, 201),
        ("verify_tls", None, 400),
        ("verify_tls", "abc", 400),
        ("root_rule", {"rule_kind": "tag_glob_csv", "rule_value": ["3.1", "3.1*"]}, 201),
        ("root_rule", {"rule_kind": "tag_glob_csv"}, 400),
        ("root_rule", {"rule_kind": "tag_glob_csv", "rule_value": []}, 400),
        ("root_rule", {"rule_kind": "incorrect", "rule_value": ["3.1", "3.1*"]}, 400),
    ],
)
def test_change_config(key, value, expected_status, client):
    """
    Verify that changing each attribute works as expected.
    """
    mirror = _setup_mirror()

    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        if key in ("http_proxy", "https_proxy", "no_proxy"):
            request_body = {"external_registry_config": {"proxy": {key: value}}}
        elif key == "verify_tls":
            request_body = {"external_registry_config": {key: value}}
        else:
            request_body = {key: value}
        conduct_api_call(cl, RepoMirrorResource, "PUT", params, request_body, expected_status)

    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        resp = conduct_api_call(cl, RepoMirrorResource, "GET", params, None, 200)

    if expected_status < 400:
        if key == "external_registry_password":
            assert key not in resp.json
        elif key == "verify_tls":
            assert resp.json["external_registry_config"]["verify_tls"] == value
        elif key in ("http_proxy", "https_proxy", "no_proxy"):
            assert resp.json["external_registry_config"]["proxy"][key] == value
        else:
            assert resp.json[key] == value
    else:
        if key == "external_registry_password":
            assert key not in resp.json
        elif key == "verify_tls":
            assert resp.json["external_registry_config"][key] != value
        elif key in ("http_proxy", "https_proxy", "no_proxy"):
            assert resp.json["external_registry_config"]["proxy"][key] != value
        else:
            assert resp.json[key] != value


@pytest.mark.parametrize(
    "request_body, expected_status",
    [
        # Set a new password and username => Success
        (
            {
                "external_registry_username": "newUsername",
                "external_registry_password": "newPassword",
            },
            201,
        ),
        # Set password and username to None => Success
        ({"external_registry_username": None, "external_registry_password": None}, 201),
        # Set username to value but password None => Sucess
        ({"external_registry_username": "myUsername", "external_registry_password": None}, 201),
        # Set only new Username => Success
        ({"external_registry_username": "myNewUsername"}, 201),
        ({"external_registry_username": None}, 201),
        # Set only new Password => Failure
        ({"external_registry_password": "myNewPassword"}, 400),
        ({"external_registry_password": None}, 400),
        # Set username and password to empty string => Success?
        ({"external_registry_username": "", "external_registry_password": ""}, 201),
    ],
)
def test_change_credentials(request_body, expected_status, client):
    """
    Verify credentials can only be modified as a pair.
    """
    mirror = _setup_mirror()

    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        conduct_api_call(cl, RepoMirrorResource, "PUT", params, request_body, expected_status)
