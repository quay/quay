import base64
import json
import os

import pytest

from util.repomirror.skopeomirror import (
    SKOPEO_TIMEOUT_SECONDS,
    AuthContent,
    SkopeoMirror,
    _registry_netloc,
    _src_dest_authfiles,
    create_authfile_content,
)


def test_create_authfile_content():
    registries = ["quay.io", "registry.redhat.io", "docker.io"]
    content = create_authfile_content(
        [
            AuthContent(registries[0], "user1", "user1"),
            AuthContent(registries[1], "user2", "user2"),
            # "anonymous" with no password: username passes the None/empty filter but
            # wrap_anonymous returns "" for missing password → empty auth value.
            AuthContent(registries[2], "anonymous", ""),
        ]
    )
    auths = content["auths"]
    assert auths[registries[0]]["auth"] == base64.b64encode("user1:user1".encode("utf8")).decode(
        "utf8"
    )
    assert auths[registries[1]]["auth"] == base64.b64encode("user2:user2".encode("utf8")).decode(
        "utf8"
    )
    assert auths[registries[2]]["auth"] == ""


def test_create_authfile_content_filters_none_username():
    content = create_authfile_content(
        [
            AuthContent("registry.example.com", None, None),
            AuthContent("quay.io", "user", "pass"),
        ]
    )
    assert set(content.get("auths", {}).keys()) == {"quay.io"}


def test_create_authfile_content_empty_when_no_credentials():
    content = create_authfile_content(
        [AuthContent("quay.io", None, None), AuthContent("docker.io", "", "")]
    )
    assert content == {"auths": {}}


def test_create_authfile_content_same_registry_overwrites():
    """Reproduce PROJQUAY-12190: when source and dest are on the same registry,
    the dict comprehension keeps only the last entry, losing source credentials."""
    content = create_authfile_content(
        [
            AuthContent("quay.example.com", "src_robot", "src_pass"),
            AuthContent("quay.example.com", "dest_robot", "dest_pass"),
        ]
    )
    auths = content["auths"]
    # With a single shared authfile keyed by hostname, only one entry survives.
    # This test documents the bug: two different credentials for the same host
    # collapse into one.
    assert len(auths) == 1
    assert auths["quay.example.com"]["auth"] == base64.b64encode(
        "dest_robot:dest_pass".encode("utf8")
    ).decode("utf8")


def test_registry_netloc_docker_transport():
    assert _registry_netloc("docker://quay.io/repo:tag") == "quay.io"
    assert _registry_netloc("docker://registry.example.com/repo:tag") == "registry.example.com"


def test_registry_netloc_filesystem_transports_return_none():
    assert _registry_netloc("oci-archive:/tmp/x.tar") is None
    assert _registry_netloc("oci:/tmp/x") is None
    assert _registry_netloc("dir:/tmp/x") is None
    assert _registry_netloc("docker-archive:/tmp/x.tar") is None


def test_registry_netloc_docker_daemon():
    assert (
        _registry_netloc("docker-daemon:registry.example.com/image:tag") == "registry.example.com"
    )
    assert _registry_netloc("docker-daemon:image") is None


@pytest.mark.integration
def test_skopeo_command_copy():
    result = SkopeoMirror().copy(
        "docker://quay.io/quay/busybox:latest",
        "oci-archive:/dev/null",
        proxy={"http_proxy": "", "https_proxy": "", "no_proxy": ""},
        timeout=SKOPEO_TIMEOUT_SECONDS,
    )
    assert result.success
    assert "Copying blob sha256:" in result.stdout
    assert result.stderr == ""


@pytest.mark.skip(reason="no fixed credentials available for authenticated testing")
def test_skopeo_command_authenticated():
    result = SkopeoMirror().copy(
        f"docker://{os.environ.get('src_image')}",
        "oci-archive:/dev/null",
        src_username=os.environ.get("user-to-authenticated"),
        src_password=os.environ.get("pass-to-authenticated"),
        proxy={"http_proxy": "", "https_proxy": "", "no_proxy": ""},
        timeout=SKOPEO_TIMEOUT_SECONDS,
    )
    assert result.success
    assert "Copying blob sha256:" in result.stdout
    assert result.stderr == ""


@pytest.mark.integration
def test_skopeo_command_tags():
    result = SkopeoMirror().tags(
        "docker://quay.io/quay/busybox",
        proxy={"http_proxy": "", "https_proxy": "", "no_proxy": ""},
        timeout=SKOPEO_TIMEOUT_SECONDS,
    )
    assert result.success
    assert len(result.tags) > 0
    assert result.stderr == ""


def test_src_dest_authfiles_yields_two_distinct_paths():
    """_src_dest_authfiles creates two independent temp files."""
    with _src_dest_authfiles(
        [AuthContent("src.example.com", "src_user", "src_pass")],
        [AuthContent("dest.example.com", "dest_user", "dest_pass")],
    ) as (src_path, dest_path):
        assert src_path != dest_path
        assert os.path.exists(src_path)
        assert os.path.exists(dest_path)

        with open(src_path) as f:
            src_content = json.loads(f.read())
        with open(dest_path) as f:
            dest_content = json.loads(f.read())

        assert "src.example.com" in src_content["auths"]
        assert "dest.example.com" not in src_content["auths"]
        assert "dest.example.com" in dest_content["auths"]
        assert "src.example.com" not in dest_content["auths"]


def test_src_dest_authfiles_same_registry_preserves_both():
    """When source and dest are on the same registry, each authfile has its own credentials."""
    with _src_dest_authfiles(
        [AuthContent("quay.example.com", "src_robot", "src_pass")],
        [AuthContent("quay.example.com", "dest_robot", "dest_pass")],
    ) as (src_path, dest_path):
        with open(src_path) as f:
            src_content = json.loads(f.read())
        with open(dest_path) as f:
            dest_content = json.loads(f.read())

        src_auth = base64.b64decode(
            src_content["auths"]["quay.example.com"]["auth"]
        ).decode("utf8")
        dest_auth = base64.b64decode(
            dest_content["auths"]["quay.example.com"]["auth"]
        ).decode("utf8")

        assert src_auth == "src_robot:src_pass"
        assert dest_auth == "dest_robot:dest_pass"
