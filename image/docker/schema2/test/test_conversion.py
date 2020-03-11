import os
import json

import pytest

from image.docker.schema1 import DockerSchema1Manifest, DOCKER_SCHEMA1_CONTENT_TYPES
from image.docker.schema2.manifest import DockerSchema2Manifest
from image.shared.schemautil import ContentRetrieverForTesting
from util.bytes import Bytes


def _get_test_file_contents(test_name, kind):
    filename = "%s.%s.json" % (test_name, kind)
    data_dir = os.path.dirname(__file__)
    with open(os.path.join(data_dir, "conversion_data", filename), "r") as f:
        return Bytes.for_string_or_unicode(f.read())


@pytest.mark.parametrize(
    "name, config_sha",
    [
        ("simple", "sha256:e7a06c2e5b7afb1bbfa9124812e87f1138c4c10d77e0a217f0b8c8c9694dc5cf"),
        ("complex", "sha256:ae6b78bedf88330a5e5392164f40d28ed8a38120b142905d30b652ebffece10e"),
        ("ubuntu", "sha256:93fd78260bd1495afb484371928661f63e64be306b7ac48e2d13ce9422dfee26"),
    ],
)
def test_legacy_layers(name, config_sha):
    cr = {}
    cr[config_sha] = _get_test_file_contents(name, "config").as_encoded_str()
    retriever = ContentRetrieverForTesting(cr)

    schema2 = DockerSchema2Manifest(_get_test_file_contents(name, "schema2"))
    schema1 = DockerSchema1Manifest(_get_test_file_contents(name, "schema1"), validate=False)

    # Check legacy layers
    schema2_legacy_layers = list(schema2.generate_legacy_layers({}, retriever))
    schema1_legacy_layers = list(schema1.generate_legacy_layers({}, retriever))
    assert len(schema1_legacy_layers) == len(schema2_legacy_layers)

    for index in range(0, len(schema1_legacy_layers)):
        schema1_legacy_layer = schema1_legacy_layers[index]
        schema2_legacy_layer = schema2_legacy_layers[index]
        assert schema1_legacy_layer.content_checksum == schema2_legacy_layer.content_checksum
        assert schema1_legacy_layer.comment == schema2_legacy_layer.comment
        assert schema1_legacy_layer.command == schema2_legacy_layer.command


@pytest.mark.parametrize(
    "name, config_sha",
    [
        ("simple", "sha256:e7a06c2e5b7afb1bbfa9124812e87f1138c4c10d77e0a217f0b8c8c9694dc5cf"),
        ("complex", "sha256:ae6b78bedf88330a5e5392164f40d28ed8a38120b142905d30b652ebffece10e"),
        ("ubuntu", "sha256:93fd78260bd1495afb484371928661f63e64be306b7ac48e2d13ce9422dfee26"),
    ],
)
def test_conversion(name, config_sha):
    cr = {}
    cr[config_sha] = _get_test_file_contents(name, "config").as_encoded_str()
    retriever = ContentRetrieverForTesting(cr)

    schema2 = DockerSchema2Manifest(_get_test_file_contents(name, "schema2"))
    schema1 = DockerSchema1Manifest(_get_test_file_contents(name, "schema1"), validate=False)

    s2to2 = schema2.convert_manifest(
        [schema2.media_type], "devtable", "somerepo", "latest", retriever
    )
    assert s2to2 == schema2

    s1to1 = schema1.convert_manifest(
        [schema1.media_type], "devtable", "somerepo", "latest", retriever
    )
    assert s1to1 == schema1

    s2to1 = schema2.convert_manifest(
        DOCKER_SCHEMA1_CONTENT_TYPES, "devtable", "somerepo", "latest", retriever
    )
    assert s2to1.media_type in DOCKER_SCHEMA1_CONTENT_TYPES
    assert len(s2to1.layers) == len(schema1.layers)

    s2toempty = schema2.convert_manifest([], "devtable", "somerepo", "latest", retriever)
    assert s2toempty is None


@pytest.mark.parametrize(
    "name, config_sha",
    [
        ("simple", "sha256:e7a06c2e5b7afb1bbfa9124812e87f1138c4c10d77e0a217f0b8c8c9694dc5cf"),
        ("complex", "sha256:ae6b78bedf88330a5e5392164f40d28ed8a38120b142905d30b652ebffece10e"),
        ("ubuntu", "sha256:93fd78260bd1495afb484371928661f63e64be306b7ac48e2d13ce9422dfee26"),
    ],
)
def test_2to1_conversion(name, config_sha):
    cr = {}
    cr[config_sha] = _get_test_file_contents(name, "config").as_encoded_str()
    retriever = ContentRetrieverForTesting(cr)

    schema2 = DockerSchema2Manifest(_get_test_file_contents(name, "schema2"))
    schema1 = DockerSchema1Manifest(_get_test_file_contents(name, "schema1"), validate=False)

    converted = schema2.get_schema1_manifest("devtable", "somerepo", "latest", retriever)
    assert len(converted.layers) == len(schema1.layers)

    image_id_map = {}
    for index in range(0, len(converted.layers)):
        converted_layer = converted.layers[index]
        schema1_layer = schema1.layers[index]

        image_id_map[schema1_layer.v1_metadata.image_id] = converted_layer.v1_metadata.image_id

        assert str(schema1_layer.digest) == str(converted_layer.digest)

        schema1_parent_id = schema1_layer.v1_metadata.parent_image_id
        converted_parent_id = converted_layer.v1_metadata.parent_image_id
        assert (schema1_parent_id is None) == (converted_parent_id is None)

        if schema1_parent_id is not None:
            assert image_id_map[schema1_parent_id] == converted_parent_id

        assert schema1_layer.v1_metadata.created == converted_layer.v1_metadata.created
        assert schema1_layer.v1_metadata.comment == converted_layer.v1_metadata.comment
        assert schema1_layer.v1_metadata.command == converted_layer.v1_metadata.command
        assert schema1_layer.v1_metadata.labels == converted_layer.v1_metadata.labels

        schema1_container_config = json.loads(schema1_layer.raw_v1_metadata)["container_config"]
        converted_container_config = json.loads(converted_layer.raw_v1_metadata)["container_config"]

        assert schema1_container_config == converted_container_config
