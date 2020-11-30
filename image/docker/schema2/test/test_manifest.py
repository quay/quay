# -*- coding: utf-8 -*-

import json
import pytest
import os

from app import docker_v2_signing_key
from image.docker.schema1 import (
    DockerSchema1ManifestBuilder,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
)
from image.docker.schema2.manifest import (
    MalformedSchema2Manifest,
    DockerSchema2Manifest,
    DockerSchema2ManifestBuilder,
    EMPTY_LAYER_BLOB_DIGEST,
)
from image.docker.schema2.config import DockerSchema2Config
from image.docker.schema2.test.test_config import CONFIG_BYTES
from image.shared.schemautil import ContentRetrieverForTesting
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
def test_malformed_manifests(json_data):
    with pytest.raises(MalformedSchema2Manifest):
        DockerSchema2Manifest(Bytes.for_string_or_unicode(json_data))


MANIFEST_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 1885,
            "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 1234,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 32654,
                "digest": "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 16724,
                "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 73109,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
        ],
    }
).encode("utf-8")

REMOTE_MANIFEST_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 1885,
            "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.foreign.diff.tar.gzip",
                "size": 1234,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
                "urls": ["http://some/url"],
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 32654,
                "digest": "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 16724,
                "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 73109,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
        ],
    }
).encode("utf-8")


def test_valid_manifest():
    manifest = DockerSchema2Manifest(Bytes.for_string_or_unicode(MANIFEST_BYTES))
    assert manifest.config.size == 1885
    assert (
        str(manifest.config.digest)
        == "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"
    )
    assert manifest.media_type == "application/vnd.docker.distribution.manifest.v2+json"
    assert not manifest.has_remote_layer
    assert manifest.has_legacy_image
    assert manifest.config_media_type == "application/vnd.docker.container.image.v1+json"
    assert manifest.layers_compressed_size == 123721

    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "Labels": {},
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "bar"},
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "bar"},
            ],
        },
        "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        1885,
    )

    assert len(manifest.filesystem_layers) == 4
    assert manifest.filesystem_layers[0].compressed_size == 1234
    assert (
        str(manifest.filesystem_layers[0].digest)
        == "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736"
    )
    assert not manifest.filesystem_layers[0].is_remote

    assert manifest.leaf_filesystem_layer == manifest.filesystem_layers[3]
    assert not manifest.leaf_filesystem_layer.is_remote
    assert manifest.leaf_filesystem_layer.compressed_size == 73109

    blob_digests = list(manifest.blob_digests)
    expected = [str(layer.digest) for layer in manifest.filesystem_layers] + [
        manifest.config.digest
    ]
    assert blob_digests == expected
    assert list(manifest.local_blob_digests) == expected

    manifest_image_layers = list(manifest.get_layers(retriever))
    assert len(manifest_image_layers) == len(list(manifest.filesystem_layers))
    for index in range(0, 4):
        assert manifest_image_layers[index].blob_digest == str(
            manifest.filesystem_layers[index].digest
        )


def test_valid_remote_manifest():
    manifest = DockerSchema2Manifest(Bytes.for_string_or_unicode(REMOTE_MANIFEST_BYTES))
    assert manifest.config.size == 1885
    assert (
        str(manifest.config.digest)
        == "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"
    )
    assert manifest.media_type == "application/vnd.docker.distribution.manifest.v2+json"
    assert manifest.has_remote_layer
    assert manifest.config_media_type == "application/vnd.docker.container.image.v1+json"
    assert manifest.layers_compressed_size == 123721

    assert len(manifest.filesystem_layers) == 4
    assert manifest.filesystem_layers[0].compressed_size == 1234
    assert (
        str(manifest.filesystem_layers[0].digest)
        == "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736"
    )
    assert manifest.filesystem_layers[0].is_remote
    assert manifest.filesystem_layers[0].urls == ["http://some/url"]

    assert manifest.leaf_filesystem_layer == manifest.filesystem_layers[3]
    assert not manifest.leaf_filesystem_layer.is_remote
    assert manifest.leaf_filesystem_layer.compressed_size == 73109

    expected = set(
        [str(layer.digest) for layer in manifest.filesystem_layers] + [manifest.config.digest]
    )

    blob_digests = set(manifest.blob_digests)
    local_digests = set(manifest.local_blob_digests)

    assert blob_digests == expected
    assert local_digests == (expected - {manifest.filesystem_layers[0].digest})

    assert manifest.has_remote_layer
    assert manifest.get_leaf_layer_v1_image_id(None) is None
    assert manifest.get_legacy_image_ids(None) is None

    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "Labels": {},
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "bar"},
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "bar"},
            ],
        },
        "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        1885,
    )

    manifest_image_layers = list(manifest.get_layers(retriever))
    assert len(manifest_image_layers) == len(list(manifest.filesystem_layers))
    for index in range(0, 4):
        assert manifest_image_layers[index].blob_digest == str(
            manifest.filesystem_layers[index].digest
        )


def test_schema2_builder():
    manifest = DockerSchema2Manifest(Bytes.for_string_or_unicode(MANIFEST_BYTES))

    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(manifest.config.digest, manifest.config.size)

    for layer in manifest.filesystem_layers:
        builder.add_layer(layer.digest, layer.compressed_size, urls=layer.urls)

    built = builder.build()
    assert built.filesystem_layers == manifest.filesystem_layers
    assert built.config == manifest.config


def test_get_manifest_labels():
    labels = dict(foo="bar", baz="meh")
    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "Labels": labels,
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [],
        },
        "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        1885,
    )

    manifest = DockerSchema2Manifest(Bytes.for_string_or_unicode(MANIFEST_BYTES))
    assert manifest.get_manifest_labels(retriever) == labels


def test_build_schema1():
    manifest = DockerSchema2Manifest(Bytes.for_string_or_unicode(MANIFEST_BYTES))
    assert not manifest.has_remote_layer

    retriever = ContentRetrieverForTesting(
        {
            "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7": CONFIG_BYTES,
        }
    )

    builder = DockerSchema1ManifestBuilder("somenamespace", "somename", "sometag")
    manifest._populate_schema1_builder(builder, retriever)
    schema1 = builder.build(docker_v2_signing_key)

    assert schema1.media_type == DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE


def test_get_schema1_manifest():
    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "Labels": {},
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "bar"},
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "foo"},
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "bar"},
            ],
        },
        "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        1885,
    )

    manifest = DockerSchema2Manifest(Bytes.for_string_or_unicode(MANIFEST_BYTES))
    schema1 = manifest.get_schema1_manifest("somenamespace", "somename", "sometag", retriever)
    assert schema1 is not None
    assert schema1.media_type == DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE

    via_convert = manifest.convert_manifest(
        [schema1.media_type], "somenamespace", "somename", "sometag", retriever
    )
    assert via_convert.digest == schema1.digest


def test_generate_legacy_layers():
    builder = DockerSchema2ManifestBuilder()
    builder.add_layer("sha256:abc123", 123)
    builder.add_layer("sha256:def456", 789)
    builder.set_config_digest("sha256:def456", 2000)
    manifest = builder.build()

    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "base"},
                {
                    "created": "2018-04-06T18:37:09.284840891Z",
                    "created_by": "middle",
                    "empty_layer": True,
                },
                {"created": "2018-04-12T18:37:09.284840891Z", "created_by": "leaf"},
            ],
        },
        "sha256:def456",
        2000,
    )

    legacy_layers = list(manifest.generate_legacy_layers({}, retriever))
    assert len(legacy_layers) == 3
    assert legacy_layers[0].content_checksum == "sha256:abc123"
    assert legacy_layers[1].content_checksum == EMPTY_LAYER_BLOB_DIGEST
    assert legacy_layers[2].content_checksum == "sha256:def456"

    assert legacy_layers[0].created == "2018-04-03T18:37:09.284840891Z"
    assert legacy_layers[1].created == "2018-04-06T18:37:09.284840891Z"
    assert legacy_layers[2].created == "2018-04-12T18:37:09.284840891Z"

    assert legacy_layers[0].command == '["base"]'
    assert legacy_layers[1].command == '["middle"]'
    assert legacy_layers[2].command == '["leaf"]'

    assert legacy_layers[2].parent_image_id == legacy_layers[1].image_id
    assert legacy_layers[1].parent_image_id == legacy_layers[0].image_id
    assert legacy_layers[0].parent_image_id is None

    assert legacy_layers[1].image_id != legacy_layers[2]
    assert legacy_layers[0].image_id != legacy_layers[1]


def test_remote_layer_manifest():
    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest("sha256:abcd", 1234)
    builder.add_layer("sha256:adef", 1234, urls=["http://some/url"])
    builder.add_layer("sha256:1352", 4567)
    builder.add_layer("sha256:1353", 4567)
    manifest = builder.build()

    assert manifest.has_remote_layer
    assert manifest.get_leaf_layer_v1_image_id(None) is None
    assert manifest.get_legacy_image_ids(None) is None
    assert not manifest.has_legacy_image

    schema1 = manifest.get_schema1_manifest("somenamespace", "somename", "sometag", None)
    assert schema1 is None

    assert set(manifest.blob_digests) == {
        "sha256:adef",
        "sha256:abcd",
        "sha256:1352",
        "sha256:1353",
    }
    assert set(manifest.local_blob_digests) == {"sha256:abcd", "sha256:1352", "sha256:1353"}


def test_unencoded_unicode_manifest():
    builder = DockerSchema2ManifestBuilder()
    builder.add_layer("sha256:abc123", 123)
    builder.set_config_digest("sha256:def456", 2000)
    manifest = builder.build()

    retriever = ContentRetrieverForTesting.for_config(
        {
            "config": {
                "author": "Sômé guy",
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {
                    "created": "2018-04-03T18:37:09.284840891Z",
                    "created_by": "base",
                    "author": "Sômé guy",
                },
            ],
        },
        "sha256:def456",
        2000,
        ensure_ascii=False,
    )

    layers = list(manifest.get_layers(retriever))
    assert layers[0].author == "Sômé guy"


def test_build_unencoded_unicode_manifest():
    config_json = json.dumps(
        {
            "config": {
                "author": "Sômé guy",
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {
                    "created": "2018-04-03T18:37:09.284840891Z",
                    "created_by": "base",
                    "author": "Sômé guy",
                },
            ],
        },
        ensure_ascii=False,
    )

    schema2_config = DockerSchema2Config(Bytes.for_string_or_unicode(config_json))

    builder = DockerSchema2ManifestBuilder()
    builder.set_config(schema2_config)
    builder.add_layer("sha256:abc123", 123)
    builder.build()


def test_load_unicode_manifest():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(test_dir, "unicode_manifest_config.json"), "rb") as f:
        retriever = ContentRetrieverForTesting()
        retriever.add_digest(
            "sha256:5bdd65cdd055c7f3bbaecdc9fd6c75f155322520f85953aa0e2724cab006d407", f.read()
        )

    with open(os.path.join(test_dir, "unicode_manifest.json"), "rb") as f:
        manifest_bytes = f.read()

    manifest = DockerSchema2Manifest(Bytes.for_string_or_unicode(manifest_bytes))
    assert (
        manifest.digest == "sha256:97556fa8c553395bd9d8e19a04acef4716ca287ffbf6bde14dd9966053912613"
    )

    layers = list(manifest.get_layers(retriever))
    assert layers[-1].author == "Sômé guy"
