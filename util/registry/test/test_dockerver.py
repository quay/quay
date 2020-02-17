import pytest

from util.registry.dockerver import docker_version
from semantic_version import Version, Spec


@pytest.mark.parametrize(
    "ua_string, ver_info",
    [
        # Old "semantic" versioning.
        (
            "docker/1.6.0 go/go1.4.2 git-commit/1234567 kernel/4.2.0-18-generic os/linux arch/amd64",
            Version("1.6.0"),
        ),
        (
            "docker/1.7.1 go/go1.4.2 kernel/4.1.7-15.23.amzn1.x86_64 os/linux arch/amd64",
            Version("1.7.1"),
        ),
        (
            "docker/1.6.2 go/go1.4.2 git-commit/7c8fca2-dirty kernel/4.0.5 os/linux arch/amd64",
            Version("1.6.2"),
        ),
        (
            "docker/1.9.0 go/go1.4.2 git-commit/76d6bc9 kernel/3.16.0-4-amd64 os/linux arch/amd64",
            Version("1.9.0"),
        ),
        (
            "docker/1.9.1 go/go1.4.2 git-commit/a34a1d5 kernel/3.10.0-229.20.1.el7.x86_64 os/linux arch/amd64",
            Version("1.9.1"),
        ),
        (
            "docker/1.8.2-circleci go/go1.4.2 git-commit/a8b52f5 kernel/3.13.0-71-generic os/linux arch/amd64",
            Version("1.8.2"),
        ),
        ("Go 1.1 package http", Version("1.5.0")),
        ("curl", None),
        ("docker/1.8 stuff", Version("1.8", partial=True)),
        # Newer date-based versioning: YY.MM.revnum
        ("docker/17.03.0 my_version_sucks", Version("17.3.0")),
        ("docker/17.03.0-foobar my_version_sucks", Version("17.3.0")),
        (
            "docker/17.10.2 go/go1.4.2 git-commit/a34a1d5 kernel/3.10.0-229.20.1.el7.x86_64 os/linux arch/amd64",
            Version("17.10.2"),
        ),
        ("docker/17.00.4 my_version_sucks", Version("17.0.4")),
        ("docker/17.12.00 my_version_sucks", Version("17.12.0")),
    ],
)
def test_parsing(ua_string, ver_info):
    parsed_ver = docker_version(ua_string)
    assert parsed_ver == ver_info, "Expected %s, Found %s" % (ver_info, parsed_ver)


@pytest.mark.parametrize(
    "spec, no_match_cases, match_cases",
    [
        (Spec("<1.6.0"), ["1.6.0", "1.6.1", "1.9.0", "100.5.2"], ["0.0.0", "1.5.99"]),
        (Spec("<1.9.0"), ["1.9.0", "100.5.2"], ["0.0.0", "1.5.99", "1.6.0", "1.6.1"]),
        (Spec("<1.6.0,>0.0.1"), ["1.6.0", "1.6.1", "1.9.0", "0.0.0"], ["1.5.99"]),
        (Spec(">17.3.0"), ["17.3.0", "1.13.0"], ["17.4.0", "17.12.1"]),
    ],
)
def test_specs(spec, no_match_cases, match_cases):
    for no_match_case in no_match_cases:
        assert not spec.match(Version(no_match_case))

    for match_case in match_cases:
        assert spec.match(Version(match_case))
