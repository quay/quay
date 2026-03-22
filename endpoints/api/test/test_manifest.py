import json
import random
from datetime import datetime

from mock import patch

from app import app as realapp
from app import storage as app_storage
from data.database import ImageStorage, ImageStorageLocation
from data.database import Manifest as ManifestTable
from data.database import ManifestPullStatistics, MediaType, TagPullStatistics
from data.model import oci
from data.model import storage as storage_model
from data.model.blob import store_blob_record_and_temp_link
from data.model.repository import create_repository
from data.model.user import get_user
from data.registry_model import registry_model
from digest.digest_tools import sha256_digest
from endpoints.api.manifest import RepositoryManifest, _get_modelcard_layer_digest
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue
from image.docker.schema2.list import DockerSchema2ManifestListBuilder
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from image.oci.index import OCIIndexBuilder
from image.oci.manifest import OCIManifest, OCIManifestBuilder
from test.fixtures import *
from util.bytes import Bytes


def test_repository_manifest(app):
    with client_with_identity("devtable", app) as cl:
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        assert repo_ref is not None, "Repository not found"

        tags = registry_model.list_all_active_repository_tags(repo_ref)
        for tag in tags:
            if tag is None:
                continue
            manifest_digest = tag.manifest_digest
            if manifest_digest is None:
                continue

            params = {
                "repository": "devtable/simple",
                "manifestref": manifest_digest,
            }
            result = conduct_api_call(cl, RepositoryManifest, "GET", params, None, 200).json
            assert result["digest"] == manifest_digest
            assert result["manifest_data"]


ARTIFACT_MANIFEST = """{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "artifactType": "application/vnd.example+type",
  "config": {
    "mediaType": "application/vnd.oci.empty.v1+json",
    "digest": "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61c12345",
    "size": 2,
    "data": "k10="
  },
  "layers": [
    {
      "mediaType": "text/markdown",
      "digest": "sha256:01196d075d7712211cb75f29a9c50c158c1df18639871a73aba777f2f0412345",
      "size": 9283,
      "annotations": {
        "org.opencontainers.image.title": "cake.txt"
      }
    },
    {
      "mediaType": "application/json",
      "digest": "sha256:2f2bba45146f073a7b8a097cb6133a6b4b66d5751e73f2a2aca8108328112345",
      "size": 1020,
      "annotations": {
        "org.opencontainers.image.title": "special_tokens_map.json"
      }
    },
    {
      "mediaType": "application/json",
      "digest": "sha256:d3b4df07a0ce3940b15c77e2ea17ab5627ca0c4bf982d2eb37966aea0a812345",
      "size": 2057451,
      "annotations": {
        "org.opencontainers.image.title": "tokenizer.json"
      }
    },
    {
      "mediaType": "application/json",
      "digest": "sha256:f533a8dbb8526be9e8f5b218e6d7be21cb4ce6fd2068286ab7e78d98ecc12345",
      "size": 4540,
      "annotations": {
        "org.opencontainers.image.title": "tokenizer_config.json"
      }
    }
  ],
  "annotations": {
    "org.opencontainers.image.created": "2025-01-31T18:20:30Z"
  }
}
 """

IMAGE_MANIFEST = """{
  "schemaVersion": 2,
  "config": {
    "mediaType": "application/vnd.oci.image.config.v1+json",
    "digest": "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "size": 2,
    "annotations": {
      "hello": "world"
    }
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar",
      "digest": "sha256:22af0898315a239117308d39acd80636326c4987510b0ec6848e58eb584ba82e",
      "size": 6,
      "annotations": {
        "fun": "more cream",
        "org.opencontainers.image.title": "cake.txt"
      }
    },
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar",
      "digest": "sha256:be6fe11876282442bead98e8b24aca07f8972a763cd366c56b4b5f7bcdd23eac",
      "size": 7,
      "annotations": {
        "org.opencontainers.image.title": "juice.txt"
      }
    }
  ],
  "annotations": {
    "foo": "bar"
  }
}"""


def test_modelcar_layer(app):
    manifest1 = OCIManifest(Bytes.for_string_or_unicode(ARTIFACT_MANIFEST))
    manifest2 = OCIManifest(Bytes.for_string_or_unicode(IMAGE_MANIFEST))

    realapp.config["UI_MODELCARD_ANNOTATION"] = {"foo": "bar"}
    realapp.config["UI_MODELCARD_LAYER_ANNOTATION"] = {"org.opencontainers.image.title": "cake.txt"}
    realapp.config["UI_MODELCARD_ARTIFACT_TYPE"] = "application/vnd.example+type"

    with patch("features.UI_MODELCARD", FeatureNameValue("UI_MODELCARD", True)):
        layer_digest1 = _get_modelcard_layer_digest(manifest1)
        assert (
            layer_digest1
            == "sha256:01196d075d7712211cb75f29a9c50c158c1df18639871a73aba777f2f0412345"
        )

        layer_digest2 = _get_modelcard_layer_digest(manifest2)
        assert (
            layer_digest2
            == "sha256:22af0898315a239117308d39acd80636326c4987510b0ec6848e58eb584ba82e"
        )


def test_repository_manifest_pull_statistics_with_data(app, initialized_db):
    """Test getting pull statistics for a manifest when data exists."""
    # Test the pull statistics retrieval directly via the model layer
    from data.model.pull_statistics import get_manifest_pull_statistics

    repo_ref = registry_model.lookup_repository("devtable", "simple")
    assert repo_ref is not None, "Repository not found"

    tags = registry_model.list_all_active_repository_tags(repo_ref)

    manifest_digest = None
    for tag in tags:
        if tag and tag.manifest_digest:
            manifest_digest = tag.manifest_digest
            break

    assert manifest_digest is not None, "No manifest found in test repository"

    # Create test pull statistics
    ManifestPullStatistics.create(
        repository=repo_ref._db_id,
        manifest_digest=manifest_digest,
        manifest_pull_count=42,
        last_manifest_pull_date=datetime(2024, 1, 15, 10, 30, 0),
    )

    # Test data model layer
    stats = get_manifest_pull_statistics(repo_ref.id, manifest_digest)
    assert stats is not None
    assert stats["manifest_digest"] == manifest_digest
    assert stats["pull_count"] == 42
    assert stats["last_pull_date"] is not None


def test_repository_manifest_pull_statistics_no_data(app, initialized_db):
    """Test getting pull statistics for a manifest when no data exists."""
    from data.model.pull_statistics import get_manifest_pull_statistics

    repo_ref = registry_model.lookup_repository("devtable", "simple")
    assert repo_ref is not None, "Repository not found"

    tags = registry_model.list_all_active_repository_tags(repo_ref)

    manifest_digest = None
    for tag in tags:
        if tag and tag.manifest_digest:
            manifest_digest = tag.manifest_digest
            break

    assert manifest_digest is not None, "No manifest found in test repository"

    # Don't create any pull statistics - test default behavior (should return None)
    stats = get_manifest_pull_statistics(repo_ref.id, manifest_digest)
    assert stats is None


def test_repository_manifest_pull_statistics_nonexistent(app, initialized_db):
    """Test getting pull statistics for a nonexistent manifest."""
    from data.model.pull_statistics import get_manifest_pull_statistics

    repo_ref = registry_model.lookup_repository("devtable", "simple")
    assert repo_ref is not None, "Repository not found"

    # Test with nonexistent digest
    stats = get_manifest_pull_statistics(
        repo_ref.id, "sha256:nonexistent1234567890abcdef1234567890abcdef1234567890abcdef12345678"
    )
    assert stats is None


def test_repository_manifest_pull_statistics_multiple_pulls(app, initialized_db):
    """Test that pull statistics reflect multiple pull events."""
    from data.model.pull_statistics import get_manifest_pull_statistics

    repo_ref = registry_model.lookup_repository("devtable", "simple")
    assert repo_ref is not None, "Repository not found"

    tags = registry_model.list_all_active_repository_tags(repo_ref)

    manifest_digest = None
    for tag in tags:
        if tag and tag.manifest_digest:
            manifest_digest = tag.manifest_digest
            break

    assert manifest_digest is not None

    # Create test pull statistics with higher counts
    ManifestPullStatistics.create(
        repository=repo_ref._db_id,
        manifest_digest=manifest_digest,
        manifest_pull_count=150,
        last_manifest_pull_date=datetime(2024, 2, 20, 14, 45, 0),
    )

    # Verify higher pull count
    stats = get_manifest_pull_statistics(repo_ref.id, manifest_digest)
    assert stats is not None
    assert stats["pull_count"] == 150
    assert stats["last_pull_date"] is not None


def _generate_config_layer(arch, layer_digest):
    """
    Helper function for generating config layer. Returns a config layer bytes and config layer digest
    tuple to the main test function.
    """
    config = {
        "architecture": arch,
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
    config_bytes = json.dumps(config).encode("utf-8")
    return config_bytes, sha256_digest(config_bytes)


def test_enrich_child_manifests_with_timestamps(app, initialized_db):
    """
    Verifies that the API is returning the enriched manifest list data with built timestamps for each
    individual child manifest.
    """
    layer_bytes = random.randbytes(1024)
    layer_digest = sha256_digest(layer_bytes)

    user = get_user("devtable")
    repo = create_repository("devtable", "test-manifest-list-parsing", user)
    assert repo is not None

    location = ImageStorageLocation.get(name="local_us")

    # Generate config layers
    config_amd64_bytes, config_amd64_digest = _generate_config_layer("amd64", layer_digest)
    config_arm64_bytes, config_arm64_digest = _generate_config_layer("arm64", layer_digest)

    # Store shared layer between two manifests
    shared_layer = ImageStorage.create(
        content_checksum=layer_digest,
        image_size=len(layer_bytes),
        compressed_size=len(layer_bytes),
    )
    layer_blob = store_blob_record_and_temp_link(
        "devtable",
        "test-manifest-list-parsing",
        layer_digest,
        location,
        len(layer_bytes),
        3600,
    )
    app_storage.put_content(
        ["local_us"],
        storage_model.get_layer_path(layer_blob),
        layer_bytes,
    )

    # Store config blobs
    blob_amd64 = store_blob_record_and_temp_link(
        "devtable",
        "test-manifest-list-parsing",
        config_amd64_digest,
        location,
        len(config_amd64_bytes),
        3600,
    )
    blob_arm64 = store_blob_record_and_temp_link(
        "devtable",
        "test-manifest-list-parsing",
        config_arm64_digest,
        location,
        len(config_arm64_bytes),
        3600,
    )

    # Write both config blobs to storage
    app_storage.put_content(
        ["local_us"],
        storage_model.get_layer_path(blob_amd64),
        config_amd64_bytes,
    )
    app_storage.put_content(
        ["local_us"],
        storage_model.get_layer_path(blob_arm64),
        config_arm64_bytes,
    )

    # Define builders
    builder_amd64_docker = DockerSchema2ManifestBuilder()
    builder_arm64_docker = DockerSchema2ManifestBuilder()
    builder_amd64_oci = OCIManifestBuilder()
    builder_arm64_oci = OCIManifestBuilder()

    # First we'll build a Docker v2 schema 2 image
    # for AMD64
    builder_amd64_docker.set_config_digest(config_amd64_digest, len(config_amd64_bytes))
    builder_amd64_docker.add_layer(layer_digest, len(layer_bytes))
    child_amd64_docker_manifest_obj = builder_amd64_docker.build()
    created_amd64 = oci.manifest.get_or_create_manifest(
        repo.id,
        child_amd64_docker_manifest_obj,
        app_storage,
        raise_on_error=True,
    )
    assert created_amd64 is not None

    # for Arm64
    builder_arm64_docker.set_config_digest(config_arm64_digest, len(config_arm64_bytes))
    builder_arm64_docker.add_layer(layer_digest, len(layer_bytes))
    child_arm64_docker_manifest_obj = builder_arm64_docker.build()
    created_arm64 = oci.manifest.get_or_create_manifest(
        repo.id,
        child_arm64_docker_manifest_obj,
        app_storage,
        raise_on_error=True,
    )
    assert created_arm64 is not None

    # Build Docker v2 manifest list from the two manifests
    list_builder_docker = DockerSchema2ManifestListBuilder()
    list_builder_docker.add_manifest(child_amd64_docker_manifest_obj, "amd64", "linux")
    list_builder_docker.add_manifest(child_arm64_docker_manifest_obj, "arm64", "linux")
    manifest_list = list_builder_docker.build()
    assert manifest_list is not None

    # Create manifest list in db
    created_list = oci.manifest.get_or_create_manifest(repo.id, manifest_list, app_storage)
    assert created_list is not None

    # Add tag for the manifest list
    tag = oci.tag.retarget_tag("latest", created_list.manifest.id, raise_on_error=True)
    assert tag is not None

    # call api
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/test-manifest-list-parsing",
            "manifestref": created_list.manifest.digest,
        }
        result = conduct_api_call(cl, RepositoryManifest, "GET", params, None, 200).json
        # Verify basic properties
        assert result["digest"] == created_list.manifest.digest
        assert result["is_manifest_list"] is True
        assert "manifests" in result

        # verify child manifests
        manifests = result["manifests"]
        assert len(manifests) == 2
        amd64_entry = next((m for m in manifests if m["platform"]["architecture"] == "amd64"), None)
        arm64_entry = next((m for m in manifests if m["platform"]["architecture"] == "arm64"), None)

        assert amd64_entry is not None
        assert arm64_entry is not None

        # verify we have timestamps and other attributes
        # for amd64 image
        assert "image_built" in amd64_entry
        assert amd64_entry["image_built"] == "2024-02-20T14:25:30.987654321Z"
        assert amd64_entry["platform"]["os"] == "linux"
        assert amd64_entry["digest"] == created_amd64.manifest.digest

        # for arm64 image
        assert "image_built" in arm64_entry
        assert arm64_entry["image_built"] == "2024-02-20T14:25:30.987654321Z"
        assert arm64_entry["platform"]["os"] == "linux"
        assert arm64_entry["digest"] == created_arm64.manifest.digest

    # reset all variables to None
    created_amd64 = None
    created_arm64 = None
    created_list = None

    # create OCI image and then repoint "latest" to the new OCI image
    # for AMD64
    builder_amd64_oci.set_config_digest(config_amd64_digest, len(config_amd64_bytes))
    builder_amd64_oci.add_layer(layer_digest, len(layer_bytes))
    child_amd64_oci_manifest_obj = builder_amd64_oci.build()
    created_amd64 = oci.manifest.get_or_create_manifest(
        repo.id,
        child_amd64_oci_manifest_obj,
        app_storage,
        raise_on_error=True,
    )
    assert created_amd64 is not None

    # for Arm64
    builder_arm64_oci.set_config_digest(config_arm64_digest, len(config_arm64_bytes))
    builder_arm64_oci.add_layer(layer_digest, len(layer_bytes))
    child_arm64_oci_manifest_obj = builder_arm64_oci.build()
    created_arm64 = oci.manifest.get_or_create_manifest(
        repo.id,
        child_arm64_oci_manifest_obj,
        app_storage,
        raise_on_error=True,
    )
    assert created_arm64 is not None

    # build OCI image index
    index_builder = OCIIndexBuilder()
    index_builder.add_manifest(child_amd64_oci_manifest_obj, "amd64", "linux")
    index_builder.add_manifest(child_arm64_oci_manifest_obj, "arm64", "linux")
    index_manifest = index_builder.build()
    assert index_manifest is not None

    # Create manifest list in db
    created_list = oci.manifest.get_or_create_manifest(repo.id, index_manifest, app_storage)
    assert created_list is not None

    # Add tag for the manifest list
    tag = oci.tag.retarget_tag("latest", created_list.manifest.id, raise_on_error=True)
    assert tag is not None

    # call api
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/test-manifest-list-parsing",
            "manifestref": created_list.manifest.digest,
        }
        result = conduct_api_call(cl, RepositoryManifest, "GET", params, None, 200).json
        # Verify basic properties
        assert result["digest"] == created_list.manifest.digest
        assert result["is_manifest_list"] is True
        assert "manifests" in result

        # verify child manifests
        manifests = result["manifests"]
        assert len(manifests) == 2
        amd64_entry = next((m for m in manifests if m["platform"]["architecture"] == "amd64"), None)
        arm64_entry = next((m for m in manifests if m["platform"]["architecture"] == "arm64"), None)

        assert amd64_entry is not None
        assert arm64_entry is not None

        # verify we have timestamps and other attributes
        # for amd64 image
        assert "image_built" in amd64_entry
        assert amd64_entry["image_built"] == "2024-02-20T14:25:30.987654321Z"
        assert amd64_entry["platform"]["os"] == "linux"
        assert amd64_entry["digest"] == created_amd64.manifest.digest

        # for arm64 image
        assert "image_built" in arm64_entry
        assert arm64_entry["image_built"] == "2024-02-20T14:25:30.987654321Z"
        assert arm64_entry["platform"]["os"] == "linux"
        assert arm64_entry["digest"] == created_arm64.manifest.digest


def test_manifest_list_sparse_no_timestamps(app, initialized_db):
    """
    Test that sparse manifest list (missing child manifests) still returns platform info without timestamps.
    This simulates proxy cache scenarios where the manifest list exists but children haven't been pulled.
    """
    user = get_user("devtable")
    repo = create_repository("devtable", "test-sparse-manifest-list", user)

    # Build manifest list with non-existent child manifests
    list_builder = DockerSchema2ManifestListBuilder()

    # These digests don't exist in the database - simulating sparse manifest list
    fake_digest_amd64 = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    fake_digest_arm64 = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    fake_digest_ppc64le = "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

    list_builder.add_manifest_digest(
        fake_digest_amd64,
        1234,
        "application/vnd.docker.distribution.manifest.v2+json",
        "amd64",
        "linux",
    )
    list_builder.add_manifest_digest(
        fake_digest_arm64,
        5678,
        "application/vnd.docker.distribution.manifest.v2+json",
        "arm64",
        "linux",
    )
    list_builder.add_manifest_digest(
        fake_digest_ppc64le,
        9012,
        "application/vnd.docker.distribution.manifest.v2+json",
        "ppc64le",
        "linux",
    )

    manifest_list = list_builder.build()
    manifest_list_bytes = manifest_list.bytes.as_encoded_str()
    manifest_list_digest = sha256_digest(manifest_list_bytes)

    # We need to inject the manifest directly to the database
    media_type = MediaType.get(name="application/vnd.docker.distribution.manifest.list.v2+json")
    created_manifest = ManifestTable.create(
        digest=manifest_list_digest,
        manifest_bytes=manifest_list_bytes,
        media_type=media_type,
        repository=repo.id,
    )

    tag = oci.tag.retarget_tag("latest", created_manifest.id, raise_on_error=True)
    assert tag is not None

    # Call the API endpoint
    with client_with_identity("devtable", app) as cl:
        params = {
            "repository": "devtable/test-sparse-manifest-list",
            "manifestref": manifest_list_digest,
        }
        result = conduct_api_call(cl, RepositoryManifest, "GET", params, None, 200).json

        # Verify manifest list properties
        assert result["digest"] == manifest_list_digest
        assert result["is_manifest_list"] is True
        assert "manifests" in result

        # Verify child manifests are returned with platform info
        manifests = result["manifests"]
        assert len(manifests) == 3

        # Find each architecture entry
        amd64_entry = next((m for m in manifests if m["platform"]["architecture"] == "amd64"), None)
        arm64_entry = next((m for m in manifests if m["platform"]["architecture"] == "arm64"), None)
        ppc64le_entry = next(
            (m for m in manifests if m["platform"]["architecture"] == "ppc64le"), None
        )

        assert amd64_entry is not None
        assert arm64_entry is not None
        assert ppc64le_entry is not None

        # Verify platform info is present
        assert amd64_entry["platform"]["os"] == "linux"
        assert amd64_entry["digest"] == fake_digest_amd64
        assert amd64_entry["size"] == 1234

        assert arm64_entry["platform"]["os"] == "linux"
        assert arm64_entry["digest"] == fake_digest_arm64
        assert arm64_entry["size"] == 5678

        assert ppc64le_entry["platform"]["os"] == "linux"
        assert ppc64le_entry["digest"] == fake_digest_ppc64le
        assert ppc64le_entry["size"] == 9012

        # Verify NO timestamps are present (child manifests don't exist in DB)
        assert "image_built" not in amd64_entry
        assert "image_built" not in arm64_entry
        assert "image_built" not in ppc64le_entry
