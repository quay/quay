import json

import pytest

from image.docker.schema2 import DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
from image.docker.schema2.manifest import DockerSchema2Manifest
from image.oci.index import MalformedIndex, OCIIndex, OCIIndexBuilder
from image.oci.manifest import OCIManifest
from image.oci.test.testdata import (
    OCI_IMAGE_INDEX_MANIFEST,
    OCI_IMAGE_INDEX_MANIFEST_WITH_ARTIFACT_TYPE_AND_SUBJECT,
    OCI_IMAGE_INDEX_MANIFEST_WITHOUT_AMD,
    OCI_IMAGE_WITH_ARTIFACT_TYPES_AND_ANNOTATIONS,
)
from image.shared.schemas import parse_manifest_from_bytes
from image.shared.schemautil import ContentRetrieverForTesting
from util.bytes import Bytes


def test_parse_basic_index():
    index = OCIIndex(Bytes.for_string_or_unicode(OCI_IMAGE_INDEX_MANIFEST))
    assert index.is_manifest_list
    assert index.digest == "sha256:6416299892584b515393076863b75f192ca6cf98583d83b8e583ec3b6f2a8a5e"
    assert index.local_blob_digests == []
    assert index.child_manifest_digests() == [
        "sha256:31dd947a0acb5d8b840dc0de40a74f336e08cb0e17ba951c2faaea6374c1a0f3",
        "sha256:4eca3b97fcd88a47c6454d0cb9ff59aeb4baeca332387e87421b2302bfc724e6",
        "sha256:dacec655f2712b6f5eabc007b154959bba7add6aafdcab883e314f16e491f9d3",
    ]
    assert (
        index.amd64_linux_manifest_digest
        == "sha256:31dd947a0acb5d8b840dc0de40a74f336e08cb0e17ba951c2faaea6374c1a0f3"
    )


def test_config_missing_required():
    valid_index = json.loads(OCI_IMAGE_INDEX_MANIFEST)
    valid_index.pop("schemaVersion")

    with pytest.raises(MalformedIndex):
        OCIIndex(Bytes.for_string_or_unicode(json.dumps(valid_index)))


def test_invalid_index():
    with pytest.raises(MalformedIndex):
        OCIIndex(Bytes.for_string_or_unicode("{}"))


def test_index_without_amd():
    index = OCIIndex(Bytes.for_string_or_unicode(OCI_IMAGE_INDEX_MANIFEST_WITHOUT_AMD))
    assert index.is_manifest_list
    assert index.digest == "sha256:a0ed0f2b3949bc731063320667062307faf4245f6872dc5bc98ee6ea5443f169"
    assert index.local_blob_digests == []
    assert index.child_manifest_digests() == [
        "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
        "sha256:5b0bcabd1ed22e9fb1310cf6c2dec7cdef19f0ad69efa1f392e94a4333501270",
    ]
    assert index.amd64_linux_manifest_digest is None


def test_index_with_artifact_type_and_subject():
    index = OCIIndex(
        Bytes.for_string_or_unicode(OCI_IMAGE_INDEX_MANIFEST_WITH_ARTIFACT_TYPE_AND_SUBJECT)
    )
    assert index.is_manifest_list
    assert index.digest == "sha256:e2469184de432b3f6cb81d3e5ab0a4b77bf7d4008db3e7f3c3ba2f36e11cef5b"
    assert index.local_blob_digests == []
    assert index.child_manifest_digests() == [
        "sha256:31dd947a0acb5d8b840dc0de40a74f336e08cb0e17ba951c2faaea6374c1a0f3",
        "sha256:4eca3b97fcd88a47c6454d0cb9ff59aeb4baeca332387e87421b2302bfc724e6",
        "sha256:dacec655f2712b6f5eabc007b154959bba7add6aafdcab883e314f16e491f9d3",
    ]
    assert (
        index.amd64_linux_manifest_digest
        == "sha256:31dd947a0acb5d8b840dc0de40a74f336e08cb0e17ba951c2faaea6374c1a0f3"
    )
    assert index.artifact_type == "application/some.thing"
    assert (
        index.subject.digest
        == "sha256:6416299892584b515393076863b75f192ca6cf98583d83b8e583ec3b6f2a8a5e"
    )


def test_index_builder_with_artifact_type_and_annotations():
    index_builder = OCIIndexBuilder()
    parsed_manifest = parse_manifest_from_bytes(
        Bytes.for_string_or_unicode(OCI_IMAGE_WITH_ARTIFACT_TYPES_AND_ANNOTATIONS),
        "application/vnd.oci.image.manifest.v1+json",
    )

    index_builder.add_manifest_for_referrers_index(parsed_manifest)
    referrers_index = index_builder.build()

    assert referrers_index.is_manifest_list
    assert referrers_index.annotations

    manifests = referrers_index.manifest_dict["manifests"]
    for manifest in manifests:
        assert manifest.get("artifactType") is not None
        assert manifest.get("annotations") is not None


DOCKER_SCHEMA2_CHILD_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 1234,
            "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 1234,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
        ],
    }
).encode("utf-8")

OCI_CHILD_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "size": 7023,
            "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 32654,
                "digest": "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
            },
        ],
    }
).encode("utf-8")

# OCI index with both the Docker v2 image and OCI image in one
MIXED_MEDIA_TYPE_INDEX_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "manifests": [
            {
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "size": len(DOCKER_SCHEMA2_CHILD_BYTES),
                "digest": "sha256:aaa111",
                "platform": {
                    "architecture": "amd64",
                    "os": "linux",
                },
            },
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "size": len(OCI_CHILD_BYTES),
                "digest": "sha256:bbb222",
                "platform": {
                    "architecture": "arm64",
                    "os": "linux",
                },
            },
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "size": len(OCI_CHILD_BYTES),
                "digest": "sha256:ccc333",
                "platform": {
                    "architecture": "s390x",
                    "os": "linux",
                },
            },
        ],
    }
).encode("utf-8")


def test_oci_index_with_mixed_docker_and_oci_children():
    """
    Tests that validation of an OCI image with mixed entries (Docker v2 schema 2 and OCI image) passes.
    """
    index = OCIIndex(Bytes.for_string_or_unicode(MIXED_MEDIA_TYPE_INDEX_BYTES))
    assert index.is_manifest_list
    assert index.child_manifest_digests() == [
        "sha256:aaa111",
        "sha256:bbb222",
        "sha256:ccc333",
    ]

    retriever = ContentRetrieverForTesting(
        {
            "sha256:aaa111": DOCKER_SCHEMA2_CHILD_BYTES,
            "sha256:bbb222": OCI_CHILD_BYTES,
            "sha256:ccc333": OCI_CHILD_BYTES,
        }
    )

    manifests = index.manifests(retriever)
    assert len(manifests) == 3

    assert isinstance(manifests[0].manifest_obj, DockerSchema2Manifest)
    assert manifests[0].manifest_obj.media_type == DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE

    assert isinstance(manifests[1].manifest_obj, OCIManifest)
    assert isinstance(manifests[2].manifest_obj, OCIManifest)

    assert index.amd64_linux_manifest_digest == "sha256:aaa111"
