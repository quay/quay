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
    content = create_authfile_content(
        [
            AuthContent("quay.io", "user1", "user1"),
            AuthContent("registry.redhat.io", "user2", "user2"),
            AuthContent("docker.io", "anonymous", ""),
        ]
    )
    assert content.get("auths").get("quay.io").get("auth") == base64.b64encode(
        "user1:user1".encode("utf8")
    ).decode("utf8")
    assert content.get("auths").get("registry.redhat.io").get("auth") == base64.b64encode(
        "user2:user2".encode("utf8")
    ).decode("utf8")
    assert content.get("auths").get("docker.io").get("auth") == ""


def test_skopeo_command_copy():
    result = SkopeoMirror().copy(
        "docker://quay.io/quay/busybox:latest",
        "oci-archive://dev/null",
        proxy={"http_proxy": "", "https_proxy": "", "no_proxy": ""},
        timeout=SKOPEO_TIMEOUT_SECONDS,
    )
    assert result.success == True
    assert "Copying blob sha256:" in result.stdout
    assert result.stderr == ""


def test_skopeo_command_authenticated():
    # since there's no fixed user to test authenticated skip for now
    assert True == True
    return
    result = SkopeoMirror().copy(
        f"docker://{os.environ.get('src_image')}",
        "oci-archive://dev/null",
        src_username=os.environ.get("user-to-authenticated"),
        src_password=os.environ.get("pass-to-authenticated"),
        proxy={"http_proxy": "", "https_proxy": "", "no_proxy": ""},
        timeout=SKOPEO_TIMEOUT_SECONDS,
    )
    assert result.success == True
    assert "Copying blob sha256:" in result.stdout
    assert result.stderr == ""


def test_skopeo_command_tags():
    result = SkopeoMirror().tags(
        "docker://quay.io/quay/busybox",
        proxy={"http_proxy": "", "https_proxy": "", "no_proxy": ""},
        timeout=SKOPEO_TIMEOUT_SECONDS,
    )
    assert result.success == True
    assert len(result.tags) > 0
    assert result.stderr == ""
