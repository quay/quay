"""
Tests for v2 endpoint capability headers.
"""

import json

import pytest
from playhouse.pool import MaxConnectionsExceeded

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


def test_MaxConnectionsExceeded_properly_returns_a_503_when_raised(app, client):
    """
    Verifies that a 503 is returned back to the caller with a retry header if
    MaxConnectionsExceeded is raised by the app during access.
    """
    with app.test_request_context("/"):
        try:
            raise MaxConnectionsExceeded("pool full")
        except Exception as e:
            response = app.handle_user_exception(e)

    assert response.status_code == 503
    assert "Retry-After" in response.headers
    assert response.headers["Retry-After"] == "5"

    data = json.loads(response.get_data(as_text=True))
    assert "errors" in data
    assert data["errors"][0]["message"] == "Service temporarily unavailable"
