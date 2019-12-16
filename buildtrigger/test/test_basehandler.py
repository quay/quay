import pytest

from buildtrigger.basehandler import BuildTriggerHandler


@pytest.mark.parametrize(
    "input,output",
    [
        ("Dockerfile", True),
        ("server.Dockerfile", True),
        ("Dockerfile", True),
        ("server.Dockerfile", True),
        ("bad file name", False),
        ("bad file name", False),
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


@pytest.mark.parametrize(
    "config, metadata, expected_tags",
    [
        pytest.param(
            {}, {"commit": "hellothereiamacommit"}, ["helloth"], id="no ref and default options",
        ),
        pytest.param(
            {},
            {"commit": "hellothereiamacommit", "ref": "refs/heads/somebranch"},
            ["somebranch"],
            id="ref and default options",
        ),
        pytest.param(
            {"default_tag_from_ref": False},
            {"commit": "hellothereiamacommit", "ref": "refs/heads/somebranch"},
            ["helloth"],
            id="ref and default turned off",
        ),
        pytest.param(
            {
                "default_tag_from_ref": False,
                "tag_templates": [
                    "${commit_info.short_sha}",
                    "author-${commit_info.author.username}",
                ],
            },
            {
                "commit": "hellothereiamacommit",
                "ref": "refs/heads/somebranch",
                "commit_info": {"author": {"username": "someguy"},},
            },
            ["author-someguy", "helloth"],
            id="template test",
        ),
        pytest.param(
            {
                "default_tag_from_ref": False,
                "tag_templates": [
                    "${commit_info.short_sha}",
                    "author-${commit_info.author.username}",
                ],
            },
            {
                "commit": "hellothereiamacommit",
                "ref": "refs/heads/somebranch",
                "default_branch": "somebranch",
                "commit_info": {"author": {"username": "someguy"},},
            },
            ["author-someguy", "helloth", "latest"],
            id="template test with default branch",
        ),
        pytest.param(
            {
                "default_tag_from_ref": False,
                "tag_templates": [
                    "${commit_info.short_sha}",
                    "author-${commit_info.author.username}",
                ],
            },
            {
                "commit": "hellothereiamacommit",
                "ref": "refs/heads/somebranch",
                "default_branch": "somebranch",
            },
            ["helloth", "latest"],
            id="missing info template test",
        ),
        pytest.param(
            {"default_tag_from_ref": False},
            {
                "commit": "hellothereiamacommit",
                "ref": "refs/heads/somebranch",
                "default_branch": "somebranch",
            },
            ["latest"],
            id="default branch",
        ),
        pytest.param(
            {"default_tag_from_ref": False, "latest_for_default_branch": False},
            {
                "commit": "hellothereiamacommit",
                "ref": "refs/heads/somebranch",
                "default_branch": "somebranch",
            },
            ["helloth"],
            id="default branch turned off",
        ),
        pytest.param(
            {
                "tag_templates": [
                    "${commit_info.short_sha}",
                    "author-${commit_info.author.username}",
                ]
            },
            {
                "commit": "hellothereiamacommit",
                "ref": "refs/heads/somebranch",
                "default_branch": "somebranch",
                "commit_info": {"author": {"username": "someguy"},},
            },
            ["author-someguy", "helloth", "latest", "somebranch"],
            id="everything test",
        ),
    ],
)
def test_determine_tags(config, metadata, expected_tags):
    tags = BuildTriggerHandler._determine_tags(config, metadata)
    assert tags == set(expected_tags)
