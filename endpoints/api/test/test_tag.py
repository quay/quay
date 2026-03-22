import json
import random
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from playhouse.test_utils import assert_query_count

from app import storage
from data.database import ImageStorage, ImageStorageLocation, Manifest, ManifestBlob
from data.model import DataModelException, ImmutableTagException, oci
from data.model.blob import store_blob_record_and_temp_link
from data.model.oci.tag import change_tag_expiration, set_tag_immutable
from data.model.repository import create_repository
from data.model.storage import get_layer_path
from data.model.user import get_user
from data.registry_model import registry_model
from digest import digest_tools
from endpoints.api.tag import ListRepositoryTags, RepositoryTag, RestoreTag
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, toggle_feature
from image.docker.schema1 import DockerSchema1Manifest
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from image.oci.manifest import OCIManifestBuilder
from test.fixtures import *
from util.bytes import Bytes


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
        ("devtable", "simple", 5),  # +2 for converting object to and from json
        ("devtable", "history", 5),  # +2 for converting object to and from json
        ("devtable", "complex", 5),  # +2 for converting object to and from json
        ("devtable", "gargantuan", 5),  # +2 for converting object to and from json
        ("buynlarge", "orgrepo", 7),  # +2 for permissions checks (uses UNION).
        ("buynlarge", "anotherorgrepo", 7),  # +2 for permissions checks (uses UNION).
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
        ("devtable", "gargantuan", 5),  # +2 for converting object to and from json
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
    from data.database import Repository
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
        manifest_bytes=json.dumps(
            {
                "schemaVersion": 2,
                "manifests": [
                    {
                        "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                        "digest": "sha256:presentchildmanifest12345678901234567890123456789012345678901",
                        "size": 100,
                    },
                    {
                        "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                        "digest": "sha256:sparsechild123456789012345678901234567890123456789012345678901",
                        "size": 100,
                    },
                ],
            }
        ),
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


def test_sparse_detection_without_manifest_child_entries(app, initialized_db):
    """
    Test sparse detection when ManifestChild entries are missing (mirror scenario).

    When a mirror repository uses architecture filtering, only mirrored architectures
    get ManifestChild entries. Non-mirrored architectures have neither ManifestChild
    nor Manifest rows. The sparse detection must still correctly identify these as
    missing by parsing the manifest list JSON.
    """
    from data.database import Manifest as ManifestTable
    from data.database import ManifestChild, Tag
    from data.model.repository import create_repository
    from image.docker.schema2 import DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
    from image.docker.schema2.manifest import DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE

    repository = create_repository("devtable", "mirrorsparse", None)

    manifest_list_media_type_id = ManifestTable.media_type.get_id(
        DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
    )
    child_media_type_id = ManifestTable.media_type.get_id(DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE)

    amd64_digest = "sha256:amd64manifest1234567890123456789012345678901234567890123456789012"
    arm64_digest = "sha256:arm64manifest1234567890123456789012345678901234567890123456789012"
    s390x_digest = "sha256:s390xmanifest1234567890123456789012345678901234567890123456789012"

    # Parent manifest list references 3 architectures
    parent_manifest = ManifestTable.create(
        repository=repository.id,
        digest="sha256:mirrorparent12345678901234567890123456789012345678901234567890123",
        media_type=manifest_list_media_type_id,
        manifest_bytes=json.dumps(
            {
                "schemaVersion": 2,
                "manifests": [
                    {
                        "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                        "digest": amd64_digest,
                        "size": 100,
                    },
                    {
                        "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                        "digest": arm64_digest,
                        "size": 100,
                    },
                    {
                        "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                        "digest": s390x_digest,
                        "size": 100,
                    },
                ],
            }
        ),
    )

    # Only amd64 was mirrored — it has a Manifest row and a ManifestChild entry
    amd64_child = ManifestTable.create(
        repository=repository.id,
        digest=amd64_digest,
        media_type=child_media_type_id,
        manifest_bytes='{"schemaVersion": 2, "config": {}}',
    )
    ManifestChild.create(
        manifest=parent_manifest,
        child_manifest=amd64_child,
        repository=repository.id,
    )

    # arm64 and s390x were NOT mirrored — no Manifest rows, no ManifestChild entries

    from data.database import get_epoch_timestamp_ms

    Tag.create(
        name="mirrortag",
        repository=repository.id,
        manifest=parent_manifest,
        lifetime_start_ms=get_epoch_timestamp_ms(),
        lifetime_end_ms=None,
        hidden=False,
        reversion=False,
        tag_kind=Tag.tag_kind.get_id("tag"),
    )

    with client_with_identity("devtable", app) as cl:
        params = {"repository": "devtable/mirrorsparse"}
        tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

        mirror_tag = next((t for t in tags if t["name"] == "mirrortag"), None)
        assert mirror_tag is not None
        assert mirror_tag["is_manifest_list"] is True
        assert mirror_tag["is_sparse"] is True
        assert mirror_tag["child_manifest_count"] == 3
        assert mirror_tag["present_child_count"] == 1

        presence_map = mirror_tag["child_manifests_presence"]
        assert presence_map[amd64_digest] is True
        assert presence_map[arm64_digest] is False
        assert presence_map[s390x_digest] is False


# Expiration/Immutability Conflict Tests


@pytest.mark.usefixtures("app")
def test_change_tag_expiration_blocked_on_immutable_tag():
    """Test that setting expiration on immutable tag raises ImmutableTagException."""
    from datetime import datetime, timedelta

    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        # Try to set expiration - should raise ImmutableTagException
        future_date = datetime.utcnow() + timedelta(days=7)
        with patch.dict(
            "data.model.oci.tag.config.app_config", {"FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE": False}
        ):
            with pytest.raises(ImmutableTagException) as exc_info:
                change_tag_expiration(tag_ref.id, future_date)
            assert "set expiration on" in str(exc_info.value)

        # Clean up
        set_tag_immutable(repo_ref.id, "latest", False)


@pytest.mark.usefixtures("app")
def test_change_tag_expiration_allowed_when_config_permits():
    """Test that setting expiration on immutable tag succeeds when FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE is True."""
    from datetime import datetime, timedelta

    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        # Set expiration - should succeed when config allows
        future_date = datetime.utcnow() + timedelta(days=7)
        with patch.dict(
            "data.model.oci.tag.config.app_config", {"FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE": True}
        ):
            _prev_exp, success = change_tag_expiration(tag_ref.id, future_date)
            assert success is True

        # Clean up
        set_tag_immutable(repo_ref.id, "latest", False)
        change_tag_expiration(tag_ref.id, None)


@pytest.mark.usefixtures("app")
def test_set_tag_immutable_blocked_on_expiring_tag():
    """Test that making an expiring tag immutable raises DataModelException."""
    from datetime import datetime, timedelta

    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")

        # Set expiration on the tag first
        future_date = datetime.utcnow() + timedelta(days=7)
        with patch.dict(
            "data.model.oci.tag.config.app_config", {"FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE": False}
        ):
            change_tag_expiration(tag_ref.id, future_date)

            # Try to make it immutable - should raise DataModelException
            with pytest.raises(DataModelException) as exc_info:
                set_tag_immutable(repo_ref.id, "latest", True)
            assert "has expiration set" in str(exc_info.value)

        # Clean up
        change_tag_expiration(tag_ref.id, None)


@pytest.mark.usefixtures("app")
def test_set_tag_immutable_allowed_when_config_permits():
    """Test that making an expiring tag immutable succeeds when FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE is True."""
    from datetime import datetime, timedelta

    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag_ref = registry_model.get_repo_tag(repo_ref, "latest")

        # Set expiration on the tag first
        future_date = datetime.utcnow() + timedelta(days=7)
        with patch.dict(
            "data.model.oci.tag.config.app_config", {"FEATURE_IMMUTABLE_TAGS_CAN_EXPIRE": True}
        ):
            change_tag_expiration(tag_ref.id, future_date)

            # Make it immutable - should succeed when config allows
            _prev_immutable, success = set_tag_immutable(repo_ref.id, "latest", True)
            assert success is True

        # Clean up
        set_tag_immutable(repo_ref.id, "latest", False)
        change_tag_expiration(tag_ref.id, None)


def test_tag_created_timestamp_schema1(app, initialized_db):
    """
    Verifies that the created timestamp can be extracted from the Docker v2 schema 1 manifest. The value
    is embedded into the v1Compatibility field.
    """
    layer_bytes = random.randbytes(1024)
    layer_digest = digest_tools.sha256_digest(layer_bytes)

    user = get_user("devtable")
    repo = create_repository("devtable", "test-image-built-schema1", user)
    assert repo is not None

    layer_blob = ImageStorage.create(
        content_checksum=layer_digest,
        image_size=len(layer_bytes),
        compressed_size=len(layer_bytes),
    )

    location = ImageStorageLocation.get(name="local_us")
    store_blob_record_and_temp_link(
        "devtable",
        "test-image-built-schema1",
        layer_digest,
        location,
        len(layer_bytes),
        120,
    )

    schema1_manifest_json = {
        "schemaVersion": 1,
        "name": "devtable/test-image-built-schema1",
        "tag": "schema1-tag",
        "architecture": "amd64",
        "fsLayers": [
            {
                "blobSum": layer_digest,
            },
        ],
        "history": [
            {
                "v1Compatibility": json.dumps(
                    {
                        "id": "abc123",
                        "created": "2024-01-15T10:30:45.123456789Z",
                        "container_config": {
                            "Cmd": ["/bin/sh"],
                        },
                        "architecture": "amd64",
                        "os": "linux",
                    }
                ),
            },
        ],
    }
    manifest_bytes = Bytes.for_string_or_unicode(json.dumps(schema1_manifest_json))

    manifest = DockerSchema1Manifest(manifest_bytes)
    created_manifest = oci.manifest.get_or_create_manifest(
        repo.id,
        manifest,
        storage,
    )

    test_tag_name = "schema1-tag"
    tag = oci.tag.retarget_tag(test_tag_name, created_manifest.manifest.id, raise_on_error=True)
    assert tag is not None

    # call the tag api and check if image_built is available
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/test-image-built-schema1",
        }
        result = conduct_api_call(cl, ListRepositoryTags, "GET", params, None, 200).json
        test_tag = next((t for t in result["tags"] if t["name"] == test_tag_name), None)
        assert test_tag is not None
        assert "image_built" in test_tag
        assert test_tag["image_built"] == "2024-01-15T10:30:45.123456789Z"


def test_tag_created_timestamp_schema2(app, initialized_db):
    """
    Verifies that the created timestamp can be extracted from the Docker v2 schema 2 manifest. The value, if exists,
    is part of the config blob.
    """
    user = get_user("devtable")
    repo = create_repository("devtable", "test-image-built-schema2", user)
    assert repo is not None

    layer_bytes = random.randbytes(1024)
    layer_digest = digest_tools.sha256_digest(layer_bytes)

    config_json = {
        "architecture": "amd64",
        "os": "linux",
        "created": "2024-02-20T14:25:30.987654321Z",
        "config": {"Env": ["PATH=/usr/local/bin:/usr/bin"]},
        "rootfs": {
            "type": "layers",
            "diff_ids": [
                layer_digest,
            ],
        },
        "history": [
            {
                "created": "2024-02-20T14:25:30.987654321Z",
                "created_by": '/bin/sh -c # (NOP) CMD ["sh"]',
            },
        ],
    }

    config_bytes = json.dumps(config_json).encode("utf-8")
    config_digest = digest_tools.sha256_digest(config_bytes)
    location = ImageStorageLocation.get(name="local_us")

    # create blob records in the database
    config_blob = store_blob_record_and_temp_link(
        "devtable",
        "test-image-built-schema2",
        config_digest,
        location,
        len(config_bytes),
        120,
    )
    layer_blob = store_blob_record_and_temp_link(
        "devtable",
        "test-image-built-schema2",
        layer_digest,
        location,
        len(layer_bytes),
        120,
    )

    # store created blobs
    storage.put_content(
        ["local_us"],
        get_layer_path(config_blob),
        config_bytes,
    )
    storage.put_content(
        ["local_us"],
        get_layer_path(layer_blob),
        layer_bytes,
    )

    # build manifest
    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(config_digest, len(config_bytes))
    builder.add_layer(layer_digest, len(layer_bytes))
    manifest_obj = builder.build()

    # create manifest
    created_manifest = oci.manifest.get_or_create_manifest(
        repo.id,
        manifest_obj,
        storage,
        raise_on_error=True,
    )
    assert created_manifest is not None

    # create test tag based on provided manifest
    test_tag_name = "schema2-created-tag"
    tag = oci.tag.retarget_tag(
        test_tag_name,
        created_manifest.manifest.id,
        raise_on_error=True,
    )
    assert tag is not None

    # call API and verify that build timestamp can be read
    params = {
        "repository": "devtable/test-image-built-schema2",
    }
    with client_with_identity("devtable", app) as cl:
        result = conduct_api_call(cl, ListRepositoryTags, "GET", params, None, 200).json
        test_tag = next((t for t in result["tags"] if t["name"] == test_tag_name), None)
        assert test_tag is not None
        assert "image_built" in test_tag
        assert test_tag["image_built"] == "2024-02-20T14:25:30.987654321Z"


def test_tag_created_timestamp_oci_image(app, initialized_db):
    """
    Verifies that the created timestamp can be extracted from the OCI image manifest. The value, if exists,
    is part of the config blob.
    """
    user = get_user("devtable")
    repo = create_repository("devtable", "test-image-built-oci", user)
    assert repo is not None

    layer_bytes = random.randbytes(1024)
    layer_digest = digest_tools.sha256_digest(layer_bytes)

    config_json = {
        "architecture": "amd64",
        "os": "linux",
        "created": "2024-02-20T14:25:30.987654321Z",
        "config": {"Env": ["PATH=/usr/local/bin:/usr/bin"]},
        "rootfs": {
            "type": "layers",
            "diff_ids": [
                layer_digest,
            ],
        },
        "history": [
            {
                "created": "2024-02-20T14:25:30.987654321Z",
                "created_by": '/bin/sh -c # (NOP) CMD ["sh"]',
            },
        ],
    }

    config_bytes = json.dumps(config_json).encode("utf-8")
    config_digest = digest_tools.sha256_digest(config_bytes)
    location = ImageStorageLocation.get(name="local_us")

    # create blob records in the database
    config_blob = store_blob_record_and_temp_link(
        "devtable",
        "test-image-built-oci",
        config_digest,
        location,
        len(config_bytes),
        120,
    )
    layer_blob = store_blob_record_and_temp_link(
        "devtable",
        "test-image-built-oci",
        layer_digest,
        location,
        len(layer_bytes),
        120,
    )

    # store created blobs
    storage.put_content(
        ["local_us"],
        get_layer_path(config_blob),
        config_bytes,
    )
    storage.put_content(
        ["local_us"],
        get_layer_path(layer_blob),
        layer_bytes,
    )

    # build manifest
    builder = OCIManifestBuilder()
    builder.set_config_digest(config_digest, len(config_bytes))
    builder.add_layer(layer_digest, len(layer_bytes))
    manifest_obj = builder.build()

    # create manifest
    created_manifest = oci.manifest.get_or_create_manifest(
        repo.id,
        manifest_obj,
        storage,
        raise_on_error=True,
    )
    assert created_manifest is not None

    # create test tag based on provided manifest
    test_tag_name = "schema2-created-tag"
    tag = oci.tag.retarget_tag(
        test_tag_name,
        created_manifest.manifest.id,
        raise_on_error=True,
    )
    assert tag is not None

    # call API and verify that build timestamp can be read
    params = {
        "repository": "devtable/test-image-built-oci",
    }
    with client_with_identity("devtable", app) as cl:
        result = conduct_api_call(cl, ListRepositoryTags, "GET", params, None, 200).json
        test_tag = next((t for t in result["tags"] if t["name"] == test_tag_name), None)
        assert test_tag is not None
        assert "image_built" in test_tag
        assert test_tag["image_built"] == "2024-02-20T14:25:30.987654321Z"
