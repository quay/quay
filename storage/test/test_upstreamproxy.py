"""
Tests for storage.upstreamproxy.UpstreamProxy.

Covers:
  - create_upstream_proxy_url: URL structure, namespace normalization, JWT payload
  - validate_upstream_proxy_auth: all 401 failure paths and the 200 happy path
"""

import base64
from unittest.mock import MagicMock, patch

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
    """
    Returns (upstream_proxy_instance, flask_test_client) backed by a minimal
    Flask app. The app is isolated from the main Quay app to avoid
    double-registration of the /_upstream_proxy_auth route.
    """
    app = Flask("test_upstreamproxy")
    app.config["SERVER_HOSTNAME"] = TEST_SERVER_HOSTNAME
    app.config["PREFERRED_URL_SCHEME"] = TEST_SCHEME
    proxy = UpstreamProxy(app, real_instance_keys)
    return proxy, app.test_client()


def _make_uri(
    proxy,
    scheme=TEST_SCHEME,
    hostname=TEST_UPSTREAM_HOSTNAME,
    local_ns=TEST_LOCAL_NAMESPACE,
    upstream_ns=TEST_UPSTREAM_NAMESPACE,
    repo=TEST_UPSTREAM_REPO,
    digest=TEST_DIGEST,
):
    """Generate a valid /_upstream_proxy/... URI using the given proxy instance."""
    full_url = proxy.create_upstream_proxy_url(
        scheme, hostname, local_ns, upstream_ns, repo, digest
    )
    return "/_upstream_proxy/" + full_url.split("/_upstream_proxy/")[1]


# ---------------------------------------------------------------------------
# create_upstream_proxy_url
# ---------------------------------------------------------------------------


class TestCreateUpstreamProxyUrl:
    def test_url_contains_correct_path_structure(self, proxy_setup):
        proxy, _ = proxy_setup
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
        proxy, _ = proxy_setup
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
        proxy, _ = proxy_setup
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


# ---------------------------------------------------------------------------
# validate_upstream_proxy_auth — 401 failure paths
# ---------------------------------------------------------------------------


class TestValidateUpstreamProxyAuthFailures:
    def test_missing_x_original_uri_returns_401(self, proxy_setup):
        _, client = proxy_setup
        resp = client.get("/_upstream_proxy_auth")
        assert resp.status_code == 401

    def test_wrong_url_prefix_returns_401(self, proxy_setup):
        _, client = proxy_setup
        resp = client.get(
            "/_upstream_proxy_auth",
            headers={
                "X-Original-URI": f"/not_upstream_proxy/token/https/host/v2/ns/repo/blobs/{TEST_DIGEST}"
            },
        )
        assert resp.status_code == 401

    def test_too_few_url_parts_returns_401(self, proxy_setup):
        _, client = proxy_setup
        resp = client.get(
            "/_upstream_proxy_auth",
            headers={"X-Original-URI": "/_upstream_proxy/token/https/host"},
        )
        assert resp.status_code == 401

    def test_wrong_v2_segment_returns_401(self, proxy_setup):
        _, client = proxy_setup
        resp = client.get(
            "/_upstream_proxy_auth",
            headers={
                "X-Original-URI": f"/_upstream_proxy/token/https/host/wrongv2/ns/repo/blobs/{TEST_DIGEST}"
            },
        )
        assert resp.status_code == 401

    def test_wrong_blobs_segment_returns_401(self, proxy_setup):
        _, client = proxy_setup
        resp = client.get(
            "/_upstream_proxy_auth",
            headers={
                "X-Original-URI": f"/_upstream_proxy/token/https/host/v2/ns/repo/wrongblobs/{TEST_DIGEST}"
            },
        )
        assert resp.status_code == 401

    def test_non_sha256_digest_returns_401(self, proxy_setup):
        _, client = proxy_setup
        resp = client.get(
            "/_upstream_proxy_auth",
            headers={
                "X-Original-URI": "/_upstream_proxy/token/https/host/v2/ns/repo/blobs/md5:abc123"
            },
        )
        assert resp.status_code == 401

    def test_invalid_base64_token_returns_401(self, proxy_setup):
        _, client = proxy_setup
        # Valid base64 characters but decodes to garbage (not a real JWT)
        bad_token = base64.urlsafe_b64encode(b"this-is-not-a-jwt").decode("ascii")
        resp = client.get(
            "/_upstream_proxy_auth",
            headers={
                "X-Original-URI": f"/_upstream_proxy/{bad_token}/https/host/v2/ns/repo/blobs/{TEST_DIGEST}"
            },
        )
        assert resp.status_code == 401

    def test_scheme_mismatch_returns_401(self, proxy_setup):
        proxy, client = proxy_setup
        uri = _make_uri(proxy)
        # Swap https → http in the URL path so it no longer matches the JWT
        tampered = uri.replace(f"/{TEST_SCHEME}/", "/http/", 1)
        resp = client.get("/_upstream_proxy_auth", headers={"X-Original-URI": tampered})
        assert resp.status_code == 401

    def test_hostname_mismatch_returns_401(self, proxy_setup):
        proxy, client = proxy_setup
        uri = _make_uri(proxy)
        tampered = uri.replace(TEST_UPSTREAM_HOSTNAME, "evil.registry.io")
        resp = client.get("/_upstream_proxy_auth", headers={"X-Original-URI": tampered})
        assert resp.status_code == 401

    def test_namespace_mismatch_returns_401(self, proxy_setup):
        proxy, client = proxy_setup
        uri = _make_uri(proxy)
        tampered = uri.replace(f"/v2/{TEST_UPSTREAM_NAMESPACE}/", "/v2/evil_ns/")
        resp = client.get("/_upstream_proxy_auth", headers={"X-Original-URI": tampered})
        assert resp.status_code == 401

    def test_proxy_cache_config_not_found_returns_401(self, proxy_setup):
        from data.model import InvalidProxyCacheConfigException

        proxy, client = proxy_setup
        uri = _make_uri(proxy)
        with patch(
            "data.model.proxy_cache.get_proxy_cache_config_for_org",
            side_effect=InvalidProxyCacheConfigException("not found"),
        ):
            resp = client.get("/_upstream_proxy_auth", headers={"X-Original-URI": uri})
        assert resp.status_code == 401

    def test_upstream_auth_failure_returns_401(self, proxy_setup):
        from proxy import UpstreamRegistryError

        proxy, client = proxy_setup
        uri = _make_uri(proxy)
        mock_proxy_instance = MagicMock()
        mock_proxy_instance._ensure_authorized.side_effect = UpstreamRegistryError("auth failed")
        with (
            patch(
                "data.model.proxy_cache.get_proxy_cache_config_for_org", return_value=MagicMock()
            ),
            patch("proxy.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get("/_upstream_proxy_auth", headers={"X-Original-URI": uri})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# validate_upstream_proxy_auth — happy path
# ---------------------------------------------------------------------------


class TestValidateUpstreamProxyAuthSuccess:
    def test_valid_request_returns_200_with_upstream_auth_header(self, proxy_setup):
        proxy, client = proxy_setup
        uri = _make_uri(proxy)

        mock_proxy_instance = MagicMock()
        mock_proxy_instance._session.headers = {"Authorization": "Bearer upstreamtoken123"}

        with (
            patch(
                "data.model.proxy_cache.get_proxy_cache_config_for_org", return_value=MagicMock()
            ),
            patch("proxy.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get("/_upstream_proxy_auth", headers={"X-Original-URI": uri})

        assert resp.status_code == 200
        assert resp.headers.get("X-Upstream-Auth") == "Bearer upstreamtoken123"

    def test_multi_level_repository_parsed_correctly(self, proxy_setup):
        proxy, client = proxy_setup
        uri = _make_uri(proxy, repo="myorg/myapp")

        mock_proxy_instance = MagicMock()
        mock_proxy_instance._session.headers = {"Authorization": "Bearer token"}

        with (
            patch(
                "data.model.proxy_cache.get_proxy_cache_config_for_org", return_value=MagicMock()
            ),
            patch("proxy.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get("/_upstream_proxy_auth", headers={"X-Original-URI": uri})

        assert resp.status_code == 200
