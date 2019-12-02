import pytest

from endpoints.api.build import RepositoryBuildList


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
