import base64

from flask import url_for

from app import instance_keys, app as original_app
from data.model.user import regenerate_robot_token, get_robot_and_metadata, get_user
from endpoints.test.shared import conduct_call, gen_basic_auth
from util.security.registry_jwt import decode_bearer_token, CLAIM_TUF_ROOTS

from test.fixtures import *


def get_robot_password(username):
    parent_name, robot_shortname = username.split("+", 1)
    parent = get_user(parent_name)
    _, token, _ = get_robot_and_metadata(robot_shortname, parent)
    return token


@pytest.mark.parametrize(
    "scope, username, password, expected_code, expected_scopes, push_private, visibility, org_create",
    [
        # Invalid repository.
        (
            "repository:devtable/simple/foo/bar/baz:pull",
            "devtable",
            "password",
            400,
            [],
            True,
            "private",
            False,
        ),
        # Invalid scopes.
        ("some_invalid_scope", "devtable", "password", 400, [], True, "private", False),
        # Invalid credentials.
        ("repository:devtable/simple:pull", "devtable", "invalid", 401, [], True, "private", False),
        # Valid credentials.
        (
            "repository:devtable/simple:pull",
            "devtable",
            "password",
            200,
            ["devtable/simple:pull"],
            True,
            "private",
            False,
        ),
        (
            "repository:devtable/simple:push",
            "devtable",
            "password",
            200,
            ["devtable/simple:push"],
            True,
            "private",
            False,
        ),
        (
            "repository:devtable/simple:pull,push",
            "devtable",
            "password",
            200,
            ["devtable/simple:push,pull"],
            True,
            "private",
            False,
        ),
        (
            "repository:devtable/simple:pull,push,*",
            "devtable",
            "password",
            200,
            ["devtable/simple:push,pull,*"],
            True,
            "private",
            False,
        ),
        (
            "repository:buynlarge/orgrepo:pull,push,*",
            "devtable",
            "password",
            200,
            ["buynlarge/orgrepo:push,pull,*"],
            True,
            "private",
            False,
        ),
        ("", "devtable", "password", 200, [], True, "private", False),
        # No credentials, non-public repo.
        (
            "repository:devtable/simple:pull",
            None,
            None,
            200,
            ["devtable/simple:"],
            True,
            "private",
            False,
        ),
        # No credentials, public repo.
        (
            "repository:public/publicrepo:pull",
            None,
            None,
            200,
            ["public/publicrepo:pull"],
            True,
            "private",
            False,
        ),
        # Reader only.
        (
            "repository:buynlarge/orgrepo:pull,push,*",
            "reader",
            "password",
            200,
            ["buynlarge/orgrepo:pull"],
            True,
            "private",
            False,
        ),
        # Unknown repository.
        (
            "repository:devtable/unknownrepo:pull,push",
            "devtable",
            "password",
            200,
            ["devtable/unknownrepo:push,pull"],
            True,
            "private",
            False,
        ),
        # Unknown repository in another namespace.
        (
            "repository:somenamespace/unknownrepo:pull,push",
            "devtable",
            "password",
            200,
            ["somenamespace/unknownrepo:"],
            True,
            "private",
            False,
        ),
        # Disabled namespace.
        (
            ["repository:devtable/simple:pull,push", "repository:disabled/complex:pull"],
            "devtable",
            "password",
            405,
            [],
            True,
            "private",
            False,
        ),
        # Multiple scopes.
        (
            ["repository:devtable/simple:pull,push", "repository:devtable/complex:pull"],
            "devtable",
            "password",
            200,
            ["devtable/simple:push,pull", "devtable/complex:pull"],
            True,
            "private",
            False,
        ),
        # Multiple scopes with restricted behavior.
        (
            ["repository:devtable/simple:pull,push", "repository:public/publicrepo:pull,push"],
            "devtable",
            "password",
            200,
            ["devtable/simple:push,pull", "public/publicrepo:pull"],
            True,
            "private",
            False,
        ),
        (
            ["repository:devtable/simple:pull,push,*", "repository:public/publicrepo:pull,push,*"],
            "devtable",
            "password",
            200,
            ["devtable/simple:push,pull,*", "public/publicrepo:pull"],
            True,
            "private",
            False,
        ),
        # Read Only State
        (
            "repository:devtable/readonly:pull,push,*",
            "devtable",
            "password",
            200,
            ["devtable/readonly:pull"],
            True,
            "private",
            False,
        ),
        # Mirror State as a typical User
        (
            "repository:devtable/mirrored:pull,push,*",
            "devtable",
            "password",
            200,
            ["devtable/mirrored:pull"],
            True,
            "private",
            False,
        ),
        # Mirror State as the robot User should have write access
        (
            "repository:devtable/mirrored:pull,push,*",
            "devtable+dtrobot",
            get_robot_password,
            200,
            ["devtable/mirrored:push,pull"],
            True,
            "private",
            False,
        ),
        # Organization repository, org admin
        (
            "repository:buynlarge/orgrepo:pull,push,*",
            "devtable",
            "password",
            200,
            ["buynlarge/orgrepo:push,pull,*"],
            True,
            "private",
            False,
        ),
        # Organization repository, org creator
        (
            "repository:buynlarge/orgrepo:pull,push,*",
            "creator",
            "password",
            200,
            ["buynlarge/orgrepo:"],
            True,
            "private",
            False,
        ),
        # Organization repository, org reader
        (
            "repository:buynlarge/orgrepo:pull,push,*",
            "reader",
            "password",
            200,
            ["buynlarge/orgrepo:pull"],
            True,
            "private",
            False,
        ),
        # Organization repository, freshuser
        (
            "repository:buynlarge/orgrepo:pull,push,*",
            "freshuser",
            "password",
            200,
            ["buynlarge/orgrepo:"],
            True,
            "private",
            False,
        ),
        # Pushed repository created private
        (
            "repository:devtable/visibility:pull,push,*",
            "devtable",
            "password",
            200,
            ["devtable/visibility:push,pull,*"],
            True,
            "private",
            False,
        ),
        # Pushed repository created public
        (
            "repository:devtable/visibility:pull,push,*",
            "devtable",
            "password",
            200,
            ["devtable/visibility:push,pull,*"],
            False,
            "public",
            False,
        ),
        # Pushed namespace created
        (
            "repository:neworg/visibility:pull,push,*",
            "devtable",
            "password",
            200,
            ["neworg/visibility:push,pull,*"],
            False,
            "public",
            True,
        ),
        # Pushed namespace bad name
        (
            "repository:NewOrg/visibility:pull,push,*",
            "devtable",
            "password",
            405,
            ["NewOrg/visibility:push,pull,*"],
            False,
            "public",
            True,
        ),
    ],
)
def test_generate_registry_jwt(
    scope,
    username,
    password,
    expected_code,
    expected_scopes,
    push_private,
    visibility,
    org_create,
    app,
    client,
):
    params = {
        "service": original_app.config["SERVER_HOSTNAME"],
        "scope": scope,
    }

    if callable(password):
        password = password(username)

    headers = {}
    if username and password:
        headers["Authorization"] = gen_basic_auth(username, password)

    original_app.config["CREATE_PRIVATE_REPO_ON_PUSH"] = push_private
    original_app.config["CREATE_NAMESPACE_ON_PUSH"] = org_create

    resp = conduct_call(
        client,
        "v2.generate_registry_jwt",
        url_for,
        "GET",
        params,
        {},
        expected_code,
        headers=headers,
    )
    if expected_code != 200:
        return

    token = resp.json["token"]
    decoded = decode_bearer_token(token, instance_keys, original_app.config)
    assert decoded["iss"] == "quay"
    assert decoded["aud"] == original_app.config["SERVER_HOSTNAME"]
    assert decoded["sub"] == username if username else "(anonymous)"

    expected_access = []
    for scope in expected_scopes:
        name, actions_str = scope.split(":")
        actions = actions_str.split(",") if actions_str else []

        expected_access.append(
            {
                "type": "repository",
                "name": name,
                "actions": actions,
            }
        )

    assert decoded["access"] == expected_access
    assert len(decoded["context"][CLAIM_TUF_ROOTS]) == len(expected_scopes)

    # Test visibility
    if scope == "repository:devtable/visibility:pull,push,*":
        assert (
            model.repository.get_repository("devtable", "visibility").visibility.name == visibility
        )
