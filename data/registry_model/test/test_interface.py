# -*- coding: utf-8 -*-

import hashlib
import json
import uuid

from datetime import datetime, timedelta
from io import BytesIO

import pytest

from mock import patch
from playhouse.test_utils import assert_query_count

from app import docker_v2_signing_key, storage
from data import model
from data.cache.test.test_cache import TEST_CACHE_CONFIG
from data.database import (
    TagManifestLabelMap,
    TagManifestToManifest,
    Manifest,
    ManifestBlob,
    ManifestLegacyImage,
    ManifestLabel,
    TagManifest,
    TagManifestLabel,
    DerivedStorageForImage,
    TorrentInfo,
    Tag,
    TagToRepositoryTag,
    ImageStorageLocation,
)
from data.cache.impl import InMemoryDataModelCache
from data.registry_model.registry_oci_model import OCIModel
from data.registry_model.datatypes import RepositoryReference
from data.registry_model.blobuploader import upload_blob, BlobUploadSettings
from data.model.blob import store_blob_record_and_temp_link
from image.shared.types import ManifestImageLayer
from image.docker.schema1 import (
    DockerSchema1ManifestBuilder,
    DOCKER_SCHEMA1_CONTENT_TYPES,
    DockerSchema1Manifest,
)
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from image.docker.schema2.list import DockerSchema2ManifestListBuilder
from util.bytes import Bytes

from test.fixtures import *


@pytest.fixture(
    params=[OCIModel(),]
)
def registry_model(request, initialized_db):
    return request.param


@pytest.fixture()
def oci_model(initialized_db):
    return OCIModel()


@pytest.mark.parametrize(
    "names, expected",
    [
        (["unknown"], None),
        (["latest"], {"latest"}),
        (["latest", "prod"], {"latest", "prod"}),
        (["latest", "prod", "another"], {"latest", "prod"}),
        (["foo", "prod"], {"prod"}),
    ],
)
def test_find_matching_tag(names, expected, registry_model):
    repo = model.repository.get_repository("devtable", "simple")
    repository_ref = RepositoryReference.for_repo_obj(repo)
    found = registry_model.find_matching_tag(repository_ref, names)
    if expected is None:
        assert found is None
    else:
        assert found.name in expected
        assert found.repository.namespace_name == "devtable"
        assert found.repository.name == "simple"


@pytest.mark.parametrize(
    "repo_namespace, repo_name, expected",
    [("devtable", "simple", {"latest", "prod"}), ("buynlarge", "orgrepo", {"latest", "prod"}),],
)
def test_get_most_recent_tag(repo_namespace, repo_name, expected, registry_model):
    repo = model.repository.get_repository(repo_namespace, repo_name)
    repository_ref = RepositoryReference.for_repo_obj(repo)
    found = registry_model.get_most_recent_tag(repository_ref)
    if expected is None:
        assert found is None
    else:
        assert found.name in expected


@pytest.mark.parametrize(
    "repo_namespace, repo_name, expected",
    [
        ("devtable", "simple", True),
        ("buynlarge", "orgrepo", True),
        ("buynlarge", "unknownrepo", False),
    ],
)
def test_lookup_repository(repo_namespace, repo_name, expected, registry_model):
    repo_ref = registry_model.lookup_repository(repo_namespace, repo_name)
    if expected:
        assert repo_ref
    else:
        assert repo_ref is None


@pytest.mark.parametrize(
    "repo_namespace, repo_name", [("devtable", "simple"), ("buynlarge", "orgrepo"),]
)
def test_lookup_manifests(repo_namespace, repo_name, registry_model):
    repo = model.repository.get_repository(repo_namespace, repo_name)
    repository_ref = RepositoryReference.for_repo_obj(repo)
    found_tag = registry_model.find_matching_tag(repository_ref, ["latest"])
    found_manifest = registry_model.get_manifest_for_tag(found_tag)
    found = registry_model.lookup_manifest_by_digest(
        repository_ref, found_manifest.digest, include_legacy_image=True
    )
    assert found._db_id == found_manifest._db_id
    assert found.digest == found_manifest.digest
    assert found.legacy_image
    assert found.legacy_image.parents

    schema1_parsed = registry_model.get_schema1_parsed_manifest(found, "foo", "bar", "baz", storage)
    assert schema1_parsed is not None


def test_lookup_unknown_manifest(registry_model):
    repo = model.repository.get_repository("devtable", "simple")
    repository_ref = RepositoryReference.for_repo_obj(repo)
    found = registry_model.lookup_manifest_by_digest(repository_ref, "sha256:deadbeef")
    assert found is None


def test_manifest_labels(registry_model):
    repo = model.repository.get_repository("devtable", "simple")
    repository_ref = RepositoryReference.for_repo_obj(repo)
    found_tag = registry_model.find_matching_tag(repository_ref, ["latest"])
    found_manifest = registry_model.get_manifest_for_tag(found_tag)

    # Create a new label.
    created = registry_model.create_manifest_label(found_manifest, "foo", "bar", "api")
    assert created.key == "foo"
    assert created.value == "bar"
    assert created.source_type_name == "api"
    assert created.media_type_name == "text/plain"

    # Ensure we can look it up.
    assert registry_model.get_manifest_label(found_manifest, created.uuid) == created

    # Ensure it is in our list of labels.
    assert created in registry_model.list_manifest_labels(found_manifest)
    assert created in registry_model.list_manifest_labels(found_manifest, key_prefix="fo")

    # Ensure it is *not* in our filtered list.
    assert created not in registry_model.list_manifest_labels(found_manifest, key_prefix="ba")

    # Delete the label and ensure it is gone.
    assert registry_model.delete_manifest_label(found_manifest, created.uuid)
    assert registry_model.get_manifest_label(found_manifest, created.uuid) is None
    assert created not in registry_model.list_manifest_labels(found_manifest)


def test_manifest_label_handlers(registry_model):
    repo = model.repository.get_repository("devtable", "simple")
    repository_ref = RepositoryReference.for_repo_obj(repo)
    found_tag = registry_model.get_repo_tag(repository_ref, "latest")
    found_manifest = registry_model.get_manifest_for_tag(found_tag)

    # Ensure the tag has no expiration.
    assert found_tag.lifetime_end_ts is None

    # Create a new label with an expires-after.
    registry_model.create_manifest_label(found_manifest, "quay.expires-after", "2h", "api")

    # Ensure the tag now has an expiration.
    updated_tag = registry_model.get_repo_tag(repository_ref, "latest")
    assert updated_tag.lifetime_end_ts == (updated_tag.lifetime_start_ts + (60 * 60 * 2))


def test_batch_labels(registry_model):
    repo = model.repository.get_repository("devtable", "history")
    repository_ref = RepositoryReference.for_repo_obj(repo)
    found_tag = registry_model.find_matching_tag(repository_ref, ["latest"])
    found_manifest = registry_model.get_manifest_for_tag(found_tag)

    with registry_model.batch_create_manifest_labels(found_manifest) as add_label:
        add_label("foo", "1", "api")
        add_label("bar", "2", "api")
        add_label("baz", "3", "api")

    # Ensure we can look them up.
    assert len(registry_model.list_manifest_labels(found_manifest)) == 3


@pytest.mark.parametrize(
    "repo_namespace, repo_name",
    [
        ("devtable", "simple"),
        ("devtable", "complex"),
        ("devtable", "history"),
        ("buynlarge", "orgrepo"),
    ],
)
def test_repository_tags(repo_namespace, repo_name, registry_model):
    repository_ref = registry_model.lookup_repository(repo_namespace, repo_name)
    tags = registry_model.list_all_active_repository_tags(
        repository_ref, include_legacy_images=True
    )
    assert len(tags)

    tags_map = registry_model.get_legacy_tags_map(repository_ref, storage)

    for tag in tags:
        found_tag = registry_model.get_repo_tag(repository_ref, tag.name, include_legacy_image=True)
        assert found_tag == tag

        if found_tag.legacy_image is None:
            continue

        found_image = registry_model.get_legacy_image(
            repository_ref, found_tag.legacy_image.docker_image_id
        )
        assert found_image == found_tag.legacy_image
        assert tag.name in tags_map
        assert tags_map[tag.name] == found_image.docker_image_id


@pytest.mark.parametrize(
    "namespace, name, expected_tag_count, has_expired",
    [
        ("devtable", "simple", 2, False),
        ("devtable", "history", 2, True),
        ("devtable", "gargantuan", 8, False),
        ("public", "publicrepo", 1, False),
    ],
)
def test_repository_tag_history(namespace, name, expected_tag_count, has_expired, registry_model):
    # Pre-cache media type loads to ensure consistent query count.
    Manifest.media_type.get_name(1)

    repository_ref = registry_model.lookup_repository(namespace, name)
    with assert_query_count(2):
        history, has_more = registry_model.list_repository_tag_history(repository_ref)
        assert not has_more
        assert len(history) == expected_tag_count

        for tag in history:
            # Retrieve the manifest to ensure it doesn't issue extra queries.
            tag.manifest

    if has_expired:
        # Ensure the latest tag is marked expired, since there is an expired one.
        with assert_query_count(1):
            assert registry_model.has_expired_tag(repository_ref, "latest")


def test_repository_tag_history_future_expires(registry_model):
    # Set the expiration of a tag to the future.
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    registry_model.change_repository_tag_expiration(tag, datetime.utcnow() + timedelta(days=7))

    # List the tag history and ensure the tag is returned with the correct expiration.
    history, has_more = registry_model.list_repository_tag_history(repository_ref)
    assert not has_more
    assert history

    for tag in history:
        if tag.name == "latest":
            assert tag.lifetime_end_ms is not None


@pytest.mark.parametrize(
    "repositories, expected_tag_count",
    [([], 0), ([("devtable", "simple"), ("devtable", "building")], 1),],
)
def test_get_most_recent_tag_lifetime_start(repositories, expected_tag_count, registry_model):
    last_modified_map = registry_model.get_most_recent_tag_lifetime_start(
        [registry_model.lookup_repository(name, namespace) for name, namespace in repositories]
    )

    assert len(last_modified_map) == expected_tag_count
    for repo_id, last_modified in last_modified_map.items():
        tag = registry_model.get_most_recent_tag(RepositoryReference.for_id(repo_id))
        assert last_modified == tag.lifetime_start_ms / 1000


@pytest.mark.parametrize(
    "repo_namespace, repo_name",
    [
        ("devtable", "simple"),
        ("devtable", "complex"),
        ("devtable", "history"),
        ("buynlarge", "orgrepo"),
    ],
)
@pytest.mark.parametrize("via_manifest", [False, True,])
def test_delete_tags(repo_namespace, repo_name, via_manifest, registry_model):
    repository_ref = registry_model.lookup_repository(repo_namespace, repo_name)
    tags = registry_model.list_all_active_repository_tags(repository_ref)
    assert len(tags)

    # Save history before the deletions.
    previous_history, _ = registry_model.list_repository_tag_history(repository_ref, size=1000)
    assert len(previous_history) >= len(tags)

    # Delete every tag in the repository.
    for tag in tags:
        if via_manifest:
            assert registry_model.delete_tag(repository_ref, tag.name)
        else:
            manifest = registry_model.get_manifest_for_tag(tag)
            if manifest is not None:
                registry_model.delete_tags_for_manifest(manifest)

        # Make sure the tag is no longer found.
        with assert_query_count(1):
            found_tag = registry_model.get_repo_tag(
                repository_ref, tag.name, include_legacy_image=True
            )
            assert found_tag is None

    # Ensure all tags have been deleted.
    tags = registry_model.list_all_active_repository_tags(repository_ref)
    assert not len(tags)

    # Ensure that the tags all live in history.
    history, _ = registry_model.list_repository_tag_history(repository_ref, size=1000)
    assert len(history) == len(previous_history)


@pytest.mark.parametrize("use_manifest", [True, False,])
def test_retarget_tag_history(use_manifest, registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "history")
    history, _ = registry_model.list_repository_tag_history(repository_ref)

    if use_manifest:
        manifest_or_legacy_image = registry_model.lookup_manifest_by_digest(
            repository_ref, history[0].manifest_digest, allow_dead=True
        )
    else:
        manifest_or_legacy_image = history[0].legacy_image

    # Retarget the tag.
    assert manifest_or_legacy_image
    updated_tag = registry_model.retarget_tag(
        repository_ref,
        "latest",
        manifest_or_legacy_image,
        storage,
        docker_v2_signing_key,
        is_reversion=True,
    )

    # Ensure the tag has changed targets.
    if use_manifest:
        assert updated_tag.manifest_digest == manifest_or_legacy_image.digest
    else:
        assert updated_tag.legacy_image == manifest_or_legacy_image

    # Ensure history has been updated.
    new_history, _ = registry_model.list_repository_tag_history(repository_ref)
    assert len(new_history) == len(history) + 1


def test_change_repository_tag_expiration(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    assert tag.lifetime_end_ts is None

    new_datetime = datetime.utcnow() + timedelta(days=2)
    previous, okay = registry_model.change_repository_tag_expiration(tag, new_datetime)

    assert okay
    assert previous is None

    tag = registry_model.get_repo_tag(repository_ref, "latest")
    assert tag.lifetime_end_ts is not None


def test_get_security_status(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tags = registry_model.list_all_active_repository_tags(
        repository_ref, include_legacy_images=True
    )
    assert len(tags)

    for tag in tags:
        assert registry_model.get_security_status(tag.legacy_image)
        registry_model.reset_security_status(tag.legacy_image)
        assert registry_model.get_security_status(tag.legacy_image)


@pytest.fixture()
def clear_rows(initialized_db):
    # Remove all new-style rows so we can backfill.
    TagToRepositoryTag.delete().execute()
    Tag.delete().execute()
    TagManifestLabelMap.delete().execute()
    ManifestLabel.delete().execute()
    ManifestBlob.delete().execute()
    ManifestLegacyImage.delete().execute()
    TagManifestToManifest.delete().execute()
    Manifest.delete().execute()
    TagManifestLabel.delete().execute()
    TagManifest.delete().execute()


@pytest.mark.parametrize(
    "namespace, expect_enabled", [("devtable", True), ("buynlarge", True), ("disabled", False),]
)
def test_is_namespace_enabled(namespace, expect_enabled, registry_model):
    assert registry_model.is_namespace_enabled(namespace) == expect_enabled


@pytest.mark.parametrize(
    "repo_namespace, repo_name",
    [
        ("devtable", "simple"),
        ("devtable", "complex"),
        ("devtable", "history"),
        ("buynlarge", "orgrepo"),
    ],
)
def test_layers_and_blobs(repo_namespace, repo_name, registry_model):
    repository_ref = registry_model.lookup_repository(repo_namespace, repo_name)
    tags = registry_model.list_all_active_repository_tags(repository_ref)
    assert tags

    for tag in tags:
        manifest = registry_model.get_manifest_for_tag(tag)
        assert manifest

        parsed = manifest.get_parsed_manifest()
        assert parsed

        layers = registry_model.list_parsed_manifest_layers(repository_ref, parsed, storage)
        assert layers

        layers = registry_model.list_parsed_manifest_layers(
            repository_ref, parsed, storage, include_placements=True
        )
        assert layers

        for index, manifest_layer in enumerate(layers):
            assert manifest_layer.blob.storage_path
            assert manifest_layer.blob.placements

            repo_blob = registry_model.get_repo_blob_by_digest(
                repository_ref, manifest_layer.blob.digest
            )
            assert repo_blob.digest == manifest_layer.blob.digest

            assert manifest_layer.estimated_size(1) is not None
            assert isinstance(manifest_layer.layer_info, ManifestImageLayer)

        blobs = registry_model.get_manifest_local_blobs(manifest, include_placements=True)
        assert {b.digest for b in blobs} == set(parsed.local_blob_digests)


def test_manifest_remote_layers(oci_model):
    # Create a config blob for testing.
    config_json = json.dumps(
        {
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    app_config = {"TESTING": True}
    repository_ref = oci_model.lookup_repository("devtable", "simple")
    with upload_blob(repository_ref, storage, BlobUploadSettings(500, 500, 500)) as upload:
        upload.upload_chunk(app_config, BytesIO(config_json))
        blob = upload.commit_to_blob(app_config)

    # Create the manifest in the repo.
    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(blob.digest, blob.compressed_size)
    builder.add_layer("sha256:abcd", 1234, urls=["http://hello/world"])
    manifest = builder.build()

    created_manifest, _ = oci_model.create_manifest_and_retarget_tag(
        repository_ref, manifest, "sometag", storage
    )
    assert created_manifest

    layers = oci_model.list_parsed_manifest_layers(
        repository_ref, created_manifest.get_parsed_manifest(), storage
    )
    assert len(layers) == 1
    assert layers[0].layer_info.is_remote
    assert layers[0].layer_info.urls == ["http://hello/world"]
    assert layers[0].blob is None


def test_derived_image(registry_model):
    # Clear all existing derived storage.
    DerivedStorageForImage.delete().execute()

    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    # Ensure the squashed image doesn't exist.
    assert registry_model.lookup_derived_image(manifest, "squash", storage, {}) is None

    # Create a new one.
    squashed = registry_model.lookup_or_create_derived_image(
        manifest, "squash", "local_us", storage, {}
    )
    assert (
        registry_model.lookup_or_create_derived_image(manifest, "squash", "local_us", storage, {})
        == squashed
    )
    assert squashed.unique_id

    # Check and set the size.
    assert squashed.blob.compressed_size is None
    registry_model.set_derived_image_size(squashed, 1234)

    found = registry_model.lookup_derived_image(manifest, "squash", storage, {})
    assert found.blob.compressed_size == 1234
    assert found.unique_id == squashed.unique_id

    # Ensure its returned now.
    assert found == squashed

    # Ensure different metadata results in a different derived image.
    found = registry_model.lookup_derived_image(manifest, "squash", storage, {"foo": "bar"})
    assert found is None

    squashed_foo = registry_model.lookup_or_create_derived_image(
        manifest, "squash", "local_us", storage, {"foo": "bar"}
    )
    assert squashed_foo != squashed

    found = registry_model.lookup_derived_image(manifest, "squash", storage, {"foo": "bar"})
    assert found == squashed_foo

    assert squashed.unique_id != squashed_foo.unique_id

    # Lookup with placements.
    squashed = registry_model.lookup_or_create_derived_image(
        manifest, "squash", "local_us", storage, {}, include_placements=True
    )
    assert squashed.blob.placements

    # Delete the derived image.
    registry_model.delete_derived_image(squashed)
    assert registry_model.lookup_derived_image(manifest, "squash", storage, {}) is None


def test_derived_image_signatures(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    derived = registry_model.lookup_or_create_derived_image(
        manifest, "squash", "local_us", storage, {}
    )
    assert derived

    registry_model.set_derived_image_signature(derived, "gpg2", "foo")
    assert registry_model.get_derived_image_signature(derived, "gpg2") == "foo"


def test_derived_image_for_manifest_list(oci_model):
    # Clear all existing derived storage.
    DerivedStorageForImage.delete().execute()

    # Create a config blob for testing.
    config_json = json.dumps(
        {
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {"created": "2018-04-03T18:37:09.284840891Z", "created_by": "do something",},
            ],
        }
    )

    app_config = {"TESTING": True}
    repository_ref = oci_model.lookup_repository("devtable", "simple")
    with upload_blob(repository_ref, storage, BlobUploadSettings(500, 500, 500)) as upload:
        upload.upload_chunk(app_config, BytesIO(config_json))
        blob = upload.commit_to_blob(app_config)

    # Create the manifest in the repo.
    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(blob.digest, blob.compressed_size)
    builder.add_layer(blob.digest, blob.compressed_size)
    amd64_manifest = builder.build()

    oci_model.create_manifest_and_retarget_tag(
        repository_ref, amd64_manifest, "submanifest", storage
    )

    # Create a manifest list, pointing to at least one amd64+linux manifest.
    builder = DockerSchema2ManifestListBuilder()
    builder.add_manifest(amd64_manifest, "amd64", "linux")
    manifestlist = builder.build()

    oci_model.create_manifest_and_retarget_tag(repository_ref, manifestlist, "listtag", storage)
    manifest = oci_model.get_manifest_for_tag(oci_model.get_repo_tag(repository_ref, "listtag"))
    assert manifest
    assert manifest.get_parsed_manifest().is_manifest_list

    # Ensure the squashed image doesn't exist.
    assert oci_model.lookup_derived_image(manifest, "squash", storage, {}) is None

    # Create a new one.
    squashed = oci_model.lookup_or_create_derived_image(manifest, "squash", "local_us", storage, {})
    assert squashed.unique_id
    assert (
        oci_model.lookup_or_create_derived_image(manifest, "squash", "local_us", storage, {})
        == squashed
    )

    # Perform lookup.
    assert oci_model.lookup_derived_image(manifest, "squash", storage, {}) == squashed


def test_torrent_info(registry_model):
    # Remove all existing info.
    TorrentInfo.delete().execute()

    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    blobs = registry_model.get_manifest_local_blobs(manifest)
    assert blobs

    assert registry_model.get_torrent_info(blobs[0]) is None
    registry_model.set_torrent_info(blobs[0], 2, "foo")

    # Set it again exactly, which should be a no-op.
    registry_model.set_torrent_info(blobs[0], 2, "foo")

    # Check the information we've set.
    torrent_info = registry_model.get_torrent_info(blobs[0])
    assert torrent_info is not None
    assert torrent_info.piece_length == 2
    assert torrent_info.pieces == "foo"

    # Try setting it again. Nothing should happen.
    registry_model.set_torrent_info(blobs[0], 3, "bar")

    torrent_info = registry_model.get_torrent_info(blobs[0])
    assert torrent_info is not None
    assert torrent_info.piece_length == 2
    assert torrent_info.pieces == "foo"


def test_blob_uploads(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")

    blob_upload = registry_model.create_blob_upload(
        repository_ref, str(uuid.uuid4()), "local_us", {"some": "metadata"}
    )
    assert blob_upload
    assert blob_upload.storage_metadata == {"some": "metadata"}
    assert blob_upload.location_name == "local_us"

    # Ensure we can find the blob upload.
    assert registry_model.lookup_blob_upload(repository_ref, blob_upload.upload_id) == blob_upload

    # Update and ensure the changes are saved.
    assert registry_model.update_blob_upload(
        blob_upload,
        1,
        "the-pieces_hash",
        blob_upload.piece_sha_state,
        {"new": "metadata"},
        2,
        3,
        blob_upload.sha_state,
    )

    updated = registry_model.lookup_blob_upload(repository_ref, blob_upload.upload_id)
    assert updated
    assert updated.uncompressed_byte_count == 1
    assert updated.piece_hashes == "the-pieces_hash"
    assert updated.storage_metadata == {"new": "metadata"}
    assert updated.byte_count == 2
    assert updated.chunk_count == 3

    # Delete the upload.
    registry_model.delete_blob_upload(blob_upload)

    # Ensure it can no longer be found.
    assert not registry_model.lookup_blob_upload(repository_ref, blob_upload.upload_id)


def test_commit_blob_upload(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    blob_upload = registry_model.create_blob_upload(
        repository_ref, str(uuid.uuid4()), "local_us", {"some": "metadata"}
    )

    # Commit the blob upload and make sure it is written as a blob.
    digest = "sha256:" + hashlib.sha256("hello").hexdigest()
    blob = registry_model.commit_blob_upload(blob_upload, digest, 60)
    assert blob.digest == digest

    # Ensure the upload can no longer be found.
    assert not registry_model.lookup_blob_upload(repository_ref, blob_upload.upload_id)


def test_mount_blob_into_repository(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    latest_tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(latest_tag)

    target_repository_ref = registry_model.lookup_repository("devtable", "complex")

    blobs = registry_model.get_manifest_local_blobs(manifest, include_placements=True)
    assert blobs

    for blob in blobs:
        # Ensure the blob doesn't exist under the repository.
        assert not registry_model.get_repo_blob_by_digest(target_repository_ref, blob.digest)

        # Mount the blob into the repository.
        assert registry_model.mount_blob_into_repository(blob, target_repository_ref, 60)

        # Ensure it now exists.
        found = registry_model.get_repo_blob_by_digest(target_repository_ref, blob.digest)
        assert found == blob


class SomeException(Exception):
    pass


def test_get_cached_repo_blob(registry_model):
    model_cache = InMemoryDataModelCache(TEST_CACHE_CONFIG)

    repository_ref = registry_model.lookup_repository("devtable", "simple")
    latest_tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(latest_tag)

    blobs = registry_model.get_manifest_local_blobs(manifest, include_placements=True)
    assert blobs

    blob = blobs[0]

    # Load a blob to add it to the cache.
    found = registry_model.get_cached_repo_blob(model_cache, "devtable", "simple", blob.digest)
    assert found.digest == blob.digest
    assert found.uuid == blob.uuid
    assert found.compressed_size == blob.compressed_size
    assert found.uncompressed_size == blob.uncompressed_size
    assert found.placements == blob.placements

    # Disconnect from the database by overwriting the connection.
    def fail(x, y):
        raise SomeException("Not connected!")

    with patch(
        "data.registry_model.registry_oci_model.model.oci.blob.get_repository_blob_by_digest", fail,
    ):
        # Make sure we can load again, which should hit the cache.
        cached = registry_model.get_cached_repo_blob(model_cache, "devtable", "simple", blob.digest)
        assert cached.digest == blob.digest
        assert cached.uuid == blob.uuid
        assert cached.compressed_size == blob.compressed_size
        assert cached.uncompressed_size == blob.uncompressed_size
        assert cached.placements == blob.placements

        # Try another blob, which should fail since the DB is not connected and the cache
        # does not contain the blob.
        with pytest.raises(SomeException):
            registry_model.get_cached_repo_blob(
                model_cache, "devtable", "simple", "some other digest"
            )


def test_create_manifest_and_retarget_tag(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    latest_tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(latest_tag).get_parsed_manifest()

    builder = DockerSchema1ManifestBuilder("devtable", "simple", "anothertag")
    builder.add_layer(
        manifest.blob_digests[0], '{"id": "%s"}' % latest_tag.legacy_image.docker_image_id
    )
    sample_manifest = builder.build(docker_v2_signing_key)
    assert sample_manifest is not None

    another_manifest, tag = registry_model.create_manifest_and_retarget_tag(
        repository_ref, sample_manifest, "anothertag", storage
    )
    assert another_manifest is not None
    assert tag is not None

    assert tag.name == "anothertag"
    assert another_manifest.get_parsed_manifest().manifest_dict == sample_manifest.manifest_dict


def test_get_schema1_parsed_manifest(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    latest_tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(latest_tag)
    assert registry_model.get_schema1_parsed_manifest(manifest, "", "", "", storage)


def test_convert_manifest(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    latest_tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(latest_tag)

    mediatypes = DOCKER_SCHEMA1_CONTENT_TYPES
    assert registry_model.convert_manifest(manifest, "", "", "", mediatypes, storage)

    mediatypes = []
    assert registry_model.convert_manifest(manifest, "", "", "", mediatypes, storage) is None


def test_create_manifest_and_retarget_tag_with_labels(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    latest_tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(latest_tag).get_parsed_manifest()

    json_metadata = {
        "id": latest_tag.legacy_image.docker_image_id,
        "config": {"Labels": {"quay.expires-after": "2w",},},
    }

    builder = DockerSchema1ManifestBuilder("devtable", "simple", "anothertag")
    builder.add_layer(manifest.blob_digests[0], json.dumps(json_metadata))
    sample_manifest = builder.build(docker_v2_signing_key)
    assert sample_manifest is not None

    another_manifest, tag = registry_model.create_manifest_and_retarget_tag(
        repository_ref, sample_manifest, "anothertag", storage
    )
    assert another_manifest is not None
    assert tag is not None

    assert tag.name == "anothertag"
    assert another_manifest.get_parsed_manifest().manifest_dict == sample_manifest.manifest_dict

    # Ensure the labels were applied.
    assert tag.lifetime_end_ms is not None


def _populate_blob(digest):
    location = ImageStorageLocation.get(name="local_us")
    store_blob_record_and_temp_link("devtable", "simple", digest, location, 1, 120)


def test_known_issue_schema1(registry_model):
    test_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(test_dir, "../../../image/docker/test/validate_manifest_known_issue.json")
    with open(path, "r") as f:
        manifest_bytes = f.read()

    manifest = DockerSchema1Manifest(Bytes.for_string_or_unicode(manifest_bytes))

    for blob_digest in manifest.local_blob_digests:
        _populate_blob(blob_digest)

    digest = manifest.digest
    assert digest == "sha256:44518f5a4d1cb5b7a6347763116fb6e10f6a8563b6c40bb389a0a982f0a9f47a"

    # Create the manifest in the database.
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    created_manifest, _ = registry_model.create_manifest_and_retarget_tag(
        repository_ref, manifest, "latest", storage
    )
    assert created_manifest
    assert created_manifest.digest == manifest.digest
    assert (
        created_manifest.internal_manifest_bytes.as_encoded_str() == manifest.bytes.as_encoded_str()
    )

    # Look it up again and validate.
    found = registry_model.lookup_manifest_by_digest(
        repository_ref, manifest.digest, allow_dead=True
    )
    assert found
    assert found.digest == digest
    assert found.internal_manifest_bytes.as_encoded_str() == manifest.bytes.as_encoded_str()
    assert found.get_parsed_manifest().digest == digest


def test_unicode_emoji(registry_model):
    builder = DockerSchema1ManifestBuilder("devtable", "simple", "latest")
    builder.add_layer(
        "sha256:abcde", json.dumps({"id": "someid", "author": u"😱",}, ensure_ascii=False)
    )

    manifest = builder.build(ensure_ascii=False)
    manifest._validate()

    for blob_digest in manifest.local_blob_digests:
        _populate_blob(blob_digest)

    # Create the manifest in the database.
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    created_manifest, _ = registry_model.create_manifest_and_retarget_tag(
        repository_ref, manifest, "latest", storage
    )
    assert created_manifest
    assert created_manifest.digest == manifest.digest
    assert (
        created_manifest.internal_manifest_bytes.as_encoded_str() == manifest.bytes.as_encoded_str()
    )

    # Look it up again and validate.
    found = registry_model.lookup_manifest_by_digest(
        repository_ref, manifest.digest, allow_dead=True
    )
    assert found
    assert found.digest == manifest.digest
    assert found.internal_manifest_bytes.as_encoded_str() == manifest.bytes.as_encoded_str()
    assert found.get_parsed_manifest().digest == manifest.digest


def test_lookup_active_repository_tags(oci_model):
    repository_ref = oci_model.lookup_repository("devtable", "simple")
    latest_tag = oci_model.get_repo_tag(repository_ref, "latest")
    manifest = oci_model.get_manifest_for_tag(latest_tag)

    tag_count = 500

    # Create a bunch of tags.
    tags_expected = set()
    for index in range(0, tag_count):
        tags_expected.add("somenewtag%s" % index)
        oci_model.retarget_tag(
            repository_ref, "somenewtag%s" % index, manifest, storage, docker_v2_signing_key
        )

    assert tags_expected

    # List the tags.
    tags_found = set()
    tag_id = None
    while True:
        if test_cached:
            model_cache = InMemoryDataModelCache(TEST_CACHE_CONFIG)
            tags = oci_model.lookup_cached_active_repository_tags(
                model_cache, repository_ref, tag_id, 11
            )
        else:
            tags = oci_model.lookup_active_repository_tags(repository_ref, tag_id, 11)

        assert len(tags) <= 11
        for tag in tags[0:10]:
            assert tag.name not in tags_found
            if tag.name in tags_expected:
                tags_found.add(tag.name)
                tags_expected.remove(tag.name)

        if len(tags) < 11:
            break

        tag_id = tags[10].id

    # Make sure we've found all the tags.
    assert tags_found
    assert not tags_expected


def test_yield_tags_for_vulnerability_notification(registry_model):
    repository_ref = registry_model.lookup_repository("devtable", "complex")

    # Check for all legacy images under the tags and ensure not raised because
    # no notification is yet registered.
    for tag in registry_model.list_all_active_repository_tags(
        repository_ref, include_legacy_images=True
    ):
        image = registry_model.get_legacy_image(
            repository_ref, tag.legacy_image.docker_image_id, include_blob=True
        )
        pairs = [(image.docker_image_id, image.blob.uuid)]
        results = list(registry_model.yield_tags_for_vulnerability_notification(pairs))
        assert not len(results)

    # Register a notification.
    model.notification.create_repo_notification(
        repository_ref.id, "vulnerability_found", "email", {}, {}
    )

    # Check again.
    for tag in registry_model.list_all_active_repository_tags(
        repository_ref, include_legacy_images=True
    ):
        image = registry_model.get_legacy_image(
            repository_ref,
            tag.legacy_image.docker_image_id,
            include_blob=True,
            include_parents=True,
        )

        # Check for every parent of the image.
        for current in image.parents:
            img = registry_model.get_legacy_image(
                repository_ref, current.docker_image_id, include_blob=True
            )
            pairs = [(img.docker_image_id, img.blob.uuid)]
            results = list(registry_model.yield_tags_for_vulnerability_notification(pairs))
            assert len(results) > 0
            assert tag.name in {t.name for t in results}

        # Check for the image itself.
        pairs = [(image.docker_image_id, image.blob.uuid)]
        results = list(registry_model.yield_tags_for_vulnerability_notification(pairs))
        assert len(results) > 0
        assert tag.name in {t.name for t in results}
