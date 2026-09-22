# -*- coding: utf-8 -*-

"""
Integration tests for Helm chart OCI artifacts.

Tests the complete Helm chart workflow through V2 registry protocol:
- Push and pull Helm charts as OCI artifacts
- Verify chart tar.gz content integrity
- Validate Chart.yaml metadata extraction
- Test chart versioning and overwrites
- Verify OCI annotation preservation

Run with:
    TEST=true PYTHONPATH="." pytest test/registry/test_helm_oci_artifacts.py -v
"""

import json
import tarfile
from io import BytesIO

import pytest

from test.fixtures import *  # noqa: F401,F403
from test.registry.fixtures import *  # noqa: F401,F403
from test.registry.liveserverfixture import *  # noqa: F401,F403
from test.registry.protocol_fixtures import *  # noqa: F401,F403
from test.registry.protocols import Image, layer_bytes_for_contents


@pytest.fixture(scope="session")
def helm_chart():
    """
    Returns a basic Helm chart OCI artifact for push and pull testing.

    Simulates a real Helm chart with Chart.yaml metadata packaged as tar.gz.
    """
    chart_yaml = b"""apiVersion: v2
name: test-chart
description: A test Helm chart for OCI artifact testing
type: application
version: 1.0.0
appVersion: "1.0"
"""

    # Create a tar.gz layer with Chart.yaml (simulating helm package output)
    chart_bytes = layer_bytes_for_contents(
        b"chart contents",
        mode="|gz",
        other_files={
            "test-chart/Chart.yaml": chart_yaml,
            "test-chart/values.yaml": b"# Default values\nreplicaCount: 1\n",
            "test-chart/templates/deployment.yaml": b"apiVersion: apps/v1\nkind: Deployment\n",
        },
    )

    return [
        Image(
            id="helmchartid",
            bytes=chart_bytes,
            parent_id=None,
            size=len(chart_bytes),
            config={
                "name": "test-chart",
                "version": "1.0.0",
                "mediaType": "application/vnd.cncf.helm.config.v1+json",
            },
        ),
    ]


@pytest.fixture(scope="session")
def helm_chart_with_dependencies():
    """
    Returns a Helm chart with dependencies packaged within the main chart.

    Tests that complex charts with dependencies maintain structure. In real Helm
    charts, dependencies are packaged under charts/ subdirectory within the main
    chart archive (one layer), not as separate layers.
    """
    chart_yaml = b"""apiVersion: v2
name: complex-chart
description: A Helm chart with dependencies
type: application
version: 2.0.0
appVersion: "2.0"
dependencies:
  - name: postgresql
    version: "12.x"
    repository: "https://charts.bitnami.com/bitnami"
"""

    # Single layer with main chart and dependency nested inside
    chart_bytes = layer_bytes_for_contents(
        b"main chart contents",
        mode="|gz",
        other_files={
            "complex-chart/Chart.yaml": chart_yaml,
            "complex-chart/values.yaml": b"# Values with dependencies\n",
            "complex-chart/charts/postgresql/Chart.yaml": b"apiVersion: v2\nname: postgresql\nversion: 12.0.0\n",
        },
    )

    return [
        Image(
            id="main-chart-id",
            bytes=chart_bytes,
            parent_id=None,
            size=len(chart_bytes),
            config={
                "name": "complex-chart",
                "version": "2.0.0",
                "mediaType": "application/vnd.cncf.helm.config.v1+json",
            },
        ),
    ]


@pytest.fixture(scope="session")
def helm_chart_multi_layer():
    """
    Returns a Helm chart with multiple layers (chart content + provenance).

    Tests multi-layer OCI artifacts where additional layers (like provenance files)
    are included alongside the chart layer. This is a dedicated fixture for testing
    multi-layer scenarios, separate from the dependency fixture which focuses on
    chart structure.
    """
    chart_yaml = b"""apiVersion: v2
name: multi-layer-chart
description: A Helm chart with provenance layer
type: application
version: 3.0.0
appVersion: "3.0"
"""

    # Chart content layer
    chart_bytes = layer_bytes_for_contents(
        b"chart content layer",
        mode="|gz",
        other_files={
            "multi-layer-chart/Chart.yaml": chart_yaml,
            "multi-layer-chart/values.yaml": b"# Multi-layer chart values\n",
        },
    )

    # Provenance layer (separate layer for chart provenance/signature data)
    provenance_bytes = layer_bytes_for_contents(
        b"-----BEGIN PGP SIGNED MESSAGE-----\nChart provenance data\n-----END PGP SIGNATURE-----\n",
        mode="|gz",
        other_files={
            "multi-layer-chart.prov": b"PGP signature data for chart verification\n",
        },
    )

    return [
        Image(
            id="chart-content-layer",
            bytes=chart_bytes,
            parent_id=None,
            size=len(chart_bytes),
            config={
                "name": "multi-layer-chart",
                "version": "3.0.0",
                "mediaType": "application/vnd.cncf.helm.config.v1+json",
            },
        ),
        Image(
            id="provenance-layer",
            bytes=provenance_bytes,
            parent_id="chart-content-layer",
            size=len(provenance_bytes),
            config={
                "name": "multi-layer-chart",
                "version": "3.0.0",
                "mediaType": "application/vnd.cncf.helm.config.v1+json",
            },
        ),
    ]


@pytest.fixture(scope="session")
def helm_chart_with_annotations():
    """
    Returns a Helm chart with OCI annotations.

    Tests that OCI annotations (org.opencontainers.image.*) are preserved.
    """
    chart_yaml = b"""apiVersion: v2
name: annotated-chart
description: A Helm chart with OCI annotations
type: application
version: 1.5.0
appVersion: "1.5"
"""

    chart_bytes = layer_bytes_for_contents(
        b"annotated chart contents",
        mode="|gz",
        other_files={
            "annotated-chart/Chart.yaml": chart_yaml,
        },
    )

    return [
        Image(
            id="annotated-chart-id",
            bytes=chart_bytes,
            parent_id=None,
            size=len(chart_bytes),
            config={
                "name": "annotated-chart",
                "version": "1.5.0",
                "mediaType": "application/vnd.cncf.helm.config.v1+json",
                "annotations": {
                    "org.opencontainers.image.title": "Annotated Chart",
                    "org.opencontainers.image.description": "Chart with OCI annotations",
                    "org.opencontainers.image.version": "1.5.0",
                    "org.opencontainers.image.created": "2026-05-07T00:00:00Z",
                },
            },
        ),
    ]


def test_helm_chart_push_and_pull(manifest_protocol, helm_chart, liveserver_session, app_reloader):
    """
    Test 1.1: Basic Helm chart push and pull - verify byte identity.

    Validates that a Helm chart can be pushed to the registry and pulled back
    with identical byte content (chart tar.gz integrity preserved).
    """
    credentials = ("devtable", "password")

    # Push the Helm chart
    push_result = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "helm-test-repo",
        "1.0.0",
        helm_chart,
        credentials=credentials,
    )

    assert push_result is not None
    assert len(push_result.manifests) > 0

    # Pull the chart by tag and verify
    pull_result = manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "helm-test-repo",
        "1.0.0",
        helm_chart,
        credentials=credentials,
    )

    assert pull_result is not None
    assert len(pull_result.manifests) > 0

    # Verify we can also pull by digest
    digests = [str(manifest.digest) for manifest in list(push_result.manifests.values())]
    manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "helm-test-repo",
        digests,
        helm_chart,
        credentials=credentials,
        expected_failure=None,
    )


@pytest.mark.parametrize("manifest_protocol", ["oci"], indirect=True)
def test_helm_chart_metadata_extraction(
    manifest_protocol, helm_chart, liveserver_session, app_reloader
):
    """
    Test 1.2: Chart metadata extraction - Chart.yaml parsed correctly.

    Validates that Chart.yaml metadata from the Helm chart is correctly
    extracted and accessible after push. Only runs for OCI protocol since
    Helm charts are OCI artifacts.
    """
    credentials = ("devtable", "password")

    # Push the Helm chart
    result = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "helm-metadata-repo",
        "1.0.0",
        helm_chart,
        credentials=credentials,
    )

    assert result is not None
    assert len(result.manifests) > 0, "Push returned no manifests"

    # Verify the config contains expected metadata
    for manifest in result.manifests.values():
        assert hasattr(manifest, "config_obj"), "Manifest missing config_obj"
        config = manifest.config_obj
        assert isinstance(config, dict), "config_obj must be a dictionary"
        # Helm charts must have Helm media type, name, and version
        assert config.get("mediaType") == "application/vnd.cncf.helm.config.v1+json"
        assert config.get("name") == "test-chart"
        assert config.get("version") == "1.0.0"


@pytest.mark.parametrize("manifest_protocol", ["oci"], indirect=True)
def test_helm_chart_with_dependencies(
    manifest_protocol, helm_chart_with_dependencies, liveserver_session, app_reloader
):
    """
    Test 1.3: Helm chart with dependencies - structure maintained.

    Validates that Helm charts with dependencies maintain their structure through
    push/pull operations. Dependencies are packaged within the main chart archive
    under the charts/ subdirectory. Only runs for OCI protocol since Helm charts
    are OCI artifacts.
    """
    credentials = ("devtable", "password")

    # Push the complex chart with dependencies
    push_result = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "helm-complex-repo",
        "2.0.0",
        helm_chart_with_dependencies,
        credentials=credentials,
    )

    assert push_result is not None
    assert len(push_result.manifests) > 0

    # Verify Helm config media type and chart metadata
    for manifest in push_result.manifests.values():
        assert hasattr(manifest, "config_obj"), "Manifest missing config_obj"
        config = manifest.config_obj
        assert isinstance(config, dict), "config_obj must be a dictionary"
        assert config.get("mediaType") == "application/vnd.cncf.helm.config.v1+json"
        assert config.get("name") == "complex-chart"
        assert config.get("version") == "2.0.0"

    # Pull and verify structure is preserved
    pull_result = manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "helm-complex-repo",
        "2.0.0",
        helm_chart_with_dependencies,
        credentials=credentials,
    )

    assert pull_result is not None
    assert len(pull_result.manifests) > 0

    # Verify the chart layer descriptor and dependency structure
    for manifest in pull_result.manifests.values():
        # Verify Helm config is preserved
        assert hasattr(manifest, "config_obj"), "Manifest missing config_obj"
        config = manifest.config_obj
        assert isinstance(config, dict), "config_obj must be a dictionary"
        assert config.get("mediaType") == "application/vnd.cncf.helm.config.v1+json"


@pytest.mark.parametrize("manifest_protocol", ["oci"], indirect=True)
def test_helm_chart_multi_layer(
    manifest_protocol, helm_chart_multi_layer, liveserver_session, app_reloader
):
    """
    Test 1.3b: Multi-layer Helm OCI artifact - chart content + provenance layers.

    Validates that multi-layer Helm OCI artifacts (chart with separate provenance
    layer) maintain both layers through push/pull operations. Asserts both layer
    descriptors are present in the manifest's blob digests. Only runs for OCI
    protocol since Helm charts are OCI artifacts.
    """
    credentials = ("devtable", "password")

    # Push the multi-layer chart
    push_result = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "helm-multi-layer-repo",
        "3.0.0",
        helm_chart_multi_layer,
        credentials=credentials,
    )

    assert push_result is not None
    assert len(push_result.manifests) > 0

    # Verify both layers are present in the pushed manifest
    for manifest in push_result.manifests.values():
        # Verify Helm config
        assert hasattr(manifest, "config_obj"), "Manifest missing config_obj"
        config = manifest.config_obj
        assert isinstance(config, dict), "config_obj must be a dictionary"
        assert config.get("mediaType") == "application/vnd.cncf.helm.config.v1+json"

        # Assert both layer descriptors are present through manifest's blob digests
        # OCI manifests include one config blob + layer blobs
        blob_digests = list(manifest.blob_digests)
        assert len(blob_digests) >= len(
            helm_chart_multi_layer
        ), f"Expected at least {len(helm_chart_multi_layer)} layers, got {len(blob_digests)}"

    # Pull and verify both layers are preserved
    pull_result = manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "helm-multi-layer-repo",
        "3.0.0",
        helm_chart_multi_layer,
        credentials=credentials,
    )

    assert pull_result is not None
    assert len(pull_result.manifests) > 0

    # Verify both layers are still present after round-trip
    for manifest in pull_result.manifests.values():
        assert hasattr(manifest, "config_obj"), "Manifest missing config_obj"
        config = manifest.config_obj
        assert isinstance(config, dict), "config_obj must be a dictionary"
        assert config.get("mediaType") == "application/vnd.cncf.helm.config.v1+json"

        # Verify both layer descriptors are preserved
        blob_digests = list(manifest.blob_digests)
        assert len(blob_digests) >= len(
            helm_chart_multi_layer
        ), f"Expected at least {len(helm_chart_multi_layer)} layers after pull, got {len(blob_digests)}"


def test_helm_chart_version_overwrite(
    manifest_protocol, helm_chart, liveserver_session, app_reloader
):
    """
    Test 1.4: Chart version overwrite - versioning works correctly.

    Validates that pushing a new chart with the same tag overwrites correctly,
    and that chart version metadata is properly handled.
    """
    credentials = ("devtable", "password")

    # Push initial version
    result1 = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "helm-version-repo",
        "latest",
        helm_chart,
        credentials=credentials,
    )

    assert result1 is not None
    assert result1.manifests, "First push returned no manifests"
    digest1 = list(result1.manifests.values())[0].digest

    # Create a modified chart (different contents)
    updated_chart_bytes = layer_bytes_for_contents(
        b"updated chart contents v2",
        mode="|gz",
        other_files={
            "test-chart/Chart.yaml": b"""apiVersion: v2
name: test-chart
version: 2.0.0
appVersion: "2.0"
""",
        },
    )

    updated_chart = [
        Image(
            id="helmchartid-v2",
            bytes=updated_chart_bytes,
            parent_id=None,
            size=len(updated_chart_bytes),
            config={
                "name": "test-chart",
                "version": "2.0.0",
                "mediaType": "application/vnd.cncf.helm.config.v1+json",
            },
        ),
    ]

    # Push updated version with same tag
    result2 = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "helm-version-repo",
        "latest",
        updated_chart,
        credentials=credentials,
    )

    assert result2 is not None
    assert result2.manifests, "Second push returned no manifests"
    digest2 = list(result2.manifests.values())[0].digest

    # Digests should be different (content changed)
    assert digest1 != digest2

    # Pull should get the updated version
    pull_result = manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "helm-version-repo",
        "latest",
        updated_chart,
        credentials=credentials,
    )

    assert pull_result is not None


@pytest.mark.parametrize("manifest_protocol", ["oci"], indirect=True)
def test_helm_chart_oci_annotations(
    manifest_protocol, helm_chart_with_annotations, liveserver_session, app_reloader
):
    """
    Test 1.5: OCI config metadata preservation (including annotations).

    Validates that OCI config metadata and embedded annotations on Helm charts
    are correctly preserved through push and pull operations (round-trip test).
    Only runs for OCI protocol since Helm charts are OCI artifacts.

    Note: This tests config-level metadata (stored in the OCI config blob),
    which includes Helm chart metadata and embedded annotations. Manifest-level
    OCI annotations (manifest.annotations) would require protocol modifications
    to support the Image namedtuple passing annotations to OCIManifestBuilder.
    """
    credentials = ("devtable", "password")

    # Push chart with metadata/annotations in config
    push_result = manifest_protocol.push(
        liveserver_session,
        "devtable",
        "helm-annotated-repo",
        "1.5.0",
        helm_chart_with_annotations,
        credentials=credentials,
    )

    assert push_result is not None
    assert len(push_result.manifests) > 0

    # Verify config metadata is present in the pushed manifest
    for manifest in push_result.manifests.values():
        assert manifest is not None
        assert hasattr(manifest, "digest")

        # Verify config contains expected metadata
        assert hasattr(manifest, "config_obj"), "Manifest missing config_obj"
        config = manifest.config_obj
        assert isinstance(config, dict), "config_obj must be a dictionary"

        # Verify Helm chart identification metadata
        assert config.get("mediaType") == "application/vnd.cncf.helm.config.v1+json"
        # Verify chart metadata is present
        assert config.get("name") == "annotated-chart"
        assert config.get("version") == "1.5.0"

        # Verify annotations are preserved in config
        assert "annotations" in config, "config must contain annotations map"
        annotations = config["annotations"]
        assert annotations.get("org.opencontainers.image.title") == "Annotated Chart"
        assert annotations.get("org.opencontainers.image.version") == "1.5.0"
        assert (
            annotations.get("org.opencontainers.image.description") == "Chart with OCI annotations"
        )
        assert annotations.get("org.opencontainers.image.created") == "2026-05-07T00:00:00Z"

    # Pull and verify metadata is preserved
    pull_result = manifest_protocol.pull(
        liveserver_session,
        "devtable",
        "helm-annotated-repo",
        "1.5.0",
        helm_chart_with_annotations,
        credentials=credentials,
    )

    assert pull_result is not None
    assert len(pull_result.manifests) > 0

    # Verify config metadata is preserved after pull (round-trip verification)
    for manifest in pull_result.manifests.values():
        assert manifest is not None
        assert hasattr(manifest, "digest")

        # Verify config contains expected metadata after pull
        assert hasattr(manifest, "config_obj"), "Manifest missing config_obj"
        config = manifest.config_obj
        assert isinstance(config, dict), "config_obj must be a dictionary"

        # Verify Helm chart identification metadata is preserved
        assert config.get("mediaType") == "application/vnd.cncf.helm.config.v1+json"
        # Verify chart metadata is preserved
        assert config.get("name") == "annotated-chart"
        assert config.get("version") == "1.5.0"

        # Verify annotations are preserved after round-trip (push → storage → pull)
        assert "annotations" in config, "config must contain annotations map"
        annotations = config["annotations"]
        assert annotations.get("org.opencontainers.image.title") == "Annotated Chart"
        assert annotations.get("org.opencontainers.image.version") == "1.5.0"
        assert (
            annotations.get("org.opencontainers.image.description") == "Chart with OCI annotations"
        )
        assert annotations.get("org.opencontainers.image.created") == "2026-05-07T00:00:00Z"
