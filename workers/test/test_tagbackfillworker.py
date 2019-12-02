from app import docker_v2_signing_key
from data import model
from data.database import (
    TagManifestLabelMap,
    TagManifestToManifest,
    Manifest,
    ManifestBlob,
    ManifestLegacyImage,
    ManifestLabel,
    TagManifest,
    RepositoryTag,
    Image,
    TagManifestLabel,
    Tag,
    TagToRepositoryTag,
    Repository,
    ImageStorage,
)
from image.docker.schema1 import DockerSchema1ManifestBuilder
from workers.tagbackfillworker import backfill_tag, _backfill_manifest

from test.fixtures import *


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


@pytest.mark.parametrize("clear_all_rows", [True, False,])
def test_tagbackfillworker(clear_all_rows, initialized_db):
    # Remove the new-style rows so we can backfill.
    TagToRepositoryTag.delete().execute()
    Tag.delete().execute()

    if clear_all_rows:
        TagManifestLabelMap.delete().execute()
        ManifestLabel.delete().execute()
        ManifestBlob.delete().execute()
        ManifestLegacyImage.delete().execute()
        TagManifestToManifest.delete().execute()
        Manifest.delete().execute()

    found_dead_tag = False

    for repository_tag in list(RepositoryTag.select()):
        # Backfill the tag.
        assert backfill_tag(repository_tag)

        # Ensure if we try again, the backfill is skipped.
        assert not backfill_tag(repository_tag)

        # Ensure that we now have the expected tag rows.
        tag_to_repo_tag = TagToRepositoryTag.get(repository_tag=repository_tag)
        tag = tag_to_repo_tag.tag
        assert tag.name == repository_tag.name
        assert tag.repository == repository_tag.repository
        assert not tag.hidden
        assert tag.reversion == repository_tag.reversion

        if repository_tag.lifetime_start_ts is None:
            assert tag.lifetime_start_ms is None
        else:
            assert tag.lifetime_start_ms == (repository_tag.lifetime_start_ts * 1000)

        if repository_tag.lifetime_end_ts is None:
            assert tag.lifetime_end_ms is None
        else:
            assert tag.lifetime_end_ms == (repository_tag.lifetime_end_ts * 1000)
            found_dead_tag = True

        assert tag.manifest

        # Ensure that we now have the expected manifest rows.
        try:
            tag_manifest = TagManifest.get(tag=repository_tag)
        except TagManifest.DoesNotExist:
            continue

        map_row = TagManifestToManifest.get(tag_manifest=tag_manifest)
        assert not map_row.broken

        manifest_row = map_row.manifest
        assert manifest_row.manifest_bytes == tag_manifest.json_data
        assert manifest_row.digest == tag_manifest.digest
        assert manifest_row.repository == tag_manifest.tag.repository

        assert tag.manifest == map_row.manifest

        legacy_image = ManifestLegacyImage.get(manifest=manifest_row).image
        assert tag_manifest.tag.image == legacy_image

        expected_storages = {tag_manifest.tag.image.storage.id}
        for parent_image_id in tag_manifest.tag.image.ancestor_id_list():
            expected_storages.add(Image.get(id=parent_image_id).storage_id)

        found_storages = {
            manifest_blob.blob_id
            for manifest_blob in ManifestBlob.select().where(ManifestBlob.manifest == manifest_row)
        }
        assert expected_storages == found_storages

        # Ensure the labels were copied over.
        tmls = list(TagManifestLabel.select().where(TagManifestLabel.annotated == tag_manifest))
        expected_labels = {tml.label_id for tml in tmls}
        found_labels = {
            m.label_id for m in ManifestLabel.select().where(ManifestLabel.manifest == manifest_row)
        }
        assert found_labels == expected_labels

    # Verify at the repository level.
    for repository in list(Repository.select()):
        tags = RepositoryTag.select().where(
            RepositoryTag.repository == repository, RepositoryTag.hidden == False
        )
        oci_tags = Tag.select().where(Tag.repository == repository)
        assert len(tags) == len(oci_tags)
        assert {t.name for t in tags} == {t.name for t in oci_tags}

        for tag in tags:
            tag_manifest = TagManifest.get(tag=tag)
            ttr = TagToRepositoryTag.get(repository_tag=tag)
            manifest = ttr.tag.manifest

            assert tag_manifest.json_data == manifest.manifest_bytes
            assert tag_manifest.digest == manifest.digest
            assert tag.image == ManifestLegacyImage.get(manifest=manifest).image
            assert tag.lifetime_start_ts == (ttr.tag.lifetime_start_ms / 1000)

            if tag.lifetime_end_ts:
                assert tag.lifetime_end_ts == (ttr.tag.lifetime_end_ms / 1000)
            else:
                assert ttr.tag.lifetime_end_ms is None

    assert found_dead_tag


def test_manifestbackfillworker_broken_manifest(clear_rows, initialized_db):
    # Delete existing tag manifest so we can reuse the tag.
    TagManifestLabel.delete().execute()
    TagManifest.delete().execute()

    # Add a broken manifest.
    broken_manifest = TagManifest.create(
        json_data="wat?", digest="sha256:foobar", tag=RepositoryTag.get()
    )

    # Ensure the backfill works.
    assert _backfill_manifest(broken_manifest)

    # Ensure the mapping is marked as broken.
    map_row = TagManifestToManifest.get(tag_manifest=broken_manifest)
    assert map_row.broken

    manifest_row = map_row.manifest
    assert manifest_row.manifest_bytes == broken_manifest.json_data
    assert manifest_row.digest == broken_manifest.digest
    assert manifest_row.repository == broken_manifest.tag.repository

    legacy_image = ManifestLegacyImage.get(manifest=manifest_row).image
    assert broken_manifest.tag.image == legacy_image


def test_manifestbackfillworker_mislinked_manifest(clear_rows, initialized_db):
    """ Tests that a manifest whose image is mislinked will have its storages relinked properly. """
    # Delete existing tag manifest so we can reuse the tag.
    TagManifestLabel.delete().execute()
    TagManifest.delete().execute()

    repo = model.repository.get_repository("devtable", "complex")
    tag_v30 = model.tag.get_active_tag("devtable", "gargantuan", "v3.0")
    tag_v50 = model.tag.get_active_tag("devtable", "gargantuan", "v5.0")

    # Add a mislinked manifest, by having its layer point to a blob in v3.0 but its image
    # be the v5.0 image.
    builder = DockerSchema1ManifestBuilder("devtable", "gargantuan", "sometag")
    builder.add_layer(tag_v30.image.storage.content_checksum, '{"id": "foo"}')
    manifest = builder.build(docker_v2_signing_key)

    mislinked_manifest = TagManifest.create(
        json_data=manifest.bytes.as_encoded_str(), digest=manifest.digest, tag=tag_v50
    )

    # Backfill the manifest and ensure its proper content checksum was linked.
    assert _backfill_manifest(mislinked_manifest)

    map_row = TagManifestToManifest.get(tag_manifest=mislinked_manifest)
    assert not map_row.broken

    manifest_row = map_row.manifest
    legacy_image = ManifestLegacyImage.get(manifest=manifest_row).image
    assert legacy_image == tag_v50.image

    manifest_blobs = list(ManifestBlob.select().where(ManifestBlob.manifest == manifest_row))
    assert len(manifest_blobs) == 1
    assert manifest_blobs[0].blob.content_checksum == tag_v30.image.storage.content_checksum


def test_manifestbackfillworker_mislinked_invalid_manifest(clear_rows, initialized_db):
    """ Tests that a manifest whose image is mislinked will attempt to have its storages relinked
      properly. """
    # Delete existing tag manifest so we can reuse the tag.
    TagManifestLabel.delete().execute()
    TagManifest.delete().execute()

    repo = model.repository.get_repository("devtable", "complex")
    tag_v50 = model.tag.get_active_tag("devtable", "gargantuan", "v5.0")

    # Add a mislinked manifest, by having its layer point to an invalid blob but its image
    # be the v5.0 image.
    builder = DockerSchema1ManifestBuilder("devtable", "gargantuan", "sometag")
    builder.add_layer("sha256:deadbeef", '{"id": "foo"}')
    manifest = builder.build(docker_v2_signing_key)

    broken_manifest = TagManifest.create(
        json_data=manifest.bytes.as_encoded_str(), digest=manifest.digest, tag=tag_v50
    )

    # Backfill the manifest and ensure it is marked as broken.
    assert _backfill_manifest(broken_manifest)

    map_row = TagManifestToManifest.get(tag_manifest=broken_manifest)
    assert map_row.broken

    manifest_row = map_row.manifest
    legacy_image = ManifestLegacyImage.get(manifest=manifest_row).image
    assert legacy_image == tag_v50.image

    manifest_blobs = list(ManifestBlob.select().where(ManifestBlob.manifest == manifest_row))
    assert len(manifest_blobs) == 0


def test_manifestbackfillworker_repeat_digest(clear_rows, initialized_db):
    """ Tests that a manifest with a shared digest will be properly linked. """
    # Delete existing tag manifest so we can reuse the tag.
    TagManifestLabel.delete().execute()
    TagManifest.delete().execute()

    repo = model.repository.get_repository("devtable", "gargantuan")
    tag_v30 = model.tag.get_active_tag("devtable", "gargantuan", "v3.0")
    tag_v50 = model.tag.get_active_tag("devtable", "gargantuan", "v5.0")

    # Build a manifest and assign it to both tags (this is allowed in the old model).
    builder = DockerSchema1ManifestBuilder("devtable", "gargantuan", "sometag")
    builder.add_layer("sha256:deadbeef", '{"id": "foo"}')
    manifest = builder.build(docker_v2_signing_key)

    manifest_1 = TagManifest.create(
        json_data=manifest.bytes.as_encoded_str(), digest=manifest.digest, tag=tag_v30
    )
    manifest_2 = TagManifest.create(
        json_data=manifest.bytes.as_encoded_str(), digest=manifest.digest, tag=tag_v50
    )

    # Backfill "both" manifests and ensure both are pointed to by a single resulting row.
    assert _backfill_manifest(manifest_1)
    assert _backfill_manifest(manifest_2)

    map_row1 = TagManifestToManifest.get(tag_manifest=manifest_1)
    map_row2 = TagManifestToManifest.get(tag_manifest=manifest_2)

    assert map_row1.manifest == map_row2.manifest


def test_manifest_backfill_broken_tag(clear_rows, initialized_db):
    """ Tests backfilling a broken tag. """
    # Delete existing tag manifest so we can reuse the tag.
    TagManifestLabel.delete().execute()
    TagManifest.delete().execute()

    # Create a tag with an image referenced missing parent images.
    repo = model.repository.get_repository("devtable", "gargantuan")
    broken_image = Image.create(
        docker_image_id="foo",
        repository=repo,
        ancestors="/348723847234/",
        storage=ImageStorage.get(),
    )
    broken_image_tag = RepositoryTag.create(repository=repo, image=broken_image, name="broken")

    # Backfill the tag.
    assert backfill_tag(broken_image_tag)

    # Ensure we backfilled, even though we reference a broken manifest.
    tag_manifest = TagManifest.get(tag=broken_image_tag)

    map_row = TagManifestToManifest.get(tag_manifest=tag_manifest)
    manifest = map_row.manifest
    assert manifest.manifest_bytes == tag_manifest.json_data

    tag = TagToRepositoryTag.get(repository_tag=broken_image_tag).tag
    assert tag.name == "broken"
    assert tag.manifest == manifest
