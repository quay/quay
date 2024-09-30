import hashlib
import json
import random
import string
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time
from mock import patch
from playhouse.test_utils import assert_query_count

from app import docker_v2_signing_key, model_cache, storage
from data import database, model
from data.database import (
    ApprBlob,
    ExternalNotificationMethod,
    ImageStorage,
    ImageStorageLocation,
    Label,
    Manifest,
    ManifestBlob,
    ManifestLabel,
    Tag,
    TagNotificationSuccess,
    UploadedBlob,
)
from data.model.oci.test.test_oci_manifest import create_manifest_for_testing
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from digest.digest_tools import sha256_digest
from endpoints.api.repositorynotification_models_pre_oci import pre_oci_model
from image.docker.schema1 import DockerSchema1ManifestBuilder
from image.oci.config import OCIConfig
from image.oci.manifest import OCIManifestBuilder
from image.shared.schemas import parse_manifest_from_bytes
from test.fixtures import *
from test.helpers import check_transitive_modifications
from util.bytes import Bytes

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


def _delete_temp_links(repo):
    """Deletes any temp links to blobs."""
    UploadedBlob.delete().where(UploadedBlob.repository == repo).execute()


def _populate_blob(repo, content):
    assert isinstance(content, bytes)
    digest = sha256_digest(content)
    location = ImageStorageLocation.get(name="local_us")
    storage.put_content(["local_us"], storage.blob_path(digest), content)
    blob = model.blob.store_blob_record_and_temp_link_in_repo(
        repo, digest, location, len(content), 120
    )
    return blob, digest


def create_repository(namespace=ADMIN_ACCESS_USER, name=REPO, **kwargs):
    user = model.user.get_user(namespace)
    repo = model.repository.create_repository(namespace, name, user)

    # Populate the repository with the tags.
    for tag_name, image_ids in kwargs.items():
        move_tag(repo, tag_name, image_ids, expect_gc=False)

    return repo


def gc_now(repository):
    return model.gc.garbage_collect_repo(repository)


def delete_tag(repository, tag, perform_gc=True, expect_gc=True):
    repo_ref = RepositoryReference.for_repo_obj(repository)
    registry_model.delete_tag(model_cache, repo_ref, tag)
    if perform_gc:
        assert gc_now(repository) == expect_gc


def move_tag(repository, tag, image_ids, expect_gc=True):
    namespace = repository.namespace_user.username
    name = repository.name

    repo_ref = RepositoryReference.for_repo_obj(repository)
    builder = DockerSchema1ManifestBuilder(namespace, name, tag)
    builder = OCIManifestBuilder()

    def history_for_image(image):
        history = {
            "created": "2018-04-03T18:37:09.284840891Z",
            "created_by": (
                ("/bin/sh -c #(nop) ENTRYPOINT %s" % image.config["Entrypoint"])
                if image.config and image.config.get("Entrypoint")
                else "/bin/sh -c #(nop) %s" % image.id
            ),
        }

        if image.is_empty:
            history["empty_layer"] = True

        return history

    config = {
        "os": "linux",
        "architecture": "amd64",
        "rootfs": {"type": "layers", "diff_ids": []},
        "history": [history_for_image(image) for image in images],
    }

    config_json = json.dumps(config, ensure_ascii=options.ensure_ascii)
    oci_config = OCIConfig(Bytes.for_string_or_unicode(config_json))
    builder.set_config(oci_config)

    # NOTE: Building root to leaf.
    parent_id = None
    for image_id in image_ids:
        config = {
            "id": image_id,
            "config": {
                "Labels": {
                    "foo": "bar",
                    "meh": "grah",
                }
            },
        }

        if parent_id:
            config["parent"] = parent_id

        # Create a storage row for the layer blob.
        _, layer_blob_digest = _populate_blob(repository, image_id.encode("ascii"))

        builder.insert_layer(layer_blob_digest, json.dumps(config))

        parent_id = image_id

    # Store the manifest.
    manifest = builder.build(docker_v2_signing_key)
    registry_model.create_manifest_and_retarget_tag(
        repo_ref, manifest, tag, storage, raise_on_error=True
    )

    tag_ref = registry_model.get_repo_tag(repo_ref, tag)
    manifest_ref = registry_model.get_manifest_for_tag(tag_ref)

    if expect_gc:
        assert gc_now(repository) == expect_gc


def _get_dangling_storage_count():
    storage_ids = set([current.id for current in ImageStorage.select()])
    referenced_by_manifest = set([blob.blob_id for blob in ManifestBlob.select()])
    referenced_by_uploaded = set([upload.blob_id for upload in UploadedBlob.select()])
    return len(storage_ids - referenced_by_manifest - referenced_by_uploaded)


def _get_dangling_label_count():
    return len(_get_dangling_labels())


def _get_dangling_labels():
    label_ids = set([current.id for current in Label.select()])
    referenced_by_manifest = set([mlabel.label_id for mlabel in ManifestLabel.select()])
    return label_ids - referenced_by_manifest


def _get_dangling_manifest_count():
    manifest_ids = set([current.id for current in Manifest.select()])
    referenced_by_tag = set([tag.manifest_id for tag in Tag.select()])
    return len(manifest_ids - referenced_by_tag)


@contextmanager
def populate_storage_for_gc():
    """
    Populate FakeStorage with dummy data for each ImageStorage row.
    """
    preferred = storage.preferred_locations[0]
    for storage_row in ImageStorage.select():
        content = b"hello world"
        storage.put_content({preferred}, storage.blob_path(storage_row.content_checksum), content)
        assert storage.exists({preferred}, storage.blob_path(storage_row.content_checksum))

    yield


@contextmanager
def assert_gc_integrity(expect_storage_removed=True):
    """
    Specialized assertion for ensuring that GC cleans up all dangling storages and labels, invokes
    the callback for images removed and doesn't invoke the callback for images *not* removed.
    """

    # Add a callback for when images are removed.
    removed_image_storages = []
    remove_callback = model.config.register_image_cleanup_callback(removed_image_storages.extend)

    # Store existing storages. We won't verify these for existence because they
    # were likely created as test data.
    existing_digests = set()
    for storage_row in ImageStorage.select():
        if storage_row.cas_path:
            existing_digests.add(storage_row.content_checksum)

    for blob_row in ApprBlob.select():
        existing_digests.add(blob_row.digest)

    # Store the number of dangling objects.
    existing_storage_count = _get_dangling_storage_count()
    existing_label_count = _get_dangling_label_count()
    existing_manifest_count = _get_dangling_manifest_count()

    # Yield to the GC test.
    with check_transitive_modifications():
        try:
            yield
        finally:
            remove_callback()

    # Ensure the number of dangling storages, manifests and labels has not changed.
    updated_storage_count = _get_dangling_storage_count()
    assert updated_storage_count == existing_storage_count

    updated_label_count = _get_dangling_label_count()
    assert updated_label_count == existing_label_count, _get_dangling_labels()

    updated_manifest_count = _get_dangling_manifest_count()
    assert updated_manifest_count == existing_manifest_count

    # Ensure all CAS storage is in the storage engine.
    preferred = storage.preferred_locations[0]
    for storage_row in ImageStorage.select():
        if storage_row.content_checksum in existing_digests:
            continue

        if storage_row.cas_path:
            storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))

    for blob_row in ApprBlob.select():
        if blob_row.digest in existing_digests:
            continue

        storage.get_content({preferred}, storage.blob_path(blob_row.digest))

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
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest, built = create_manifest_for_testing(
        repo, differentiation_field="1", include_shared_blob=True
    )
    model.oci.tag.retarget_tag("latest", manifest)

    # Ensure that no repositories are returned by the has garbage check.
    assert model.oci.tag.find_repository_with_garbage(1000000000) is None

    # Delete a tag.
    delete_tag(repo, "latest", perform_gc=False)

    # There should still not be any repositories with garbage, due to time machine.
    assert model.oci.tag.find_repository_with_garbage(1000000000) is None

    # Change the time machine expiration on the namespace.
    (
        database.User.update(removed_tag_expiration_s=0)
        .where(database.User.username == ADMIN_ACCESS_USER)
        .execute()
    )

    # Now we should find the repository for GC.
    repository = model.oci.tag.find_repository_with_garbage(0)
    assert repository is not None
    assert repository.name == "newrepo"

    # GC the repository.
    assert gc_now(repository)

    # There should now be no repositories with garbage.
    assert model.oci.tag.find_repository_with_garbage(0) is None


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
    repo1 = model.repository.create_repository("devtable", "newrepo", None)
    manifest1, built1 = create_manifest_for_testing(
        repo1, differentiation_field="1", include_shared_blob=True
    )
    model.oci.tag.retarget_tag("tag1", manifest1)

    with assert_gc_integrity(expect_storage_removed=True):
        delete_tag(repo1, "tag1", expect_gc=True)


def test_two_tags_unshared_manifests(default_tag_policy, initialized_db):
    """
    Repository has two tags with no shared manifest between them.
    """
    repo1 = model.repository.create_repository("devtable", "newrepo", None)
    manifest1, built1 = create_manifest_for_testing(
        repo1, differentiation_field="1", include_shared_blob=True
    )
    manifest2, built2 = create_manifest_for_testing(
        repo1, differentiation_field="1", include_shared_blob=False
    )

    model.oci.tag.retarget_tag("tag1", manifest1)
    model.oci.tag.retarget_tag("tag2", manifest2)

    with assert_gc_integrity(expect_storage_removed=True):
        delete_tag(repo1, "tag1", expect_gc=True)

    # Ensure the blobs for manifest2 still all exist.
    preferred = storage.preferred_locations[0]
    for blob_digest in built2.local_blob_digests:
        storage_row = ImageStorage.get(content_checksum=blob_digest)

        assert storage_row.cas_path
        storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))


def test_two_tags_shared_manifest(default_tag_policy, initialized_db):
    """
    Repository has two tags with shared manifest.

    Deleting the tag should not remove the shared manifest.
    """
    repo1 = model.repository.create_repository("devtable", "newrepo", None)
    manifest1, built1 = create_manifest_for_testing(
        repo1, differentiation_field="1", include_shared_blob=True
    )

    model.oci.tag.retarget_tag("tag1", manifest1)
    model.oci.tag.retarget_tag("tag2", manifest1)

    with assert_gc_integrity(expect_storage_removed=False):
        delete_tag(repo1, "latest", expect_gc=False)

    preferred = storage.preferred_locations[0]
    for blob_digest in built1.local_blob_digests:
        storage_row = ImageStorage.get(content_checksum=blob_digest)

        assert storage_row.cas_path
        storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))


def test_multiple_shared_manifest(default_tag_policy, initialized_db):
    """
    Repository has multiple tags with shared manifests.

    Selectively deleting the tags, and verifying at each step.
    """
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest1, built1 = create_manifest_for_testing(
        repo, differentiation_field="1", include_shared_blob=True
    )
    manifest2, built2 = create_manifest_for_testing(
        repo, differentiation_field="2", include_shared_blob=True
    )
    manifest3, built3 = create_manifest_for_testing(
        repo, differentiation_field="3", include_shared_blob=False
    )

    assert set(built1.local_blob_digests).intersection(built2.local_blob_digests)
    assert built1.config.digest == built2.config.digest

    # Create tags pointing to the manifests.
    model.oci.tag.retarget_tag("tag1", manifest1)
    model.oci.tag.retarget_tag("tag2", manifest2)
    model.oci.tag.retarget_tag("tag3", manifest3)

    with assert_gc_integrity(expect_storage_removed=True):
        delete_tag(repo, "tag3", expect_gc=True)

    with assert_gc_integrity(expect_storage_removed=False):
        delete_tag(repo, "tag1", expect_gc=True)

    with assert_gc_integrity(expect_storage_removed=True):
        delete_tag(repo, "tag2", expect_gc=True)


def test_empty_gc(default_tag_policy, initialized_db):
    with assert_gc_integrity(expect_storage_removed=False):
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest1, built1 = create_manifest_for_testing(
            repo, differentiation_field="1", include_shared_blob=True
        )
        assert not gc_now(repo)


def test_time_machine_no_gc(default_tag_policy, initialized_db):
    """
    Repository has two tags with shared manfiest.

    Deleting the tags should not remove any images
    """
    with assert_gc_integrity(expect_storage_removed=False):
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest1, built1 = create_manifest_for_testing(
            repo, differentiation_field="1", include_shared_blob=True
        )
        model.oci.tag.retarget_tag("tag1", manifest1)
        model.oci.tag.retarget_tag("tag2", manifest1)

        _set_tag_expiration_policy(repo.namespace_user.username, 60 * 60 * 24)

        with assert_gc_integrity():
            delete_tag(repo, "tag1", expect_gc=False)

        with assert_gc_integrity():
            delete_tag(repo, "tag2", expect_gc=False)

        # Ensure the blobs for manifest1 still all exist.
        preferred = storage.preferred_locations[0]
        for blob_digest in built1.local_blob_digests:
            storage_row = ImageStorage.get(content_checksum=blob_digest)

            assert storage_row.cas_path
            storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))


def test_time_machine_gc(default_tag_policy, initialized_db):
    """
    Repository has two tags with shared images.

    Deleting the second tag should cause the images for the first deleted tag to gc.
    """
    now = datetime.utcnow()

    with assert_gc_integrity():
        with freeze_time(now):
            repo = model.repository.create_repository("devtable", "newrepo", None)
            manifest1, built1 = create_manifest_for_testing(
                repo, differentiation_field="1", include_shared_blob=True
            )
            model.oci.tag.retarget_tag("tag1", manifest1)

            _set_tag_expiration_policy(repo.namespace_user.username, 1)

            with assert_gc_integrity(expect_storage_removed=False):
                delete_tag(repo, "tag1", expect_gc=False)

            # Ensure the blobs for manifest1 still all exist.
            preferred = storage.preferred_locations[0]
            for blob_digest in built1.local_blob_digests:
                storage_row = ImageStorage.get(content_checksum=blob_digest)

                assert storage_row.cas_path
                storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))

        with freeze_time(now + timedelta(seconds=2)):
            with assert_gc_integrity(expect_storage_removed=True):
                delete_tag(repo, "tag1", expect_gc=True)


def test_manifest_with_tags(default_tag_policy, initialized_db):
    """
    A repository with two tags pointing to a manifest.

    Deleting and GCing one of the tag should not result in the storage and its CAS data being removed.
    """
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest1, built1 = create_manifest_for_testing(
        repo, differentiation_field="1", include_shared_blob=True
    )

    # Create tags pointing to the manifests.
    model.oci.tag.retarget_tag("tag1", manifest1)
    model.oci.tag.retarget_tag("tag2", manifest1)

    with assert_gc_integrity(expect_storage_removed=False):
        # Delete tag2.
        model.oci.tag.delete_tag(repo, "tag2")
        assert gc_now(repo)

    # Ensure the blobs for manifest1 still all exist.
    preferred = storage.preferred_locations[0]
    for blob_digest in built1.local_blob_digests:
        storage_row = ImageStorage.get(content_checksum=blob_digest)

        assert storage_row.cas_path
        storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))


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

    with assert_gc_integrity(expect_storage_removed=True):
        # Delete tag2.
        model.oci.tag.delete_tag(repo, "tag2")
        assert gc_now(repo)

    # Ensure the blobs for manifest1 still all exist.
    preferred = storage.preferred_locations[0]
    for blob_digest in built1.local_blob_digests:
        storage_row = ImageStorage.get(content_checksum=blob_digest)

        assert storage_row.cas_path
        storage.get_content({preferred}, storage.blob_path(storage_row.content_checksum))


def test_garbage_collect_storage(default_tag_policy, initialized_db):
    with populate_storage_for_gc():
        preferred = storage.preferred_locations[0]

        # Get a random sample of storages
        uploadedblobs = list(UploadedBlob.select())
        random_uploadedblobs = random.sample(
            uploadedblobs, random.randrange(1, len(uploadedblobs) + 1)
        )
        model.storage.garbage_collect_storage([b.blob.id for b in random_uploadedblobs])
        # Ensure that the blobs' storage weren't removed, since we didn't GC anything
        for uploadedblob in random_uploadedblobs:
            assert storage.exists(
                {preferred}, storage.blob_path(uploadedblob.blob.content_checksum)
            )


def test_purge_repository_storage_blob(default_tag_policy, initialized_db):
    with populate_storage_for_gc():
        expected_blobs_removed_from_storage = set()
        preferred = storage.preferred_locations[0]

        # Check that existing uploadedblobs has an object in storage
        for repo in database.Repository.select().order_by(database.Repository.id):
            for uploadedblob in UploadedBlob.select().where(UploadedBlob.repository == repo):
                assert storage.exists(
                    {preferred}, storage.blob_path(uploadedblob.blob.content_checksum)
                )

        # Remove eveyrhing
        for repo in database.Repository.select():  # .order_by(database.Repository.id):
            for uploadedblob in UploadedBlob.select().where(UploadedBlob.repository == repo):
                # Check if only this repository is referencing the uploadedblob
                # If so, the blob should be removed from storage
                has_depedent_manifestblob = (
                    ManifestBlob.select()
                    .where(
                        ManifestBlob.blob == uploadedblob.blob,
                        ManifestBlob.repository != repo,
                    )
                    .count()
                )
                has_dependent_uploadedblobs = (
                    UploadedBlob.select()
                    .where(
                        UploadedBlob == uploadedblob,
                        UploadedBlob.repository != repo,
                    )
                    .count()
                )

                if not has_depedent_manifestblob and not has_dependent_uploadedblobs:
                    expected_blobs_removed_from_storage.add(uploadedblob.blob)

            assert model.gc.purge_repository(repo, force=True)

        for removed_blob_from_storage in expected_blobs_removed_from_storage:
            assert not storage.exists(
                {preferred}, storage.blob_path(removed_blob_from_storage.content_checksum)
            )


def test_delete_manifests_with_subject(initialized_db):
    def generate_random_data_for_layer():
        charset = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return "".join(random.choice(charset) for _ in range(random.randrange(1, 20)))

    repository = create_repository("devtable", "newrepo")

    config1 = {
        "os": "linux",
        "architecture": "amd64",
        "rootfs": {"type": "layers", "diff_ids": []},
        "history": [],
    }
    config1_json = json.dumps(config1)
    _, config1_digest = _populate_blob(repository, config1_json.encode("ascii"))

    # Add a blob of random data.
    random_data1 = generate_random_data_for_layer()
    _, random_digest1 = _populate_blob(repository, random_data1.encode("ascii"))

    oci_builder1 = OCIManifestBuilder()
    oci_builder1.set_config_digest(config1_digest, len(config1_json.encode("utf-8")))
    oci_builder1.add_layer(random_digest1, len(random_data1.encode("utf-8")))
    oci_manifest1 = oci_builder1.build()

    # Manifest 2
    # Add a blob containing the config.
    config2 = {
        "os": "linux",
        "architecture": "amd64",
        "rootfs": {"type": "layers", "diff_ids": []},
        "history": [],
    }
    config2_json = json.dumps(config2)
    _, config2_digest = _populate_blob(repository, config2_json.encode("ascii"))

    # Add a blob of random data.
    random_data2 = generate_random_data_for_layer()
    _, random_digest2 = _populate_blob(repository, random_data1.encode("ascii"))

    oci_builder2 = OCIManifestBuilder()
    oci_builder2.set_config_digest(config2_digest, len(config2_json.encode("utf-8")))
    oci_builder2.add_layer(random_digest2, len(random_data2.encode("utf-8")))
    oci_builder2.set_subject(
        oci_manifest1.digest, len(oci_manifest1.bytes.as_encoded_str()), oci_manifest1.media_type
    )
    oci_manifest2 = oci_builder2.build()

    manifest1_created = model.oci.manifest.get_or_create_manifest(
        repository, oci_manifest1, storage
    )
    assert manifest1_created

    # Delete temp tags for GC check
    Tag.delete().where(Tag.manifest == manifest1_created.manifest.id).execute()

    # Subject does not have referrers yet
    assert not model.gc._check_manifest_used(manifest1_created.manifest.id)

    manifest2_created = model.oci.manifest.get_or_create_manifest(
        repository, oci_manifest2, storage
    )
    assert manifest2_created

    # Check that the "temp" tag won't expire for the referrer
    tag2 = Tag.select().where(Tag.manifest == manifest2_created.manifest.id).get()
    assert tag2.lifetime_end_ms is None

    assert model.gc._check_manifest_used(manifest1_created.manifest.id)

    # The referrer should also be considered in use even without a tag,
    # otherwise GC would delete a valid manifest referrer.
    # These are kept alive with a "non-temporary" hidden tag.
    # In order to clean these up, they need to be manually deleted for now.
    assert model.gc._check_manifest_used(manifest2_created.manifest.id)


def test_tag_cleanup_with_autoprune_policy(default_tag_policy, initialized_db):
    repo1 = model.repository.create_repository("devtable", "newrepo", None)
    slack = ExternalNotificationMethod.get(ExternalNotificationMethod.name == "slack")
    notification = pre_oci_model.create_repo_notification(
        namespace_name="devtable",
        repository_name="newrepo",
        event_name="repo_image_expiry",
        method_name=slack.name,
        method_config={"url": "http://example.com"},
        event_config={"days": 5},
        title="Image(s) will expire in 5 days",
    )
    notification = model.notification.get_repo_notification(notification.uuid)
    manifest1, built1 = create_manifest_for_testing(
        repo1, differentiation_field="1", include_shared_blob=True
    )
    model.oci.tag.retarget_tag("tag1", manifest1)
    tag = Tag.select().where(Tag.name == "tag1", Tag.manifest == manifest1.id).get()

    TagNotificationSuccess.create(notification=notification.id, tag=tag.id, method=slack.id)

    with assert_gc_integrity(expect_storage_removed=True):
        delete_tag(repo1, "tag1", expect_gc=True)

    tag_notification_count = (
        TagNotificationSuccess.select().where(TagNotificationSuccess.tag == tag.id).count()
    )
    assert tag_notification_count == 0
