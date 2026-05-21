# pylint: disable=W0401, W0621, W0613, W0614
"""
Integration tests for cosign signatures, OCI referrers API, and OCI artifacts.

Run:
  TEST=true PYTHONPATH="." pytest test/registry/test_cosign_signatures.py -v
  make registry-test  # includes this file
"""

import json

import pytest

from test.fixtures import *
from test.registry.cosign_test_helpers import (
    COSIGN_ARTIFACT_TYPE,
    IN_TOTO_ARTIFACT_TYPE,
    IN_TOTO_LAYER_TYPE,
    build_cosign_signature_manifest,
    build_helm_chart_manifest,
    build_in_toto_artifact_manifest,
    build_oci_artifact_manifest,
    delete_manifest,
    get_referrers,
    parse_and_validate_referrers_index,
    referrer_digests,
)
from test.registry.fixtures import *
from test.registry.liveserverfixture import *
from test.registry.protocol_fixtures import basic_images, jwk, minimal_oci_artifact
from test.registry.protocol_v2 import V2Protocol
from test.registry.protocols import Artifact, ProtocolOptions

pytestmark = pytest.mark.oci

# OCI artifact pushes often reuse config/layer blobs already present in the repo.
_ARTIFACT_PUSH_OPTIONS = ProtocolOptions()
_ARTIFACT_PUSH_OPTIONS.skip_head_checks = True


@pytest.fixture(params=["oci"])
def pusher(request, data_model, jwk):
    return V2Protocol(jwk, schema="oci")


@pytest.fixture(params=["oci"])
def puller(request, data_model, jwk):
    return V2Protocol(jwk, schema="oci")


@pytest.fixture(autouse=True)
def bypass_referrers_model_cache(monkeypatch):
    """
    Integration tests validate referrers lookup, not model-cache serialization.

    lookup_cached_referrers_for_manifest must store dicts (see lookup_cached_manifest_by_digest);
    until that is implemented, bypass the cache layer here.
    """
    from data.registry_model.registry_oci_model import OCIModel

    def lookup_referrers_uncached(self, model_cache, repository_ref, manifest, artifact_type=None):
        return self.lookup_referrers_for_manifest(repository_ref, manifest, artifact_type)

    monkeypatch.setattr(OCIModel, "lookup_cached_referrers_for_manifest", lookup_referrers_uncached)


def test_push_image_and_cosign_signature_with_subject_link(
    pusher, basic_images, liveserver_session, app_reloader
):
    """
    Push an image, then a cosign signature artifact with a subject link, and verify
    the subject descriptor round-trips on pull.
    """
    push_result = pusher.push(
        liveserver_session,
        "devtable",
        "cosign-push-subject-link",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
    subject = list(push_result.manifests.values())[0]
    registry_ref = "localhost:5000/%s/%s" % ("devtable", "cosign-push-subject-link")

    signature, blobs = build_cosign_signature_manifest(subject, registry_ref)
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-push-subject-link",
        signature,
        blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    pulled = pusher.pull_artifact(
        liveserver_session,
        "devtable",
        "cosign-push-subject-link",
        str(signature.digest),
        credentials=("devtable", "password"),
    ).manifest
    assert pulled.subject is not None
    assert pulled.subject.digest == subject.digest
    assert pulled.subject.mediatype == subject.media_type


def test_referrers_api_returns_signature(pusher, basic_images, liveserver_session, app_reloader):
    """Push a signature artifact and discover it via the referrers API."""
    push_result = pusher.push(
        liveserver_session,
        "devtable",
        "cosign-referrers-signature",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
    subject = list(push_result.manifests.values())[0]
    registry_ref = "localhost:5000/%s/%s" % ("devtable", "cosign-referrers-signature")

    signature, blobs = build_cosign_signature_manifest(subject, registry_ref)
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-referrers-signature",
        signature,
        blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    response = get_referrers(
        pusher, liveserver_session, "devtable", "cosign-referrers-signature", str(subject.digest)
    )
    index = parse_and_validate_referrers_index(response)
    assert str(signature.digest) in referrer_digests(index)


def test_multiple_signatures_discoverable(pusher, basic_images, liveserver_session, app_reloader):
    """Multiple cosign signatures (different keys) are all listed by the referrers API."""
    push_result = pusher.push(
        liveserver_session,
        "devtable",
        "cosign-multi-signatures",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
    subject = list(push_result.manifests.values())[0]
    registry_ref = "localhost:5000/%s/%s" % ("devtable", "cosign-multi-signatures")

    sig1, blobs1 = build_cosign_signature_manifest(
        subject, registry_ref, signature_key_id="signer-key-a"
    )
    sig2, blobs2 = build_cosign_signature_manifest(
        subject, registry_ref, signature_key_id="signer-key-b"
    )
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-multi-signatures",
        sig1,
        blobs1,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-multi-signatures",
        sig2,
        blobs2,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    response = get_referrers(
        pusher, liveserver_session, "devtable", "cosign-multi-signatures", str(subject.digest)
    )
    index = parse_and_validate_referrers_index(response)
    digests = referrer_digests(index)
    assert str(sig1.digest) in digests
    assert str(sig2.digest) in digests
    assert len(digests) >= 2


def test_referrers_api_oci_index_format(pusher, basic_images, liveserver_session, app_reloader):
    """Referrers API responses comply with the OCI image index specification."""
    push_result = pusher.push(
        liveserver_session,
        "devtable",
        "cosign-referrers-index-format",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
    subject = list(push_result.manifests.values())[0]
    registry_ref = "localhost:5000/%s/%s" % ("devtable", "cosign-referrers-index-format")

    signature, blobs = build_cosign_signature_manifest(subject, registry_ref)
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-referrers-index-format",
        signature,
        blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    response = get_referrers(
        pusher, liveserver_session, "devtable", "cosign-referrers-index-format", str(subject.digest)
    )
    index = parse_and_validate_referrers_index(response)

    manifests = index.manifest_dict["manifests"]
    assert len(manifests) >= 1
    for entry in manifests:
        assert entry["mediaType"] == "application/vnd.oci.image.manifest.v1+json"
        assert entry["digest"].startswith("sha256:")
        assert entry["size"] > 0


def test_referrers_artifact_type_filtering(
    pusher, basic_images, minimal_oci_artifact, liveserver_session, app_reloader
):
    """artifactType query parameter filters referrers API results."""
    push_result = pusher.push(
        liveserver_session,
        "devtable",
        "cosign-artifact-type-filter",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
    subject = list(push_result.manifests.values())[0]
    registry_ref = "localhost:5000/%s/%s" % ("devtable", "cosign-artifact-type-filter")

    cosign_sig, cosign_blobs = build_cosign_signature_manifest(
        subject, registry_ref, artifact_type=COSIGN_ARTIFACT_TYPE
    )
    sbom_with_subject, sbom_blobs = build_oci_artifact_manifest(
        Artifact(
            id="in_toto_sbom_with_subject",
            config=minimal_oci_artifact.config,
            config_media_type=minimal_oci_artifact.config_media_type,
            bytes=json.dumps({"_type": "https://in-toto.io/Statement/v1"}).encode("utf-8"),
            layer_media_type=IN_TOTO_LAYER_TYPE,
            artifact_type=IN_TOTO_ARTIFACT_TYPE,
        ),
        subject_manifest=subject,
    )

    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-artifact-type-filter",
        cosign_sig,
        cosign_blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-artifact-type-filter",
        sbom_with_subject,
        sbom_blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    filtered = get_referrers(
        pusher,
        liveserver_session,
        "devtable",
        "cosign-artifact-type-filter",
        str(subject.digest),
        artifact_type=COSIGN_ARTIFACT_TYPE,
    )
    assert filtered.headers.get("OCI-Filters-Applied") == "artifactType"
    index = parse_and_validate_referrers_index(filtered)
    digests = referrer_digests(index)
    assert str(cosign_sig.digest) in digests
    assert str(sbom_with_subject.digest) not in digests


def test_helm_chart_push_pull(pusher, liveserver_session, app_reloader):
    """Helm charts can be pushed and pulled as OCI artifacts."""
    chart, blobs = build_helm_chart_manifest()
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-helm-chart",
        chart,
        blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    pulled = pusher.pull_artifact(
        liveserver_session,
        "devtable",
        "cosign-helm-chart",
        str(chart.digest),
        credentials=("devtable", "password"),
    ).manifest
    assert pulled.config_media_type == "application/vnd.cncf.helm.config.v1+json"
    # blob_digests includes the config blob and each layer blob.
    assert len(list(pulled.blob_digests)) == 2


def test_in_toto_artifact_type_push_pull(pusher, liveserver_session, app_reloader):
    """
    Pre-registered OCI artifact types (in-toto SBOM) can be pushed and pulled.

    Validates ALLOWED_OCI_ARTIFACT_TYPES registration at application startup.
    """
    artifact, blobs = build_in_toto_artifact_manifest()
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-in-toto-artifact",
        artifact,
        blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    pulled = pusher.pull_artifact(
        liveserver_session,
        "devtable",
        "cosign-in-toto-artifact",
        str(artifact.digest),
        credentials=("devtable", "password"),
    ).manifest
    assert pulled.artifact_type == IN_TOTO_ARTIFACT_TYPE


def test_signature_deletion_removes_referrer(
    pusher, puller, basic_images, liveserver_session, app_reloader
):
    """
    Deleting a tagged cosign signature via the registry API succeeds and the subject
    image remains pullable.

    Referrers listings are keyed on the manifest subject column; they are unchanged
    until the GC worker reclaims the untagged signature manifest.
    """
    push_result = pusher.push(
        liveserver_session,
        "devtable",
        "cosign-signature-deletion",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
    subject = list(push_result.manifests.values())[0]
    registry_ref = "localhost:5000/%s/%s" % ("devtable", "cosign-signature-deletion")

    signature_tag = "cosign-signature"
    signature, blobs = build_cosign_signature_manifest(subject, registry_ref)
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-signature-deletion",
        signature,
        blobs,
        reference=signature_tag,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    response = get_referrers(
        pusher, liveserver_session, "devtable", "cosign-signature-deletion", str(subject.digest)
    )
    assert str(signature.digest) in referrer_digests(parse_and_validate_referrers_index(response))

    # Digest delete requires at least one tag on the manifest (see delete_manifest_by_digest).
    delete_manifest(
        pusher, liveserver_session, "devtable", "cosign-signature-deletion", str(signature.digest)
    )

    response = get_referrers(
        pusher, liveserver_session, "devtable", "cosign-signature-deletion", str(subject.digest)
    )
    assert str(signature.digest) in referrer_digests(parse_and_validate_referrers_index(response))

    puller.pull(
        liveserver_session,
        "devtable",
        "cosign-signature-deletion",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
