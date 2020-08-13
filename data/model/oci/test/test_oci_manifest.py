import json

from playhouse.test_utils import assert_query_count

from app import docker_v2_signing_key, storage

from digest.digest_tools import sha256_digest
from data.database import (
    Tag,
    ManifestBlob,
    ImageStorageLocation,
    ManifestChild,
    ImageStorage,
    Image,
    RepositoryTag,
    get_epoch_timestamp_ms,
)
from data.model.oci.manifest import lookup_manifest, get_or_create_manifest, CreateManifestException
from data.model.oci.tag import filter_to_alive_tags, get_tag
from data.model.oci.shared import get_legacy_image_for_manifest
from data.model.oci.label import list_manifest_labels
from data.model.oci.retriever import RepositoryContentRetriever
from data.model.repository import get_repository, create_repository
from data.model.image import find_create_or_link_image
from data.model.blob import store_blob_record_and_temp_link
from data.model.storage import get_layer_path
from image.shared.interfaces import ContentRetriever
from image.shared.schemas import parse_manifest_from_bytes
from image.docker.schema1 import DockerSchema1ManifestBuilder, DockerSchema1Manifest
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder, DockerSchema2Manifest
from image.docker.schema2.list import DockerSchema2ManifestListBuilder
from util.bytes import Bytes

from test.fixtures import *


def test_lookup_manifest(initialized_db):
    found = False
    for tag in filter_to_alive_tags(Tag.select()):
        found = True
        repo = tag.repository
        digest = tag.manifest.digest
        with assert_query_count(1):
            assert lookup_manifest(repo, digest) == tag.manifest

    assert found

    for tag in Tag.select():
        repo = tag.repository
        digest = tag.manifest.digest
        with assert_query_count(1):
            assert lookup_manifest(repo, digest, allow_dead=True) == tag.manifest


def test_lookup_manifest_dead_tag(initialized_db):
    dead_tag = Tag.select().where(Tag.lifetime_end_ms <= get_epoch_timestamp_ms()).get()
    assert dead_tag.lifetime_end_ms <= get_epoch_timestamp_ms()

    assert lookup_manifest(dead_tag.repository, dead_tag.manifest.digest) is None
    assert (
        lookup_manifest(dead_tag.repository, dead_tag.manifest.digest, allow_dead=True)
        == dead_tag.manifest
    )


def create_manifest_for_testing(repository, differentiation_field="1"):
    # Populate a manifest.
    layer_json = json.dumps(
        {"config": {}, "rootfs": {"type": "layers", "diff_ids": []}, "history": [],}
    )

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    remote_digest = sha256_digest("something")
    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    builder.add_layer(remote_digest, 1234, urls=["http://hello/world" + differentiation_field])
    manifest = builder.build()

    created = get_or_create_manifest(repository, manifest, storage)
    assert created
    return created.manifest, manifest


def test_lookup_manifest_child_tag(initialized_db):
    repository = create_repository("devtable", "newrepo", None)
    manifest, manifest_impl = create_manifest_for_testing(repository)

    # Mark the hidden tag as dead.
    hidden_tag = Tag.get(manifest=manifest, hidden=True)
    hidden_tag.lifetime_end_ms = hidden_tag.lifetime_start_ms
    hidden_tag.save()

    # Ensure the manifest cannot currently be looked up, as it is not pointed to by an alive tag.
    assert lookup_manifest(repository, manifest.digest) is None
    assert lookup_manifest(repository, manifest.digest, allow_dead=True) is not None

    # Populate a manifest list.
    list_builder = DockerSchema2ManifestListBuilder()
    list_builder.add_manifest(manifest_impl, "amd64", "linux")
    manifest_list = list_builder.build()

    # Write the manifest list, which should also write the manifests themselves.
    created_tuple = get_or_create_manifest(repository, manifest_list, storage)
    assert created_tuple is not None

    # Since the manifests are not yet referenced by a tag, they cannot be found.
    assert lookup_manifest(repository, manifest.digest) is None
    assert lookup_manifest(repository, manifest_list.digest) is None

    # Unless we ask for "dead" manifests.
    assert lookup_manifest(repository, manifest.digest, allow_dead=True) is not None
    assert lookup_manifest(repository, manifest_list.digest, allow_dead=True) is not None


def _populate_blob(content):
    content = Bytes.for_string_or_unicode(content).as_encoded_str()
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = store_blob_record_and_temp_link(
        "devtable", "newrepo", digest, location, len(content), 120
    )
    storage.put_content(["local_us"], get_layer_path(blob), content)
    return blob, digest


@pytest.mark.parametrize("schema_version", [1, 2,])
def test_get_or_create_manifest(schema_version, initialized_db):
    repository = create_repository("devtable", "newrepo", None)

    expected_labels = {
        "Foo": "Bar",
        "Baz": "Meh",
    }

    layer_json = json.dumps(
        {
            "id": "somelegacyid",
            "config": {"Labels": expected_labels,},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    # Create a legacy image.
    find_create_or_link_image("somelegacyid", repository, "devtable", {}, "local_us")

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    # Add a blob of random data.
    random_data = "hello world"
    _, random_digest = _populate_blob(random_data)

    # Build the manifest.
    if schema_version == 1:
        builder = DockerSchema1ManifestBuilder("devtable", "simple", "anothertag")
        builder.add_layer(random_digest, layer_json)
        sample_manifest_instance = builder.build(docker_v2_signing_key)
    elif schema_version == 2:
        builder = DockerSchema2ManifestBuilder()
        builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
        builder.add_layer(random_digest, len(random_data.encode("utf-8")))
        sample_manifest_instance = builder.build()

    assert sample_manifest_instance.layers_compressed_size is not None

    # Create a new manifest.
    created_manifest = get_or_create_manifest(repository, sample_manifest_instance, storage)
    created = created_manifest.manifest
    newly_created = created_manifest.newly_created

    assert newly_created
    assert created is not None
    assert created.media_type.name == sample_manifest_instance.media_type
    assert created.digest == sample_manifest_instance.digest
    assert created.manifest_bytes == sample_manifest_instance.bytes.as_encoded_str()
    assert created_manifest.labels_to_apply == expected_labels
    assert created.config_media_type == sample_manifest_instance.config_media_type
    assert created.layers_compressed_size == sample_manifest_instance.layers_compressed_size

    # Lookup the manifest and verify.
    found = lookup_manifest(repository, created.digest, allow_dead=True)
    assert found.digest == created.digest
    assert found.config_media_type == created.config_media_type
    assert found.layers_compressed_size == created.layers_compressed_size

    # Verify it has a temporary tag pointing to it.
    assert Tag.get(manifest=created, hidden=True).lifetime_end_ms

    # Verify the linked blobs.
    blob_digests = [
        mb.blob.content_checksum
        for mb in ManifestBlob.select().where(ManifestBlob.manifest == created)
    ]

    assert random_digest in blob_digests
    if schema_version == 2:
        assert config_digest in blob_digests

    # Retrieve it again and ensure it is the same manifest.
    created_manifest2 = get_or_create_manifest(repository, sample_manifest_instance, storage)
    created2 = created_manifest2.manifest
    newly_created2 = created_manifest2.newly_created

    assert not newly_created2
    assert created2 == created

    # Ensure it again has a temporary tag.
    assert Tag.get(manifest=created2, hidden=True).lifetime_end_ms

    # Ensure the labels were added.
    labels = list(list_manifest_labels(created))
    assert len(labels) == 2

    labels_dict = {label.key: label.value for label in labels}
    assert labels_dict == expected_labels


def test_get_or_create_manifest_invalid_image(initialized_db):
    repository = get_repository("devtable", "simple")

    latest_tag = get_tag(repository, "latest")

    manifest_bytes = Bytes.for_string_or_unicode(latest_tag.manifest.manifest_bytes)
    parsed = parse_manifest_from_bytes(
        manifest_bytes, latest_tag.manifest.media_type.name, validate=False
    )

    builder = DockerSchema1ManifestBuilder("devtable", "simple", "anothertag")
    builder.add_layer(parsed.blob_digests[0], '{"id": "foo", "parent": "someinvalidimageid"}')
    sample_manifest_instance = builder.build(docker_v2_signing_key)

    created_manifest = get_or_create_manifest(repository, sample_manifest_instance, storage)
    assert created_manifest is None


def test_get_or_create_manifest_list(initialized_db):
    repository = create_repository("devtable", "newrepo", None)

    expected_labels = {
        "Foo": "Bar",
        "Baz": "Meh",
    }

    layer_json = json.dumps(
        {
            "id": "somelegacyid",
            "config": {"Labels": expected_labels,},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    # Create a legacy image.
    find_create_or_link_image("somelegacyid", repository, "devtable", {}, "local_us")

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    # Add a blob of random data.
    random_data = "hello world"
    _, random_digest = _populate_blob(random_data)

    # Build the manifests.
    v1_builder = DockerSchema1ManifestBuilder("devtable", "simple", "anothertag")
    v1_builder.add_layer(random_digest, layer_json)
    v1_manifest = v1_builder.build(docker_v2_signing_key).unsigned()

    v2_builder = DockerSchema2ManifestBuilder()
    v2_builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    v2_builder.add_layer(random_digest, len(random_data.encode("utf-8")))
    v2_manifest = v2_builder.build()

    # Write the manifests.
    v1_created = get_or_create_manifest(repository, v1_manifest, storage)
    assert v1_created
    assert v1_created.manifest.digest == v1_manifest.digest

    v2_created = get_or_create_manifest(repository, v2_manifest, storage)
    assert v2_created
    assert v2_created.manifest.digest == v2_manifest.digest

    # Build the manifest list.
    list_builder = DockerSchema2ManifestListBuilder()
    list_builder.add_manifest(v1_manifest, "amd64", "linux")
    list_builder.add_manifest(v2_manifest, "amd32", "linux")
    manifest_list = list_builder.build()

    # Write the manifest list, which should also write the manifests themselves.
    created_tuple = get_or_create_manifest(repository, manifest_list, storage)
    assert created_tuple is not None

    created_list = created_tuple.manifest
    assert created_list
    assert created_list.media_type.name == manifest_list.media_type
    assert created_list.digest == manifest_list.digest
    assert created_list.config_media_type == manifest_list.config_media_type
    assert created_list.layers_compressed_size == manifest_list.layers_compressed_size

    # Ensure the child manifest links exist.
    child_manifests = {
        cm.child_manifest.digest: cm.child_manifest
        for cm in ManifestChild.select().where(ManifestChild.manifest == created_list)
    }
    assert len(child_manifests) == 2
    assert v1_manifest.digest in child_manifests
    assert v2_manifest.digest in child_manifests

    assert child_manifests[v1_manifest.digest].media_type.name == v1_manifest.media_type
    assert child_manifests[v2_manifest.digest].media_type.name == v2_manifest.media_type


def test_get_or_create_manifest_list_duplicate_child_manifest(initialized_db):
    repository = create_repository("devtable", "newrepo", None)

    expected_labels = {
        "Foo": "Bar",
        "Baz": "Meh",
    }

    layer_json = json.dumps(
        {
            "id": "somelegacyid",
            "config": {"Labels": expected_labels,},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    # Create a legacy image.
    find_create_or_link_image("somelegacyid", repository, "devtable", {}, "local_us")

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    # Add a blob of random data.
    random_data = "hello world"
    _, random_digest = _populate_blob(random_data)

    # Build the manifest.
    v2_builder = DockerSchema2ManifestBuilder()
    v2_builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    v2_builder.add_layer(random_digest, len(random_data.encode("utf-8")))
    v2_manifest = v2_builder.build()

    # Write the manifest.
    v2_created = get_or_create_manifest(repository, v2_manifest, storage)
    assert v2_created
    assert v2_created.manifest.digest == v2_manifest.digest

    # Build the manifest list, with the child manifest repeated.
    list_builder = DockerSchema2ManifestListBuilder()
    list_builder.add_manifest(v2_manifest, "amd64", "linux")
    list_builder.add_manifest(v2_manifest, "amd32", "linux")
    manifest_list = list_builder.build()

    # Write the manifest list, which should also write the manifests themselves.
    created_tuple = get_or_create_manifest(repository, manifest_list, storage)
    assert created_tuple is not None

    created_list = created_tuple.manifest
    assert created_list
    assert created_list.media_type.name == manifest_list.media_type
    assert created_list.digest == manifest_list.digest

    # Ensure the child manifest links exist.
    child_manifests = {
        cm.child_manifest.digest: cm.child_manifest
        for cm in ManifestChild.select().where(ManifestChild.manifest == created_list)
    }
    assert len(child_manifests) == 1
    assert v2_manifest.digest in child_manifests
    assert child_manifests[v2_manifest.digest].media_type.name == v2_manifest.media_type

    # Try to create again and ensure we get back the same manifest list.
    created2_tuple = get_or_create_manifest(repository, manifest_list, storage)
    assert created2_tuple is not None
    assert created2_tuple.manifest == created_list


def test_get_or_create_manifest_with_remote_layers(initialized_db):
    repository = create_repository("devtable", "newrepo", None)

    layer_json = json.dumps(
        {
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    # Add a blob of random data.
    random_data = "hello world"
    _, random_digest = _populate_blob(random_data)

    remote_digest = sha256_digest(b"something")

    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    builder.add_layer(remote_digest, 1234, urls=["http://hello/world"])
    builder.add_layer(random_digest, len(random_data.encode("utf-8")))
    manifest = builder.build()

    assert remote_digest in manifest.blob_digests
    assert remote_digest not in manifest.local_blob_digests

    assert manifest.has_remote_layer
    assert not manifest.has_legacy_image
    assert manifest.get_schema1_manifest("foo", "bar", "baz", None) is None

    # Write the manifest.
    created_tuple = get_or_create_manifest(repository, manifest, storage)
    assert created_tuple is not None

    created_manifest = created_tuple.manifest
    assert created_manifest
    assert created_manifest.media_type.name == manifest.media_type
    assert created_manifest.digest == manifest.digest
    assert created_manifest.config_media_type == manifest.config_media_type
    assert created_manifest.layers_compressed_size == manifest.layers_compressed_size

    # Verify the legacy image.
    legacy_image = get_legacy_image_for_manifest(created_manifest)
    assert legacy_image is None

    # Verify the linked blobs.
    blob_digests = {
        mb.blob.content_checksum
        for mb in ManifestBlob.select().where(ManifestBlob.manifest == created_manifest)
    }

    assert random_digest in blob_digests
    assert config_digest in blob_digests
    assert remote_digest not in blob_digests


def create_manifest_for_testing(repository, differentiation_field="1", include_shared_blob=False):
    # Populate a manifest.
    layer_json = json.dumps(
        {"config": {}, "rootfs": {"type": "layers", "diff_ids": []}, "history": [],}
    )

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    remote_digest = sha256_digest(b"something")
    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    builder.add_layer(remote_digest, 1234, urls=["http://hello/world" + differentiation_field])

    if include_shared_blob:
        _, blob_digest = _populate_blob("some data here")
        builder.add_layer(blob_digest, 4567)

    manifest = builder.build()

    created = get_or_create_manifest(repository, manifest, storage)
    assert created
    return created.manifest, manifest


def test_retriever(initialized_db):
    repository = create_repository("devtable", "newrepo", None)

    layer_json = json.dumps(
        {
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    # Add a blob of random data.
    random_data = "hello world"
    _, random_digest = _populate_blob(random_data)

    # Add another blob of random data.
    other_random_data = "hi place"
    _, other_random_digest = _populate_blob(other_random_data)

    remote_digest = sha256_digest(b"something")

    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    builder.add_layer(other_random_digest, len(other_random_data.encode("utf-8")))
    builder.add_layer(random_digest, len(random_data.encode("utf-8")))
    manifest = builder.build()

    assert config_digest in manifest.blob_digests
    assert random_digest in manifest.blob_digests
    assert other_random_digest in manifest.blob_digests

    assert config_digest in manifest.local_blob_digests
    assert random_digest in manifest.local_blob_digests
    assert other_random_digest in manifest.local_blob_digests

    # Write the manifest.
    created_tuple = get_or_create_manifest(repository, manifest, storage)
    assert created_tuple is not None

    created_manifest = created_tuple.manifest
    assert created_manifest
    assert created_manifest.media_type.name == manifest.media_type
    assert created_manifest.digest == manifest.digest

    # Verify the linked blobs.
    blob_digests = {
        mb.blob.content_checksum
        for mb in ManifestBlob.select().where(ManifestBlob.manifest == created_manifest)
    }

    assert random_digest in blob_digests
    assert other_random_digest in blob_digests
    assert config_digest in blob_digests

    # Delete any Image rows linking to the blobs from temp tags.
    for blob_digest in blob_digests:
        storage_row = ImageStorage.get(content_checksum=blob_digest)
        for image in list(Image.select().where(Image.storage == storage_row)):
            all_temp = all(
                [rt.hidden for rt in RepositoryTag.select().where(RepositoryTag.image == image)]
            )
            if all_temp:
                RepositoryTag.delete().where(RepositoryTag.image == image).execute()
                image.delete_instance(recursive=True)

    # Verify the blobs in the retriever.
    retriever = RepositoryContentRetriever(repository, storage)
    assert (
        retriever.get_manifest_bytes_with_digest(created_manifest.digest)
        == manifest.bytes.as_encoded_str()
    )

    for blob_digest in blob_digests:
        assert retriever.get_blob_bytes_with_digest(blob_digest) is not None


class BrokenRetriever(ContentRetriever):
    def get_manifest_bytes_with_digest(self, digest):
        return None

    def get_blob_bytes_with_digest(self, digest):
        return None


def test_create_manifest_cannot_load_config_blob(initialized_db):
    repository = create_repository("devtable", "newrepo", None)

    layer_json = json.dumps(
        {
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    # Add a blob of random data.
    random_data = "hello world"
    _, random_digest = _populate_blob(random_data)

    remote_digest = sha256_digest(b"something")

    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    builder.add_layer(random_digest, len(random_data.encode("utf-8")))
    manifest = builder.build()

    broken_retriever = BrokenRetriever()

    # Write the manifest.
    with pytest.raises(CreateManifestException):
        get_or_create_manifest(
            repository, manifest, storage, retriever=broken_retriever, raise_on_error=True
        )
