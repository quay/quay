from datetime import datetime

from mock import patch

from app import app as realapp
from data.database import ManifestPullStatistics, TagPullStatistics
from data.model.repository import create_repository
from data.model.user import get_user
from data.registry_model import registry_model
from endpoints.api.manifest import RepositoryManifest, _get_modelcard_layer_digest
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue
from image.oci.manifest import OCIManifest
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
