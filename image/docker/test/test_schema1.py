# -*- coding: utf-8 -*-

import os
import json

import pytest

from app import docker_v2_signing_key
from image.docker.schema1 import (
    MalformedSchema1Manifest,
    DockerSchema1Manifest,
    DockerSchema1ManifestBuilder,
)
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
    with pytest.raises(MalformedSchema1Manifest):
        DockerSchema1Manifest(Bytes.for_string_or_unicode(json_data))


MANIFEST_BYTES = json.dumps(
    {
        "name": "hello-world",
        "tag": "latest",
        "architecture": "amd64",
        "fsLayers": [
            {"blobSum": "sha256:cd8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11"},
            {"blobSum": "sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11"},
            {"blobSum": "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef"},
        ],
        "history": [
            {"v1Compatibility": '{"id":"sizedid", "parent": "someid", "Size": 1234}'},
            {"v1Compatibility": '{"id":"someid", "parent": "anotherid"}'},
            {"v1Compatibility": '{"id":"anotherid"}'},
        ],
        "schemaVersion": 1,
        "signatures": [
            {
                "header": {
                    "jwk": {
                        "crv": "P-256",
                        "kid": "OD6I:6DRK:JXEJ:KBM4:255X:NSAA:MUSF:E4VM:ZI6W:CUN2:L4Z6:LSF4",
                        "kty": "EC",
                        "x": "3gAwX48IQ5oaYQAYSxor6rYYc_6yjuLCjtQ9LUakg4A",
                        "y": "t72ge6kIA1XOjqjVoEOiPPAURltJFBMGDSQvEGVB010",
                    },
                    "alg": "ES256",
                },
                "signature": "XREm0L8WNn27Ga_iE_vRnTxVMhhYY0Zst_FfkKopg6gWSoTOZTuW4rK0fg_IqnKkEKlbD83tD46LKEGi5aIVFg",
                "protected": "eyJmb3JtYXRMZW5ndGgiOjY2MjgsImZvcm1hdFRhaWwiOiJDbjAiLCJ0aW1lIjoiMjAxNS0wNC0wOFQxODo1Mjo1OVoifQ",
            }
        ],
    }
)


def test_valid_manifest():
    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(MANIFEST_BYTES), validate=False)
    assert len(manifest.signatures) == 1
    assert manifest.namespace == ""
    assert manifest.repo_name == "hello-world"
    assert manifest.tag == "latest"
    assert manifest.image_ids == {"sizedid", "someid", "anotherid"}
    assert manifest.parent_image_ids == {"someid", "anotherid"}
    assert manifest.layers_compressed_size == 1234
    assert manifest.config_media_type is None

    assert len(manifest.layers) == 3

    assert manifest.layers[0].v1_metadata.image_id == "anotherid"
    assert manifest.layers[0].v1_metadata.parent_image_id is None

    assert manifest.layers[1].v1_metadata.image_id == "someid"
    assert manifest.layers[1].v1_metadata.parent_image_id == "anotherid"

    assert manifest.layers[2].v1_metadata.image_id == "sizedid"
    assert manifest.layers[2].v1_metadata.parent_image_id == "someid"

    assert manifest.layers[0].compressed_size is None
    assert manifest.layers[1].compressed_size is None
    assert manifest.layers[2].compressed_size == 1234

    assert manifest.leaf_layer == manifest.layers[2]
    assert manifest.created_datetime is None

    unsigned = manifest.unsigned()
    assert unsigned.namespace == manifest.namespace
    assert unsigned.repo_name == manifest.repo_name
    assert unsigned.tag == manifest.tag
    assert unsigned.layers == manifest.layers
    assert unsigned.blob_digests == manifest.blob_digests
    assert unsigned.digest != manifest.digest

    image_layers = list(manifest.get_layers(None))
    assert len(image_layers) == 3
    for index in range(0, 3):
        assert image_layers[index].layer_id == manifest.layers[index].v1_metadata.image_id
        assert image_layers[index].blob_digest == manifest.layers[index].digest
        assert image_layers[index].command == manifest.layers[index].v1_metadata.command


def test_validate_manifest():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(test_dir, "validated_manifest.json"), "r") as f:
        manifest_bytes = f.read()

    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(manifest_bytes), validate=True)
    digest = manifest.digest
    assert digest == "sha256:b5dc4f63fdbd64f34f2314c0747ef81008f9fcddce4edfc3fd0e8ec8b358d571"
    assert manifest.created_datetime


def test_validate_manifest_with_unicode():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(test_dir, "validated_manifest_with_unicode.json"), "r") as f:
        manifest_bytes = f.read()

    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(manifest_bytes), validate=True)
    digest = manifest.digest
    assert digest == "sha256:815ecf45716a96b19d54d911e6ace91f78bab26ca0dd299645d9995dacd9f1ef"
    assert manifest.created_datetime


def test_validate_manifest_with_unicode_encoded():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(test_dir, "manifest_unicode_row.json"), "r") as f:
        manifest_bytes = json.loads(f.read())[0]["json_data"]

    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(manifest_bytes), validate=True)
    digest = manifest.digest
    assert digest == "sha256:dde3714ce7e23edc6413aa85c0b42792e4f2f79e9ea36afc154d63ff3d04e86c"
    assert manifest.created_datetime


def test_validate_manifest_with_unencoded_unicode():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(test_dir, "manifest_unencoded_unicode.json"), "r") as f:
        manifest_bytes = f.read()

    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(manifest_bytes))
    digest = manifest.digest
    assert digest == "sha256:5d8a0f34744a39bf566ba430251adc0cc86587f86aed3ac2acfb897f349777bc"
    assert manifest.created_datetime

    layers = list(manifest.get_layers(None))
    assert layers[-1].author == "Sômé guy"


@pytest.mark.parametrize("with_key", [None, docker_v2_signing_key,])
def test_build_unencoded_unicode_manifest(with_key):
    builder = DockerSchema1ManifestBuilder("somenamespace", "somerepo", "sometag")
    builder.add_layer(
        "sha256:abcde", json.dumps({"id": "someid", "author": "Sômé guy",}, ensure_ascii=False)
    )

    built = builder.build(with_key, ensure_ascii=False)
    built._validate()


def test_validate_manifest_known_issue():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(test_dir, "validate_manifest_known_issue.json"), "r") as f:
        manifest_bytes = f.read()

    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(manifest_bytes))
    digest = manifest.digest
    assert digest == "sha256:44518f5a4d1cb5b7a6347763116fb6e10f6a8563b6c40bb389a0a982f0a9f47a"
    assert manifest.created_datetime

    layers = list(manifest.get_layers(None))
    assert layers[-1].author is None


@pytest.mark.parametrize("with_key", [None, docker_v2_signing_key,])
def test_validate_manifest_with_emoji(with_key):
    builder = DockerSchema1ManifestBuilder("somenamespace", "somerepo", "sometag")
    builder.add_layer(
        "sha256:abcde", json.dumps({"id": "someid", "author": "😱",}, ensure_ascii=False)
    )

    built = builder.build(with_key, ensure_ascii=False)
    built._validate()

    # Ensure the manifest can be reloaded.
    built_bytes = built.bytes.as_encoded_str()
    DockerSchema1Manifest(Bytes.for_string_or_unicode(built_bytes))


@pytest.mark.parametrize("with_key", [None, docker_v2_signing_key,])
def test_validate_manifest_with_none_metadata_layer(with_key):
    builder = DockerSchema1ManifestBuilder("somenamespace", "somerepo", "sometag")
    builder.add_layer("sha256:abcde", None)

    built = builder.build(with_key, ensure_ascii=False)
    built._validate()

    # Ensure the manifest can be reloaded.
    built_bytes = built.bytes.as_encoded_str()
    DockerSchema1Manifest(Bytes.for_string_or_unicode(built_bytes))


def test_build_with_metadata_removed():
    builder = DockerSchema1ManifestBuilder("somenamespace", "somerepo", "sometag")
    builder.add_layer(
        "sha256:abcde",
        json.dumps(
            {
                "id": "someid",
                "parent": "someid",
                "author": "😱",
                "comment": "hello world!",
                "created": "1975-01-02 12:34",
                "Size": 5678,
                "container_config": {"Cmd": "foobar", "more": "stuff", "goes": "here",},
            }
        ),
    )
    builder.add_layer(
        "sha256:abcde",
        json.dumps(
            {
                "id": "anotherid",
                "author": "😱",
                "created": "1985-02-03 12:34",
                "Size": 1234,
                "container_config": {"Cmd": "barbaz", "more": "stuff", "goes": "here",},
            }
        ),
    )

    built = builder.build(None)
    built._validate()

    assert built.leaf_layer_v1_image_id == "someid"

    with_metadata_removed = builder.with_metadata_removed().build()
    with_metadata_removed._validate()

    built_layers = list(built.get_layers(None))
    with_metadata_removed_layers = list(with_metadata_removed.get_layers(None))

    assert len(built_layers) == len(with_metadata_removed_layers)
    for index, built_layer in enumerate(built_layers):
        with_metadata_removed_layer = with_metadata_removed_layers[index]

        assert built_layer.layer_id == with_metadata_removed_layer.layer_id
        assert built_layer.compressed_size == with_metadata_removed_layer.compressed_size
        assert built_layer.command == with_metadata_removed_layer.command
        assert built_layer.comment == with_metadata_removed_layer.comment
        assert built_layer.author == with_metadata_removed_layer.author
        assert built_layer.blob_digest == with_metadata_removed_layer.blob_digest
        assert built_layer.created_datetime == with_metadata_removed_layer.created_datetime

    assert built.leaf_layer_v1_image_id == with_metadata_removed.leaf_layer_v1_image_id
    assert built_layers[-1].layer_id == built.leaf_layer_v1_image_id

    assert json.loads(built_layers[-1].internal_layer.raw_v1_metadata) == json.loads(
        with_metadata_removed_layers[-1].internal_layer.raw_v1_metadata
    )


def test_validate_manifest_without_metadata():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(test_dir, "validated_manifest.json"), "r") as f:
        manifest_bytes = f.read()

    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(manifest_bytes), validate=True)
    digest = manifest.digest
    assert digest == "sha256:b5dc4f63fdbd64f34f2314c0747ef81008f9fcddce4edfc3fd0e8ec8b358d571"
    assert manifest.created_datetime

    with_metadata_removed = manifest._unsigned_builder().with_metadata_removed().build()
    assert with_metadata_removed.leaf_layer_v1_image_id == manifest.leaf_layer_v1_image_id

    manifest_layers = list(manifest.get_layers(None))
    with_metadata_removed_layers = list(with_metadata_removed.get_layers(None))

    assert len(manifest_layers) == len(with_metadata_removed_layers)
    for index, built_layer in enumerate(manifest_layers):
        with_metadata_removed_layer = with_metadata_removed_layers[index]

        assert built_layer.layer_id == with_metadata_removed_layer.layer_id
        assert built_layer.compressed_size == with_metadata_removed_layer.compressed_size
        assert built_layer.command == with_metadata_removed_layer.command
        assert built_layer.comment == with_metadata_removed_layer.comment
        assert built_layer.author == with_metadata_removed_layer.author
        assert built_layer.blob_digest == with_metadata_removed_layer.blob_digest
        assert built_layer.created_datetime == with_metadata_removed_layer.created_datetime

    assert with_metadata_removed.digest != manifest.digest

    assert with_metadata_removed.namespace == manifest.namespace
    assert with_metadata_removed.repo_name == manifest.repo_name
    assert with_metadata_removed.tag == manifest.tag
    assert with_metadata_removed.created_datetime == manifest.created_datetime
    assert with_metadata_removed.checksums == manifest.checksums
    assert with_metadata_removed.image_ids == manifest.image_ids
    assert with_metadata_removed.parent_image_ids == manifest.parent_image_ids
