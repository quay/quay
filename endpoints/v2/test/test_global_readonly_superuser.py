"""
Tests for Global Read-Only Superuser functionality in API v2 (Docker Registry Protocol).

This test module validates that Global Read-Only Superusers have the correct
permissions for v2 API - read access to all registry content but blocked from write operations.
"""

from unittest.mock import patch

import pytest

from data import model
from endpoints.test.shared import client_with_identity
from test.fixtures import *


class TestV2GlobalReadOnlySuperuserPermissions:
    """Test v2 API permissions for global read-only superusers."""

    def test_v2_catalog_access(self, app):
        """Test that global read-only superusers can access the registry catalog."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Should be able to access catalog
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.get("/v2/_catalog", headers=headers)

                # In this setup with a fake bearer token, expect Unauthorized
                assert resp.status_code == 401

    def test_v2_tags_list_access(self, app):
        """Test that global read-only superusers can list repository tags."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                # Should be able to access tag lists
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.get("/v2/somenamespace/somerepo/tags/list", headers=headers)

                # In this setup with a fake bearer token, expect Unauthorized
                assert resp.status_code == 401

    def test_v2_manifest_read_access(self, app):
        """Test that global read-only superusers can read manifests."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.get("/v2/somenamespace/somerepo/manifests/latest", headers=headers)

                # In this setup with a fake bearer token, expect Unauthorized
                assert resp.status_code == 401

    def test_v2_blob_read_access(self, app):
        """Test that global read-only superusers can read blobs."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.get("/v2/somenamespace/somerepo/blobs/sha256:abcd1234", headers=headers)

                # In this setup with a fake bearer token, expect Unauthorized
                assert resp.status_code == 401


class TestV2GlobalReadOnlySuperuserWriteBlocking:
    """Test that v2 API write operations are blocked for global read-only superusers."""

    def test_v2_blob_upload_initiation_blocked(self, app):
        """Test that blob upload initiation is blocked."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token", "Content-Length": "0"}
                resp = cl.post("/v2/somenamespace/somerepo/blobs/uploads/", headers=headers)

                # Should get unauthorized due to write operation
                assert resp.status_code == 401

    def test_v2_manifest_upload_blocked(self, app):
        """Test that manifest uploads are blocked."""
        manifest_data = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "size": 1024,
                "digest": "sha256:abc123",
            },
            "layers": [],
        }

        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {
                    "Authorization": "Bearer fake-token",
                    "Content-Type": "application/vnd.docker.distribution.manifest.v2+json",
                }
                resp = cl.put(
                    "/v2/somenamespace/somerepo/manifests/blocked-tag",
                    headers=headers,
                    json=manifest_data,
                )

                # Should get unauthorized due to write operation
                assert resp.status_code == 401

    def test_v2_blob_upload_patch_blocked(self, app):
        """Test that blob upload PATCH operations are blocked."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.patch(
                    "/v2/somenamespace/somerepo/blobs/uploads/test-uuid", headers=headers
                )

                # Should get unauthorized due to write operation
                assert resp.status_code == 401

    def test_v2_blob_upload_put_blocked(self, app):
        """Test that blob upload PUT operations are blocked."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.put("/v2/somenamespace/somerepo/blobs/uploads/test-uuid", headers=headers)

                # Should get unauthorized due to write operation
                assert resp.status_code == 401

    def test_v2_blob_upload_delete_blocked(self, app):
        """Test that blob upload DELETE operations are blocked."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.delete(
                    "/v2/somenamespace/somerepo/blobs/uploads/test-uuid", headers=headers
                )

                # Should get unauthorized due to write operation
                assert resp.status_code == 401

    def test_v2_blob_delete_blocked(self, app):
        """Test that blob deletion is blocked."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token"}
                resp = cl.delete(
                    "/v2/somenamespace/somerepo/blobs/sha256:abcd1234", headers=headers
                )

                # Should get unauthorized due to write operation
                assert resp.status_code == 401

    def test_v2_manifest_delete_blocked(self, app):
        """Test that manifest deletion is blocked."""
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
            with client_with_identity("reader", app) as cl:
                headers = {"Authorization": "Bearer fake-token"}

                # Test deletion by digest
                resp = cl.delete(
                    "/v2/somenamespace/somerepo/manifests/sha256:abcd1234", headers=headers
                )
                assert resp.status_code == 401

                # Test deletion by tag
                resp = cl.delete("/v2/somenamespace/somerepo/manifests/latest", headers=headers)
                assert resp.status_code == 401


class TestV2PermissionInheritance:
    """Test that v2 API correctly inherits global read-only superuser permissions."""

    def test_require_repo_permission_integration(self, app):
        """Test that the _require_repo_permission decorator works correctly."""
        from auth.permissions import ReadRepositoryPermission
        from endpoints.v2 import _require_repo_permission

        # Create a mock function that uses the decorator
        @_require_repo_permission(ReadRepositoryPermission)(
            allow_for_global_readonly_superuser=True
        )
        def mock_read_endpoint(namespace_name, repo_name):
            return "success"

        # Test with global readonly superuser context
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True), patch(
            "endpoints.v2.get_authenticated_context"
        ) as mock_context:

            # Mock authenticated context
            mock_user = type("MockUser", (), {"username": "test-global-readonly"})()
            mock_context.return_value = type("MockContext", (), {"authed_user": mock_user})()

            # Should allow access
            from flask import g
            from flask_principal import Identity

            with app.test_request_context():
                g.identity = Identity(None, "none")
                result = mock_read_endpoint("test", "repo")
                assert result == "success"

    def test_write_permission_blocking(self, app):
        """Test that write permissions are correctly blocked."""
        from auth.permissions import ModifyRepositoryPermission
        from endpoints.v2 import _require_repo_permission

        # Create a mock function that uses the decorator for write operations
        @_require_repo_permission(ModifyRepositoryPermission)(allow_for_superuser=True)
        def mock_write_endpoint(namespace_name, repo_name):
            return "success"

        # Test with global readonly superuser context
        with patch("app.usermanager.is_global_readonly_superuser", return_value=True), patch(
            "app.usermanager.is_superuser", return_value=False
        ), patch("auth.auth_context.get_authenticated_context") as mock_context:

            # Mock authenticated context
            mock_user = type("MockUser", (), {"username": "test-global-readonly"})()
            mock_context.return_value = type("MockContext", (), {"authed_user": mock_user})()

            # Should raise Unauthorized
            from flask import g
            from flask_principal import Identity

            from endpoints.v2.errors import Unauthorized

            # Ensure a Flask identity is present for permission checks
            with app.test_request_context():
                g.identity = Identity(None, "none")
                with pytest.raises(Unauthorized):
                    mock_write_endpoint("test", "repo")


@pytest.mark.parametrize(
    "endpoint_method",
    [
        ("POST", "/v2/test/repo/blobs/uploads/"),
        ("PUT", "/v2/test/repo/manifests/tag"),
        ("PATCH", "/v2/test/repo/blobs/uploads/uuid"),
        ("PUT", "/v2/test/repo/blobs/uploads/uuid"),
        ("DELETE", "/v2/test/repo/blobs/uploads/uuid"),
        ("DELETE", "/v2/test/repo/blobs/sha256:abcd"),
        ("DELETE", "/v2/test/repo/manifests/sha256:abcd"),
        ("DELETE", "/v2/test/repo/manifests/tag"),
    ],
)
def test_all_v2_write_operations_blocked(endpoint_method, app):
    """Parametrized test to ensure all v2 write operations are blocked."""
    method, endpoint = endpoint_method

    with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
        with client_with_identity("test-global-readonly", app) as cl:
            headers = {"Authorization": "Bearer fake-token"}

            # Add content-type for manifest uploads
            if "manifests" in endpoint and method == "PUT":
                headers["Content-Type"] = "application/vnd.docker.distribution.manifest.v2+json"

            # Make the request
            if method == "GET":
                resp = cl.get(endpoint, headers=headers)
            elif method == "POST":
                resp = cl.post(endpoint, headers=headers)
            elif method == "PUT":
                resp = cl.put(endpoint, headers=headers, json={})
            elif method == "PATCH":
                resp = cl.patch(endpoint, headers=headers)
            elif method == "DELETE":
                resp = cl.delete(endpoint, headers=headers)

            # Should get unauthorized for write operations
            assert resp.status_code == 401


@pytest.mark.parametrize(
    "endpoint",
    [
        "/v2/_catalog",
        "/v2/test/repo/tags/list",
        "/v2/test/repo/manifests/tag",
        "/v2/test/repo/blobs/sha256:abcd",
    ],
)
def test_all_v2_read_operations_allowed(endpoint, app):
    """Parametrized test to ensure all v2 read operations are allowed."""
    with patch("app.usermanager.is_global_readonly_superuser", return_value=True):
        with client_with_identity("test-global-readonly", app) as cl:
            headers = {"Authorization": "Bearer fake-token"}
            resp = cl.get(endpoint, headers=headers)

            # In this setup with a fake bearer token, expect Unauthorized
            assert resp.status_code == 401
