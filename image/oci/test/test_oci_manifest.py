import hashlib
import json

import pytest
from dateutil.parser import parse as parse_date

from image.docker.schema1 import DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
from image.oci import register_artifact_type
from image.oci.manifest import MalformedOCIManifest, OCIManifest
from image.oci.test.test_oci_config import CONFIG_BYTES, CONFIG_DIGEST, CONFIG_SIZE
from image.shared.schemautil import ContentRetrieverForTesting
from util.bytes import Bytes

SAMPLE_MANIFEST = json.dumps(
    {
        "schemaVersion": 2,
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "size": CONFIG_SIZE,
            "digest": CONFIG_DIGEST,
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 32654,
                "digest": "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 16724,
                "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 73109,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
        ],
        "annotations": {"com.example.key1": "value1", "com.example.key2": "value2"},
    }
).encode("utf-8")
SAMPLE_MANIFEST_DIGEST = "sha256:" + hashlib.sha256(SAMPLE_MANIFEST).hexdigest()


SAMPLE_REMOTE_MANIFEST = json.dumps(
    {
        "schemaVersion": 2,
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "size": CONFIG_SIZE,
            "digest": CONFIG_DIGEST,
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 32654,
                "digest": "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
            },
            {
                "mediaType": "application/vnd.oci.image.layer.nondistributable.v1.tar+gzip",
                "size": 16724,
                "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
                "urls": ["https://foo/bar"],
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 73109,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
        ],
        "annotations": {"com.example.key1": "value1", "com.example.key2": "value2"},
    }
).encode("utf-8")
SAMPLE_REMOTE_MANIFEST_DIGEST = "sha256:" + hashlib.sha256(SAMPLE_REMOTE_MANIFEST).hexdigest()


def test_parse_basic_manifest():
    manifest = OCIManifest(Bytes.for_string_or_unicode(SAMPLE_MANIFEST))
    assert not manifest.is_manifest_list
    assert manifest.digest == SAMPLE_MANIFEST_DIGEST

    assert manifest.blob_digests == [
        "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
        "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
        "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
        CONFIG_DIGEST,
    ]

    assert manifest.local_blob_digests == manifest.blob_digests

    assert len(manifest.filesystem_layers) == 3
    assert (
        str(manifest.leaf_filesystem_layer.digest)
        == "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736"
    )

    assert not manifest.has_remote_layer
    assert manifest.has_legacy_image
    assert manifest.annotations == {"com.example.key1": "value1", "com.example.key2": "value2"}

    retriever = ContentRetrieverForTesting.for_config(
        json.loads(CONFIG_BYTES.decode("utf-8")), CONFIG_DIGEST, CONFIG_SIZE
    )
    manifest_created = manifest.get_created_date(retriever)
    assert manifest_created == parse_date("2015-10-31T22:22:56.015925234Z")


def test_parse_basic_remote_manifest():
    manifest = OCIManifest(Bytes.for_string_or_unicode(SAMPLE_REMOTE_MANIFEST))
    assert not manifest.is_manifest_list
    assert manifest.digest == SAMPLE_REMOTE_MANIFEST_DIGEST

    assert manifest.blob_digests == [
        "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
        "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
        "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
        CONFIG_DIGEST,
    ]

    assert manifest.local_blob_digests == [
        "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
        "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
        CONFIG_DIGEST,
    ]

    assert len(manifest.filesystem_layers) == 3
    assert (
        str(manifest.leaf_filesystem_layer.digest)
        == "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736"
    )

    assert manifest.has_remote_layer

    assert not manifest.has_legacy_image
    assert not manifest.get_legacy_image_ids(None)


def test_get_schema1_manifest():
    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "Labels": {
                    "foo": "bar",
                },
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "bar"},
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
            ],
            "architecture": "amd64",
            "os": "linux",
        },
        CONFIG_DIGEST,
        CONFIG_SIZE,
    )

    manifest = OCIManifest(Bytes.for_string_or_unicode(SAMPLE_MANIFEST))
    assert manifest.get_manifest_labels(retriever) == {
        "com.example.key1": "value1",
        "com.example.key2": "value2",
        "foo": "bar",
    }

    schema1 = manifest.get_schema1_manifest("somenamespace", "somename", "sometag", retriever)
    assert schema1 is not None
    assert schema1.media_type == DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
    assert set(schema1.local_blob_digests) == (set(manifest.local_blob_digests) - {CONFIG_DIGEST})
    assert len(schema1.layers) == 3

    via_convert = manifest.convert_manifest(
        [schema1.media_type], "somenamespace", "somename", "sometag", retriever
    )
    assert via_convert.digest == schema1.digest


@pytest.mark.parametrize("ignore_unknown_mediatypes", [True, False])
def test_validate_manifest_invalid_config_type(ignore_unknown_mediatypes):
    manifest_bytes = """{
      "schemaVersion": 2,
      "config": {
        "mediaType": "application/some.other.thing",
        "digest": "sha256:6bd578ec7d1e7381f63184dfe5fbe7f2f15805ecc4bfd485e286b76b1e796524",
        "size": 145
      },
      "layers": [
        {
          "mediaType": "application/tar+gzip",
          "digest": "sha256:ce879e86a8f71031c0f1ab149a26b000b3b5b8810d8d047f240ef69a6b2516ee",
          "size": 2807
        }
      ]
    }"""

    if ignore_unknown_mediatypes:
        OCIManifest(
            Bytes.for_string_or_unicode(manifest_bytes),
            ignore_unknown_mediatypes=ignore_unknown_mediatypes,
        )
    else:
        with pytest.raises(MalformedOCIManifest):
            OCIManifest(Bytes.for_string_or_unicode(manifest_bytes))


@pytest.mark.parametrize("ignore_unknown_mediatypes", [True, False])
def test_validate_manifest_with_subject_artifact_type(ignore_unknown_mediatypes):
    manifest_bytes = json.dumps(
        {
            "schemaVersion": 2,
            "artifactType": "application/some.thing",
            "config": {
                "mediaType": "application/some.other.thing",
                "digest": "sha256:6bd578ec7d1e7381f63184dfe5fbe7f2f15805ecc4bfd485e286b76b1e796524",
                "size": 145,
            },
            "layers": [
                {
                    "mediaType": "application/tar+gzip",
                    "digest": "sha256:ce879e86a8f71031c0f1ab149a26b000b3b5b8810d8d047f240ef69a6b2516ee",
                    "size": 2807,
                }
            ],
            "subject": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "size": CONFIG_SIZE,
                "digest": CONFIG_DIGEST,
            },
        }
    ).encode("utf-8")

    if ignore_unknown_mediatypes:
        OCIManifest(
            Bytes.for_string_or_unicode(manifest_bytes),
            ignore_unknown_mediatypes=ignore_unknown_mediatypes,
        )
    else:
        with pytest.raises(MalformedOCIManifest):
            OCIManifest(Bytes.for_string_or_unicode(manifest_bytes))


def test_get_schema1_manifest_missing_history():
    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "Labels": {
                    "foo": "bar",
                },
                "Cmd": ["dosomething"],
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "architecture": "amd64",
            "os": "linux",
        },
        CONFIG_DIGEST,
        CONFIG_SIZE,
    )

    manifest = OCIManifest(Bytes.for_string_or_unicode(SAMPLE_MANIFEST))
    assert manifest.get_manifest_labels(retriever) == {
        "com.example.key1": "value1",
        "com.example.key2": "value2",
        "foo": "bar",
    }

    schema1 = manifest.get_schema1_manifest("somenamespace", "somename", "sometag", retriever)
    assert schema1 is not None
    assert schema1.media_type == DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
    assert set(schema1.local_blob_digests) == (set(manifest.local_blob_digests) - {CONFIG_DIGEST})
    assert len(schema1.layers) == 3

    via_convert = manifest.convert_manifest(
        [schema1.media_type], "somenamespace", "somename", "sometag", retriever
    )
    assert via_convert.digest == schema1.digest

    final_layer = schema1.leaf_layer
    assert final_layer.v1_metadata.command == '[["dosomething"]]'


def test_get_schema1_manifest_incorrect_history():
    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "Labels": {
                    "foo": "bar",
                },
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
            ],
            "architecture": "amd64",
            "os": "linux",
        },
        CONFIG_DIGEST,
        CONFIG_SIZE,
    )

    manifest = OCIManifest(Bytes.for_string_or_unicode(SAMPLE_MANIFEST))
    assert manifest.get_manifest_labels(retriever) == {
        "com.example.key1": "value1",
        "com.example.key2": "value2",
        "foo": "bar",
    }

    with pytest.raises(MalformedOCIManifest):
        manifest.get_schema1_manifest("somenamespace", "somename", "sometag", retriever)


def test_validate_helm_oci_manifest():
    manifest_bytes = """{
      "schemaVersion":2,
      "config":{
        "mediaType":"application/vnd.cncf.helm.config.v1+json",
        "digest":"sha256:65a07b841ece031e6d0ec5eb948eacb17aa6d7294cdeb01d5348e86242951487",
        "size":141
      },
    "layers": [
      {
        "mediaType":"application/tar+gzip",
        "digest":"sha256:d84c9c29e0899862a0fa0f73da4d9f8c8c38e2da5d3258764aa7ba74bb914718",
        "size":3562
       }
      ]
    }"""

    HELM_CHART_CONFIG_TYPE = "application/vnd.cncf.helm.config.v1+json"
    HELM_CHART_LAYER_TYPES = ["application/tar+gzip"]
    register_artifact_type(HELM_CHART_CONFIG_TYPE, HELM_CHART_LAYER_TYPES)
    manifest = OCIManifest(Bytes.for_string_or_unicode(manifest_bytes))
