import json

from datetime import datetime
from time import time

import pytest

from mock import patch

from app import docker_v2_signing_key
from data.database import (
    Image,
    RepositoryTag,
    ImageStorage,
    Repository,
    Manifest,
    ManifestBlob,
    ManifestLegacyImage,
    TagManifestToManifest,
    Tag,
    TagToRepositoryTag,
)
from data.model.repository import create_repository
from data.model.tag import (
    list_active_repo_tags,
    create_or_update_tag,
    delete_tag,
    get_matching_tags,
    _tag_alive,
    get_matching_tags_for_images,
    change_tag_expiration,
    get_active_tag,
    store_tag_manifest_for_testing,
    get_most_recent_tag,
    get_active_tag_for_repo,
    create_or_update_tag_for_repo,
    set_tag_end_ts,
)
from data.model.image import find_create_or_link_image
from image.docker.schema1 import DockerSchema1ManifestBuilder
from util.timedeltastring import convert_to_timedelta
from util.bytes import Bytes

from test.fixtures import *


def _get_expected_tags(image):
    expected_query = (
        RepositoryTag.select()
        .join(Image)
        .where(RepositoryTag.hidden == False)
        .where((Image.id == image.id) | (Image.ancestors ** ("%%/%s/%%" % image.id)))
    )
    return set([tag.id for tag in _tag_alive(expected_query)])


@pytest.mark.parametrize("max_subqueries,max_image_lookup_count", [(1, 1), (10, 10), (100, 500),])
def test_get_matching_tags(max_subqueries, max_image_lookup_count, initialized_db):
    with patch("data.model.tag._MAX_SUB_QUERIES", max_subqueries):
        with patch("data.model.tag._MAX_IMAGE_LOOKUP_COUNT", max_image_lookup_count):
            # Test for every image in the test database.
            for image in Image.select(Image, ImageStorage).join(ImageStorage):
                matching_query = get_matching_tags(image.docker_image_id, image.storage.uuid)
                matching_tags = set([tag.id for tag in matching_query])
                expected_tags = _get_expected_tags(image)
                assert matching_tags == expected_tags, "mismatch for image %s" % image.id

                oci_tags = list(
                    Tag.select()
                    .join(TagToRepositoryTag)
                    .where(TagToRepositoryTag.repository_tag << expected_tags)
                )
                assert len(oci_tags) == len(expected_tags)


@pytest.mark.parametrize("max_subqueries,max_image_lookup_count", [(1, 1), (10, 10), (100, 500),])
def test_get_matching_tag_ids_for_images(max_subqueries, max_image_lookup_count, initialized_db):
    with patch("data.model.tag._MAX_SUB_QUERIES", max_subqueries):
        with patch("data.model.tag._MAX_IMAGE_LOOKUP_COUNT", max_image_lookup_count):
            # Try for various sets of the first N images.
            for count in [5, 10, 15]:
                pairs = []
                expected_tags_ids = set()
                for image in Image.select(Image, ImageStorage).join(ImageStorage):
                    if len(pairs) >= count:
                        break

                    pairs.append((image.docker_image_id, image.storage.uuid))
                    expected_tags_ids.update(_get_expected_tags(image))

                matching_tags_ids = set([tag.id for tag in get_matching_tags_for_images(pairs)])
                assert matching_tags_ids == expected_tags_ids


@pytest.mark.parametrize("max_subqueries,max_image_lookup_count", [(1, 1), (10, 10), (100, 500),])
def test_get_matching_tag_ids_for_all_images(
    max_subqueries, max_image_lookup_count, initialized_db
):
    with patch("data.model.tag._MAX_SUB_QUERIES", max_subqueries):
        with patch("data.model.tag._MAX_IMAGE_LOOKUP_COUNT", max_image_lookup_count):
            pairs = []
            for image in Image.select(Image, ImageStorage).join(ImageStorage):
                pairs.append((image.docker_image_id, image.storage.uuid))

            expected_tags_ids = set([tag.id for tag in _tag_alive(RepositoryTag.select())])
            matching_tags_ids = set([tag.id for tag in get_matching_tags_for_images(pairs)])

            # Ensure every alive tag was found.
            assert matching_tags_ids == expected_tags_ids


def test_get_matching_tag_ids_images_filtered(initialized_db):
    def filter_query(query):
        return query.join(Repository).where(Repository.name == "simple")

    filtered_images = filter_query(
        Image.select(Image, ImageStorage)
        .join(RepositoryTag)
        .switch(Image)
        .join(ImageStorage)
        .switch(Image)
    )

    expected_tags_query = _tag_alive(filter_query(RepositoryTag.select()))

    pairs = []
    for image in filtered_images:
        pairs.append((image.docker_image_id, image.storage.uuid))

    matching_tags = get_matching_tags_for_images(
        pairs, filter_images=filter_query, filter_tags=filter_query
    )

    expected_tag_ids = set([tag.id for tag in expected_tags_query])
    matching_tags_ids = set([tag.id for tag in matching_tags])

    # Ensure every alive tag was found.
    assert matching_tags_ids == expected_tag_ids


def _get_oci_tag(tag):
    return (
        Tag.select().join(TagToRepositoryTag).where(TagToRepositoryTag.repository_tag == tag)
    ).get()


def assert_tags(repository, *args):
    tags = list(list_active_repo_tags(repository))
    assert len(tags) == len(args)

    tags_dict = {}
    for tag in tags:
        assert not tag.name in tags_dict
        assert not tag.hidden
        assert not tag.lifetime_end_ts or tag.lifetime_end_ts > time()

        tags_dict[tag.name] = tag

        oci_tag = _get_oci_tag(tag)
        assert oci_tag.name == tag.name
        assert not oci_tag.hidden
        assert oci_tag.reversion == tag.reversion

        if tag.lifetime_end_ts:
            assert oci_tag.lifetime_end_ms == (tag.lifetime_end_ts * 1000)
        else:
            assert oci_tag.lifetime_end_ms is None

    for expected in args:
        assert expected in tags_dict


def test_create_reversion_tag(initialized_db):
    repository = create_repository("devtable", "somenewrepo", None)
    manifest = Manifest.get()
    image1 = find_create_or_link_image("foobarimage1", repository, None, {}, "local_us")

    footag = create_or_update_tag_for_repo(
        repository, "foo", image1.docker_image_id, oci_manifest=manifest, reversion=True
    )
    assert footag.reversion

    oci_tag = _get_oci_tag(footag)
    assert oci_tag.name == footag.name
    assert not oci_tag.hidden
    assert oci_tag.reversion == footag.reversion


def test_list_active_tags(initialized_db):
    # Create a new repository.
    repository = create_repository("devtable", "somenewrepo", None)
    manifest = Manifest.get()

    # Create some images.
    image1 = find_create_or_link_image("foobarimage1", repository, None, {}, "local_us")
    image2 = find_create_or_link_image("foobarimage2", repository, None, {}, "local_us")

    # Make sure its tags list is empty.
    assert_tags(repository)

    # Add some new tags.
    footag = create_or_update_tag_for_repo(
        repository, "foo", image1.docker_image_id, oci_manifest=manifest
    )
    bartag = create_or_update_tag_for_repo(
        repository, "bar", image1.docker_image_id, oci_manifest=manifest
    )

    # Since timestamps are stored on a second-granularity, we need to make the tags "start"
    # before "now", so when we recreate them below, they don't conflict.
    footag.lifetime_start_ts -= 5
    footag.save()

    bartag.lifetime_start_ts -= 5
    bartag.save()

    footag_oci = _get_oci_tag(footag)
    footag_oci.lifetime_start_ms -= 5000
    footag_oci.save()

    bartag_oci = _get_oci_tag(bartag)
    bartag_oci.lifetime_start_ms -= 5000
    bartag_oci.save()

    # Make sure they are returned.
    assert_tags(repository, "foo", "bar")

    # Set the expirations to be explicitly empty.
    set_tag_end_ts(footag, None)
    set_tag_end_ts(bartag, None)

    # Make sure they are returned.
    assert_tags(repository, "foo", "bar")

    # Mark as a tag as expiring in the far future, and make sure it is still returned.
    set_tag_end_ts(footag, footag.lifetime_start_ts + 10000000)

    # Make sure they are returned.
    assert_tags(repository, "foo", "bar")

    # Delete a tag and make sure it isn't returned.
    footag = delete_tag("devtable", "somenewrepo", "foo")
    set_tag_end_ts(footag, footag.lifetime_end_ts - 4)

    assert_tags(repository, "bar")

    # Add a new foo again.
    footag = create_or_update_tag_for_repo(
        repository, "foo", image1.docker_image_id, oci_manifest=manifest
    )
    footag.lifetime_start_ts -= 3
    footag.save()

    footag_oci = _get_oci_tag(footag)
    footag_oci.lifetime_start_ms -= 3000
    footag_oci.save()

    assert_tags(repository, "foo", "bar")

    # Mark as a tag as expiring in the far future, and make sure it is still returned.
    set_tag_end_ts(footag, footag.lifetime_start_ts + 10000000)

    # Make sure they are returned.
    assert_tags(repository, "foo", "bar")

    # "Move" foo by updating it and make sure we don't get duplicates.
    create_or_update_tag_for_repo(repository, "foo", image2.docker_image_id, oci_manifest=manifest)
    assert_tags(repository, "foo", "bar")


@pytest.mark.parametrize(
    "expiration_offset, expected_offset",
    [(None, None), ("0s", "1h"), ("30m", "1h"), ("2h", "2h"), ("2w", "2w"), ("200w", "104w"),],
)
def test_change_tag_expiration(expiration_offset, expected_offset, initialized_db):
    repository = create_repository("devtable", "somenewrepo", None)
    image1 = find_create_or_link_image("foobarimage1", repository, None, {}, "local_us")

    manifest = Manifest.get()
    footag = create_or_update_tag_for_repo(
        repository, "foo", image1.docker_image_id, oci_manifest=manifest
    )

    expiration_date = None
    if expiration_offset is not None:
        expiration_date = datetime.utcnow() + convert_to_timedelta(expiration_offset)

    assert change_tag_expiration(footag, expiration_date)

    # Lookup the tag again.
    footag_updated = get_active_tag("devtable", "somenewrepo", "foo")
    oci_tag = _get_oci_tag(footag_updated)

    if expected_offset is None:
        assert footag_updated.lifetime_end_ts is None
        assert oci_tag.lifetime_end_ms is None
    else:
        start_date = datetime.utcfromtimestamp(footag_updated.lifetime_start_ts)
        end_date = datetime.utcfromtimestamp(footag_updated.lifetime_end_ts)
        expected_end_date = start_date + convert_to_timedelta(expected_offset)
        assert (expected_end_date - end_date).total_seconds() < 5  # variance in test

        assert oci_tag.lifetime_end_ms == (footag_updated.lifetime_end_ts * 1000)


def random_storages():
    return list(ImageStorage.select().where(~(ImageStorage.content_checksum >> None)).limit(10))


def repeated_storages():
    storages = list(ImageStorage.select().where(~(ImageStorage.content_checksum >> None)).limit(5))
    return storages + storages


@pytest.mark.parametrize("get_storages", [random_storages, repeated_storages,])
def test_store_tag_manifest(get_storages, initialized_db):
    # Create a manifest with some layers.
    builder = DockerSchema1ManifestBuilder("devtable", "simple", "sometag")

    storages = get_storages()
    assert storages

    repo = model.repository.get_repository("devtable", "simple")
    storage_id_map = {}
    for index, storage in enumerate(storages):
        image_id = "someimage%s" % index
        builder.add_layer(storage.content_checksum, json.dumps({"id": image_id}))
        find_create_or_link_image(image_id, repo, "devtable", {}, "local_us")
        storage_id_map[storage.content_checksum] = storage.id

    manifest = builder.build(docker_v2_signing_key)
    tag_manifest, _ = store_tag_manifest_for_testing(
        "devtable", "simple", "sometag", manifest, manifest.leaf_layer_v1_image_id, storage_id_map
    )

    # Ensure we have the new-model expected rows.
    mapping_row = TagManifestToManifest.get(tag_manifest=tag_manifest)
    manifest_bytes = Bytes.for_string_or_unicode(mapping_row.manifest.manifest_bytes).as_encoded_str()

    assert mapping_row.manifest is not None
    assert manifest_bytes == manifest.bytes.as_encoded_str()
    assert mapping_row.manifest.digest == str(manifest.digest)

    blob_rows = {
        m.blob_id
        for m in ManifestBlob.select().where(ManifestBlob.manifest == mapping_row.manifest)
    }
    assert blob_rows == {s.id for s in storages}

    assert ManifestLegacyImage.get(manifest=mapping_row.manifest).image == tag_manifest.tag.image


def test_get_most_recent_tag(initialized_db):
    # Create a hidden tag that is the most recent.
    repo = model.repository.get_repository("devtable", "simple")
    image = model.tag.get_tag_image("devtable", "simple", "latest")
    model.tag.create_temporary_hidden_tag(repo, image, 10000000)

    # Ensure we find a non-hidden tag.
    found = model.tag.get_most_recent_tag(repo)
    assert not found.hidden


def test_get_active_tag_for_repo(initialized_db):
    repo = model.repository.get_repository("devtable", "simple")
    image = model.tag.get_tag_image("devtable", "simple", "latest")
    hidden_tag = model.tag.create_temporary_hidden_tag(repo, image, 10000000)

    # Ensure get active tag for repo cannot find it.
    assert model.tag.get_active_tag_for_repo(repo, hidden_tag) is None
    assert model.tag.get_active_tag_for_repo(repo, "latest") is not None
