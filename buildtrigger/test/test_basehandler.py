import pytest

from buildtrigger.basehandler import BuildTriggerHandler


@pytest.mark.parametrize(
    "input,output",
    [
        ("Dockerfile", True),
        ("server.Dockerfile", True),
        (u"Dockerfile", True),
        (u"server.Dockerfile", True),
        ("bad file name", False),
        (u"bad file name", False),
    ],
)
def test_path_is_dockerfile(input, output):
    assert BuildTriggerHandler.filename_is_dockerfile(input) == output


@pytest.mark.parametrize(
    "input,output",
    [
        ("", {}),
        ("/a", {"/a": ["/"]}),
        ("a", {"/a": ["/"]}),
        ("/b/a", {"/b/a": ["/b", "/"]}),
        ("b/a", {"/b/a": ["/b", "/"]}),
        ("/c/b/a", {"/c/b/a": ["/c/b", "/c", "/"]}),
        ("/a//b//c", {"/a/b/c": ["/", "/a", "/a/b"]}),
        ("/a", {"/a": ["/"]}),
    ],
)
def test_subdir_path_map_no_previous(input, output):
    actual_mapping = BuildTriggerHandler.get_parent_directory_mappings(input)
    for key in actual_mapping:
        value = actual_mapping[key]
        actual_mapping[key] = value.sort()
    for key in output:
        value = output[key]
        output[key] = value.sort()

    assert actual_mapping == output


@pytest.mark.parametrize(
    "new_path,original_dictionary,output",
    [
        ("/a", {}, {"/a": ["/"]}),
        (
            "b",
            {"/a": ["some_path", "another_path"]},
            {"/a": ["some_path", "another_path"], "/b": ["/"]},
        ),
        (
            "/a/b/c/d",
            {"/e": ["some_path", "another_path"]},
            {"/e": ["some_path", "another_path"], "/a/b/c/d": ["/", "/a", "/a/b", "/a/b/c"]},
        ),
    ],
)
def test_subdir_path_map(new_path, original_dictionary, output):
    actual_mapping = BuildTriggerHandler.get_parent_directory_mappings(
        new_path, original_dictionary
    )
    for key in actual_mapping:
        value = actual_mapping[key]
        actual_mapping[key] = value.sort()
    for key in output:
        value = output[key]
        output[key] = value.sort()

    assert actual_mapping == output
