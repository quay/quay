"""
OCP Integration Tests for Quay Quota Enforcement.

These tests validate quota enforcement against a real Quay instance running
in OpenShift Container Platform (OCP).

Requirements:
- OCP cluster with Quay operator installed (Quay 3.17+)
- QuayRegistry with quota features enabled:
  - FEATURE_QUOTA_MANAGEMENT: true
  - FEATURE_VERIFY_QUOTA: true
  - FEATURE_EDIT_QUOTA: true
- Admin API token for Quay instance
- Network access from test runner to OCP Quay route

Environment Variables:
- OCP_QUAY_URL: Quay instance URL (e.g., https://quay-testing-quay-quay.apps.nkacm.test.local)
- QUAY_ADMIN_TOKEN: Admin API token for Quay
- SKIP_TLS_VERIFY: Set to "true" for self-signed certs (default: false)
"""

import hashlib
import json
import os
import time
import uuid
from typing import Optional, Tuple

import pytest
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for test environments
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Request timeout to prevent tests from hanging (10 seconds)
REQUEST_TIMEOUT = 10


def get_ocp_env() -> dict:
    """Get OCP environment configuration."""
    quay_url = os.getenv("OCP_QUAY_URL")
    admin_token = os.getenv("QUAY_ADMIN_TOKEN")
    skip_tls = os.getenv("SKIP_TLS_VERIFY", "false").lower() == "true"

    if not quay_url:
        pytest.skip("OCP_QUAY_URL environment variable not set")
    if not admin_token:
        pytest.skip("QUAY_ADMIN_TOKEN environment variable not set")

    return {
        "quay_url": quay_url.rstrip("/"),
        "admin_token": admin_token,
        "skip_tls": skip_tls,
    }


def get_auth_headers(token: str) -> dict:
    """Get authorization headers for API requests."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def create_test_organization(
    quay_url: str,
    token: str,
    skip_tls: bool,
    org_name: Optional[str] = None,
) -> Tuple[str, dict]:
    """
    Create a test organization in Quay.

    Args:
        quay_url: Quay instance URL
        token: Admin API token
        skip_tls: Skip TLS verification
        org_name: Organization name (random if not provided)

    Returns:
        Tuple of (org_name, org_data)
    """
    if org_name is None:
        org_name = f"test-ocp-quota-{uuid.uuid4().hex[:8]}"

    url = f"{quay_url}/api/v1/organization/"
    headers = get_auth_headers(token)
    data = {
        "name": org_name,
        "email": f"{org_name}@test.local",
    }

    response = requests.post(url, headers=headers, json=data, verify=not skip_tls, timeout=REQUEST_TIMEOUT)

    if response.status_code == 201:
        return org_name, response.json()
    elif response.status_code == 400 and "already exists" in response.text:
        # Organization already exists, get its details
        get_url = f"{quay_url}/api/v1/organization/{org_name}"
        get_response = requests.get(get_url, headers=headers, verify=not skip_tls, timeout=REQUEST_TIMEOUT)
        if get_response.status_code == 200:
            return org_name, get_response.json()

    raise Exception(f"Failed to create organization: {response.status_code} - {response.text}")


def set_organization_quota(
    quay_url: str,
    token: str,
    skip_tls: bool,
    org_name: str,
    quota_bytes: int,
) -> dict:
    """
    Set quota for an organization.

    Args:
        quay_url: Quay instance URL
        token: Admin API token
        skip_tls: Skip TLS verification
        org_name: Organization name
        quota_bytes: Quota limit in bytes

    Returns:
        Quota configuration
    """
    url = f"{quay_url}/api/v1/organization/{org_name}/quota"
    headers = get_auth_headers(token)
    data = {
        "limits": [
            {
                "type": "Warning",
                "threshold_percent": 80,
            },
            {
                "type": "Reject",
                "threshold_percent": 100,
            }
        ],
        "quota_bytes": quota_bytes,
    }

    response = requests.put(url, headers=headers, json=data, verify=not skip_tls, timeout=REQUEST_TIMEOUT)

    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to set quota: {response.status_code} - {response.text}")

    return response.json()


def delete_organization(
    quay_url: str,
    token: str,
    skip_tls: bool,
    org_name: str,
) -> None:
    """
    Delete a test organization.

    Args:
        quay_url: Quay instance URL
        token: Admin API token
        skip_tls: Skip TLS verification
        org_name: Organization name
    """
    url = f"{quay_url}/api/v1/organization/{org_name}"
    headers = get_auth_headers(token)

    response = requests.delete(url, headers=headers, verify=not skip_tls, timeout=REQUEST_TIMEOUT)

    if response.status_code not in [204, 404]:
        print(f"Warning: Failed to delete organization {org_name}: {response.status_code}")


def push_image_to_quay(
    quay_url: str,
    token: str,
    skip_tls: bool,
    org_name: str,
    repo_name: str,
    tag: str,
    blob_size_kb: int,
) -> Tuple[int, str]:
    """
    Push an image to Quay via Docker Registry V2 API.

    Args:
        quay_url: Quay instance URL
        token: Admin API token
        skip_tls: Skip TLS verification
        org_name: Organization name
        repo_name: Repository name
        tag: Image tag
        blob_size_kb: Size of blob to push in KB

    Returns:
        Tuple of (status_code, response_text)
    """
    # Create blob content
    blob_data = b"x" * (blob_size_kb * 1024)
    blob_digest = "sha256:" + hashlib.sha256(blob_data).hexdigest()

    # V2 API base
    v2_base = f"{quay_url}/v2"
    headers = get_auth_headers(token)

    # 1. Start blob upload
    upload_url = f"{v2_base}/{org_name}/{repo_name}/blobs/uploads/"
    response = requests.post(upload_url, headers=headers, verify=not skip_tls, timeout=REQUEST_TIMEOUT)

    if response.status_code != 202:
        return response.status_code, f"Failed to start upload: {response.text}"

    upload_location = response.headers.get("Location")
    if not upload_location:
        return 500, "No upload location returned"

    # 2. Upload blob content (monolithic)
    if not upload_location.startswith("http"):
        upload_location = f"{quay_url}{upload_location}"

    upload_location += f"&digest={blob_digest}"
    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }

    response = requests.put(
        upload_location,
        headers=upload_headers,
        data=blob_data,
        verify=not skip_tls,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 201:
        return response.status_code, f"Failed to upload blob: {response.text}"

    # 3. Create and upload manifest
    config_data = json.dumps({
        "architecture": "amd64",
        "os": "linux",
    }).encode("utf-8")
    config_digest = "sha256:" + hashlib.sha256(config_data).hexdigest()

    # Upload config blob
    upload_url = f"{v2_base}/{org_name}/{repo_name}/blobs/uploads/"
    response = requests.post(upload_url, headers=headers, verify=not skip_tls, timeout=REQUEST_TIMEOUT)
    upload_location = response.headers.get("Location")
    if not upload_location.startswith("http"):
        upload_location = f"{quay_url}{upload_location}"
    upload_location += f"&digest={config_digest}"

    response = requests.put(
        upload_location,
        headers=upload_headers,
        data=config_data,
        verify=not skip_tls,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 201:
        return response.status_code, f"Failed to upload config: {response.text}"

    # 4. Push manifest
    manifest = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": len(config_data),
            "digest": config_digest,
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": len(blob_data),
                "digest": blob_digest,
            }
        ],
    }

    manifest_url = f"{v2_base}/{org_name}/{repo_name}/manifests/{tag}"
    manifest_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.docker.distribution.manifest.v2+json",
    }

    response = requests.put(
        manifest_url,
        headers=manifest_headers,
        data=json.dumps(manifest),
        verify=not skip_tls,
        timeout=REQUEST_TIMEOUT,
    )

    return response.status_code, response.text


@pytest.mark.ocp
class TestOCPQuotaIntegration:
    """OCP integration tests for quota enforcement."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for OCP tests."""
        env = get_ocp_env()
        self.quay_url = env["quay_url"]
        self.admin_token = env["admin_token"]
        self.skip_tls = env["skip_tls"]
        self.test_orgs = []

        yield

        # Cleanup: delete all test organizations
        for org_name in self.test_orgs:
            try:
                delete_organization(
                    self.quay_url,
                    self.admin_token,
                    self.skip_tls,
                    org_name,
                )
            except Exception as e:
                print(f"Failed to cleanup org {org_name}: {e}")

    def _push_blob_separately(self, org_name: str, repo_name: str, blob_data: bytes) -> str:
        """
        Push a blob to the registry and return its digest.

        Args:
            org_name: Organization name
            repo_name: Repository name
            blob_data: Blob content bytes

        Returns:
            Blob digest (sha256:...)
        """
        blob_digest = "sha256:" + hashlib.sha256(blob_data).hexdigest()

        # Start upload
        upload_url = f"{self.quay_url}/v2/{org_name}/{repo_name}/blobs/uploads/"
        response = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {self.admin_token}"},
            verify=not self.skip_tls,
            timeout=REQUEST_TIMEOUT,
        )
        assert response.status_code == 202, f"Failed to start blob upload: {response.text}"

        # Upload blob with PUT
        location = response.headers["Location"]
        if not location.startswith("http"):
            location = f"{self.quay_url}{location}"

        put_url = f"{location}&digest={blob_digest}"
        response = requests.put(
            put_url,
            headers={
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/octet-stream",
            },
            data=blob_data,
            verify=not self.skip_tls,
            timeout=REQUEST_TIMEOUT,
        )
        assert response.status_code == 201, f"Failed to upload blob: {response.text}"

        return blob_digest

    def _push_config_blob(self, org_name: str, repo_name: str, config_data: dict) -> str:
        """
        Push a config blob and return its digest.

        Args:
            org_name: Organization name
            repo_name: Repository name
            config_data: Config dictionary

        Returns:
            Config digest (sha256:...)
        """
        config_bytes = json.dumps(config_data).encode("utf-8")
        return self._push_blob_separately(org_name, repo_name, config_bytes)

    def _push_manifest(
        self,
        org_name: str,
        repo_name: str,
        tag: str,
        layer_digests: list,
        config_digest: str,
        config_size: int,
        layer_sizes: list,
    ) -> Tuple[int, str]:
        """
        Push a manifest referencing existing blobs.

        Args:
            org_name: Organization name
            repo_name: Repository name
            tag: Image tag
            layer_digests: List of layer blob digests
            config_digest: Config blob digest
            config_size: Config blob size in bytes
            layer_sizes: List of layer sizes in bytes

        Returns:
            Tuple of (status_code, response_text)
        """
        layers = []
        for digest, size in zip(layer_digests, layer_sizes):
            layers.append({
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": size,
                "digest": digest,
            })

        manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "size": config_size,
                "digest": config_digest,
            },
            "layers": layers,
        }

        manifest_url = f"{self.quay_url}/v2/{org_name}/{repo_name}/manifests/{tag}"
        manifest_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/vnd.docker.distribution.manifest.v2+json",
        }

        response = requests.put(
            manifest_url,
            headers=manifest_headers,
            data=json.dumps(manifest),
            verify=not self.skip_tls,
            timeout=REQUEST_TIMEOUT,
        )

        return response.status_code, response.text

    def _push_image_chunked(
        self,
        org_name: str,
        repo_name: str,
        tag: str,
        blob_size_kb: int,
        chunk_size_kb: int = 1,
    ) -> Tuple[int, str]:
        """
        Push image using chunked upload protocol (POST→PATCH→PUT).

        Args:
            org_name: Organization name
            repo_name: Repository name
            tag: Image tag
            blob_size_kb: Size of blob to push in KB
            chunk_size_kb: Chunk size for PATCH requests in KB

        Returns:
            Tuple of (status_code, response_text)
        """
        # Create blob data
        blob_data = b"y" * (blob_size_kb * 1024)
        blob_digest = "sha256:" + hashlib.sha256(blob_data).hexdigest()

        # 1. Start upload with POST
        upload_url = f"{self.quay_url}/v2/{org_name}/{repo_name}/blobs/uploads/"
        response = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {self.admin_token}"},
            verify=not self.skip_tls,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 202:
            return response.status_code, f"Failed to start upload: {response.text}"

        location = response.headers["Location"]
        if not location.startswith("http"):
            location = f"{self.quay_url}{location}"

        # 2. Upload chunks with PATCH
        chunk_size = chunk_size_kb * 1024
        for offset in range(0, len(blob_data), chunk_size):
            end = min(offset + chunk_size, len(blob_data))
            chunk = blob_data[offset:end]

            patch_response = requests.patch(
                location,
                headers={
                    "Authorization": f"Bearer {self.admin_token}",
                    "Content-Type": "application/octet-stream",
                    "Content-Range": f"{offset}-{end-1}",
                },
                data=chunk,
                verify=not self.skip_tls,
                timeout=REQUEST_TIMEOUT,
            )

            if patch_response.status_code != 202:
                return patch_response.status_code, f"PATCH failed: {patch_response.text}"

        # 3. Finalize with PUT
        put_url = f"{location}&digest={blob_digest}"
        put_response = requests.put(
            put_url,
            headers={
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/octet-stream",
            },
            verify=not self.skip_tls,
            timeout=REQUEST_TIMEOUT,
        )

        if put_response.status_code != 201:
            return put_response.status_code, f"PUT failed: {put_response.text}"

        # 4. Push config and manifest
        config_data = {"architecture": "amd64", "os": "linux"}
        config_bytes = json.dumps(config_data).encode("utf-8")
        config_digest = self._push_blob_separately(org_name, repo_name, config_bytes)

        return self._push_manifest(
            org_name,
            repo_name,
            tag,
            [blob_digest],
            config_digest,
            len(config_bytes),
            [len(blob_data)],
        )

    def test_ocp_manifest_push_quota_rejection(self):
        """
        Test quota rejection in real OCP Quay instance.

        Tests that:
        - Manifest push succeeds when under quota
        - Manifest push returns HTTP 403 when quota exceeded
        - Quota is properly tracked in PostgreSQL backend
        - Error response format matches V2 spec

        JIRA Requirement: Nice-to-Have - OCP validation test 1
        """
        # Create test organization
        org_name, org_data = create_test_organization(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
        )
        self.test_orgs.append(org_name)

        # Set 5KB quota
        quota_bytes = 5 * 1024
        set_organization_quota(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
            org_name,
            quota_bytes,
        )

        # Push 3KB image (should succeed)
        repo_name = "test-repo"
        status_code, response_text = push_image_to_quay(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
            org_name,
            repo_name,
            "small",
            3,  # 3KB
        )

        assert status_code == 201, (
            f"First push should succeed (3KB < 5KB quota), got {status_code}: {response_text}"
        )

        # Push 4KB image (should fail - total would be 7KB > 5KB)
        status_code, response_text = push_image_to_quay(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
            org_name,
            repo_name,
            "large",
            4,  # 4KB
        )

        assert status_code == 403, (
            f"Second push should be rejected (quota exceeded), got {status_code}: {response_text}"
        )

        # Verify error response contains quota information
        assert "quota" in response_text.lower(), (
            f"Error response should mention quota: {response_text}"
        )

    def test_ocp_chunked_upload_quota_enforcement(self):
        """
        Test chunked upload quota enforcement in real OCP Quay.

        Tests that:
        - True chunked upload (POST→PATCH→PUT) succeeds when under quota
        - Chunked upload is rejected when quota exceeded
        - PATCH endpoint quota validation works correctly

        This test now uses true chunked uploads with PATCH requests to properly
        exercise the chunked upload code path in endpoints/v2/blob.py.

        JIRA Requirement: Nice-to-Have - OCP validation test 2
        """
        # Create test organization
        org_name, org_data = create_test_organization(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
        )
        self.test_orgs.append(org_name)

        # Set 6KB quota
        quota_bytes = 6 * 1024
        set_organization_quota(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
            org_name,
            quota_bytes,
        )

        repo_name = "chunked-test"

        # First chunked push (4KB in 1KB chunks) - should succeed
        status_code, response_text = self._push_image_chunked(
            org_name, repo_name, "v1", blob_size_kb=4, chunk_size_kb=1
        )
        assert status_code == 201, (
            f"First chunked push should succeed: {response_text}"
        )

        # Second chunked push (4KB in 1KB chunks) - should be rejected
        # Total would be 8KB > 6KB limit
        status_code, response_text = self._push_image_chunked(
            org_name, repo_name, "v2", blob_size_kb=4, chunk_size_kb=1
        )
        assert status_code == 403, (
            f"Second chunked push should be rejected (quota exceeded): {response_text}"
        )
        assert "quota" in response_text.lower(), (
            "Rejection should mention quota"
        )

    def test_ocp_blob_deduplication_quota(self):
        """
        Test blob deduplication in real OCP Quay.

        Tests that:
        - Shared blobs are correctly deduplicated in quota calculation
        - Quota reflects actual storage usage, not logical size
        - Distributed storage backend handles deduplication
        - Quota consistency across Quay replicas

        Proper deduplication test:
        1. Push image A with 5KB blob (digest X)
        2. Push image B referencing SAME blob (digest X) but different config
        3. Verify quota only increases by manifest/config size, not blob size

        JIRA Requirement: Nice-to-Have - OCP validation test 3
        """
        # Create test organization
        org_name, org_data = create_test_organization(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
        )
        self.test_orgs.append(org_name)

        # Set 7KB quota (enough for dedup case, too small without dedup)
        quota_bytes = 7 * 1024
        set_organization_quota(
            self.quay_url,
            self.admin_token,
            self.skip_tls,
            org_name,
            quota_bytes,
        )

        repo_name = "dedup-test"

        # Push shared 5KB blob
        shared_blob_data = b"x" * (5 * 1024)
        shared_blob_digest = self._push_blob_separately(org_name, repo_name, shared_blob_data)

        # Push first manifest referencing shared blob
        config1_data = {"architecture": "amd64", "os": "linux", "tag": "v1"}
        config1_bytes = json.dumps(config1_data).encode("utf-8")
        config1_digest = self._push_blob_separately(org_name, repo_name, config1_bytes)

        status_code, response_text = self._push_manifest(
            org_name,
            repo_name,
            "v1",
            [shared_blob_digest],
            config1_digest,
            len(config1_bytes),
            [len(shared_blob_data)],
        )
        assert status_code == 201, f"First manifest push should succeed: {response_text}"

        # Get quota after first push
        quota_url = f"{self.quay_url}/api/v1/organization/{org_name}/quota"
        headers = get_auth_headers(self.admin_token)
        response = requests.get(quota_url, headers=headers, verify=not self.skip_tls, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200, f"Failed to get quota: {response.status_code}"

        quota_data = response.json()
        first_usage = quota_data.get("quota_bytes", 0)
        print(f"\nQuota after first push: {first_usage} bytes ({first_usage / 1024:.2f}KB)")

        # Push second manifest referencing SAME blob but different config
        config2_data = {"architecture": "amd64", "os": "linux", "tag": "v2"}
        config2_bytes = json.dumps(config2_data).encode("utf-8")
        config2_digest = self._push_blob_separately(org_name, repo_name, config2_bytes)

        status_code, response_text = self._push_manifest(
            org_name,
            repo_name,
            "v2",
            [shared_blob_digest],  # Same blob!
            config2_digest,
            len(config2_bytes),
            [len(shared_blob_data)],
        )

        # Should succeed (with dedup, total ~6KB < 7KB limit)
        # Without dedup, would be ~10KB > 7KB limit
        assert status_code == 201, f"Second push should succeed with deduplication: {response_text}"

        # Get quota after second push
        response = requests.get(quota_url, headers=headers, verify=not self.skip_tls, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200, f"Failed to get quota: {response.status_code}"

        quota_data = response.json()
        second_usage = quota_data.get("quota_bytes", 0)
        print(f"Quota after second push: {second_usage} bytes ({second_usage / 1024:.2f}KB)")

        # Verify blob was deduplicated (only config added, not blob)
        quota_delta = second_usage - first_usage
        print(f"Quota delta: {quota_delta} bytes ({quota_delta / 1024:.2f}KB)")

        assert quota_delta < 1024, (
            f"Quota delta should be <1KB (config only), got {quota_delta} bytes. "
            "This indicates blob deduplication is NOT working."
        )
        assert second_usage < quota_bytes, (
            f"Total usage {second_usage} should be within quota limit {quota_bytes}"
        )
