import pytest

from data.model.build import list_repository_builds
from data.model.repository import create_repository
from data.model.user import get_user
from endpoints.api.build import RepositoryBuildList
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize(
    "request_json,subdir,context",
    [
        ({}, "/Dockerfile", "/"),
        ({"context": "/some_context"}, "/some_context/Dockerfile", "/some_context"),
        ({"subdirectory": "some_context"}, "some_context/Dockerfile", "some_context"),
        ({"subdirectory": "some_context/"}, "some_context/Dockerfile", "some_context/"),
        ({"dockerfile_path": "some_context/Dockerfile"}, "some_context/Dockerfile", "some_context"),
        (
            {"dockerfile_path": "some_context/Dockerfile", "context": "/"},
            "some_context/Dockerfile",
            "/",
        ),
        (
            {"dockerfile_path": "some_context/Dockerfile", "context": "/", "subdirectory": "slime"},
            "some_context/Dockerfile",
            "/",
        ),
    ],
)
def test_extract_dockerfile_args(request_json, subdir, context):
    actual_context, actual_subdir = RepositoryBuildList.get_dockerfile_context(request_json)
    assert subdir == actual_subdir
    assert context == actual_context


def test_request_build_refused_in_proxy_cache_org(app):
    create_repository("proxyorg", "cached", get_user("devtable"))

    with client_with_identity("devtable", app) as cl:
        params = {"repository": "proxyorg/cached"}
        body = {"archive_url": "https://example.com/context.tar.gz"}
        resp = conduct_api_call(cl, RepositoryBuildList, "POST", params, body, 400)

    assert "proxy cache" in resp.json["error_message"]
    assert not list(list_repository_builds("proxyorg", "cached", 10))
