"""
E2E tests for security scanning lifecycle.

Tests the complete scan-on-push workflow from image push to vulnerability results,
scanner unavailability handling, and re-scan on CVE database updates.
"""

import base64
from unittest.mock import Mock, create_autospec
from urllib.parse import urlparse

import pytest

from app import app as application
from app import instance_keys, storage
from data import model
from data.database import IndexerVersion, IndexStatus, Manifest, ManifestSecurityStatus
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from data.secscan_model.datatypes import ScanLookupStatus
from data.secscan_model.secscan_v4_model import V4SecurityScanner
from initdb import create_schema2_or_oci_manifest_for_testing
from test.fixtures import *
from util.secscan.v4.api import APIRequestFailure, ClairSecurityScannerAPI
from util.secscan.v4.fake import fake_security_scanner


@pytest.fixture()
def set_secscan_config():
    """Configure Clair V4 endpoint for tests."""
    # Save original config values
    original_endpoint = application.config.get("SECURITY_SCANNER_V4_ENDPOINT")
    original_feature = application.config.get("FEATURE_SECURITY_SCANNER")
    original_psk = application.config.get("SECURITY_SCANNER_V4_PSK")

    # Set test config
    application.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://fakesecurityscanner:6060"
    application.config["FEATURE_SECURITY_SCANNER"] = True
    application.config["SECURITY_SCANNER_V4_PSK"] = base64.b64encode(b"test-psk").decode()
    yield

    # Restore original config values
    if original_endpoint is None:
        application.config.pop("SECURITY_SCANNER_V4_ENDPOINT", None)
    else:
        application.config["SECURITY_SCANNER_V4_ENDPOINT"] = original_endpoint

    if original_feature is None:
        application.config.pop("FEATURE_SECURITY_SCANNER", None)
    else:
        application.config["FEATURE_SECURITY_SCANNER"] = original_feature

    if original_psk is None:
        application.config.pop("SECURITY_SCANNER_V4_PSK", None)
    else:
        application.config["SECURITY_SCANNER_V4_PSK"] = original_psk


def create_test_repository(namespace="devtable", repo_name="secscan-test"):
    """
    Create test repository for security scanning.

    Args:
        namespace: Repository namespace (default: devtable)
        repo_name: Repository name (default: secscan-test)

    Returns:
        RepositoryReference object
    """
    user = model.user.get_user(namespace)
    repo = model.repository.create_repository(namespace, repo_name, user)
    return RepositoryReference.for_repo_obj(repo)


def create_test_manifest(repo, num_layers=3, tag="latest"):
    """
    Create Docker v2 manifest for testing.

    Args:
        repo: RepositoryReference object
        num_layers: Number of layers in manifest (default: 3)
        tag: Tag name (default: latest)

    Returns:
        Manifest object
    """
    tag_map = {}
    structure = (num_layers, [], [tag])
    create_schema2_or_oci_manifest_for_testing(repo._db_obj, structure, tag_map)
    tag_ref = registry_model.get_repo_tag(repo, tag)
    return registry_model.get_manifest_for_tag(tag_ref)


def test_scan_on_push_lifecycle(initialized_db, set_secscan_config):
    """
    Test complete scan-on-push lifecycle: push → worker indexes → CVEs queryable.

    This test verifies:
    1. Security worker successfully indexes a manifest with Clair
    2. Manifest status transitions from NOT_INDEXED to COMPLETED
    3. Vulnerability data is queryable via the security API
    4. CVE details (name, severity, fixed version) are correctly returned

    Run with:
        TEST=true PYTHONPATH="." pytest test/test_secscan_e2e.py::test_scan_on_push_lifecycle -v
    """
    # Setup: Create repository and manifest
    repo = create_test_repository()
    manifest = create_test_manifest(repo, num_layers=3, tag="latest")

    # Configure fake Clair with test vulnerabilities
    hostname = urlparse(application.config["SECURITY_SCANNER_V4_ENDPOINT"]).netloc
    with fake_security_scanner(hostname=hostname) as fake:
        # Simulate Clair returning a vulnerability in the scan
        fake.vulnerability_reports[manifest.digest] = {
            "manifest_hash": manifest.digest,
            "packages": {
                "1": {
                    "id": "1",
                    "name": "openssl",
                    "version": "1.0.1",
                    "kind": "",
                    "normalized_version": "",
                    "arch": "",
                    "module": "",
                    "cpe": "",
                    "source": {},
                },
            },
            "distributions": {
                "1": {
                    "id": "1",
                    "did": "ubuntu",
                    "name": "Ubuntu",
                    "version": "20.04",
                    "version_code_name": "focal",
                    "version_id": "20.04",
                    "arch": "amd64",
                    "cpe": "",
                    "pretty_name": "Ubuntu 20.04 LTS",
                },
            },
            "environments": {
                "1": {
                    "package_db": "1",
                    "introduced_in": "sha256:abc123",
                    "distribution_id": "1",
                },
            },
            "vulnerabilities": {
                "CVE-2024-1234": {
                    "id": "CVE-2024-1234",
                    "updater": "ubuntu",
                    "name": "CVE-2024-1234",
                    "description": "Test critical vulnerability",
                    "issued": "2024-01-01T00:00:00Z",
                    "links": "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-1234",
                    "severity": "Critical",
                    "normalized_severity": "Critical",
                    "fixed_in_version": "1.2.3",
                    "package_name": "",
                    "package_kind": "",
                    "dist_id": "",
                    "dist_name": "",
                    "dist_version": "",
                    "dist_version_code_name": "",
                    "dist_version_id": "",
                    "dist_arch": "",
                    "dist_cpe": "",
                    "dist_pretty_name": "",
                    "arch": "",
                    "repository_name": "",
                    "repository_uri": "",
                    "repository_cpe": "",
                },
            },
            "package_vulnerabilities": {
                "1": ["CVE-2024-1234"],
            },
        }

        # Trigger security worker indexing
        secscan = V4SecurityScanner(application, instance_keys, storage)
        secscan.perform_indexing_recent_manifests()
        next_token = secscan.perform_indexing()

        # Verify status updated to COMPLETED
        mss = ManifestSecurityStatus.get(manifest=manifest._db_id)
        assert mss.index_status == IndexStatus.COMPLETED
        assert mss.indexer_hash == fake.indexer_state
        assert mss.indexer_version == IndexerVersion.V4

        # Verify CVE data queryable via API
        security_info = secscan.load_security_information(manifest, include_vulnerabilities=True)
        assert security_info.status == ScanLookupStatus.SUCCESS

        # Verify vulnerability data structure
        assert security_info.security_information is not None
        assert security_info.security_information.Layer is not None

        # Verify we have features (packages) with vulnerabilities
        features = security_info.security_information.Layer.Features
        assert len(features) > 0

        # Find the feature with our test CVE
        vuln_feature = None
        for feature in features:
            if feature.Vulnerabilities and len(feature.Vulnerabilities) > 0:
                vuln_feature = feature
                break

        assert vuln_feature is not None, "Expected to find feature with vulnerabilities"

        # Verify CVE details
        vulnerabilities = vuln_feature.Vulnerabilities
        cve_names = [v.Name for v in vulnerabilities]
        assert "CVE-2024-1234" in cve_names

        # Find our specific CVE and verify details
        test_cve = next(v for v in vulnerabilities if v.Name == "CVE-2024-1234")
        assert test_cve.Severity == "Critical"
        assert test_cve.FixedBy == "1.2.3"
        assert "Test critical vulnerability" in test_cve.Description


def test_scanner_unavailability(initialized_db, set_secscan_config):
    """
    Test graceful degradation when Clair is unreachable.

    This test verifies:
    1. Manifest can be created even when Clair is unavailable
    2. Security worker handles connection errors gracefully
    3. Scan status is marked as FAILED (not stuck in IN_PROGRESS)
    4. Error details are recorded in error_json field

    Run with:
        TEST=true PYTHONPATH="." pytest test/test_secscan_e2e.py::test_scanner_unavailability -v
    """
    # Setup: Create repository and manifest
    repo = create_test_repository(repo_name="secscan-unavailable")
    manifest = create_test_manifest(repo, num_layers=3, tag="latest")

    # Make Clair unavailable (mock returns connection errors)
    # state() returns successfully so perform_indexing() proceeds
    # index() fails to trigger the error handling path that sets FAILED status
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = create_autospec(ClairSecurityScannerAPI, spec_set=True)
    secscan._secscan_api.state.return_value = "test-indexer-state"
    secscan._secscan_api.index.side_effect = APIRequestFailure()

    # Trigger worker - should handle error gracefully
    # The error will be caught internally and status set to FAILED
    secscan.perform_indexing()

    # Verify manifest still exists (push not blocked)
    assert Manifest.get(id=manifest._db_id) is not None

    # Verify that ManifestSecurityStatus was created and shows FAILED
    # Connection errors should result in FAILED status, not MANIFEST_UNSUPPORTED
    mss = ManifestSecurityStatus.get(manifest=manifest._db_id)
    assert (
        mss.index_status == IndexStatus.FAILED
    ), f"Expected IndexStatus.FAILED for scanner unavailability, got {mss.index_status}"

    # Verify error_json contains error information
    assert mss.error_json is not None, "Expected error_json to be populated for failed scan"
    error_str = str(mss.error_json).lower()
    assert (
        "error" in error_str
        or "failed" in error_str
        or "exception" in error_str
        or "request" in error_str
    ), f"Expected error information in error_json, got: {mss.error_json}"


def test_rescan_on_cve_update(initialized_db, set_secscan_config):
    """
    Test re-scan when CVE database updates.

    This test verifies:
    1. Initial scan returns no vulnerabilities
    2. Simulated CVE database update adds new vulnerabilities to Clair
    3. Indexer state change triggers re-indexing
    4. Re-scan detects newly added vulnerabilities
    5. New CVE data is correctly queryable

    Run with:
        TEST=true PYTHONPATH="." pytest test/test_secscan_e2e.py::test_rescan_on_cve_update -v
    """
    # Setup: Create repository and manifest
    repo = create_test_repository(repo_name="secscan-rescan")
    manifest = create_test_manifest(repo, num_layers=3, tag="v1.0.0")

    hostname = urlparse(application.config["SECURITY_SCANNER_V4_ENDPOINT"]).netloc
    with fake_security_scanner(hostname=hostname) as fake:
        # Initial scan: no vulnerabilities
        fake.vulnerability_reports[manifest.digest] = {
            "manifest_hash": manifest.digest,
            "packages": {},
            "distributions": {},
            "environments": {},
            "vulnerabilities": {},
            "package_vulnerabilities": {},
        }

        secscan = V4SecurityScanner(application, instance_keys, storage)
        secscan.perform_indexing()

        # Verify manifest was indexed
        mss = ManifestSecurityStatus.get(manifest=manifest._db_id)
        assert mss.index_status == IndexStatus.COMPLETED
        initial_indexer_hash = mss.indexer_hash

        # Verify no CVEs initially
        security_info = secscan.load_security_information(manifest, include_vulnerabilities=True)
        assert security_info.status == ScanLookupStatus.SUCCESS
        # No packages means no vulnerabilities
        assert len(security_info.security_information.Layer.Features) == 0

        # Simulate CVE database update with new vulnerability
        fake.vulnerability_reports[manifest.digest] = {
            "manifest_hash": manifest.digest,
            "packages": {
                "1": {
                    "id": "1",
                    "name": "curl",
                    "version": "7.68.0",
                    "kind": "",
                    "normalized_version": "",
                    "arch": "",
                    "module": "",
                    "cpe": "",
                    "source": {},
                },
            },
            "distributions": {
                "1": {
                    "id": "1",
                    "did": "debian",
                    "name": "Debian",
                    "version": "10",
                    "version_code_name": "buster",
                    "version_id": "10",
                    "arch": "amd64",
                    "cpe": "",
                    "pretty_name": "Debian GNU/Linux 10 (buster)",
                },
            },
            "environments": {
                "1": {
                    "package_db": "1",
                    "introduced_in": "sha256:def456",
                    "distribution_id": "1",
                },
            },
            "vulnerabilities": {
                "CVE-2024-9999": {
                    "id": "CVE-2024-9999",
                    "updater": "debian",
                    "name": "CVE-2024-9999",
                    "description": "Newly discovered high severity vulnerability in curl",
                    "issued": "2024-02-01T00:00:00Z",
                    "links": "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-9999",
                    "severity": "High",
                    "normalized_severity": "High",
                    "fixed_in_version": "7.70.0",
                    "package_name": "",
                    "package_kind": "",
                    "dist_id": "",
                    "dist_name": "",
                    "dist_version": "",
                    "dist_version_code_name": "",
                    "dist_version_id": "",
                    "dist_arch": "",
                    "dist_cpe": "",
                    "dist_pretty_name": "",
                    "arch": "",
                    "repository_name": "",
                    "repository_uri": "",
                    "repository_cpe": "",
                },
            },
            "package_vulnerabilities": {
                "1": ["CVE-2024-9999"],
            },
        }

        # Change indexer state to trigger re-index
        new_state = "new_indexer_state_v2"
        fake.indexer_state = new_state

        # Trigger re-indexing by running perform_indexing again
        # The worker will detect the indexer state change and re-index
        secscan.perform_indexing_recent_manifests()
        secscan.perform_indexing()

        # Verify indexer hash was updated
        mss = ManifestSecurityStatus.get(manifest=manifest._db_id)
        assert mss.index_status == IndexStatus.COMPLETED
        assert mss.indexer_hash == new_state
        assert mss.indexer_hash != initial_indexer_hash

        # Verify new CVE detected
        security_info = secscan.load_security_information(manifest, include_vulnerabilities=True)
        assert security_info.status == ScanLookupStatus.SUCCESS

        # Verify we now have features with vulnerabilities
        features = security_info.security_information.Layer.Features
        assert len(features) > 0

        # Find feature with the new CVE
        vuln_feature = None
        for feature in features:
            if feature.Vulnerabilities and len(feature.Vulnerabilities) > 0:
                vuln_feature = feature
                break

        assert vuln_feature is not None, "Expected to find feature with new vulnerability"

        # Verify new CVE details
        vulnerabilities = vuln_feature.Vulnerabilities
        cve_names = [v.Name for v in vulnerabilities]
        assert "CVE-2024-9999" in cve_names

        # Find our specific CVE and verify details
        new_cve = next(v for v in vulnerabilities if v.Name == "CVE-2024-9999")
        assert new_cve.Severity == "High"
        assert new_cve.FixedBy == "7.70.0"
        assert "Newly discovered" in new_cve.Description
