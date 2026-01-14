"""
Tests for v2 endpoint capability headers.
"""

import pytest

from app import app as realapp
from endpoints.test.shared import toggle_feature
from test.fixtures import *


class TestV2CapabilityHeaders:
    def test_v2_base_sparse_header_disabled(self, app):
        """Test v2 base endpoint includes sparse capability header when disabled."""
        with toggle_feature("SPARSE_INDEX", False):
            with app.test_client() as cl:
                rv = cl.get("/v2/")
                assert rv.headers.get("X-Sparse-Manifest-Support") == "false"
                assert rv.headers.get("X-Required-Architectures") is None

    def test_v2_base_sparse_header_enabled(self, app):
        """Test v2 base endpoint includes sparse capability header when enabled."""
        with toggle_feature("SPARSE_INDEX", True):
            with app.test_client() as cl:
                rv = cl.get("/v2/")
                assert rv.headers.get("X-Sparse-Manifest-Support") == "true"

    def test_v2_base_required_archs_header(self, app):
        """Test v2 base endpoint includes required architectures header."""
        with toggle_feature("SPARSE_INDEX", True):
            original_archs = realapp.config.get("SPARSE_INDEX_REQUIRED_ARCHS", [])
            realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = ["amd64", "arm64"]
            try:
                with app.test_client() as cl:
                    rv = cl.get("/v2/")
                    assert rv.headers.get("X-Sparse-Manifest-Support") == "true"
                    assert rv.headers.get("X-Required-Architectures") == "amd64,arm64"
            finally:
                realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = original_archs

    def test_v2_base_no_required_archs_header_when_empty(self, app):
        """Test v2 base endpoint does not include required architectures header when empty."""
        with toggle_feature("SPARSE_INDEX", True):
            original_archs = realapp.config.get("SPARSE_INDEX_REQUIRED_ARCHS", [])
            realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = []
            try:
                with app.test_client() as cl:
                    rv = cl.get("/v2/")
                    assert rv.headers.get("X-Sparse-Manifest-Support") == "true"
                    # No header when empty list
                    assert rv.headers.get("X-Required-Architectures") is None
            finally:
                realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = original_archs

    def test_v2_base_no_required_archs_header_when_disabled(self, app):
        """Test v2 base endpoint does not include required architectures header when sparse disabled."""
        with toggle_feature("SPARSE_INDEX", False):
            original_archs = realapp.config.get("SPARSE_INDEX_REQUIRED_ARCHS", [])
            realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = ["amd64", "arm64"]
            try:
                with app.test_client() as cl:
                    rv = cl.get("/v2/")
                    assert rv.headers.get("X-Sparse-Manifest-Support") == "false"
                    # No header when sparse is disabled, even if archs configured
                    assert rv.headers.get("X-Required-Architectures") is None
            finally:
                realapp.config["SPARSE_INDEX_REQUIRED_ARCHS"] = original_archs
