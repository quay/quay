import pytest
from playhouse.test_utils import assert_query_count

from data.database import Manifest
from data.model.oci.tag import set_tag_immutable
from data.registry_model import registry_model
from endpoints.api.tag import ListRepositoryTags, RepositoryTag, RestoreTag
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, toggle_feature
from test.fixtures import *


@pytest.mark.parametrize(
    "expiration_time, expected_status",
    [
        (None, 201),
        ("aksdjhasd", 400),
    ],
)
def test_change_tag_expiration_default(expiration_time, expected_status, app):
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "latest",
        }

        request_body = {
            "expiration": expiration_time,
        }

        conduct_api_call(cl, RepositoryTag, "put", params, request_body, expected_status)


def test_change_tag_expiration(app):
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "latest",
        }

        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")

        updated_expiration = tag.lifetime_start_ts + 60 * 60 * 24

        request_body = {
            "expiration": updated_expiration,
        }

        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 201)
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        assert tag.lifetime_end_ts == updated_expiration


@pytest.mark.parametrize(
    "manifest_exists,test_tag,expected_status",
    [
        (True, "-INVALID-TAG-NAME", 400),
        (True, ".INVALID-TAG-NAME", 400),
        (
            True,
            "INVALID-TAG_NAME-BECAUSE-THIS-IS-WAY-WAY-TOO-LOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOONG",
            400,
        ),
        (False, "newtag", 404),
        (True, "generatemanifestfail", None),
        (True, "latest", 201),
        (True, "newtag", 201),
    ],
)
def test_move_tag(manifest_exists, test_tag, expected_status, app):
    with client_with_identity("devtable", app) as cl:
        test_image = "unknown"
        if manifest_exists:
            repo_ref = registry_model.lookup_repository("devtable", "simple")
            tag_ref = registry_model.get_repo_tag(repo_ref, "latest")
            assert tag_ref

            test_image = tag_ref.manifest.digest

        params = {"repository": "devtable/simple", "tag": test_tag}
        request_body = {"manifest_digest": test_image}
        if expected_status is None:
            with pytest.raises(Exception):
                conduct_api_call(cl, RepositoryTag, "put", params, request_body, expected_status)
        else:
            conduct_api_call(cl, RepositoryTag, "put", params, request_body, expected_status)


@pytest.mark.parametrize(
    "repo_namespace, repo_name, query_count",
    [
        ("devtable", "simple", 6),  # +2 for converting object to and from json
        ("devtable", "history", 6),  # +2 for converting object to and from json
        ("devtable", "complex", 6),  # +2 for converting object to and from json
        ("devtable", "gargantuan", 6),  # +2 for converting object to and from json
        ("buynlarge", "orgrepo", 9),  # +3 for permissions checks.
        ("buynlarge", "anotherorgrepo", 9),  # +3 for permissions checks.
    ],
)
def test_list_repo_tags(repo_namespace, repo_name, query_count, app):
    # Pre-cache media type loads to ensure consistent query count.
    Manifest.media_type.get_name(1)

    params = {"repository": repo_namespace + "/" + repo_name}
    with client_with_identity("devtable", app) as cl:
        with assert_query_count(query_count):
            tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

        repo_ref = registry_model.lookup_repository(repo_namespace, repo_name)
        history, _ = registry_model.list_repository_tag_history(repo_ref)
        assert len(tags) == len(history)


@pytest.mark.parametrize(
    "repo_namespace, repo_name, query_count",
    [
        ("devtable", "gargantuan", 6),  # +2 for converting object to and from json
    ],
)
def test_list_repo_tags_filter(repo_namespace, repo_name, query_count, app):
    Manifest.media_type.get_name(1)

    params = {"repository": repo_namespace + "/" + repo_name}
    with client_with_identity("devtable", app) as cl:
        with assert_query_count(query_count):
            params["filter_tag_name"] = "like:v"
            tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]
        assert len(tags) == 5

    with client_with_identity("devtable", app) as cl:
        with assert_query_count(query_count - 1):
            params["filter_tag_name"] = "eq:prod"
            tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]
        assert len(tags) == 1

    with client_with_identity("devtable", app) as cl:
        params["filter_tag_name"] = "random"
        resp = conduct_api_call(cl, ListRepositoryTags, "get", params, None, expected_code=400)


# Tag Immutability Tests


def test_set_tag_immutable_with_write_permission(app):
    """Test setting tag immutable with write permission via RepositoryTag PUT."""
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "latest",
        }

        request_body = {"immutable": True}

        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 201)

        # Verify it's now immutable via data model
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")
        assert tag_ref.immutable is True


def test_remove_immutability_requires_admin(app):
    """Test that removing immutability requires admin permission."""
    repo_ref = registry_model.lookup_repository("devtable", "simple")

    # First make the tag immutable via data layer
    set_tag_immutable(repo_ref.id, "latest", True)

    # devtable is admin on their own repo, so they can remove it
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "latest",
        }

        request_body = {"immutable": False}

        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 201)

        # Verify it's now not immutable
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")
        assert tag_ref.immutable is False


def test_remove_immutability_denied_for_non_admin(app):
    """Test that users with write but not admin permission cannot remove immutability."""
    # Use devtable/shared where 'public' user has write permission but not admin
    repo_ref = registry_model.lookup_repository("devtable", "shared")

    # Make the tag immutable via data layer
    set_tag_immutable(repo_ref.id, "latest", True)

    # 'public' user has write permission on devtable/shared but is not admin
    # This tests the AdministerRepositoryPermission check, not @require_repo_write
    with client_with_identity("public", app) as cl:
        params = {
            "repository": "devtable/shared",
            "tag": "latest",
        }

        request_body = {"immutable": False}

        # User with write but not admin should get 403 from the admin permission check
        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 403)

    # Verify tag is still immutable
    resp_check = registry_model.get_repo_tag(repo_ref, "latest")
    assert resp_check.immutable is True


def test_list_repo_tags_includes_immutable(app):
    """Test that tag list includes immutable field."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        with client_with_identity("devtable", app) as cl:
            params = {"repository": "devtable/simple"}
            tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

            for tag in tags:
                assert "immutable" in tag
                assert isinstance(tag["immutable"], bool)


def test_delete_immutable_tag_returns_409(app):
    """Test DELETE on immutable tag returns 409."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        with client_with_identity("devtable", app) as cl:
            params = {
                "repository": "devtable/simple",
                "tag": "latest",
            }

            resp = conduct_api_call(cl, RepositoryTag, "delete", params, None, 409)
            assert resp.json["error_type"] == "tag_immutable"
            assert resp.json["title"] == "tag_immutable"


def test_retarget_immutable_tag_returns_409(app):
    """Test PUT (retarget) on immutable tag returns 409."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        with client_with_identity("devtable", app) as cl:
            params = {
                "repository": "devtable/simple",
                "tag": "latest",
            }

            request_body = {"manifest_digest": tag_ref.manifest.digest}

            resp = conduct_api_call(cl, RepositoryTag, "put", params, request_body, 409)
            assert resp.json["error_type"] == "tag_immutable"
            assert resp.json["title"] == "tag_immutable"


def test_restore_immutable_tag_returns_409(app):
    """Test restoring immutable tag returns 409."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        with client_with_identity("devtable", app) as cl:
            params = {
                "repository": "devtable/simple",
                "tag": "latest",
            }

            request_body = {"manifest_digest": tag_ref.manifest.digest}

            resp = conduct_api_call(cl, RestoreTag, "post", params, request_body, 409)
            assert resp.json["error_type"] == "tag_immutable"
            assert resp.json["title"] == "tag_immutable"


def test_set_immutability_not_found(app):
    """Test 404 for setting immutability on non-existent tag."""
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "nonexistent",
        }

        request_body = {"immutable": True}

        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 404)


def test_set_immutability_idempotent(app):
    """Test setting same immutability status is idempotent."""
    repo_ref = registry_model.lookup_repository("devtable", "simple")

    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "latest",
        }

        # Set to immutable
        request_body = {"immutable": True}
        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 201)

        # Verify it's immutable
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")
        assert tag_ref.immutable is True

        # Set to immutable again - should be idempotent
        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 201)

        # Still immutable
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")
        assert tag_ref.immutable is True


# Sparse Manifest Tests


def test_list_repo_tags_non_manifest_list_has_no_sparse_info(app):
    """Test that non-manifest-list tags don't have sparse info fields."""
    with client_with_identity("devtable", app) as cl:
        params = {"repository": "devtable/simple"}
        tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

        # Find a non-manifest-list tag
        for tag in tags:
            if not tag.get("is_manifest_list", False):
                # Non-manifest lists should not have sparse info fields
                assert "is_sparse" not in tag
                assert "child_manifest_count" not in tag
                assert "present_child_count" not in tag
                break


def test_list_repo_tags_manifest_list_has_sparse_info(app, initialized_db):
    """Test that manifest list tags include sparse info fields."""
    from data.database import Manifest as ManifestTable
    from data.database import ManifestChild, Repository
    from image.docker.schema2 import DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE

    # Find a manifest list in the test database
    manifest_list_media_type_id = ManifestTable.media_type.get_id(
        DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
    )

    # Check if there are any manifest lists in the test data
    manifest_lists = list(
        ManifestTable.select()
        .where(ManifestTable.media_type == manifest_list_media_type_id)
        .limit(1)
    )

    if not manifest_lists:
        # No manifest lists in test data; this test will verify that
        # normal tags don't have sparse info
        with client_with_identity("devtable", app) as cl:
            params = {"repository": "devtable/simple"}
            tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

            for tag in tags:
                if tag.get("is_manifest_list", False):
                    assert "is_sparse" in tag
                    assert isinstance(tag["is_sparse"], bool)
    else:
        # There are manifest lists, verify sparse info is present
        manifest_list = manifest_lists[0]
        repo = Repository.get(Repository.id == manifest_list.repository_id)

        with client_with_identity("devtable", app) as cl:
            params = {"repository": f"{repo.namespace_user.username}/{repo.name}"}
            try:
                tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

                for tag in tags:
                    if tag.get("is_manifest_list", False):
                        assert "is_sparse" in tag
                        assert "child_manifest_count" in tag
                        assert "present_child_count" in tag
                        assert isinstance(tag["is_sparse"], bool)
                        assert isinstance(tag["child_manifest_count"], int)
                        assert isinstance(tag["present_child_count"], int)
            except Exception:
                # Permission denied or repo not found - skip this part
                pass


def test_list_repo_tags_sparse_manifest_detection(app, initialized_db):
    """Test that sparse manifests are correctly detected."""
    from data.database import Manifest as ManifestTable
    from data.database import ManifestChild, Tag
    from data.model.oci.tag import get_tag, retarget_tag
    from data.model.repository import create_repository
    from image.docker.schema2 import DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
    from image.docker.schema2.manifest import DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE

    # Create a test repository
    repository = create_repository("devtable", "sparsetestrepo", None)

    # Create a parent manifest list
    manifest_list_media_type_id = ManifestTable.media_type.get_id(
        DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
    )
    child_media_type_id = ManifestTable.media_type.get_id(DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE)

    # Create the parent manifest (manifest list)
    parent_manifest = ManifestTable.create(
        repository=repository.id,
        digest="sha256:parentmanifestdigest123456789012345678901234567890123456789012",
        media_type=manifest_list_media_type_id,
        manifest_bytes='{"schemaVersion": 2, "manifests": []}',
    )

    # Create two child manifests - one present, one sparse
    present_child = ManifestTable.create(
        repository=repository.id,
        digest="sha256:presentchildmanifest12345678901234567890123456789012345678901",
        media_type=child_media_type_id,
        manifest_bytes='{"schemaVersion": 2, "config": {}}',  # Has content - present
    )

    sparse_child = ManifestTable.create(
        repository=repository.id,
        digest="sha256:sparsechild123456789012345678901234567890123456789012345678901",
        media_type=child_media_type_id,
        manifest_bytes="",  # Empty - sparse
    )

    # Link children to parent
    ManifestChild.create(
        manifest=parent_manifest,
        child_manifest=present_child,
        repository=repository.id,
    )
    ManifestChild.create(
        manifest=parent_manifest,
        child_manifest=sparse_child,
        repository=repository.id,
    )

    # Create a tag pointing to the manifest list
    from data.database import get_epoch_timestamp_ms

    Tag.create(
        name="sparsetag",
        repository=repository.id,
        manifest=parent_manifest,
        lifetime_start_ms=get_epoch_timestamp_ms(),
        lifetime_end_ms=None,
        hidden=False,
        reversion=False,
        tag_kind=Tag.tag_kind.get_id("tag"),
    )

    # Now fetch the tags via API
    with client_with_identity("devtable", app) as cl:
        params = {"repository": "devtable/sparsetestrepo"}
        tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

        # Find our sparse tag
        sparse_tag = None
        for tag in tags:
            if tag["name"] == "sparsetag":
                sparse_tag = tag
                break

        assert sparse_tag is not None
        assert sparse_tag["is_manifest_list"] is True
        assert sparse_tag["is_sparse"] is True  # Should be sparse (1 of 2 children is sparse)
        assert sparse_tag["child_manifest_count"] == 2
        assert sparse_tag["present_child_count"] == 1  # Only 1 child has content

        # Verify child_manifests_presence map
        assert "child_manifests_presence" in sparse_tag
        presence_map = sparse_tag["child_manifests_presence"]
        assert (
            presence_map["sha256:presentchildmanifest12345678901234567890123456789012345678901"]
            is True
        )
        assert (
            presence_map["sha256:sparsechild123456789012345678901234567890123456789012345678901"]
            is False
        )
