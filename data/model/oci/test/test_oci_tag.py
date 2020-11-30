from calendar import timegm
from datetime import timedelta, datetime

from playhouse.test_utils import assert_query_count

from data.database import (
    Tag,
    ManifestLegacyImage,
    TagToRepositoryTag,
    TagManifestToManifest,
    TagManifest,
    Manifest,
    Repository,
)
from data.model.oci.test.test_oci_manifest import create_manifest_for_testing
from data.model.oci.tag import (
    find_matching_tag,
    get_most_recent_tag,
    get_most_recent_tag_lifetime_start,
    list_alive_tags,
    filter_to_alive_tags,
    filter_to_visible_tags,
    list_repository_tag_history,
    get_expired_tag,
    get_tag,
    delete_tag,
    delete_tags_for_manifest,
    change_tag_expiration,
    set_tag_expiration_for_manifest,
    retarget_tag,
    create_temporary_tag_if_necessary,
    lookup_alive_tags_shallow,
    lookup_unrecoverable_tags,
    get_epoch_timestamp_ms,
)
from data.model.repository import get_repository, create_repository

from test.fixtures import *


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
        tags = lookup_alive_tags_shallow(tag.repository)
        found = True
        assert tag in tags

    assert found

    # Ensure hidden tags cannot be listed.
    tag = Tag.get()
    tag.hidden = True
    tag.save()

    tags = lookup_alive_tags_shallow(tag.repository)
    assert tag not in tags


def test_get_tag(initialized_db):
    found = False
    for tag in filter_to_visible_tags(filter_to_alive_tags(Tag.select())):
        repo = tag.repository

        with assert_query_count(1):
            assert get_tag(repo, tag.name) == tag
        found = True

    assert found


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
    for tag in list(filter_to_visible_tags(filter_to_alive_tags(Tag.select()))):
        repo = tag.repository

        assert get_tag(repo, tag.name) == tag
        assert tag.lifetime_end_ms is None

        with assert_query_count(3):
            assert delete_tag(repo, tag.name) == tag

        assert get_tag(repo, tag.name) is None
        found = True

    assert found


def test_delete_tags_for_manifest(initialized_db):
    for tag in list(filter_to_visible_tags(filter_to_alive_tags(Tag.select()))):
        repo = tag.repository
        assert get_tag(repo, tag.name) == tag

        with assert_query_count(4):
            assert delete_tags_for_manifest(tag.manifest) == [tag]

        assert get_tag(repo, tag.name) is None


def test_delete_tags_for_manifest_same_manifest(initialized_db):
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
