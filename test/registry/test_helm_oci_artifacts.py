# pylint: disable=W0401, W0621, W0613, W0614
"""
Registry protocol tests for Helm charts stored as OCI artifacts.

Manifests are shaped like a `helm push`: the config blob is Chart.yaml as JSON, the
first layer is the packaged chart .tgz, and a signed chart adds a provenance layer.

Run:
  TEST=true PYTHONPATH="." pytest test/registry/test_helm_oci_artifacts.py -v
"""

import gzip
import tarfile
from io import BytesIO

import pytest

from test.fixtures import *
from test.registry.cosign_test_helpers import (
    HELM_CONFIG_TYPE,
    HELM_LAYER_TYPE,
    HELM_PROVENANCE_TYPE,
    build_oci_artifact_manifest,
)
from test.registry.fixtures import *
from test.registry.liveserverfixture import *
from test.registry.protocol_fixtures import jwk
from test.registry.protocol_v2 import V2Protocol
from test.registry.protocols import Artifact, ProtocolOptions, artifact_config_bytes

NAMESPACE = "devtable"
CREDENTIALS = ("devtable", "password")

# Pushing one chart under a second tag uploads blobs the repository already has.
_PUSH_OPTIONS = ProtocolOptions()
_PUSH_OPTIONS.skip_head_checks = True


@pytest.fixture()
def protocol(data_model, jwk):
    return V2Protocol(jwk, schema="oci")


def helm_chart(name, version):
    """Return an Artifact laid out like the manifest `helm push` writes for a minimal chart."""
    chart = {
        "apiVersion": "v2",
        "name": name,
        "version": version,
        "description": "Helm OCI registry test chart",
        "type": "application",
    }
    chart_yaml = "".join("%s: %s\n" % item for item in chart.items()).encode("utf-8")

    tar_bytes = BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as tar:
        for path, contents in (
            ("Chart.yaml", chart_yaml),
            ("values.yaml", b"replicaCount: 1\n"),
        ):
            info = tarfile.TarInfo("%s/%s" % (name, path))
            info.size = len(contents)
            tar.addfile(info, BytesIO(contents))

    return Artifact(
        id=name,
        config=chart,
        config_media_type=HELM_CONFIG_TYPE,
        bytes=gzip.compress(tar_bytes.getvalue(), mtime=0),
        layer_media_type=HELM_LAYER_TYPE,
    )


def push_chart(protocol, session, repo_name, manifest, blobs, reference):
    """Push a chart manifest and its blobs under the given tag."""
    protocol.push_artifact(
        session,
        NAMESPACE,
        repo_name,
        manifest,
        blobs,
        reference=reference,
        credentials=CREDENTIALS,
        options=_PUSH_OPTIONS,
    )


def pull_chart(protocol, session, repo_name, reference):
    """Pull a chart manifest by tag or digest."""
    return protocol.pull_artifact(session, NAMESPACE, repo_name, reference, credentials=CREDENTIALS)


def fetch_blob(protocol, session, repo_name, digest, headers):
    """Return the bytes the V2 blob endpoint serves for digest."""
    return protocol.conduct(
        session,
        "GET",
        "/v2/%s/%s/blobs/%s" % (NAMESPACE, repo_name, digest),
        headers=headers,
    ).content


def test_helm_chart_pull_returns_helm_media_types_and_pushed_bytes(
    protocol, liveserver_session, app_reloader
):
    """A pushed chart pulls back with Helm media types and byte-identical config and chart."""
    repo = "helm-push-pull"
    artifact = helm_chart("pushpull", "0.1.0")
    manifest, blobs = build_oci_artifact_manifest(artifact)
    push_chart(protocol, liveserver_session, repo, manifest, blobs, "0.1.0")

    pulled = pull_chart(protocol, liveserver_session, repo, "0.1.0")
    assert pulled.manifest.digest == manifest.digest
    assert pulled.manifest.config_media_type == HELM_CONFIG_TYPE
    layers = pulled.manifest.filesystem_layers
    assert [layer.mediatype for layer in layers] == [HELM_LAYER_TYPE]

    def fetch(digest):
        return fetch_blob(protocol, liveserver_session, repo, digest, pulled.headers)

    assert fetch(pulled.manifest.config.digest) == artifact_config_bytes(artifact)
    assert fetch(layers[0].digest) == artifact.bytes


def test_signed_helm_chart_keeps_chart_then_provenance_layer(
    protocol, liveserver_session, app_reloader
):
    """A signed chart pulls back with its chart and provenance layers in order, byte-identical."""
    repo = "helm-signed"
    artifact = helm_chart("signedchart", "0.1.0")
    provenance = (
        b"-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\nname: signedchart\n"
        b"-----BEGIN PGP SIGNATURE-----\n\ntest\n-----END PGP SIGNATURE-----\n"
    )
    manifest, blobs = build_oci_artifact_manifest(
        artifact, extra_layers=[(HELM_PROVENANCE_TYPE, provenance)]
    )
    push_chart(protocol, liveserver_session, repo, manifest, blobs, "0.1.0")

    pulled = pull_chart(protocol, liveserver_session, repo, "0.1.0")
    layers = pulled.manifest.filesystem_layers
    assert [layer.mediatype for layer in layers] == [HELM_LAYER_TYPE, HELM_PROVENANCE_TYPE]
    assert [
        fetch_blob(protocol, liveserver_session, repo, layer.digest, pulled.headers)
        for layer in layers
    ] == [artifact.bytes, provenance]


def test_helm_chart_new_version_moves_latest_and_old_digest_still_pulls(
    protocol, liveserver_session, app_reloader
):
    """Pushing 0.2.0 moves latest off 0.1.0, and 0.1.0 still pulls by tag and by digest."""
    repo = "helm-versions"
    v1, v1_blobs = build_oci_artifact_manifest(helm_chart("versions", "0.1.0"))
    v2, v2_blobs = build_oci_artifact_manifest(helm_chart("versions", "0.2.0"))

    def pulled_digest(reference):
        return pull_chart(protocol, liveserver_session, repo, reference).manifest.digest

    for reference in ("0.1.0", "latest"):
        push_chart(protocol, liveserver_session, repo, v1, v1_blobs, reference)
    assert pulled_digest("latest") == v1.digest

    for reference in ("0.2.0", "latest"):
        push_chart(protocol, liveserver_session, repo, v2, v2_blobs, reference)
    assert pulled_digest("latest") == v2.digest
    assert pulled_digest("0.2.0") == v2.digest
    assert pulled_digest("0.1.0") == v1.digest
    assert pulled_digest(v1.digest) == v1.digest


def test_helm_chart_manifest_annotations_round_trip(protocol, liveserver_session, app_reloader):
    """Manifest-level org.opencontainers.image.* annotations come back unchanged on pull."""
    repo = "helm-annotated"
    annotations = {
        "org.opencontainers.image.created": "2026-10-27T09:50:30-04:00",
        "org.opencontainers.image.description": "Helm OCI registry test chart",
        "org.opencontainers.image.title": "annotated",
        "org.opencontainers.image.version": "0.1.0",
    }
    manifest, blobs = build_oci_artifact_manifest(
        helm_chart("annotated", "0.1.0"), annotations=annotations
    )
    push_chart(protocol, liveserver_session, repo, manifest, blobs, "0.1.0")

    pulled = pull_chart(protocol, liveserver_session, repo, "0.1.0")
    assert pulled.manifest.annotations == annotations
