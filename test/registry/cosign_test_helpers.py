"""
Helpers for cosign signature and OCI referrers registry integration tests.

Builds OCI artifact manifests (cosign signatures, Helm charts, SBOMs) and helpers for
the referrers API and manifest deletion.
"""

import copy
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE, OCI_IMAGE_MANIFEST_CONTENT_TYPE
from image.oci.index import OCIIndex
from image.oci.manifest import OCIManifest
from test.registry.protocol_fixtures import MINIMAL_OCI_ARTIFACT_CONFIG
from test.registry.protocols import Artifact, artifact_config_bytes
from util.bytes import Bytes

COSIGN_SIMPLE_SIGNING_LAYER_TYPE = "application/vnd.dev.cosign.simplesigning.v1+json"
COSIGN_ARTIFACT_TYPE = "application/vnd.dev.cosign.simplesigning.v1+json"
IN_TOTO_LAYER_TYPE = "application/vnd.in-toto+json"
IN_TOTO_ARTIFACT_TYPE = "application/vnd.in-toto+json"

HELM_CONFIG_TYPE = "application/vnd.cncf.helm.config.v1+json"
HELM_LAYER_TYPE = "application/tar+gzip"

OCI_CONFIG_TYPE = "application/vnd.oci.image.config.v1+json"
DEFAULT_CREDENTIALS = ("devtable", "password")


def digest_for_bytes(data: bytes) -> str:
    """Return a sha256 content digest string for the given bytes."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def build_cosign_signature_payload(subject_digest: str, registry_ref: str) -> bytes:
    """
    Build a cosign simplesigning v1 JSON layer payload.

    Matches the structure cosign stores for container image signatures.
    """
    payload = {
        "critical": {
            "identity": {"docker-reference": registry_ref},
            "image": {"docker-manifest-digest": subject_digest},
            "type": "cosign container image signature",
        },
        "optional": None,
    }
    return json.dumps(payload).encode("utf-8")


def build_oci_artifact_manifest(
    artifact: Artifact,
    subject_manifest: Optional[OCIManifest] = None,
) -> Tuple[OCIManifest, Dict[str, bytes]]:
    """
    Build an OCI manifest for a generic artifact (signature, SBOM, Helm chart, etc.).

    Returns the manifest and a dict of blob digest -> bytes to upload.
    """
    config_bytes = artifact_config_bytes(artifact)
    layer_bytes = artifact.bytes
    config_media_type = artifact.config_media_type
    layer_media_type = artifact.layer_media_type
    artifact_type = artifact.artifact_type
    layer_annotations = artifact.layer_annotations

    config_digest = digest_for_bytes(config_bytes)
    layer_digest = digest_for_bytes(layer_bytes)

    layer_descriptor: Dict[str, Any] = {
        "mediaType": layer_media_type,
        "size": len(layer_bytes),
        "digest": layer_digest,
    }
    if layer_annotations:
        layer_descriptor["annotations"] = layer_annotations

    manifest_dict: Dict[str, Any] = {
        "schemaVersion": 2,
        "mediaType": OCI_IMAGE_MANIFEST_CONTENT_TYPE,
        "config": {
            "mediaType": config_media_type,
            "size": len(config_bytes),
            "digest": config_digest,
        },
        "layers": [layer_descriptor],
    }

    if artifact_type:
        manifest_dict["artifactType"] = artifact_type

    if subject_manifest is not None:
        subject_bytes = subject_manifest.bytes.as_encoded_str()
        manifest_dict["subject"] = {
            "mediaType": subject_manifest.media_type,
            "size": len(subject_bytes),
            "digest": str(subject_manifest.digest),
        }

    manifest = OCIManifest(Bytes.for_string_or_unicode(json.dumps(manifest_dict)))
    blobs = {
        config_digest: config_bytes,
        layer_digest: layer_bytes,
    }
    return manifest, blobs


def build_cosign_signature_manifest(
    subject_manifest: OCIManifest,
    registry_ref: str,
    artifact_type: Optional[str] = COSIGN_ARTIFACT_TYPE,
    signature_key_id: str = "key1",
) -> Tuple[OCIManifest, Dict[str, bytes]]:
    """Build a cosign signature manifest that references subject_manifest via subject."""
    sig_payload = build_cosign_signature_payload(str(subject_manifest.digest), registry_ref)
    artifact = Artifact(
        id="cosign_signature",
        config=copy.deepcopy(MINIMAL_OCI_ARTIFACT_CONFIG),
        config_media_type=OCI_CONFIG_TYPE,
        bytes=sig_payload,
        layer_media_type=COSIGN_SIMPLE_SIGNING_LAYER_TYPE,
        artifact_type=artifact_type,
        layer_annotations={
            "dev.cosignproject.cosign/signature": "MEUCIQ%s" % signature_key_id,
        },
    )
    return build_oci_artifact_manifest(artifact, subject_manifest=subject_manifest)


def build_in_toto_artifact_manifest() -> Tuple[OCIManifest, Dict[str, bytes]]:
    """Build an in-toto SBOM-style OCI artifact manifest (pre-registered artifact type)."""
    artifact = Artifact(
        id="in_toto_sbom",
        config=copy.deepcopy(MINIMAL_OCI_ARTIFACT_CONFIG),
        config_media_type=OCI_CONFIG_TYPE,
        bytes=json.dumps({"_type": "https://in-toto.io/Statement/v1"}).encode("utf-8"),
        layer_media_type=IN_TOTO_LAYER_TYPE,
        artifact_type=IN_TOTO_ARTIFACT_TYPE,
        layer_annotations=None,
    )
    return build_oci_artifact_manifest(artifact)


def build_helm_chart_manifest() -> Tuple[OCIManifest, Dict[str, bytes]]:
    """Build a minimal Helm chart OCI artifact manifest."""
    artifact = Artifact(
        id="helm_chart",
        config={
            "name": "test-chart",
            "version": "0.1.0",
            "description": "integration test chart",
        },
        config_media_type=HELM_CONFIG_TYPE,
        bytes=b"fake helm chart archive bytes for testing",
        layer_media_type=HELM_LAYER_TYPE,
        artifact_type=None,
        layer_annotations=None,
    )
    return build_oci_artifact_manifest(artifact)


def auth_headers(protocol, session, namespace, repo_name, credentials, scopes):
    """Perform V2 auth and return bearer headers."""
    protocol.ping(session)
    token, _ = protocol.auth(
        session,
        credentials,
        namespace,
        repo_name,
        scopes=scopes,
    )
    assert token is not None
    return {"Authorization": "Bearer " + token}


def get_referrers(
    protocol,
    session,
    namespace: str,
    repo_name: str,
    subject_digest: str,
    credentials=DEFAULT_CREDENTIALS,
    artifact_type: Optional[str] = None,
):
    """GET the OCI referrers API for a subject manifest digest."""
    repo_path = protocol.repo_name(namespace, repo_name)
    scopes = ["repository:%s:pull" % repo_path]
    headers = auth_headers(protocol, session, namespace, repo_name, credentials, scopes)
    headers["Accept"] = OCI_IMAGE_INDEX_CONTENT_TYPE

    params = {}
    if artifact_type is not None:
        params["artifactType"] = artifact_type

    return protocol.conduct(
        session,
        "GET",
        "/v2/%s/referrers/%s" % (repo_path, subject_digest),
        expected_status=200,
        headers=headers,
        params=params,
    )


def parse_and_validate_referrers_index(response) -> OCIIndex:
    """
    Parse a referrers API response and validate it is a well-formed OCI index.
    """
    assert response.headers["Content-Type"] == OCI_IMAGE_INDEX_CONTENT_TYPE
    index = OCIIndex(Bytes.for_string_or_unicode(response.text))
    assert index.schema_version == 2
    assert index.media_type == OCI_IMAGE_INDEX_CONTENT_TYPE
    return index


def referrer_digests(index: OCIIndex) -> List[str]:
    """Return digest strings listed in a referrers index."""
    return [str(digest) for digest in index.child_manifest_digests()]


def delete_manifest(
    protocol,
    session,
    namespace: str,
    repo_name: str,
    manifest_ref: str,
    credentials=DEFAULT_CREDENTIALS,
):
    """Delete a manifest by digest or tag via the V2 API."""
    repo_path = protocol.repo_name(namespace, repo_name)
    scopes = ["repository:%s:*" % repo_path]
    headers = auth_headers(protocol, session, namespace, repo_name, credentials, scopes)

    protocol.conduct(
        session,
        "DELETE",
        "/v2/%s/manifests/%s" % (repo_path, manifest_ref),
        expected_status=202,
        headers=headers,
    )
