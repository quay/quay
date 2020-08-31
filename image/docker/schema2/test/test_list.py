import json
import pytest

from image.docker.schema1 import (
    DockerSchema1Manifest,
    DOCKER_SCHEMA1_CONTENT_TYPES,
    DockerSchema1ManifestBuilder,
)
from image.docker.schema2 import DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
from image.docker.schema2.manifest import DockerSchema2Manifest
from image.docker.schema2.list import (
    MalformedSchema2ManifestList,
    DockerSchema2ManifestList,
    DockerSchema2ManifestListBuilder,
    MismatchManifestException,
)
from image.docker.schema2.test.test_manifest import MANIFEST_BYTES as v22_bytes
from image.shared.schemautil import ContentRetrieverForTesting
from image.docker.test.test_schema1 import MANIFEST_BYTES as v21_bytes
from util.bytes import Bytes


@pytest.mark.parametrize(
    "json_data",
    [
        "",
        "{}",
        """
  {
    "unknown": "key"
  }
  """,
    ],
)
def test_malformed_manifest_lists(json_data):
    with pytest.raises(MalformedSchema2ManifestList):
        DockerSchema2ManifestList(Bytes.for_string_or_unicode(json_data))


MANIFESTLIST_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
        "manifests": [
            {
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "size": 946,
                "digest": "sha256:e6",
                "platform": {
                    "architecture": "ppc64le",
                    "os": "linux",
                },
            },
            {
                "mediaType": "application/vnd.docker.distribution.manifest.v1+json",
                "size": 1051,
                "digest": "sha256:5b",
                "platform": {"architecture": "amd64", "os": "linux", "features": ["sse4"]},
            },
        ],
    }
).encode("utf-8")

NO_AMD_MANIFESTLIST_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
        "manifests": [
            {
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "size": 946,
                "digest": "sha256:e6",
                "platform": {
                    "architecture": "ppc64le",
                    "os": "linux",
                },
            },
        ],
    }
).encode("utf-8")

retriever = ContentRetrieverForTesting(
    {
        "sha256:e6": v22_bytes,
        "sha256:5b": v21_bytes,
    }
)


def test_valid_manifestlist():
    manifestlist = DockerSchema2ManifestList(Bytes.for_string_or_unicode(MANIFESTLIST_BYTES))
    assert len(manifestlist.manifests(retriever)) == 2

    assert manifestlist.media_type == "application/vnd.docker.distribution.manifest.list.v2+json"
    assert manifestlist.bytes.as_encoded_str() == MANIFESTLIST_BYTES
    assert manifestlist.manifest_dict == json.loads(MANIFESTLIST_BYTES)
    assert manifestlist.get_layers(retriever) is None
    assert manifestlist.config_media_type is None
    assert manifestlist.layers_compressed_size is None
    assert not manifestlist.blob_digests

    for index, manifest in enumerate(manifestlist.manifests(retriever)):
        if index == 0:
            assert isinstance(manifest.manifest_obj, DockerSchema2Manifest)
            assert manifest.manifest_obj.schema_version == 2
        else:
            assert isinstance(manifest.manifest_obj, DockerSchema1Manifest)
            assert manifest.manifest_obj.schema_version == 1

    # Check retrieval of a schema 2 manifest. This should return None, because the schema 2 manifest
    # is not amd64-compatible.
    schema2_manifest = manifestlist.convert_manifest(
        [DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE], "foo", "bar", "baz", retriever
    )
    assert schema2_manifest is None

    # Check retrieval of a schema 1 manifest.
    compatible_manifest = manifestlist.get_schema1_manifest("foo", "bar", "baz", retriever)
    assert compatible_manifest.schema_version == 1

    schema1_manifest = manifestlist.convert_manifest(
        DOCKER_SCHEMA1_CONTENT_TYPES, "foo", "bar", "baz", retriever
    )
    assert schema1_manifest.schema_version == 1
    assert schema1_manifest.digest == compatible_manifest.digest

    # Ensure it validates.
    manifestlist.validate(retriever)

    assert manifestlist.amd64_linux_manifest_digest == "sha256:5b"


def test_get_schema1_manifest_no_matching_list():
    manifestlist = DockerSchema2ManifestList(Bytes.for_string_or_unicode(NO_AMD_MANIFESTLIST_BYTES))
    assert len(manifestlist.manifests(retriever)) == 1

    assert manifestlist.media_type == "application/vnd.docker.distribution.manifest.list.v2+json"
    assert manifestlist.bytes.as_encoded_str() == NO_AMD_MANIFESTLIST_BYTES
    assert manifestlist.amd64_linux_manifest_digest is None

    compatible_manifest = manifestlist.get_schema1_manifest("foo", "bar", "baz", retriever)
    assert compatible_manifest is None


def test_builder():
    existing = DockerSchema2ManifestList(Bytes.for_string_or_unicode(MANIFESTLIST_BYTES))
    builder = DockerSchema2ManifestListBuilder()
    for index, manifest in enumerate(existing.manifests(retriever)):
        builder.add_manifest(manifest.manifest_obj, "amd64", "linux")

    built = builder.build()
    assert len(built.manifests(retriever)) == 2
    assert built.amd64_linux_manifest_digest is not None


def test_builder_no_amd():
    existing = DockerSchema2ManifestList(Bytes.for_string_or_unicode(MANIFESTLIST_BYTES))
    builder = DockerSchema2ManifestListBuilder()
    for index, manifest in enumerate(existing.manifests(retriever)):
        builder.add_manifest(manifest.manifest_obj, "intel386", "os")

    built = builder.build()
    assert len(built.manifests(retriever)) == 2
    assert built.amd64_linux_manifest_digest is None


def test_invalid_manifestlist():
    # Build a manifest list with a schema 1 manifest of the wrong architecture.
    builder = DockerSchema1ManifestBuilder("foo", "bar", "baz")
    builder.add_layer("sha:2356", '{"id": "foo"}')
    manifest = builder.build().unsigned()

    listbuilder = DockerSchema2ManifestListBuilder()
    listbuilder.add_manifest(manifest, "amd32", "linux")
    manifestlist = listbuilder.build()

    retriever = ContentRetrieverForTesting()
    retriever.add_digest(manifest.digest, manifest.bytes.as_encoded_str())

    with pytest.raises(MismatchManifestException):
        manifestlist.validate(retriever)
