import json
from calendar import timegm
from datetime import datetime, timedelta

import pytest
from mock import MagicMock, patch
from playhouse.test_utils import assert_query_count

from app import storage
from data import model
from data.database import ImageStorageLocation, ManifestChild, Repository, Tag, User
from data.model import ImmutableTagException
from data.model.blob import store_blob_record_and_temp_link
from data.model.oci.manifest import get_or_create_manifest
from data.model.oci.tag import (
    change_tag_expiration,
    create_temporary_tag_if_necessary,
    create_temporary_tag_outside_timemachine,
    delete_tag,
    delete_tags_for_manifest,
    filter_to_alive_tags,
    filter_to_visible_tags,
    find_matching_tag,
    get_child_manifests,
    get_current_tag,
    get_epoch_timestamp_ms,
    get_expired_tag,
    get_most_recent_tag,
    get_most_recent_tag_lifetime_start,
    get_tag,
    get_tag_by_manifest_id,
    is_tag_immutable,
    list_alive_tags,
    list_repository_tag_history,
    lookup_alive_tags_shallow,
    lookup_unrecoverable_tags,
    remove_tag_from_timemachine,
    retarget_tag,
    set_tag_expiration_for_manifest,
    set_tag_immutable,
    set_tags_immutability_for_manifest,
)
from data.model.oci.test.test_oci_manifest import create_manifest_for_testing
from data.model.repository import create_repository, get_repository
from data.model.storage import get_layer_path
from data.model.user import get_user
from digest.digest_tools import sha256_digest
from image.docker.schema2.list import DockerSchema2ManifestListBuilder
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from test.fixtures import *
from util.bytes import Bytes


def _populate_blob(content):
    content = Bytes.for_string_or_unicode(content).as_encoded_str()
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = store_blob_record_and_temp_link(
        "devtable", "newrepo", digest, location, len(content), 120
    )
    storage.put_content(["local_us"], get_layer_path(blob), content)
    return blob, digest


@pytest.mark.parametrize(
    "namespace_name, repo_name, tag_names, expected",
    [
        ("devtable", "simple", ["latest"], "latest"),
        ("devtable", "simple", ["unknown", "latest"], "latest"),
        ("devtable", "simple", ["unknown"], None),
    ],
)
def test_find_matching_tag(namespace_name, repo_name, tag_names, expected, initialized_db):
    repo = get_repository(namespace_name, repo_name)
    if expected is not None:
        with assert_query_count(1):
            found = find_matching_tag(repo, tag_names)

        assert found is not None
        assert found.name == expected
        assert not found.lifetime_end_ms
    else:
        with assert_query_count(1):
            assert find_matching_tag(repo, tag_names) is None


def test_get_most_recent_tag_lifetime_start(initialized_db):
    repo = get_repository("devtable", "simple")
    tag = get_most_recent_tag(repo)

    with assert_query_count(1):
        tags = get_most_recent_tag_lifetime_start([repo])
        assert tags[repo.id] == tag.lifetime_start_ms

    no_tags = get_most_recent_tag_lifetime_start([])
    assert isinstance(no_tags, dict) and len(no_tags) == 0


def test_get_most_recent_tag(initialized_db):
    repo = get_repository("outsideorg", "coolrepo")

    with assert_query_count(1):
        assert get_most_recent_tag(repo).name == "latest"


def test_get_most_recent_tag_empty_repo(initialized_db):
    empty_repo = create_repository("devtable", "empty", None)

    with assert_query_count(1):
        assert get_most_recent_tag(empty_repo) is None


def test_list_alive_tags(initialized_db):
    found = False
    for tag in filter_to_visible_tags(filter_to_alive_tags(Tag.select())):
        tags = list_alive_tags(tag.repository)
        assert tag in tags
        found = True

    assert found

    # Ensure hidden tags cannot be listed.
    tag = Tag.get()
    tag.hidden = True
    tag.save()

    tags = list_alive_tags(tag.repository)
    assert tag not in tags


def test_lookup_alive_tags_shallow(initialized_db):
    found = False
    for tag in filter_to_visible_tags(filter_to_alive_tags(Tag.select())):
        tags, _ = lookup_alive_tags_shallow(tag.repository)
        found = True
        assert tag in tags

    assert found

    # Ensure hidden tags cannot be listed.
    tag = Tag.get()
    tag.hidden = True
    tag.save()

    tags, _ = lookup_alive_tags_shallow(tag.repository)
    assert tag not in tags


def test_get_tag(initialized_db):
    found = False
    for tag in filter_to_visible_tags(filter_to_alive_tags(Tag.select())):
        repo = tag.repository

        with assert_query_count(1):
            assert get_tag(repo, tag.name) == tag
        found = True

    assert found


def test_get_tag_by_manifest_id_tag_doesnt_exist(initialized_db):
    tag = get_tag_by_manifest_id(1111, 9999)
    assert tag is None


def test_get_tag_by_manifest_id_valid_tag(initialized_db):
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest, _ = create_manifest_for_testing(repo, "1")
    tag = get_tag_by_manifest_id(repo.id, manifest.id)
    assert tag is not None


def test_get_tag_by_manifest_id_expired_tag(initialized_db):
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest, _ = create_manifest_for_testing(repo, "1")
    before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
    count = (
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        )
        .where(Tag.manifest == manifest.id)
        .execute()
    )
    assert count == 1
    tag = get_tag_by_manifest_id(repo.id, manifest.id)
    assert tag is not None


def test_get_tag_by_manifest_id_multiple_tags_returns_latest(initialized_db):
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest, _ = create_manifest_for_testing(repo, "1")
    before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
    count = (
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        )
        .where(Tag.manifest == manifest.id)
        .execute()
    )
    assert count == 1
    expired_tag = get_tag_by_manifest_id(repo.id, manifest.id)
    new_tag = create_temporary_tag_if_necessary(manifest, get_epoch_timestamp_ms() + 3600 * 1000)
    tag = get_tag_by_manifest_id(repo.id, manifest.id)
    assert tag is not None
    assert tag.id == new_tag.id
    assert tag.lifetime_end_ms > expired_tag.lifetime_end_ms


def test_get_current_tag_with_single_existing_tag(initialized_db):
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest, _ = create_manifest_for_testing(repo, "1")
    t = manifest.tag_set.get()
    tag = get_current_tag(repo.id, t.name)
    assert tag.id == t.id


def test_get_current_tag_with_no_existing_tag(initialized_db):
    repo = model.repository.create_repository("devtable", "newrepo", None)
    tag = get_current_tag(repo.id, "does-not-exist")
    assert tag is None


def test_get_current_tag_with_expired_tag(initialized_db):
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest, _ = create_manifest_for_testing(repo, "1")
    before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
    count = (
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        )
        .where(Tag.manifest == manifest.id)
        .execute()
    )
    assert count == 1


def test_get_current_tag_with_multiple_expired_tags(initialized_db):
    repo = model.repository.create_repository("devtable", "newrepo", None)
    manifest, _ = create_manifest_for_testing(repo, "1")
    nowms = get_epoch_timestamp_ms()
    count = (
        Tag.update(
            lifetime_start_ms=nowms - timedelta(hours=24).total_seconds() * 1000,
            lifetime_end_ms=nowms - timedelta(hours=12).total_seconds() * 1000,
        )
        .where(Tag.manifest == manifest.id)
        .execute()
    )
    expired_tag = create_temporary_tag_if_necessary(manifest, 3600)
    expired_tag = Tag.create(
        name="v6.6.6",
        repository=repo.id,
        lifetime_start_ms=nowms - timedelta(hours=10).total_seconds() * 1000,
        lifetime_end_ms=nowms - timedelta(hours=8).total_seconds() * 1000,
        reversion=False,
        hidden=False,
        manifest=manifest,
        tag_kind=Tag.tag_kind.get_id("tag"),
    )
    tag = Tag.create(
        name="v6.6.6",
        repository=repo.id,
        lifetime_start_ms=nowms - timedelta(hours=5).total_seconds() * 1000,
        lifetime_end_ms=nowms + timedelta(hours=5).total_seconds() * 1000,
        reversion=False,
        hidden=False,
        manifest=manifest,
        tag_kind=Tag.tag_kind.get_id("tag"),
    )
    current_tag = get_current_tag(repo.id, tag.name)
    assert current_tag.id == tag.id


@pytest.mark.parametrize(
    "namespace_name, repo_name",
    [
        ("devtable", "simple"),
        ("devtable", "complex"),
    ],
)
def test_list_repository_tag_history(namespace_name, repo_name, initialized_db):
    repo = get_repository(namespace_name, repo_name)

    with assert_query_count(1):
        results, has_more = list_repository_tag_history(repo, 1, 100)

    assert results
    assert not has_more

    assert results[0].manifest.id is not None
    assert results[0].manifest.digest is not None
    assert results[0].manifest.media_type is not None
    assert results[0].manifest.layers_compressed_size is not None


def test_list_repository_tag_history_with_history(initialized_db):
    repo = get_repository("devtable", "history")

    with assert_query_count(1):
        results, _ = list_repository_tag_history(repo, 1, 100)

    assert len(results) == 2
    assert results[0].lifetime_end_ms is None
    assert results[1].lifetime_end_ms is not None

    with assert_query_count(1):
        results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")

    assert len(results) == 2
    assert results[0].lifetime_end_ms is None
    assert results[1].lifetime_end_ms is not None

    with assert_query_count(1):
        results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="foobar")

    assert len(results) == 0


def test_list_repository_tag_history_all_tags(initialized_db):
    for tag in Tag.select():
        repo = tag.repository
        with assert_query_count(1):
            results, _ = list_repository_tag_history(repo, 1, 1000)

        assert (tag in results) == (not tag.hidden)


@pytest.mark.parametrize(
    "namespace_name, repo_name, tag_name, expected",
    [
        ("devtable", "simple", "latest", False),
        ("devtable", "simple", "unknown", False),
        ("devtable", "complex", "latest", False),
        ("devtable", "history", "latest", True),
    ],
)
def test_get_expired_tag(namespace_name, repo_name, tag_name, expected, initialized_db):
    repo = get_repository(namespace_name, repo_name)

    with assert_query_count(1):
        assert bool(get_expired_tag(repo, tag_name)) == expected


def test_delete_tag(initialized_db):
    found = False
    with patch("data.model.config.app_config", {"RESET_CHILD_MANIFEST_EXPIRATION": False}):
        for tag in list(filter_to_visible_tags(filter_to_alive_tags(Tag.select()))):
            repo = tag.repository

            assert get_tag(repo, tag.name) == tag
            assert tag.lifetime_end_ms is None

            with assert_query_count(5):
                assert delete_tag(repo, tag.name) == tag

            assert get_tag(repo, tag.name) is None
            found = True

    assert found


def test_delete_tag_manifest_list(initialized_db):
    with patch("data.model.config.app_config", {"RESET_CHILD_MANIFEST_EXPIRATION": True}):
        repository = create_repository("devtable", "newrepo", None)
        tag = _create_manifest_list(repository)

        # Assert temporary tags were created and are alive
        child_manifests = list(get_child_manifests(repository.id, tag.manifest))
        assert len(child_manifests) == 2
        for child_manifest in child_manifests:
            child_tag = get_tag_by_manifest_id(repository.id, child_manifest.child_manifest)
            assert child_tag.name.startswith("$temp-")
            assert child_tag.lifetime_end_ms > get_epoch_timestamp_ms()

        with assert_query_count(10):
            assert delete_tag(repository.id, tag.name) == tag

        # Assert temporary tags pointing to child manifest are now expired
        child_manifests = list(get_child_manifests(repository.id, tag.manifest))
        assert len(child_manifests) == 2
        for child_manifest in child_manifests:
            child_tag = get_tag_by_manifest_id(repository.id, child_manifest.child_manifest)
            assert child_tag.name.startswith("$temp-")
            assert child_tag.lifetime_end_ms <= get_epoch_timestamp_ms()


def test_delete_tags_for_manifest(initialized_db):
    with patch("data.model.config.app_config", {"RESET_CHILD_MANIFEST_EXPIRATION": False}):
        for tag in list(filter_to_visible_tags(filter_to_alive_tags(Tag.select()))):
            repo = tag.repository
            assert get_tag(repo, tag.name) == tag

            with assert_query_count(7):
                assert delete_tags_for_manifest(tag.manifest) == [tag]

            assert get_tag(repo, tag.name) is None


def test_delete_tags_for_manifest_same_manifest(initialized_db):
    with patch("data.model.config.app_config", {"RESET_CHILD_MANIFEST_EXPIRATION": False}):
        new_repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest_1, _ = create_manifest_for_testing(new_repo, "1")
        manifest_2, _ = create_manifest_for_testing(new_repo, "2")

        assert manifest_1.digest != manifest_2.digest

        # Add some tag history, moving a tag back and forth between two manifests.
        retarget_tag("latest", manifest_1)
        retarget_tag("latest", manifest_2)
        retarget_tag("latest", manifest_1)
        retarget_tag("latest", manifest_2)

        retarget_tag("another1", manifest_1)
        retarget_tag("another2", manifest_2)

        # Delete all tags pointing to the first manifest.
        delete_tags_for_manifest(manifest_1)

        assert get_tag(new_repo, "latest").manifest == manifest_2
        assert get_tag(new_repo, "another1") is None
        assert get_tag(new_repo, "another2").manifest == manifest_2

        # Delete all tags pointing to the second manifest, which should actually delete the `latest`
        # tag now.
        delete_tags_for_manifest(manifest_2)
        assert get_tag(new_repo, "latest") is None
        assert get_tag(new_repo, "another1") is None
        assert get_tag(new_repo, "another2") is None


@pytest.mark.parametrize(
    "timedelta, expected_timedelta",
    [
        pytest.param(timedelta(seconds=1), timedelta(hours=1), id="less than minimum"),
        pytest.param(timedelta(weeks=300), timedelta(weeks=104), id="more than maxium"),
        pytest.param(timedelta(weeks=1), timedelta(weeks=1), id="within range"),
    ],
)
def test_change_tag_expiration(timedelta, expected_timedelta, initialized_db):
    now = datetime.utcnow()
    now_ms = timegm(now.utctimetuple()) * 1000

    tag = Tag.get()
    tag.lifetime_start_ms = now_ms
    tag.save()

    original_end_ms, okay = change_tag_expiration(tag, now + timedelta)
    assert okay
    assert original_end_ms == tag.lifetime_end_ms

    updated_tag = Tag.get(id=tag.id)
    offset = expected_timedelta.total_seconds() * 1000
    expected_ms = updated_tag.lifetime_start_ms + offset
    assert updated_tag.lifetime_end_ms == expected_ms

    original_end_ms, okay = change_tag_expiration(tag, None)
    assert okay
    assert original_end_ms == expected_ms

    updated_tag = Tag.get(id=tag.id)
    assert updated_tag.lifetime_end_ms is None


def test_set_tag_expiration_for_manifest(initialized_db):
    tag = Tag.get()
    manifest = tag.manifest
    assert manifest is not None

    set_tag_expiration_for_manifest(manifest, datetime.utcnow() + timedelta(weeks=1))

    updated_tag = Tag.get(id=tag.id)
    assert updated_tag.lifetime_end_ms is not None


def test_create_temporary_tag_if_necessary(initialized_db):
    tag = Tag.get()
    manifest = tag.manifest
    assert manifest is not None

    # Ensure no tag is created, since an existing one is present.
    created = create_temporary_tag_if_necessary(manifest, 60)
    assert created is None

    # Mark the tag as deleted.
    tag.lifetime_end_ms = 1
    tag.save()

    # Now create a temp tag.
    created = create_temporary_tag_if_necessary(manifest, 60)
    assert created is not None
    assert created.hidden
    assert created.name.startswith("$temp-")
    assert created.manifest == manifest
    assert created.lifetime_end_ms is not None
    assert created.lifetime_end_ms == (created.lifetime_start_ms + 60000)

    # Try again and ensure it is not created.
    created = create_temporary_tag_if_necessary(manifest, 30)
    assert created is None


def test_create_temporary_tag_outside_timemachine(initialized_db):
    tag = Tag.get()
    manifest = tag.manifest
    assert manifest is not None

    created = create_temporary_tag_outside_timemachine(manifest)

    namespace = (
        User.select(User.removed_tag_expiration_s)
        .join(Repository, on=(Repository.namespace_user == User.id))
        .where(Repository.id == manifest.repository_id)
        .get()
    )

    assert created is not None and created
    assert created.hidden
    assert created.name.startswith("$temp-")
    assert created.manifest == manifest
    assert created.lifetime_end_ms is not None
    assert (
        created.lifetime_end_ms
        < get_epoch_timestamp_ms() - namespace.removed_tag_expiration_s * 1000
    )


def test_retarget_tag(initialized_db):
    repo = get_repository("devtable", "history")
    results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")

    assert len(results) == 2
    assert results[0].lifetime_end_ms is None
    assert results[1].lifetime_end_ms is not None

    # Revert back to the original manifest.
    created = retarget_tag(
        "latest", results[0].manifest, is_reversion=True, now_ms=results[1].lifetime_end_ms + 10000
    )
    assert created.lifetime_end_ms is None
    assert created.reversion
    assert created.name == "latest"
    assert created.manifest == results[0].manifest

    # Verify in the history.
    results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")

    assert len(results) == 3
    assert results[0].lifetime_end_ms is None
    assert results[1].lifetime_end_ms is not None
    assert results[2].lifetime_end_ms is not None

    assert results[0] == created


def test_retarget_tag_wrong_name(initialized_db):
    repo = get_repository("devtable", "history")
    results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")
    assert len(results) == 2

    created = retarget_tag("someothername", results[1].manifest, is_reversion=True)
    assert created is None

    results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")
    assert len(results) == 2


def test_lookup_unrecoverable_tags(initialized_db):
    # Ensure no existing tags are found.
    for repo in Repository.select():
        assert not list(lookup_unrecoverable_tags(repo))

    # Mark a tag as outside the expiration window and ensure it is found.
    repo = get_repository("devtable", "history")
    results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")
    assert len(results) == 2

    results[1].lifetime_end_ms = 1
    results[1].save()

    # Ensure the tag is now found.
    found = list(lookup_unrecoverable_tags(repo))
    assert found
    assert len(found) == 1
    assert found[0] == results[1]

    # Mark the tag as expiring in the future and ensure it is no longer found.
    results[1].lifetime_end_ms = get_epoch_timestamp_ms() + 1000000
    results[1].save()

    found = list(lookup_unrecoverable_tags(repo))
    assert not found


def test_remove_tag_from_timemachine(initialized_db):
    org = get_user("devtable")
    repo = get_repository("devtable", "history")
    results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")
    assert len(results) == 2
    assert org.removed_tag_expiration_s > 0

    expiration_window = org.removed_tag_expiration_s
    manifest_id = results[0].manifest

    # Expire the tags
    now_ms = get_epoch_timestamp_ms()
    results[0].lifetime_end_ms = now_ms - 100
    results[1].lifetime_end_ms = now_ms - 101

    # Recreate scenario of the same tag being deleted twice
    # by setting the tags to the same manifest
    results[1].manifest = manifest_id

    results[0].save()
    results[1].save()

    updated = remove_tag_from_timemachine(repo.id, "latest", manifest_id)
    assert updated

    results, _ = list_repository_tag_history(repo, 1, 100, specific_tag_name="latest")
    for tag in results:
        assert tag.lifetime_end_ms < get_epoch_timestamp_ms() - expiration_window
        assert not tag.hidden


def test_remove_tag_from_timemachine_alive(initialized_db):
    org = get_user("devtable")
    repo = get_repository("devtable", "history")
    tag = get_tag(repo, "latest")
    assert tag.lifetime_end_ms is None or tag.lifetime_end_ms > get_epoch_timestamp_ms()
    assert tag is not None
    assert org.removed_tag_expiration_s > 0

    expiration_window = org.removed_tag_expiration_s

    updated = remove_tag_from_timemachine(repo.id, "latest", tag.manifest, is_alive=True)
    assert updated

    tag = Tag.select().where(Tag.id == tag.id).get()
    assert tag.lifetime_end_ms < get_epoch_timestamp_ms() - expiration_window
    assert not tag.hidden


def test_remove_tag_from_timemachine_submanifests(initialized_db):
    org = get_user("devtable")
    assert org.removed_tag_expiration_s > 0
    expiration_window = org.removed_tag_expiration_s
    repository = create_repository("devtable", "newrepo", None)

    created_tag = _create_manifest_list(repository)
    created_tag.lifetime_end_ms = get_epoch_timestamp_ms() - 100
    created_tag.save()

    updated = remove_tag_from_timemachine(
        created_tag.repository, "manifestlist", created_tag.manifest, include_submanifests=True
    )
    assert updated

    updated_tag = Tag.select().where(Tag.id == created_tag.id).get()
    assert updated_tag.lifetime_end_ms < get_epoch_timestamp_ms() - expiration_window
    assert not updated_tag.hidden

    child_manifests = [
        cm.child_manifest
        for cm in ManifestChild.select().where(ManifestChild.manifest == created_tag.manifest)
    ]
    tags = list(Tag.select().where(Tag.manifest << child_manifests))
    for tag in tags:
        assert tag.lifetime_end_ms < get_epoch_timestamp_ms() - expiration_window
        assert tag.hidden
        assert tag.name.startswith("$temp-")


def _create_manifest_list(repository):
    layer_json = json.dumps(
        {
            "id": "somelegacyid",
            "config": {
                "Labels": {},
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {
                    "created": "2018-04-03T18:37:09.284840891Z",
                    "created_by": "do something",
                },
            ],
        }
    )

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json)

    # Add a blob of random data.
    random_data_1 = "foo"
    _, random_digest_1 = _populate_blob(random_data_1)
    random_data_2 = "bar"
    _, random_digest_2 = _populate_blob(random_data_2)

    # Build the manifests.
    manifest_1_builder = DockerSchema2ManifestBuilder()
    manifest_1_builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    manifest_1_builder.add_layer(random_digest_1, len(random_data_1.encode("utf-8")))
    manifest_1 = manifest_1_builder.build()

    manifest_2_builder = DockerSchema2ManifestBuilder()
    manifest_2_builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    manifest_2_builder.add_layer(random_digest_2, len(random_data_2.encode("utf-8")))
    manifest_2 = manifest_2_builder.build()

    # Write the manifests.
    v1_created = get_or_create_manifest(repository, manifest_1, storage)
    assert v1_created
    assert v1_created.manifest.digest == manifest_1.digest

    v2_created = get_or_create_manifest(repository, manifest_2, storage)
    assert v2_created
    assert v2_created.manifest.digest == manifest_2.digest

    # Build the manifest list.
    list_builder = DockerSchema2ManifestListBuilder()
    list_builder.add_manifest(manifest_1, "amd64", "linux")
    list_builder.add_manifest(manifest_2, "amd32", "linux")
    manifest_list = list_builder.build()

    # Write the manifest list, which should also write the manifests themselves.
    created_tuple = get_or_create_manifest(repository, manifest_list, storage)
    assert created_tuple is not None

    return retarget_tag("manifestlist", created_tuple.manifest)


# =============================================================================
# Immutable Tag Tests
# =============================================================================


class TestImmutableTagException:
    def test_exception_message(self):
        """Test that ImmutableTagException has correct message format."""
        exc = ImmutableTagException("latest", "delete", 123)
        assert exc.tag_name == "latest"
        assert exc.operation == "delete"
        assert exc.repository_id == 123
        assert str(exc) == "Cannot delete immutable tag 'latest'"

    def test_exception_message_overwrite(self):
        """Test exception message for overwrite operation."""
        exc = ImmutableTagException("v1.0", "overwrite")
        assert str(exc) == "Cannot overwrite immutable tag 'v1.0'"


class TestDeleteTagImmutable:
    def test_delete_tag_immutable_raises_exception(self, initialized_db):
        """Test that deleting an immutable tag raises ImmutableTagException."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a real tag (not a temporary hidden one)
        tag = retarget_tag("v1.0", manifest.id)

        # Mark tag as immutable
        Tag.update(immutable=True).where(Tag.id == tag.id).execute()

        with patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True)):
            with pytest.raises(ImmutableTagException) as exc_info:
                delete_tag(repo.id, tag.name)

            assert exc_info.value.tag_name == tag.name
            assert exc_info.value.operation == "delete"
            assert exc_info.value.repository_id == repo.id

    @patch("data.model.config.app_config", {"RESET_CHILD_MANIFEST_EXPIRATION": False})
    def test_delete_tag_mutable_works(self, initialized_db):
        """Test that deleting a mutable tag works normally."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a real tag (not a temporary hidden one)
        tag = retarget_tag("v1.0", manifest.id)

        # Tag is mutable by default
        assert not tag.immutable

        deleted = delete_tag(repo.id, tag.name)
        assert deleted is not None
        assert get_tag(repo.id, tag.name) is None


class TestRetargetTagImmutable:
    @patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True))
    def test_retarget_tag_immutable_raises_exception(self, initialized_db):
        """Test that overwriting an immutable tag raises ImmutableTagException."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest_1, _ = create_manifest_for_testing(repo, "1")
        manifest_2, _ = create_manifest_for_testing(repo, "2")

        tag = retarget_tag("mytag", manifest_1.id)

        # Mark tag as immutable
        Tag.update(immutable=True).where(Tag.id == tag.id).execute()

        with pytest.raises(ImmutableTagException) as exc_info:
            retarget_tag("mytag", manifest_2.id, raise_on_error=True)

        assert exc_info.value.tag_name == "mytag"
        assert exc_info.value.operation == "overwrite"

    @patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True))
    def test_retarget_tag_immutable_returns_none(self, initialized_db):
        """Test that overwriting an immutable tag returns None when raise_on_error=False."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest_1, _ = create_manifest_for_testing(repo, "1")
        manifest_2, _ = create_manifest_for_testing(repo, "2")

        tag = retarget_tag("mytag", manifest_1.id)

        # Mark tag as immutable
        Tag.update(immutable=True).where(Tag.id == tag.id).execute()

        result = retarget_tag("mytag", manifest_2.id, raise_on_error=False)
        assert result is None

        # Verify original tag still exists and points to original manifest
        current_tag = get_tag(repo.id, "mytag")
        assert current_tag is not None
        assert current_tag.manifest_id == manifest_1.id

    def test_retarget_tag_new_tag_alongside_immutable(self, initialized_db):
        """Test that creating a new tag works when immutable tags exist."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest_1, _ = create_manifest_for_testing(repo, "1")
        manifest_2, _ = create_manifest_for_testing(repo, "2")

        tag_1 = retarget_tag("immutable-tag", manifest_1.id)

        # Mark first tag as immutable
        Tag.update(immutable=True).where(Tag.id == tag_1.id).execute()

        # Creating a new tag with different name should work
        tag_2 = retarget_tag("new-tag", manifest_2.id)
        assert tag_2 is not None
        assert tag_2.name == "new-tag"


class TestRemoveTagFromTimemachineImmutable:
    @patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True))
    def test_remove_alive_immutable_tag_returns_false(self, initialized_db):
        """Test that permanently deleting an alive immutable tag returns False and logs."""
        repo = get_repository("devtable", "history")
        tag = get_tag(repo.id, "latest")
        assert tag is not None

        # Mark tag as immutable
        Tag.update(immutable=True).where(Tag.id == tag.id).execute()

        # Should return False instead of raising exception
        result = remove_tag_from_timemachine(repo.id, "latest", tag.manifest_id, is_alive=True)
        assert result is False

        # Tag should still exist
        assert get_tag(repo.id, "latest") is not None

    @patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True))
    def test_remove_expired_immutable_tag_is_skipped(self, initialized_db):
        """Test that permanently deleting an expired immutable tag skips it."""
        repo = get_repository("devtable", "history")
        results, _ = list_repository_tag_history(repo.id, 1, 100, specific_tag_name="latest")
        assert len(results) >= 2

        # Get the expired tag and mark it as immutable
        expired_tag = results[1]
        now_ms = get_epoch_timestamp_ms()
        Tag.update(
            lifetime_end_ms=now_ms - 100,
            immutable=True,
        ).where(Tag.id == expired_tag.id).execute()

        # Should succeed but skip the immutable tag
        result = remove_tag_from_timemachine(repo.id, "latest", expired_tag.manifest_id)
        # Returns False because no mutable tags were updated
        assert result is False


class TestIsTagImmutable:
    def test_is_tag_immutable_returns_true(self, initialized_db):
        """Test that is_tag_immutable returns True for immutable tags."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a real tag (not a temporary hidden one)
        tag = retarget_tag("v1.0", manifest.id)

        Tag.update(immutable=True).where(Tag.id == tag.id).execute()

        result = is_tag_immutable(repo.id, tag.name)
        assert result is True

    def test_is_tag_immutable_returns_false(self, initialized_db):
        """Test that is_tag_immutable returns False for mutable tags."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a real tag (not a temporary hidden one)
        tag = retarget_tag("v1.0", manifest.id)

        result = is_tag_immutable(repo.id, tag.name)
        assert result is False

    def test_is_tag_immutable_returns_none_for_nonexistent(self, initialized_db):
        """Test that is_tag_immutable returns None for non-existent tags."""
        repo = model.repository.create_repository("devtable", "newrepo", None)

        result = is_tag_immutable(repo.id, "nonexistent")
        assert result is None


class TestSetTagImmutable:
    def test_set_tag_immutable_true(self, initialized_db):
        """Test setting a tag as immutable."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a real tag (not a temporary hidden one)
        tag = retarget_tag("v1.0", manifest.id)

        prev, success = set_tag_immutable(repo.id, tag.name, True)

        assert prev is False
        assert success is True

        # Verify tag is now immutable
        updated_tag = Tag.get_by_id(tag.id)
        assert updated_tag.immutable is True

    def test_set_tag_immutable_false(self, initialized_db):
        """Test setting a tag as mutable."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a real tag (not a temporary hidden one)
        tag = retarget_tag("v1.0", manifest.id)

        # First make it immutable
        Tag.update(immutable=True).where(Tag.id == tag.id).execute()

        prev, success = set_tag_immutable(repo.id, tag.name, False)

        assert prev is True
        assert success is True

        # Verify tag is now mutable
        updated_tag = Tag.get_by_id(tag.id)
        assert updated_tag.immutable is False

    def test_set_tag_immutable_nonexistent_tag(self, initialized_db):
        """Test setting immutability on non-existent tag returns failure."""
        repo = model.repository.create_repository("devtable", "newrepo", None)

        prev, success = set_tag_immutable(repo.id, "nonexistent", True)

        assert prev is None
        assert success is False

    def test_set_tag_immutable_no_change(self, initialized_db):
        """Test that setting same immutability value returns success without update."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a real tag (not a temporary hidden one)
        tag = retarget_tag("v1.0", manifest.id)

        # Tag is already mutable (False)
        prev, success = set_tag_immutable(repo.id, tag.name, False)

        assert prev is False
        assert success is True


class TestFeatureFlagDisabled:
    """Test that immutable tags can be deleted when feature flag is disabled."""

    def test_delete_immutable_tag_when_feature_disabled(self, initialized_db):
        """When FEATURE_IMMUTABLE_TAGS is False, deleting immutable tags succeeds."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")
        tag = retarget_tag("v1.0", manifest)

        Tag.update(immutable=True).where(Tag.id == tag.id).execute()

        with patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=False)):
            deleted = delete_tag(repo.id, "v1.0")
            assert deleted is not None


class TestDeleteTagsForManifestImmutable:
    """Test delete_tags_for_manifest with immutable tags."""

    @patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True))
    def test_delete_tags_for_manifest_raises_on_immutable(self, initialized_db):
        """Raises ImmutableTagException when any tag is immutable."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create two tags pointing to same manifest
        tag1 = retarget_tag("v1.0", manifest)
        retarget_tag("v2.0", manifest)

        # Make one immutable
        Tag.update(immutable=True).where(Tag.id == tag1.id).execute()

        with pytest.raises(ImmutableTagException) as exc_info:
            delete_tags_for_manifest(manifest)

        assert exc_info.value.tag_name == "v1.0"
        assert exc_info.value.operation == "delete"

        # Both tags should still exist (no partial deletion)
        assert get_tag(repo.id, "v1.0") is not None
        assert get_tag(repo.id, "v2.0") is not None

    @patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True))
    def test_delete_tags_for_manifest_raises_all_immutable(self, initialized_db):
        """Raises ImmutableTagException when all tags are immutable."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        tag1 = retarget_tag("v1.0", manifest)
        tag2 = retarget_tag("v2.0", manifest)

        # Make both immutable
        Tag.update(immutable=True).where(Tag.id << [tag1.id, tag2.id]).execute()

        with pytest.raises(ImmutableTagException):
            delete_tags_for_manifest(manifest)

        # Both tags should still exist
        assert get_tag(repo.id, "v1.0") is not None
        assert get_tag(repo.id, "v2.0") is not None

    @patch("data.model.oci.tag.features", MagicMock(IMMUTABLE_TAGS=True))
    def test_delete_tags_for_manifest_succeeds_all_mutable(self, initialized_db):
        """Succeeds when no tags are immutable."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        retarget_tag("v1.0", manifest)
        retarget_tag("v2.0", manifest)

        deleted = delete_tags_for_manifest(manifest)

        assert len(deleted) == 2
        assert {t.name for t in deleted} == {"v1.0", "v2.0"}

        # Both tags should be gone
        assert get_tag(repo.id, "v1.0") is None
        assert get_tag(repo.id, "v2.0") is None


class TestSetTagsImmutabilityForManifest:
    def test_sets_all_alive_tags_immutable(self, initialized_db):
        """Test that all alive tags for a manifest are set immutable."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create multiple tags pointing to same manifest
        tag1 = retarget_tag("v1.0", manifest.id)
        tag2 = retarget_tag("v2.0", manifest.id)

        # Verify tags are not immutable
        assert not tag1.immutable
        assert not tag2.immutable

        # Set all tags for manifest as immutable
        count = set_tags_immutability_for_manifest(manifest.id, True)

        # Verify count and immutability
        assert count == 2
        assert Tag.get_by_id(tag1.id).immutable is True
        assert Tag.get_by_id(tag2.id).immutable is True

    def test_does_not_update_expired_tags(self, initialized_db):
        """Test that expired tags are not updated."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a tag and then expire it
        tag = retarget_tag("v1.0", manifest.id)
        now_ms = get_epoch_timestamp_ms()
        Tag.update(lifetime_end_ms=now_ms - 1000).where(Tag.id == tag.id).execute()

        # Set immutability for manifest
        count = set_tags_immutability_for_manifest(manifest.id, True)

        # Expired tag should not be updated
        assert count == 0
        assert Tag.get_by_id(tag.id).immutable is False

    def test_does_not_update_hidden_tags(self, initialized_db):
        """Test that hidden (temp) tags are not updated."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # Create a temporary (hidden) tag
        temp_tag = create_temporary_tag_if_necessary(manifest, 3600)
        assert temp_tag.hidden

        # Set immutability for manifest
        count = set_tags_immutability_for_manifest(manifest.id, True)

        # Hidden tag should not be updated
        assert count == 0
        assert Tag.get_by_id(temp_tag.id).immutable is False

    def test_returns_count_of_updated_tags(self, initialized_db):
        """Test return value is count of updated tags."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        # No tags initially
        count = set_tags_immutability_for_manifest(manifest.id, True)
        assert count == 0

        # Add one tag
        tag1 = retarget_tag("v1.0", manifest.id)
        count = set_tags_immutability_for_manifest(manifest.id, True)
        assert count == 1

        # Add another tag
        Tag.update(immutable=False).where(Tag.id == tag1.id).execute()
        retarget_tag("v2.0", manifest.id)
        count = set_tags_immutability_for_manifest(manifest.id, True)
        assert count == 2

    def test_can_set_immutable_false(self, initialized_db):
        """Test that immutability can be removed from tags."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "1")

        tag = retarget_tag("v1.0", manifest.id)

        # First make immutable
        set_tags_immutability_for_manifest(manifest.id, True)
        assert Tag.get_by_id(tag.id).immutable is True

        # Then remove immutability
        count = set_tags_immutability_for_manifest(manifest.id, False)
        assert count == 1
        assert Tag.get_by_id(tag.id).immutable is False


class TestRetargetTagRaceCondition:
    """Tests for retarget_tag race condition protection via repository locking."""

    def test_retarget_tag_creates_single_active_tag(self, initialized_db):
        """Test that multiple retarget_tag calls produce only one active tag."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest1, _ = create_manifest_for_testing(repo, "race1")
        manifest2, _ = create_manifest_for_testing(repo, "race2")

        tag1 = retarget_tag("racelatest", manifest1.id)
        assert tag1 is not None
        assert tag1.lifetime_end_ms is None

        tag2 = retarget_tag("racelatest", manifest2.id)
        assert tag2 is not None
        assert tag2.lifetime_end_ms is None

        active_tags = list(
            Tag.select().where(
                Tag.repository == repo.id, Tag.name == "racelatest", Tag.lifetime_end_ms >> None
            )
        )
        assert len(active_tags) == 1
        assert active_tags[0].id == tag2.id

        tag1_refreshed = Tag.get_by_id(tag1.id)
        assert tag1_refreshed.lifetime_end_ms is not None

    def test_retarget_tag_new_tag_no_duplicate(self, initialized_db):
        """Test that creating a new tag doesn't create duplicates."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "newtag1")

        tag = retarget_tag("noduptag", manifest.id)
        assert tag is not None
        assert tag.lifetime_end_ms is None

        active_tags = list(
            Tag.select().where(
                Tag.repository == repo.id, Tag.name == "noduptag", Tag.lifetime_end_ms >> None
            )
        )
        assert len(active_tags) == 1

    def test_retarget_tag_expires_previous_correctly(self, initialized_db):
        """Test that previous tag is expired with correct timestamp."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest1, _ = create_manifest_for_testing(repo, "expire1")
        manifest2, _ = create_manifest_for_testing(repo, "expire2")

        now_ms = get_epoch_timestamp_ms()
        tag1 = retarget_tag("expiretag", manifest1.id, now_ms=now_ms)
        assert tag1.lifetime_start_ms == now_ms

        later_ms = now_ms + 10000
        tag2 = retarget_tag("expiretag", manifest2.id, now_ms=later_ms)
        assert tag2.lifetime_start_ms == later_ms

        tag1_refreshed = Tag.get_by_id(tag1.id)
        assert tag1_refreshed.lifetime_end_ms == later_ms

    def test_retarget_tag_repository_not_found_returns_none(self, initialized_db):
        """Test that retarget_tag returns None when repository lock fails."""
        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "reponotfound1")

        def mock_db_for_update(query):
            mock_result = MagicMock()
            mock_result.get.side_effect = Repository.DoesNotExist()
            return mock_result

        with patch("data.model.oci.tag.db_for_update", mock_db_for_update):
            result = retarget_tag("failingtag", manifest.id, raise_on_error=False)
            assert result is None

    def test_retarget_tag_repository_not_found_raises_exception(self, initialized_db):
        """Test that retarget_tag raises exception when repository lock fails and raise_on_error=True."""
        from data.model.oci.tag import RetargetTagException

        repo = model.repository.create_repository("devtable", "newrepo", None)
        manifest, _ = create_manifest_for_testing(repo, "reponotfound2")

        def mock_db_for_update(query):
            mock_result = MagicMock()
            mock_result.get.side_effect = Repository.DoesNotExist()
            return mock_result

        with patch("data.model.oci.tag.db_for_update", mock_db_for_update):
            with pytest.raises(RetargetTagException) as exc_info:
                retarget_tag("failingtag", manifest.id, raise_on_error=True)
            assert "Repository no longer exists" in str(exc_info.value)
