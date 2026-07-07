from mock import patch

import pytest

from data import model
from endpoints.api import api
from endpoints.api.organization import (
    Organization,
    OrganizationCollaboratorList,
    OrganizationProxyCacheConfig,
    ProxyCacheConfigValidation,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, toggle_feature
from test.fixtures import *


@pytest.mark.parametrize(
    "expiration, expected_code",
    [
        (0, 200),
        (100, 400),
        (100000000000000000000, 400),
    ],
)
def test_change_tag_expiration(expiration, expected_code, app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            Organization,
            "PUT",
            {"orgname": "buynlarge"},
            body={"tag_expiration_s": expiration},
            expected_code=expected_code,
        )


def test_get_organization_collaborators(app):
    params = {"orgname": "buynlarge"}

    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(cl, OrganizationCollaboratorList, "GET", params)

    collaborator_names = [c["name"] for c in resp.json["collaborators"]]
    assert "outsideorg" in collaborator_names
    assert "devtable" not in collaborator_names
    assert "reader" not in collaborator_names

    for collaborator in resp.json["collaborators"]:
        if collaborator["name"] == "outsideorg":
            assert "orgrepo" in collaborator["repositories"]
            assert "anotherorgrepo" not in collaborator["repositories"]


@pytest.fixture()
def _mock_dns_for_ssrf_validation():
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns


@pytest.mark.usefixtures("_mock_dns_for_ssrf_validation")
class TestProxyCacheSSRFProtection:
    """Tests for SSRF protection in proxy cache configuration endpoints (CVE-2026-32591)."""

    def _cleanup_proxy_cache_config(self, orgname):
        try:
            model.proxy_cache.delete_proxy_cache_config(orgname)
        except Exception:
            pass

    def test_create_with_private_ip_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "10.0.0.1"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_loopback_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "127.0.0.1"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_aws_metadata_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "169.254.169.254"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_kubernetes_hostname_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "kubernetes.default.svc"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_gcp_metadata_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "metadata.google.internal"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_valid_registry_succeeds(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "docker.io"}
                conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 201)

        self._cleanup_proxy_cache_config("buynlarge")

    def test_validate_with_private_ip_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "10.0.0.1"}
                resp = conduct_api_call(cl, ProxyCacheConfigValidation, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_validate_with_aws_metadata_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "169.254.169.254"}
                resp = conduct_api_call(cl, ProxyCacheConfigValidation, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_validate_with_localhost_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "localhost"}
                resp = conduct_api_call(cl, ProxyCacheConfigValidation, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_upstream_namespace_and_private_ip_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "10.0.0.1/myorg"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")
