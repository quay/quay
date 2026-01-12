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
