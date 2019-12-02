import pytest

from buildman.component.buildcomponent import BuildComponent


@pytest.mark.parametrize(
    "input,expected_path,expected_file",
    [
        ("", "/", "Dockerfile"),
        ("/", "/", "Dockerfile"),
        ("/Dockerfile", "/", "Dockerfile"),
        ("/server.Dockerfile", "/", "server.Dockerfile"),
        ("/somepath", "/somepath", "Dockerfile"),
        ("/somepath/", "/somepath", "Dockerfile"),
        ("/somepath/Dockerfile", "/somepath", "Dockerfile"),
        ("/somepath/server.Dockerfile", "/somepath", "server.Dockerfile"),
        ("/somepath/some_other_path", "/somepath/some_other_path", "Dockerfile"),
        ("/somepath/some_other_path/", "/somepath/some_other_path", "Dockerfile"),
        ("/somepath/some_other_path/Dockerfile", "/somepath/some_other_path", "Dockerfile"),
        (
            "/somepath/some_other_path/server.Dockerfile",
            "/somepath/some_other_path",
            "server.Dockerfile",
        ),
    ],
)
def test_path_is_dockerfile(input, expected_path, expected_file):
    actual_path, actual_file = BuildComponent.name_and_path(input)
    assert actual_path == expected_path
    assert actual_file == expected_file


@pytest.mark.parametrize(
    "build_config,context,dockerfile_path",
    [
        ({}, "", ""),
        ({"build_subdir": "/builddir/Dockerfile"}, "", "/builddir/Dockerfile"),
        ({"context": "/builddir"}, "/builddir", ""),
        (
            {"context": "/builddir", "build_subdir": "/builddir/Dockerfile"},
            "/builddir",
            "Dockerfile",
        ),
        (
            {"context": "/some_other_dir/Dockerfile", "build_subdir": "/builddir/Dockerfile"},
            "/builddir",
            "Dockerfile",
        ),
        ({"context": "/", "build_subdir": "Dockerfile"}, "/", "Dockerfile"),
    ],
)
def test_extract_dockerfile_args(build_config, context, dockerfile_path):
    actual_context, actual_dockerfile_path = BuildComponent.extract_dockerfile_args(build_config)
    assert context == actual_context
    assert dockerfile_path == actual_dockerfile_path
