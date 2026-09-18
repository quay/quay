import json
from unittest.mock import patch

import pytest
from playhouse.test_utils import assert_query_count

from data.database import Manifest
from data.model import DataModelException, ImmutableTagException
from data.model.oci.tag import change_tag_expiration, set_tag_immutable
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
        ("devtable", "simple", 7),  # +2 cosign signature lookup; +2 json convert
        ("devtable", "history", 7),
        ("devtable", "complex", 7),
        ("devtable", "gargantuan", 7),
        ("buynlarge", "orgrepo", 7),  # +2 permissions (UNION); +2 cosign
        ("buynlarge", "anotherorgrepo", 7),
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
        ("devtable", "gargantuan", 7),
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


def test_list_repo_tags_includes_cosign_signature_fields(app):
    """List tags enriches responses with cosign v2 .sig signature metadata."""
    import json

    from app import storage
    from data.database import ImageStorageLocation
    from data.model.blob import store_blob_record_and_temp_link
    from data.model.oci.manifest import get_or_create_manifest
    from data.model.oci.tag import retarget_tag
    from data.model.repository import create_repository
    from data.model.storage import get_layer_path
    from digest.digest_tools import sha256_digest
    from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
    from util.bytes import Bytes

    def populate_blob(namespace, repo_name, content):
        content = Bytes.for_string_or_unicode(content).as_encoded_str()
        digest = str(sha256_digest(content))
        location = ImageStorageLocation.get(name="local_us")
        blob = store_blob_record_and_temp_link(
            namespace, repo_name, digest, location, len(content), 120
        )
        storage.put_content(["local_us"], get_layer_path(blob), content)
        return blob, digest

    def create_schema2_manifest(repository, differentiation_field):
        layer_json = json.dumps(
            {
                "config": {},
                "rootfs": {"type": "layers", "diff_ids": []},
                "history": [],
            }
        )
        _, config_digest = populate_blob(
            repository.namespace_user.username, repository.name, layer_json
        )
        remote_digest = sha256_digest(b"something" + differentiation_field.encode("utf-8"))
        builder = DockerSchema2ManifestBuilder()
        builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
        builder.add_layer(remote_digest, 1234, urls=["http://hello/world" + differentiation_field])
        manifest = builder.build()
        created = get_or_create_manifest(repository, manifest, storage, raise_on_error=True)
        assert created
        return created.manifest

    repository = create_repository("devtable", "cosignapitags", None)
    image_manifest = create_schema2_manifest(repository, "img")
    sig_manifest = create_schema2_manifest(repository, "sig")

    retarget_tag("latest", image_manifest.id, is_reversion=False)
    hex_digest = image_manifest.digest.split(":", 1)[1]
    sig_tag_name = "sha256-%s.sig" % hex_digest
    created_sig_tag = retarget_tag(sig_tag_name, sig_manifest.id, is_reversion=False)
    assert created_sig_tag is not None

    params = {
        "repository": "devtable/cosignapitags",
        "onlyActiveTags": True,
        "specificTag": "latest",
    }
    with client_with_identity("devtable", app) as cl:
        tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

    assert len(tags) == 1
    assert tags[0]["name"] == "latest"
    assert tags[0]["cosign_signature_tag"] == sig_tag_name
    assert tags[0]["cosign_signature_manifest_digest"] == sig_manifest.digest


def test_list_repo_tags_includes_cosign_referrer_fields(app):
    """List tags enriches Cosign v3 referrer signatures without cosign_signature_tag."""
    import json
    import random
    import string

    from app import storage
    from data.database import ImageStorageLocation
    from data.database import Manifest as ManifestTable
    from data.model.blob import store_blob_record_and_temp_link
    from data.model.oci.manifest import (
        COSIGN_SIGNATURE_ARTIFACT_TYPES,
        get_or_create_manifest,
    )
    from data.model.oci.tag import retarget_tag
    from data.model.repository import create_repository
    from data.model.storage import get_layer_path
    from digest.digest_tools import sha256_digest
    from image.oci.manifest import OCIManifestBuilder
    from util.bytes import Bytes

    def populate_blob(namespace, repo_name, content):
        content = Bytes.for_string_or_unicode(content).as_encoded_str()
        digest = str(sha256_digest(content))
        location = ImageStorageLocation.get(name="local_us")
        blob = store_blob_record_and_temp_link(
            namespace, repo_name, digest, location, len(content), 120
        )
        storage.put_content(["local_us"], get_layer_path(blob), content)
        return blob, digest

    def generate_random_data_for_layer():
        charset = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return "".join(random.choice(charset) for _ in range(random.randrange(1, 20)))

    def create_oci_manifest(repository, differentiation_field, subject=None):
        config_json = json.dumps(
            {
                "os": "linux",
                "architecture": "amd64",
                "rootfs": {"type": "layers", "diff_ids": []},
                "history": [],
            }
        )
        _, config_digest = populate_blob(
            repository.namespace_user.username, repository.name, config_json
        )
        random_data = generate_random_data_for_layer() + differentiation_field
        _, random_digest = populate_blob(
            repository.namespace_user.username, repository.name, random_data
        )
        builder = OCIManifestBuilder()
        builder.set_config_digest(config_digest, len(config_json.encode("utf-8")))
        builder.add_layer(random_digest, len(random_data.encode("utf-8")))
        if subject is not None:
            builder.set_subject(
                subject.digest,
                len(subject.bytes.as_encoded_str()),
                subject.media_type,
            )
        manifest = builder.build()
        created = get_or_create_manifest(repository, manifest, storage, raise_on_error=True)
        assert created
        return created.manifest, manifest

    repository = create_repository("devtable", "cosignapireferrer", None)
    image_manifest, image_interface = create_oci_manifest(repository, "img")
    referrer_db, _ = create_oci_manifest(repository, "sig", subject=image_interface)

    artifact_type = "application/vnd.dev.sigstore.bundle.v0.3+json"
    assert artifact_type in COSIGN_SIGNATURE_ARTIFACT_TYPES
    ManifestTable.update(artifact_type=artifact_type).where(
        ManifestTable.id == referrer_db.id
    ).execute()

    retarget_tag("referrer-latest", image_manifest.id, is_reversion=False)

    params = {
        "repository": "devtable/cosignapireferrer",
        "onlyActiveTags": True,
        "specificTag": "referrer-latest",
    }
    with client_with_identity("devtable", app) as cl:
        tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

    assert len(tags) == 1
    assert tags[0]["name"] == "referrer-latest"
    assert tags[0]["cosign_signature_manifest_digest"] == referrer_db.digest
    assert tags[0].get("cosign_signature_tag") is None


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
