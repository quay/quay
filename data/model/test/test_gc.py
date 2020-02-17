import hashlib
import pytest

from datetime import datetime, timedelta

from mock import patch

from app import storage, docker_v2_signing_key

from contextlib import contextmanager
from playhouse.test_utils import assert_query_count

from freezegun import freeze_time

from data import model, database
from data.database import (
    Image,
    ImageStorage,
    DerivedStorageForImage,
    Label,
    TagManifestLabel,
    ApprBlob,
    Manifest,
    TagManifestToManifest,
    ManifestBlob,
    Tag,
    TagToRepositoryTag,
)
from data.model.oci.test.test_oci_manifest import create_manifest_for_testing
from image.docker.schema1 import DockerSchema1ManifestBuilder
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from image.docker.schemas import parse_manifest_from_bytes
from util.bytes import Bytes

from test.fixtures import *


ADMIN_ACCESS_USER = "devtable"
PUBLIC_USER = "public"

REPO = "somerepo"


def _set_tag_expiration_policy(namespace, expiration_s):
    namespace_user = model.user.get_user(namespace)
    model.user.change_user_tag_expiration(namespace_user, expiration_s)


@pytest.fixture()
def default_tag_policy(initialized_db):
    _set_tag_expiration_policy(ADMIN_ACCESS_USER, 0)
    _set_tag_expiration_policy(PUBLIC_USER, 0)


def create_image(docker_image_id, repository_obj, username):
    preferred = storage.preferred_locations[0]
    image = model.image.find_create_or_link_image(
        docker_image_id, repository_obj, username, {}, preferred
    )
    image.storage.uploading = False
    image.storage.save()

    # Create derived images as well.
    model.image.find_or_create_derived_storage(image, "squash", preferred)
    model.image.find_or_create_derived_storage(image, "aci", preferred)

    # Add some torrent info.
    try:
        database.TorrentInfo.get(storage=image.storage)
    except database.TorrentInfo.DoesNotExist:
        model.storage.save_torrent_info(image.storage, 1, b"helloworld")

    # Add some additional placements to the image.
    for location_name in ["local_eu"]:
        location = database.ImageStorageLocation.get(name=location_name)

        try:
            database.ImageStoragePlacement.get(location=location, storage=image.storage)
        except:
            continue

        database.ImageStoragePlacement.create(location=location, storage=image.storage)

    return image.storage


def store_tag_manifest(namespace, repo_name, tag_name, image_id):
    builder = DockerSchema1ManifestBuilder(namespace, repo_name, tag_name)
    storage_id_map = {}
    try:
        image_storage = ImageStorage.select().where(~(ImageStorage.content_checksum >> None)).get()
        builder.add_layer(image_storage.content_checksum, '{"id": "foo"}')
        storage_id_map[image_storage.content_checksum] = image_storage.id
    except ImageStorage.DoesNotExist:
        pass

    manifest = builder.build(docker_v2_signing_key)
    manifest_row, _ = model.tag.store_tag_manifest_for_testing(
        namespace, repo_name, tag_name, manifest, image_id, storage_id_map
    )
    return manifest_row


def create_repository(namespace=ADMIN_ACCESS_USER, name=REPO, **kwargs):
    user = model.user.get_user(namespace)
    repo = model.repository.create_repository(namespace, name, user)

    # Populate the repository with the tags.
    image_map = {}
    for tag_name in kwargs:
        image_ids = kwargs[tag_name]
        parent = None

        for image_id in image_ids:
            if not image_id in image_map:
                image_map[image_id] = create_image(image_id, repo, namespace)

            v1_metadata = {
                "id": image_id,
            }
            if parent is not None:
                v1_metadata["parent"] = parent.docker_image_id

            # Set the ancestors for the image.
            parent = model.image.set_image_metadata(
                image_id, namespace, name, "", "", "", v1_metadata, parent=parent
            )

        # Set the tag for the image.
        tag_manifest = store_tag_manifest(namespace, name, tag_name, image_ids[-1])

        # Add some labels to the tag.
        model.label.create_manifest_label(tag_manifest, "foo", "bar", "manifest")
        model.label.create_manifest_label(tag_manifest, "meh", "grah", "manifest")

    return repo


def gc_now(repository):
    assert model.gc.garbage_collect_repo(repository)


def delete_tag(repository, tag, perform_gc=True, expect_gc=True):
    model.tag.delete_tag(repository.namespace_user.username, repository.name, tag)
    if perform_gc:
        assert model.gc.garbage_collect_repo(repository) == expect_gc


def move_tag(repository, tag, docker_image_id, expect_gc=True):
    model.tag.create_or_update_tag(
        repository.namespace_user.username, repository.name, tag, docker_image_id
    )
    assert model.gc.garbage_collect_repo(repository) == expect_gc


def assert_not_deleted(repository, *args):
    for docker_image_id in args:
        assert model.image.get_image_by_id(
            repository.namespace_user.username, repository.name, docker_image_id
        )


def assert_deleted(repository, *args):
    for docker_image_id in args:
        try:
            # Verify the image is missing when accessed by the repository.
            model.image.get_image_by_id(
                repository.namespace_user.username, repository.name, docker_image_id
            )
        except model.DataModelException:
            return

        assert False, "Expected image %s to be deleted" % docker_image_id


def _get_dangling_storage_count():
    storage_ids = set([current.id for current in ImageStorage.select()])
    referenced_by_image = set([image.storage_id for image in Image.select()])
    referenced_by_manifest = set([blob.blob_id for blob in ManifestBlob.select()])
    referenced_by_derived = set(
        [derived.derivative_id for derived in DerivedStorageForImage.select()]
    )
    return len(storage_ids - referenced_by_image - referenced_by_derived - referenced_by_manifest)


def _get_dangling_label_count():
    return len(_get_dangling_labels())


def _get_dangling_labels():
    label_ids = set([current.id for current in Label.select()])
    referenced_by_manifest = set([mlabel.label_id for mlabel in TagManifestLabel.select()])
    return label_ids - referenced_by_manifest


def _get_dangling_manifest_count():
    manifest_ids = set([current.id for current in Manifest.select()])
    referenced_by_tag_manifest = set([tmt.manifest_id for tmt in TagManifestToManifest.select()])
    return len(manifest_ids - referenced_by_tag_manifest)


@contextmanager
def assert_gc_integrity(expect_storage_removed=True, check_oci_tags=True):
    """
    Specialized assertion for ensuring that GC cleans up all dangling storages and labels, invokes
    the callback for images removed and doesn't invoke the callback for images *not* removed.
    """
    # Add a callback for when images are removed.
    removed_image_storages = []
    model.config.register_image_cleanup_callback(removed_image_storages.extend)

    # Store the number of dangling storages and labels.
    existing_storage_count = _get_dangling_storage_count()
    existing_label_count = _get_dangling_label_count()
    existing_manifest_count = _get_dangling_manifest_count()
    yield

    # Ensure the number of dangling storages, manifests and labels has not changed.
    updated_storage_count = _get_dangling_storage_count()
    assert updated_storage_count == existing_storage_count

    updated_label_count = _get_dangling_label_count()
    assert updated_label_count == existing_label_count, _get_dangling_labels()

    updated_manifest_count = _get_dangling_manifest_count()
    assert updated_manifest_count == existing_manifest_count

    # Ensure that for each call to the image+storage cleanup callback, the image and its
    # storage is not found *anywhere* in the database.
    for removed_image_and_storage in removed_image_storages:
        with pytest.raises(Image.DoesNotExist):
            Image.get(id=removed_image_and_storage.id)

        # Ensure that image storages are only removed if not shared.
        shared = Image.select().where(Image.storage == removed_image_and_storage.storage_id).count()
        if shared == 0:
            shared = (
                ManifestBlob.select()
                .where(ManifestBlob.blob == removed_image_and_storage.storage_id)
                .count()
            )

        if shared == 0:
            with pytest.raises(ImageStorage.DoesNotExist):
                ImageStorage.get(id=removed_image_and_storage.storage_id)

            with pytest.raises(ImageStorage.DoesNotExist):
                ImageStorage.get(uuid=removed_image_and_storage.storage.uuid)

    # Ensure all CAS storage is in the storage engine.
    preferred = storage.preferred_locations[0]
    for storage_row in ImageStorage.select():
        if storage_row.cas_path:
            storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))

    for blob_row in ApprBlob.select():
        storage.get_content({preferred}, storage.blob_path(blob_row.digest))

    # Ensure there are no danglings OCI tags.
    if check_oci_tags:
        oci_tags = {t.id for t in Tag.select()}
        referenced_oci_tags = {t.tag_id for t in TagToRepositoryTag.select()}
        assert not oci_tags - referenced_oci_tags

    # Ensure all tags have valid manifests.
    for manifest in {t.manifest for t in Tag.select()}:
        # Ensure that the manifest's blobs all exist.
        found_blobs = {
            b.blob.content_checksum
            for b in ManifestBlob.select().where(ManifestBlob.manifest == manifest)
        }

        parsed = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(manifest.manifest_bytes), manifest.media_type.name
        )
        assert set(parsed.local_blob_digests) == found_blobs


def test_has_garbage(default_tag_policy, initialized_db):
    """
    Remove all existing repositories, then add one without garbage, check, then add one with
    garbage, and check again.
    """
    # Delete all existing repos.
    for repo in database.Repository.select().order_by(database.Repository.id):
        assert model.gc.purge_repository(repo, force=True)

    # Change the time machine expiration on the namespace.
    (
        database.User.update(removed_tag_expiration_s=1000000000)
        .where(database.User.username == ADMIN_ACCESS_USER)
        .execute()
    )

    # Create a repository without any garbage.
    repository = create_repository(latest=["i1", "i2", "i3"])

    # Ensure that no repositories are returned by the has garbage check.
    assert model.repository.find_repository_with_garbage(1000000000) is None

    # Delete a tag.
    delete_tag(repository, "latest", perform_gc=False)

    # There should still not be any repositories with garbage, due to time machine.
    assert model.repository.find_repository_with_garbage(1000000000) is None

    # Change the time machine expiration on the namespace.
    (
        database.User.update(removed_tag_expiration_s=0)
        .where(database.User.username == ADMIN_ACCESS_USER)
        .execute()
    )

    # Now we should find the repository for GC.
    repository = model.repository.find_repository_with_garbage(0)
    assert repository is not None
    assert repository.name == REPO

    # GC the repository.
    assert model.gc.garbage_collect_repo(repository)

    # There should now be no repositories with garbage.
    assert model.repository.find_repository_with_garbage(0) is None


def test_find_garbage_policy_functions(default_tag_policy, initialized_db):
    with assert_query_count(1):
        one_policy = model.repository.get_random_gc_policy()
        all_policies = model.repository._get_gc_expiration_policies()
        assert one_policy in all_policies


def test_one_tag(default_tag_policy, initialized_db):
    """
    Create a repository with a single tag, then remove that tag and verify that the repository is
    now empty.
    """
    with assert_gc_integrity():
        repository = create_repository(latest=["i1", "i2", "i3"])
        delete_tag(repository, "latest")
        assert_deleted(repository, "i1", "i2", "i3")


def test_two_tags_unshared_images(default_tag_policy, initialized_db):
    """
    Repository has two tags with no shared images between them.
    """
    with assert_gc_integrity():
        repository = create_repository(latest=["i1", "i2", "i3"], other=["f1", "f2"])
        delete_tag(repository, "latest")
        assert_deleted(repository, "i1", "i2", "i3")
        assert_not_deleted(repository, "f1", "f2")


def test_two_tags_shared_images(default_tag_policy, initialized_db):
    """
    Repository has two tags with shared images.

    Deleting the tag should only remove the unshared images.
    """
    with assert_gc_integrity():
        repository = create_repository(latest=["i1", "i2", "i3"], other=["i1", "f1"])
        delete_tag(repository, "latest")
        assert_deleted(repository, "i2", "i3")
        assert_not_deleted(repository, "i1", "f1")


def test_unrelated_repositories(default_tag_policy, initialized_db):
    """
    Two repositories with different images.

    Removing the tag from one leaves the other's images intact.
    """
    with assert_gc_integrity():
        repository1 = create_repository(latest=["i1", "i2", "i3"], name="repo1")
        repository2 = create_repository(latest=["j1", "j2", "j3"], name="repo2")

        delete_tag(repository1, "latest")

        assert_deleted(repository1, "i1", "i2", "i3")
        assert_not_deleted(repository2, "j1", "j2", "j3")


def test_related_repositories(default_tag_policy, initialized_db):
    """
    Two repositories with shared images.

    Removing the tag from one leaves the other's images intact.
    """
    with assert_gc_integrity():
        repository1 = create_repository(latest=["i1", "i2", "i3"], name="repo1")
        repository2 = create_repository(latest=["i1", "i2", "j1"], name="repo2")

        delete_tag(repository1, "latest")

        assert_deleted(repository1, "i3")
        assert_not_deleted(repository2, "i1", "i2", "j1")


def test_inaccessible_repositories(default_tag_policy, initialized_db):
    """
    Two repositories under different namespaces should result in the images being deleted but not
    completely removed from the database.
    """
    with assert_gc_integrity():
        repository1 = create_repository(namespace=ADMIN_ACCESS_USER, latest=["i1", "i2", "i3"])
        repository2 = create_repository(namespace=PUBLIC_USER, latest=["i1", "i2", "i3"])

        delete_tag(repository1, "latest")
        assert_deleted(repository1, "i1", "i2", "i3")
        assert_not_deleted(repository2, "i1", "i2", "i3")


def test_many_multiple_shared_images(default_tag_policy, initialized_db):
    """
    Repository has multiple tags with shared images.

    Delete all but one tag.
    """
    with assert_gc_integrity():
        repository = create_repository(
            latest=["i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "j0"],
            master=["i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "j1"],
        )

        # Delete tag latest. Should only delete j0, since it is not shared.
        delete_tag(repository, "latest")

        assert_deleted(repository, "j0")
        assert_not_deleted(repository, "i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "j1")

        # Delete tag master. Should delete the rest of the images.
        delete_tag(repository, "master")

        assert_deleted(repository, "i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "j1")


def test_multiple_shared_images(default_tag_policy, initialized_db):
    """
    Repository has multiple tags with shared images.

    Selectively deleting the tags, and verifying at each step.
    """
    with assert_gc_integrity():
        repository = create_repository(
            latest=["i1", "i2", "i3"],
            other=["i1", "f1", "f2"],
            third=["t1", "t2", "t3"],
            fourth=["i1", "f1"],
        )

        # Current state:
        # latest -> i3->i2->i1
        # other -> f2->f1->i1
        # third -> t3->t2->t1
        # fourth -> f1->i1

        # Delete tag other. Should delete f2, since it is not shared.
        delete_tag(repository, "other")
        assert_deleted(repository, "f2")
        assert_not_deleted(repository, "i1", "i2", "i3", "t1", "t2", "t3", "f1")

        # Current state:
        # latest -> i3->i2->i1
        # third -> t3->t2->t1
        # fourth -> f1->i1

        # Move tag fourth to i3. This should remove f1 since it is no longer referenced.
        move_tag(repository, "fourth", "i3")
        assert_deleted(repository, "f1")
        assert_not_deleted(repository, "i1", "i2", "i3", "t1", "t2", "t3")

        # Current state:
        # latest -> i3->i2->i1
        # third -> t3->t2->t1
        # fourth -> i3->i2->i1

        # Delete tag 'latest'. This should do nothing since fourth is on the same branch.
        delete_tag(repository, "latest")
        assert_not_deleted(repository, "i1", "i2", "i3", "t1", "t2", "t3")

        # Current state:
        # third -> t3->t2->t1
        # fourth -> i3->i2->i1

        # Delete tag 'third'. This should remove t1->t3.
        delete_tag(repository, "third")
        assert_deleted(repository, "t1", "t2", "t3")
        assert_not_deleted(repository, "i1", "i2", "i3")

        # Current state:
        # fourth -> i3->i2->i1

        # Add tag to i1.
        move_tag(repository, "newtag", "i1", expect_gc=False)
        assert_not_deleted(repository, "i1", "i2", "i3")

        # Current state:
        # fourth -> i3->i2->i1
        # newtag -> i1

        # Delete tag 'fourth'. This should remove i2 and i3.
        delete_tag(repository, "fourth")
        assert_deleted(repository, "i2", "i3")
        assert_not_deleted(repository, "i1")

        # Current state:
        # newtag -> i1

        # Delete tag 'newtag'. This should remove the remaining image.
        delete_tag(repository, "newtag")
        assert_deleted(repository, "i1")

        # Current state:
        # (Empty)


def test_empty_gc(default_tag_policy, initialized_db):
    with assert_gc_integrity(expect_storage_removed=False):
        repository = create_repository(
            latest=["i1", "i2", "i3"],
            other=["i1", "f1", "f2"],
            third=["t1", "t2", "t3"],
            fourth=["i1", "f1"],
        )

        assert not model.gc.garbage_collect_repo(repository)
        assert_not_deleted(repository, "i1", "i2", "i3", "t1", "t2", "t3", "f1", "f2")


def test_time_machine_no_gc(default_tag_policy, initialized_db):
    """
    Repository has two tags with shared images.

    Deleting the tag should not remove any images
    """
    with assert_gc_integrity(expect_storage_removed=False):
        repository = create_repository(latest=["i1", "i2", "i3"], other=["i1", "f1"])
        _set_tag_expiration_policy(repository.namespace_user.username, 60 * 60 * 24)

        delete_tag(repository, "latest", expect_gc=False)
        assert_not_deleted(repository, "i2", "i3")
        assert_not_deleted(repository, "i1", "f1")


def test_time_machine_gc(default_tag_policy, initialized_db):
    """
    Repository has two tags with shared images.

    Deleting the second tag should cause the images for the first deleted tag to gc.
    """
    now = datetime.utcnow()

    with assert_gc_integrity():
        with freeze_time(now):
            repository = create_repository(latest=["i1", "i2", "i3"], other=["i1", "f1"])

            _set_tag_expiration_policy(repository.namespace_user.username, 1)

            delete_tag(repository, "latest", expect_gc=False)
            assert_not_deleted(repository, "i2", "i3")
            assert_not_deleted(repository, "i1", "f1")

        with freeze_time(now + timedelta(seconds=2)):
            # This will cause the images associated with latest to gc
            delete_tag(repository, "other")
            assert_deleted(repository, "i2", "i3")
            assert_not_deleted(repository, "i1", "f1")


def test_images_shared_storage(default_tag_policy, initialized_db):
    """
    Repository with two tags, both with the same shared storage.

    Deleting the first tag should delete the first image, but *not* its storage.
    """
    with assert_gc_integrity(expect_storage_removed=False):
        repository = create_repository()

        # Add two tags, each with their own image, but with the same storage.
        image_storage = model.storage.create_v1_storage(storage.preferred_locations[0])

        first_image = Image.create(
            docker_image_id="i1", repository=repository, storage=image_storage, ancestors="/"
        )

        second_image = Image.create(
            docker_image_id="i2", repository=repository, storage=image_storage, ancestors="/"
        )

        store_tag_manifest(
            repository.namespace_user.username,
            repository.name,
            "first",
            first_image.docker_image_id,
        )

        store_tag_manifest(
            repository.namespace_user.username,
            repository.name,
            "second",
            second_image.docker_image_id,
        )

        # Delete the first tag.
        delete_tag(repository, "first")
        assert_deleted(repository, "i1")
        assert_not_deleted(repository, "i2")


def test_image_with_cas(default_tag_policy, initialized_db):
    """
    A repository with a tag pointing to an image backed by CAS.

    Deleting and GCing the tag should result in the storage and its CAS data being removed.
    """
    with assert_gc_integrity(expect_storage_removed=True):
        repository = create_repository()

        # Create an image storage record under CAS.
        content = b"hello world"
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        preferred = storage.preferred_locations[0]
        storage.put_content({preferred}, storage.blob_path(digest), content)

        image_storage = database.ImageStorage.create(content_checksum=digest, uploading=False)
        location = database.ImageStorageLocation.get(name=preferred)
        database.ImageStoragePlacement.create(location=location, storage=image_storage)

        # Ensure the CAS path exists.
        assert storage.exists({preferred}, storage.blob_path(digest))

        # Create the image and the tag.
        first_image = Image.create(
            docker_image_id="i1", repository=repository, storage=image_storage, ancestors="/"
        )

        store_tag_manifest(
            repository.namespace_user.username,
            repository.name,
            "first",
            first_image.docker_image_id,
        )

        assert_not_deleted(repository, "i1")

        # Delete the tag.
        delete_tag(repository, "first")
        assert_deleted(repository, "i1")

        # Ensure the CAS path is gone.
        assert not storage.exists({preferred}, storage.blob_path(digest))


def test_images_shared_cas(default_tag_policy, initialized_db):
    """
    A repository, each two tags, pointing to the same image, which has image storage with the same
    *CAS path*, but *distinct records*.

    Deleting the first tag should delete the first image, and its storage, but not the file in
    storage, as it shares its CAS path.
    """
    with assert_gc_integrity(expect_storage_removed=True):
        repository = create_repository()

        # Create two image storage records with the same content checksum.
        content = b"hello world"
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        preferred = storage.preferred_locations[0]
        storage.put_content({preferred}, storage.blob_path(digest), content)

        is1 = database.ImageStorage.create(content_checksum=digest, uploading=False)
        is2 = database.ImageStorage.create(content_checksum=digest, uploading=False)

        location = database.ImageStorageLocation.get(name=preferred)

        database.ImageStoragePlacement.create(location=location, storage=is1)
        database.ImageStoragePlacement.create(location=location, storage=is2)

        # Ensure the CAS path exists.
        assert storage.exists({preferred}, storage.blob_path(digest))

        # Create two images in the repository, and two tags, each pointing to one of the storages.
        first_image = Image.create(
            docker_image_id="i1", repository=repository, storage=is1, ancestors="/"
        )

        second_image = Image.create(
            docker_image_id="i2", repository=repository, storage=is2, ancestors="/"
        )

        store_tag_manifest(
            repository.namespace_user.username,
            repository.name,
            "first",
            first_image.docker_image_id,
        )

        store_tag_manifest(
            repository.namespace_user.username,
            repository.name,
            "second",
            second_image.docker_image_id,
        )

        assert_not_deleted(repository, "i1", "i2")

        # Delete the first tag.
        delete_tag(repository, "first")
        assert_deleted(repository, "i1")
        assert_not_deleted(repository, "i2")

        # Ensure the CAS path still exists.
        assert storage.exists({preferred}, storage.blob_path(digest))


def test_images_shared_cas_with_new_blob_table(default_tag_policy, initialized_db):
    """
    A repository with a tag and image that shares its CAS path with a record in the new Blob table.

    Deleting the first tag should delete the first image, and its storage, but not the file in
    storage, as it shares its CAS path with the blob row.
    """
    with assert_gc_integrity(expect_storage_removed=True):
        repository = create_repository()

        # Create two image storage records with the same content checksum.
        content = b"hello world"
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        preferred = storage.preferred_locations[0]
        storage.put_content({preferred}, storage.blob_path(digest), content)

        media_type = database.MediaType.get(name="text/plain")

        is1 = database.ImageStorage.create(content_checksum=digest, uploading=False)
        database.ApprBlob.create(digest=digest, size=0, media_type=media_type)

        location = database.ImageStorageLocation.get(name=preferred)
        database.ImageStoragePlacement.create(location=location, storage=is1)

        # Ensure the CAS path exists.
        assert storage.exists({preferred}, storage.blob_path(digest))

        # Create the image in the repository, and the tag.
        first_image = Image.create(
            docker_image_id="i1", repository=repository, storage=is1, ancestors="/"
        )

        store_tag_manifest(
            repository.namespace_user.username,
            repository.name,
            "first",
            first_image.docker_image_id,
        )

        assert_not_deleted(repository, "i1")

        # Delete the tag.
        delete_tag(repository, "first")
        assert_deleted(repository, "i1")

        # Ensure the CAS path still exists, as it is referenced by the Blob table
        assert storage.exists({preferred}, storage.blob_path(digest))


def test_super_long_image_chain_gc(app, default_tag_policy):
    """
    Test that a super long chain of images all gets properly GCed.
    """
    with assert_gc_integrity():
        images = ["i%s" % i for i in range(0, 100)]
        repository = create_repository(latest=images)
        delete_tag(repository, "latest")

        # Ensure the repository is now empty.
        assert_deleted(repository, *images)


def test_manifest_v2_shared_config_and_blobs(app, default_tag_policy):
    """
    Test that GCing a tag that refers to a V2 manifest with the same config and some shared blobs as
    another manifest ensures that the config blob and shared blob are NOT GCed.
    """
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest1, built1 = create_manifest_for_testing(
        repo, differentiation_field="1", include_shared_blob=True
    )
    manifest2, built2 = create_manifest_for_testing(
        repo, differentiation_field="2", include_shared_blob=True
    )

    assert set(built1.local_blob_digests).intersection(built2.local_blob_digests)
    assert built1.config.digest == built2.config.digest

    # Create tags pointing to the manifests.
    model.oci.tag.retarget_tag("tag1", manifest1)
    model.oci.tag.retarget_tag("tag2", manifest2)

    with assert_gc_integrity(expect_storage_removed=True, check_oci_tags=False):
        # Delete tag2.
        model.oci.tag.delete_tag(repo, "tag2")
        assert model.gc.garbage_collect_repo(repo)

    # Ensure the blobs for manifest1 still all exist.
    preferred = storage.preferred_locations[0]
    for blob_digest in built1.local_blob_digests:
        storage_row = ImageStorage.get(content_checksum=blob_digest)

        assert storage_row.cas_path
        storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))
