"""
Tests for the registry capabilities API endpoint.
"""

import pytest

from app import app as realapp
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, toggle_feature
from test.fixtures import *


class TestRegistryCapabilities:
    def test_capabilities_no_auth_required(self, app):
        """Test capabilities endpoint accessible without authentication."""
        from endpoints.api.capabilities import RegistryCapabilities
        from endpoints.test.shared import add_csrf_param

        with app.test_client() as cl:
            params = add_csrf_param(cl, {})
            rv = cl.get(
                "/api/v1/registry/capabilities",
                headers={"Content-Type": "application/json"},
            )
            assert rv.status_code == 200

    def test_capabilities_sparse_disabled(self, app):
        """Test capabilities endpoint when sparse manifests disabled."""
        from endpoints.api.capabilities import RegistryCapabilities

        with toggle_feature("SPARSE_INDEX", False):
            with client_with_identity("devtable", app) as cl:
                resp = conduct_api_call(cl, RegistryCapabilities, "GET", {}, None, 200)
                assert resp.json["sparse_manifests"]["supported"] is False
                assert resp.json["sparse_manifests"]["required_architectures"] == []
                assert resp.json["sparse_manifests"]["optional_architectures_allowed"] is False

    def test_capabilities_sparse_enabled(self, app):
        """Test capabilities endpoint when sparse manifests enabled."""
        from endpoints.api.capabilities import RegistryCapabilities

        with toggle_feature("SPARSE_INDEX", True):
            with client_with_identity("devtable", app) as cl:
                resp = conduct_api_call(cl, RegistryCapabilities, "GET", {}, None, 200)
                assert resp.json["sparse_manifests"]["supported"] is True

    def test_capabilities_with_required_archs(self, app):
        """Test capabilities endpoint with required architectures configured."""
        from endpoints.api.capabilities import RegistryCapabilities

        with toggle_feature("SPARSE_INDEX", True):
            original_archs = realapp.config.get("SPARSE_INDEX_REQUIRED_ARCHS", [])
            realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = ["amd64", "arm64"]
            try:
                with client_with_identity("devtable", app) as cl:
                    resp = conduct_api_call(cl, RegistryCapabilities, "GET", {}, None, 200)
                    assert resp.json["sparse_manifests"]["supported"] is True
                    assert resp.json["sparse_manifests"]["required_architectures"] == [
                        "amd64",
                        "arm64",
                    ]
                    assert resp.json["sparse_manifests"]["optional_architectures_allowed"] is True
            finally:
                realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = original_archs

    def test_capabilities_sparse_enabled_no_required_archs(self, app):
        """Test capabilities endpoint when sparse enabled but no required archs."""
        from endpoints.api.capabilities import RegistryCapabilities

        with toggle_feature("SPARSE_INDEX", True):
            original_archs = realapp.config.get("SPARSE_INDEX_REQUIRED_ARCHS", [])
            realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = []
            try:
                with client_with_identity("devtable", app) as cl:
                    resp = conduct_api_call(cl, RegistryCapabilities, "GET", {}, None, 200)
                    assert resp.json["sparse_manifests"]["supported"] is True
                    assert resp.json["sparse_manifests"]["required_architectures"] == []
                    # optional_architectures_allowed is False when no required archs
                    assert resp.json["sparse_manifests"]["optional_architectures_allowed"] is False
            finally:
                realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = original_archs

    def test_capabilities_response_structure(self, app):
        """Test capabilities endpoint response has correct structure."""
        from endpoints.api.capabilities import RegistryCapabilities

        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(cl, RegistryCapabilities, "GET", {}, None, 200)
            # Verify top-level keys exist
            assert "sparse_manifests" in resp.json
            # Verify sparse_manifests structure
            assert "supported" in resp.json["sparse_manifests"]
            assert "required_architectures" in resp.json["sparse_manifests"]
            assert "optional_architectures_allowed" in resp.json["sparse_manifests"]
