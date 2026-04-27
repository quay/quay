import base64
import os

import pytest

from util.repomirror.skopeomirror import (
    SKOPEO_TIMEOUT_SECONDS,
    AuthContent,
    SkopeoMirror,
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
    assert "registry.example.com" not in content.get("auths", {})
    assert "quay.io" in content.get("auths", {})


def test_create_authfile_content_empty_when_no_credentials():
    content = create_authfile_content(
        [AuthContent("quay.io", None, None), AuthContent("docker.io", "", "")]
    )
    assert content == {"auths": {}}


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
