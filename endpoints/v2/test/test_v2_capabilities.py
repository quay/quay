"""
Tests for v2 endpoint capability headers.
"""

import pytest

from endpoints.test.shared import toggle_feature
from test.fixtures import *


class TestV2CapabilityHeaders:
    def test_v2_base_sparse_header_disabled(self, app):
        """Test v2 base endpoint includes sparse capability header when disabled."""
        with toggle_feature("SPARSE_INDEX", False):
            with app.test_client() as cl:
                rv = cl.get("/v2/")
                assert rv.headers.get("X-Sparse-Manifest-Support") == "false"

    def test_v2_base_sparse_header_enabled(self, app):
        """Test v2 base endpoint includes sparse capability header when enabled."""
        with toggle_feature("SPARSE_INDEX", True):
            with app.test_client() as cl:
                rv = cl.get("/v2/")
                assert rv.headers.get("X-Sparse-Manifest-Support") == "true"
