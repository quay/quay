import hashlib

from contextlib import contextmanager

from app import storage, docker_v2_signing_key
from data import model, database
from data.registry_model import registry_model
from endpoints.v2.manifest import _write_manifest
from image.docker.schema1 import DockerSchema1ManifestBuilder

from test.fixtures import *


ADMIN_ACCESS_USER = "devtable"
REPO = "simple"
FIRST_TAG = "first"
SECOND_TAG = "second"
THIRD_TAG = "third"


@contextmanager
def set_tag_expiration_policy(namespace, expiration_s=0):
    namespace_user = model.user.get_user(namespace)
    model.user.change_user_tag_expiration(namespace_user, expiration_s)
    yield


def _perform_cleanup():
    database.RepositoryTag.delete().where(database.RepositoryTag.hidden == True).execute()
    repo_object = model.repository.get_repository(ADMIN_ACCESS_USER, REPO)
    model.gc.garbage_collect_repo(repo_object)


def test_missing_link(initialized_db):
    """
    Tests for a corner case that could result in missing a link to a blob referenced by a manifest.
    The test exercises the case as follows:

    1) Push a manifest of a single layer with a Docker ID `FIRST_ID`, pointing
        to blob `FIRST_BLOB`. The database should contain the tag referencing the layer, with
        no changed ID and the blob not being GCed.

    2) Push a manifest of two layers:

        Layer 1: `FIRST_ID` with blob `SECOND_BLOB`: Will result in a new synthesized ID
        Layer 2: `SECOND_ID` with blob `THIRD_BLOB`: Will result in `SECOND_ID` pointing to the
                `THIRD_BLOB`, with a parent pointing to the new synthesized ID's layer.

    3) Push a manifest of two layers:

        Layer 1: `THIRD_ID` with blob `FOURTH_BLOB`: Will result in a new `THIRD_ID` layer
        Layer 2: `FIRST_ID` with blob  `THIRD_BLOB`: Since `FIRST_ID` already points to `SECOND_BLOB`,
                this will synthesize a new ID. With the current bug, the synthesized ID will match
                that of `SECOND_ID`, leaving `THIRD_ID` unlinked and therefore, after a GC, missing
                `FOURTH_BLOB`.
    """
    with set_tag_expiration_policy("devtable", 0):
        location_name = storage.preferred_locations[0]
        location = database.ImageStorageLocation.get(name=location_name)

        # Create first blob.
        first_blob_sha = "sha256:" + hashlib.sha256(b"FIRST").hexdigest()
        model.blob.store_blob_record_and_temp_link(
            ADMIN_ACCESS_USER, REPO, first_blob_sha, location, 0, 0, 0
        )

        # Push the first manifest.
        first_manifest = (
            DockerSchema1ManifestBuilder(ADMIN_ACCESS_USER, REPO, FIRST_TAG)
            .add_layer(first_blob_sha, '{"id": "first"}')
            .build(docker_v2_signing_key)
        )

        _write_manifest(ADMIN_ACCESS_USER, REPO, FIRST_TAG, first_manifest)

        # Delete all temp tags and perform GC.
        _perform_cleanup()

        # Ensure that the first blob still exists, along with the first tag.
        assert (
            model.blob.get_repo_blob_by_digest(ADMIN_ACCESS_USER, REPO, first_blob_sha) is not None
        )

        repository_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, REPO)
        found_tag = registry_model.get_repo_tag(
            repository_ref, FIRST_TAG, include_legacy_image=True
        )
        assert found_tag is not None
        assert found_tag.legacy_image.docker_image_id == "first"

        # Create the second and third blobs.
        second_blob_sha = "sha256:" + hashlib.sha256(b"SECOND").hexdigest()
        third_blob_sha = "sha256:" + hashlib.sha256(b"THIRD").hexdigest()

        model.blob.store_blob_record_and_temp_link(
            ADMIN_ACCESS_USER, REPO, second_blob_sha, location, 0, 0, 0
        )
        model.blob.store_blob_record_and_temp_link(
            ADMIN_ACCESS_USER, REPO, third_blob_sha, location, 0, 0, 0
        )

        # Push the second manifest.
        second_manifest = (
            DockerSchema1ManifestBuilder(ADMIN_ACCESS_USER, REPO, SECOND_TAG)
            .add_layer(third_blob_sha, '{"id": "second", "parent": "first"}')
            .add_layer(second_blob_sha, '{"id": "first"}')
            .build(docker_v2_signing_key)
        )

        _write_manifest(ADMIN_ACCESS_USER, REPO, SECOND_TAG, second_manifest)

        # Delete all temp tags and perform GC.
        _perform_cleanup()

        # Ensure that the first and second blobs still exists, along with the second tag.
        assert registry_model.get_repo_blob_by_digest(repository_ref, first_blob_sha) is not None
        assert registry_model.get_repo_blob_by_digest(repository_ref, second_blob_sha) is not None
        assert registry_model.get_repo_blob_by_digest(repository_ref, third_blob_sha) is not None

        found_tag = registry_model.get_repo_tag(
            repository_ref, FIRST_TAG, include_legacy_image=True
        )
        assert found_tag is not None
        assert found_tag.legacy_image.docker_image_id == "first"

        # Ensure the IDs have changed.
        found_tag = registry_model.get_repo_tag(
            repository_ref, SECOND_TAG, include_legacy_image=True
        )
        assert found_tag is not None
        assert found_tag.legacy_image.docker_image_id != "second"

        # Create the fourth blob.
        fourth_blob_sha = "sha256:" + hashlib.sha256(b"FOURTH").hexdigest()
        model.blob.store_blob_record_and_temp_link(
            ADMIN_ACCESS_USER, REPO, fourth_blob_sha, location, 0, 0, 0
        )

        # Push the third manifest.
        third_manifest = (
            DockerSchema1ManifestBuilder(ADMIN_ACCESS_USER, REPO, THIRD_TAG)
            .add_layer(third_blob_sha, '{"id": "second", "parent": "first"}')
            .add_layer(
                fourth_blob_sha, '{"id": "first"}'
            )  # Note the change in BLOB from the second manifest.
            .build(docker_v2_signing_key)
        )

        _write_manifest(ADMIN_ACCESS_USER, REPO, THIRD_TAG, third_manifest)

        # Delete all temp tags and perform GC.
        _perform_cleanup()

        # Ensure all blobs are present.
        assert registry_model.get_repo_blob_by_digest(repository_ref, first_blob_sha) is not None
        assert registry_model.get_repo_blob_by_digest(repository_ref, second_blob_sha) is not None
        assert registry_model.get_repo_blob_by_digest(repository_ref, third_blob_sha) is not None
        assert registry_model.get_repo_blob_by_digest(repository_ref, fourth_blob_sha) is not None

        # Ensure new synthesized IDs were created.
        second_tag = registry_model.get_repo_tag(
            repository_ref, SECOND_TAG, include_legacy_image=True
        )
        third_tag = registry_model.get_repo_tag(
            repository_ref, THIRD_TAG, include_legacy_image=True
        )
        assert second_tag.legacy_image.docker_image_id != third_tag.legacy_image.docker_image_id
