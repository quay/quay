import hashlib
import json

from io import BytesIO

import pytest

from mock import patch

from app import docker_v2_signing_key

from data.registry_model.blobuploader import BlobUploadSettings, upload_blob
from data.registry_model.manifestbuilder import create_manifest_builder, lookup_manifest_builder
from data.registry_model.registry_oci_model import OCIModel

from storage.distributedstorage import DistributedStorage
from storage.fakestorage import FakeStorage
from test.fixtures import *


@pytest.fixture(params=[OCIModel])
def registry_model(request, initialized_db):
    return request.param()


@pytest.fixture()
def fake_session():
    with patch("data.registry_model.manifestbuilder.session", {}):
        yield


@pytest.mark.parametrize(
    "layers",
    [
        pytest.param([("someid", None, b"some data")], id="Single layer"),
        pytest.param(
            [("parentid", None, b"some parent data"), ("someid", "parentid", b"some data")],
            id="Multi layer",
        ),
    ],
)
def test_build_manifest(layers, fake_session, registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "complex")
    storage = DistributedStorage({"local_us": FakeStorage(None)}, ["local_us"])
    settings = BlobUploadSettings("2M", 3600)
    app_config = {"TESTING": True}

    builder = create_manifest_builder(repository_ref, storage, docker_v2_signing_key)
    assert (
        lookup_manifest_builder(repository_ref, "anotherid", storage, docker_v2_signing_key) is None
    )
    assert (
        lookup_manifest_builder(repository_ref, builder.builder_id, storage, docker_v2_signing_key)
        is not None
    )

    blobs_by_layer = {}
    for layer_id, parent_id, layer_bytes in layers:
        # Start a new layer.
        assert builder.start_layer(
            layer_id, json.dumps({"id": layer_id, "parent": parent_id}), "local_us", None, 60
        )

        checksum = hashlib.sha1(layer_bytes).hexdigest()

        # Assign it a blob.
        with upload_blob(repository_ref, storage, settings) as uploader:
            uploader.upload_chunk(app_config, BytesIO(layer_bytes))
            blob = uploader.commit_to_blob(app_config)
            blobs_by_layer[layer_id] = blob
            builder.assign_layer_blob(builder.lookup_layer(layer_id), blob, [checksum])

        # Validate the checksum.
        assert builder.validate_layer_checksum(builder.lookup_layer(layer_id), checksum)

    # Commit the manifest to a tag.
    tag = builder.commit_tag_and_manifest("somenewtag", builder.lookup_layer(layers[-1][0]))
    assert tag
    assert tag in builder.committed_tags

    # Mark the builder as done.
    builder.done()

    # Verify the legacy image for the tag.
    found = registry_model.get_repo_tag(repository_ref, "somenewtag")
    assert found
    assert found.name == "somenewtag"

    # Verify the blob and manifest.
    manifest = registry_model.get_manifest_for_tag(found)
    assert manifest

    parsed = manifest.get_parsed_manifest()
    assert len(list(parsed.layers)) == len(layers)

    for index, (layer_id, parent_id, layer_bytes) in enumerate(layers):
        assert list(parsed.blob_digests)[index] == blobs_by_layer[layer_id].digest
        assert list(parsed.layers)[index].v1_metadata.image_id == layer_id
        assert list(parsed.layers)[index].v1_metadata.parent_image_id == parent_id

    assert parsed.leaf_layer_v1_image_id == layers[-1][0]


def test_build_manifest_missing_parent(fake_session, registry_model):
    storage = DistributedStorage({"local_us": FakeStorage(None)}, ["local_us"])
    repository_ref = registry_model.lookup_repository("devtable", "complex")
    builder = create_manifest_builder(repository_ref, storage, docker_v2_signing_key)

    assert (
        builder.start_layer(
            "somelayer",
            json.dumps({"id": "somelayer", "parent": "someparent"}),
            "local_us",
            None,
            60,
        )
        is None
    )
