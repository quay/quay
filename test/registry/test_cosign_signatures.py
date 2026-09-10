# pylint: disable=W0401, W0621, W0613, W0614
"""
Integration tests for cosign signatures, OCI referrers API, and OCI artifacts.

Run:
  TEST=true PYTHONPATH="." pytest test/registry/test_cosign_signatures.py -v
  make registry-test  # includes this file
"""

import copy
import json

import pytest

from image.oci import register_artifact_type
from test.fixtures import *
from test.registry.cosign_test_helpers import (
    COSIGN_ARTIFACT_TYPE,
    IN_TOTO_ARTIFACT_TYPE,
    IN_TOTO_LAYER_TYPE,
    build_cosign_signature_manifest,
    build_helm_chart_manifest,
    build_oci_artifact_manifest,
    get_referrers,
    parse_and_validate_referrers_index,
    referrer_digests,
)
from test.registry.fixtures import *
from test.registry.liveserverfixture import *
from test.registry.protocol_fixtures import (
    MINIMAL_OCI_ARTIFACT_CONFIG,
    basic_images,
    jwk,
    minimal_oci_artifact,
)
from test.registry.protocol_v2 import V2Protocol
from test.registry.protocols import Artifact, Failures, ProtocolOptions

pytestmark = pytest.mark.oci

# OCI artifact pushes often reuse config/layer blobs already present in the repo.
_ARTIFACT_PUSH_OPTIONS = ProtocolOptions()
_ARTIFACT_PUSH_OPTIONS.skip_head_checks = True

# Custom artifact media types that are NOT in the default ALLOWED_OCI_ARTIFACT_TYPES.
# Used to verify that runtime registration of new types actually works.
CUSTOM_TEST_CONFIG_TYPE = "application/vnd.test.custom.config.v1+json"
CUSTOM_TEST_LAYER_TYPE = "application/vnd.test.custom.layer.v1+json"
CUSTOM_TEST_ARTIFACT_TYPE = "application/vnd.test.custom.artifact.v1+json"


@pytest.fixture(params=["oci"])
def pusher(request, data_model, jwk):
    return V2Protocol(jwk, schema="oci")


@pytest.fixture(params=["oci"])
def puller(request, data_model, jwk):
    return V2Protocol(jwk, schema="oci")


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


def test_custom_artifact_type_push_pull(pusher, liveserver_session, app_reloader):
    """
    A dynamically registered custom artifact type can be pushed and pulled.

    Registers a unique config/layer media-type pair that is NOT in the default
    ALLOWED_OCI_ARTIFACT_TYPES, then pushes and pulls an artifact using those
    types to prove the registration mechanism works end-to-end.
    """
    register_artifact_type(CUSTOM_TEST_CONFIG_TYPE, [CUSTOM_TEST_LAYER_TYPE])

    artifact = Artifact(
        id="custom_test_artifact",
        config=copy.deepcopy(MINIMAL_OCI_ARTIFACT_CONFIG),
        config_media_type=CUSTOM_TEST_CONFIG_TYPE,
        bytes=json.dumps({"test": "custom-artifact-payload"}).encode("utf-8"),
        layer_media_type=CUSTOM_TEST_LAYER_TYPE,
        artifact_type=CUSTOM_TEST_ARTIFACT_TYPE,
        layer_annotations=None,
    )
    manifest, blobs = build_oci_artifact_manifest(artifact)

    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-custom-artifact",
        manifest,
        blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    pulled = pusher.pull_artifact(
        liveserver_session,
        "devtable",
        "cosign-custom-artifact",
        str(manifest.digest),
        credentials=("devtable", "password"),
    ).manifest
    assert pulled.artifact_type == CUSTOM_TEST_ARTIFACT_TYPE
    assert pulled.config_media_type == CUSTOM_TEST_CONFIG_TYPE


def test_base_image_deletion_preserves_signature(
    pusher, puller, basic_images, liveserver_session, app_reloader
):
    """
    Deleting the base image tag preserves the cosign signature manifest.

    After pushing a base image and attaching a cosign signature, delete the base
    image tag. The signature manifest must survive the tag deletion (GC has not
    run), confirming that signatures are not immediately lost when their subject
    image tag is removed.

    Note: the referrers API requires the subject manifest to be resolvable via
    an alive tag, so referrer discovery is expected to fail after the subject
    tag is deleted. This test validates signature *manifest* preservation, not
    referrer-index availability.
    """
    push_result = pusher.push(
        liveserver_session,
        "devtable",
        "cosign-base-deletion",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
    )
    subject = list(push_result.manifests.values())[0]
    registry_ref = "localhost:5000/%s/%s" % ("devtable", "cosign-base-deletion")

    signature, blobs = build_cosign_signature_manifest(subject, registry_ref)
    pusher.push_artifact(
        liveserver_session,
        "devtable",
        "cosign-base-deletion",
        signature,
        blobs,
        credentials=("devtable", "password"),
        options=_ARTIFACT_PUSH_OPTIONS,
    )

    # Verify the signature is discoverable via referrers before deletion.
    response = get_referrers(
        pusher, liveserver_session, "devtable", "cosign-base-deletion", str(subject.digest)
    )
    assert str(signature.digest) in referrer_digests(parse_and_validate_referrers_index(response))

    # Delete the base image tag (not the signature).
    pusher.delete(
        liveserver_session,
        "devtable",
        "cosign-base-deletion",
        "latest",
        credentials=("devtable", "password"),
    )

    # Confirm the base image tag is actually gone.
    puller.pull(
        liveserver_session,
        "devtable",
        "cosign-base-deletion",
        "latest",
        basic_images,
        credentials=("devtable", "password"),
        expected_failure=Failures.UNKNOWN_TAG,
    )

    # The signature artifact itself must still be pullable by digest because
    # GC has not yet reclaimed the untagged manifest.
    pulled_sig = pusher.pull_artifact(
        liveserver_session,
        "devtable",
        "cosign-base-deletion",
        str(signature.digest),
        credentials=("devtable", "password"),
    ).manifest
    assert pulled_sig.subject is not None
    assert pulled_sig.subject.digest == subject.digest
