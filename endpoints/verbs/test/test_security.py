import pytest

from flask import url_for
from endpoints.test.shared import conduct_call, gen_basic_auth
from test.fixtures import *

NO_ACCESS_USER = "freshuser"
READ_ACCESS_USER = "reader"
ADMIN_ACCESS_USER = "devtable"
CREATOR_ACCESS_USER = "creator"

PUBLIC_REPO = "public/publicrepo"
PRIVATE_REPO = "devtable/shared"
ORG_REPO = "buynlarge/orgrepo"
ANOTHER_ORG_REPO = "buynlarge/anotherorgrepo"

ACI_ARGS = {
    "server": "someserver",
    "tag": "fake",
    "os": "linux",
    "arch": "x64",
}


@pytest.mark.parametrize(
    "user",
    [
        (0, None),
        (1, NO_ACCESS_USER),
        (2, READ_ACCESS_USER),
        (3, CREATOR_ACCESS_USER),
        (4, ADMIN_ACCESS_USER),
    ],
)
@pytest.mark.parametrize(
    "endpoint,method,repository,single_repo_path,params,expected_statuses",
    [
        ("get_aci_signature", "GET", PUBLIC_REPO, False, ACI_ARGS, (404, 404, 404, 404, 404)),
        ("get_aci_signature", "GET", PRIVATE_REPO, False, ACI_ARGS, (403, 403, 404, 403, 404)),
        ("get_aci_signature", "GET", ORG_REPO, False, ACI_ARGS, (403, 403, 404, 403, 404)),
        ("get_aci_signature", "GET", ANOTHER_ORG_REPO, False, ACI_ARGS, (403, 403, 403, 403, 404)),
        # get_aci_image
        ("get_aci_image", "GET", PUBLIC_REPO, False, ACI_ARGS, (404, 404, 404, 404, 404)),
        ("get_aci_image", "GET", PRIVATE_REPO, False, ACI_ARGS, (403, 403, 404, 403, 404)),
        ("get_aci_image", "GET", ORG_REPO, False, ACI_ARGS, (403, 403, 404, 403, 404)),
        ("get_aci_image", "GET", ANOTHER_ORG_REPO, False, ACI_ARGS, (403, 403, 403, 403, 404)),
        # get_squashed_tag
        (
            "get_squashed_tag",
            "GET",
            PUBLIC_REPO,
            False,
            dict(tag="fake"),
            (404, 404, 404, 404, 404),
        ),
        (
            "get_squashed_tag",
            "GET",
            PRIVATE_REPO,
            False,
            dict(tag="fake"),
            (403, 403, 404, 403, 404),
        ),
        ("get_squashed_tag", "GET", ORG_REPO, False, dict(tag="fake"), (403, 403, 404, 403, 404)),
        (
            "get_squashed_tag",
            "GET",
            ANOTHER_ORG_REPO,
            False,
            dict(tag="fake"),
            (403, 403, 403, 403, 404),
        ),
        # get_tag_torrent
        (
            "get_tag_torrent",
            "GET",
            PUBLIC_REPO,
            True,
            dict(digest="sha256:1234"),
            (404, 404, 404, 404, 404),
        ),
        (
            "get_tag_torrent",
            "GET",
            PRIVATE_REPO,
            True,
            dict(digest="sha256:1234"),
            (403, 403, 404, 403, 404),
        ),
        (
            "get_tag_torrent",
            "GET",
            ORG_REPO,
            True,
            dict(digest="sha256:1234"),
            (403, 403, 404, 403, 404),
        ),
        (
            "get_tag_torrent",
            "GET",
            ANOTHER_ORG_REPO,
            True,
            dict(digest="sha256:1234"),
            (403, 403, 403, 403, 404),
        ),
    ],
)
def test_verbs_security(
    user, endpoint, method, repository, single_repo_path, params, expected_statuses, app, client
):
    headers = {}
    if user[1] is not None:
        headers["Authorization"] = gen_basic_auth(user[1], "password")

    if single_repo_path:
        params["repository"] = repository
    else:
        (namespace, repo_name) = repository.split("/")
        params["namespace"] = namespace
        params["repository"] = repo_name

    conduct_call(
        client,
        "verbs." + endpoint,
        url_for,
        method,
        params,
        expected_code=expected_statuses[user[0]],
        headers=headers,
    )
