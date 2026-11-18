import base64

import pytest
from flask import Flask

from storage.upstreamproxy import (
    UPSTREAM_PROXY_ACCESS_TYPE,
    UPSTREAM_PROXY_SUBJECT,
    UpstreamProxy,
)
from test.fixtures import *  # noqa: F401, F403 — sets up the SQLite test database
from util.security.registry_jwt import decode_bearer_token

TEST_SERVER_HOSTNAME = "quay.test"
TEST_SCHEME = "https"
TEST_UPSTREAM_HOSTNAME = "registry-1.docker.io"
TEST_LOCAL_NAMESPACE = "myorg"
TEST_UPSTREAM_NAMESPACE = "library"
TEST_UPSTREAM_REPO = "ubuntu"
TEST_DIGEST = "sha256:" + "a" * 64


@pytest.fixture
def real_instance_keys(initialized_db):
    from app import instance_keys

    return instance_keys


@pytest.fixture
def proxy_setup(real_instance_keys):
    app = Flask("test_upstreamproxy")
    app.config["SERVER_HOSTNAME"] = TEST_SERVER_HOSTNAME
    app.config["PREFERRED_URL_SCHEME"] = TEST_SCHEME
    proxy = UpstreamProxy(app, real_instance_keys)
    return proxy


class TestCreateUpstreamProxyUrl:
    def test_url_contains_correct_path_structure(self, proxy_setup):
        """
        Verifies that the set up URL has the proper path structure and
        components.
        """
        proxy = proxy_setup
        url = proxy.create_upstream_proxy_url(
            TEST_SCHEME,
            TEST_UPSTREAM_HOSTNAME,
            TEST_LOCAL_NAMESPACE,
            TEST_UPSTREAM_NAMESPACE,
            TEST_UPSTREAM_REPO,
            TEST_DIGEST,
        )
        assert "/_upstream_proxy/" in url
        expected_suffix = (
            f"/{TEST_SCHEME}/{TEST_UPSTREAM_HOSTNAME}"
            f"/v2/{TEST_UPSTREAM_NAMESPACE}/{TEST_UPSTREAM_REPO}/blobs/{TEST_DIGEST}"
        )
        assert expected_suffix in url

    def test_empty_upstream_namespace_normalized_to_library(self, proxy_setup):
        """
        Verifies that the library namespace normalization works as intended.
        """
        proxy = proxy_setup
        url = proxy.create_upstream_proxy_url(
            TEST_SCHEME,
            TEST_UPSTREAM_HOSTNAME,
            TEST_LOCAL_NAMESPACE,
            "",
            TEST_UPSTREAM_REPO,
            TEST_DIGEST,
        )
        assert "/v2/library/" in url

    def test_jwt_payload_contains_correct_access_fields(self, proxy_setup, real_instance_keys):
        """
        Verifies that the created payload has all the necessary fields.
        """
        proxy = proxy_setup
        url = proxy.create_upstream_proxy_url(
            TEST_SCHEME,
            TEST_UPSTREAM_HOSTNAME,
            TEST_LOCAL_NAMESPACE,
            TEST_UPSTREAM_NAMESPACE,
            TEST_UPSTREAM_REPO,
            TEST_DIGEST,
        )

        # Extract and verify the JWT embedded in the URL
        encoded_token = url.split("/_upstream_proxy/")[1].split("/")[0]
        token = base64.urlsafe_b64decode(encoded_token)
        decoded = decode_bearer_token(token, real_instance_keys, proxy.app.config)

        assert decoded["sub"] == UPSTREAM_PROXY_SUBJECT
        access = decoded["access"]
        assert len(access) == 1
        a = access[0]
        assert a["type"] == UPSTREAM_PROXY_ACCESS_TYPE
        assert a["scheme"] == TEST_SCHEME
        assert a["hostname"] == TEST_UPSTREAM_HOSTNAME
        assert a["local_namespace"] == TEST_LOCAL_NAMESPACE
        assert a["upstream_namespace"] == TEST_UPSTREAM_NAMESPACE
        assert a["upstream_repository"] == TEST_UPSTREAM_REPO
        assert a["blob_sha"] == TEST_DIGEST
