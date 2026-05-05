from unittest.mock import MagicMock, patch

import pytest

from app import storage
from data.model.blob import store_blob_record_and_temp_link
from data.model.organization import create_organization
from data.model.proxy_cache import create_proxy_cache_config
from data.model.repository import create_repository
from data.model.storage import get_layer_path
from data.model.user import get_user
from data.registry_model.registry_proxy_model import ProxyModel
from digest.digest_tools import sha256_digest
from test.fixtures import *
from workers.proxycacheblobworker import ProxyCacheBlobWorker


@pytest.fixture()
def proxy_cache_blob_worker():
    return ProxyCacheBlobWorker(None)


@pytest.fixture()
@patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
def registry_proxy_model(initialized_db):
    orgname = "testorg"
    user = get_user("devtable")
    org = create_organization(orgname, "{self.orgname}@devtable.com", user)
    org.save()
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )
    return ProxyModel(
        orgname,
        "app-sre/ubi8-ubi",
        user,
    )


def test_proxy_cache_blob_download(proxy_cache_blob_worker, registry_proxy_model, app):
    # ImageStorage(placeholder) does not exist
    assert not proxy_cache_blob_worker._should_download_blob(
        "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
        1,
        registry_proxy_model,
    )


def test_process_queue_item_with_none_username(proxy_cache_blob_worker, initialized_db):
    """Test that worker handles None username for public repositories (PROJQUAY-9346)"""

    # Setup test data
    orgname = "testorg"
    user = get_user("devtable")
    org = create_organization(orgname, f"{orgname}@devtable.com", user)
    org.save()

    # Create proxy cache config for the organization
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )

    # Create a test repository
    repo = create_repository(orgname, "test_repo", user)

    # Create job details with None username (public repository scenario)
    job_details = {
        "repo_id": repo.id,
        "namespace": orgname,
        "digest": "sha256:test_digest",
        "username": None,  # This simulates public repository access
    }

    # Mock the _should_download_blob method to return False so we don't actually download
    with patch.object(proxy_cache_blob_worker, "_should_download_blob", return_value=False):
        # This should not raise an exception
        proxy_cache_blob_worker.process_queue_item(job_details)


def test_process_queue_item_with_username(proxy_cache_blob_worker, initialized_db):
    """Test that worker handles normal username case correctly"""
    from data.model.organization import create_organization
    from data.model.proxy_cache import create_proxy_cache_config
    from data.model.repository import create_repository
    from data.model.user import create_user_noverify, get_user

    # Setup test data
    orgname = "testorg2"
    admin_user = get_user("devtable")
    org = create_organization(orgname, f"{orgname}@devtable.com", admin_user)
    org.save()

    # Create proxy cache config for the organization
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )

    # Create a test repository
    repo = create_repository(orgname, "test_repo", admin_user)

    # Create a test user
    test_user = create_user_noverify("testuser", "testuser@example.com")

    # Create job details with actual username
    job_details = {
        "repo_id": repo.id,
        "namespace": orgname,
        "digest": "sha256:test_digest",
        "username": "testuser",
    }

    # Mock the _should_download_blob method to return False so we don't actually download
    with patch.object(proxy_cache_blob_worker, "_should_download_blob", return_value=False):
        # This should work normally
        proxy_cache_blob_worker.process_queue_item(job_details)


def test_all_blobs_downloaded_for_manifest_all_complete(proxy_cache_blob_worker, initialized_db):
    """Test detection when all blobs for a manifest have been downloaded"""
    from data.database import (
        ImageStorage,
        ImageStorageLocation,
        ImageStoragePlacement,
        Manifest,
        ManifestBlob,
        MediaType,
        Repository,
    )

    # Get a test repository
    repo = Repository.get(Repository.name == "simple")

    # Get or create media type for manifest
    media_type, _ = MediaType.get_or_create(
        name="application/vnd.docker.distribution.manifest.v2+json"
    )

    # Create a test manifest
    manifest = Manifest.create(
        digest="sha256:test_manifest_complete",
        manifest_bytes='{"test": "manifest"}',
        media_type=media_type,
        repository=repo,
    )

    # Create test blobs with placements
    location = ImageStorageLocation.get()

    blob1 = ImageStorage.create(
        content_checksum="sha256:blob1_complete",
        image_size=1024,
        uncompressed_size=2048,
    )
    ImageStoragePlacement.create(storage=blob1, location=location.id)
    ManifestBlob.create(manifest=manifest, blob=blob1, repository=repo)

    blob2 = ImageStorage.create(
        content_checksum="sha256:blob2_complete",
        image_size=2048,
        uncompressed_size=4096,
    )
    ImageStoragePlacement.create(storage=blob2, location=location.id)
    ManifestBlob.create(manifest=manifest, blob=blob2, repository=repo)

    # All blobs have placements, should return True
    result = proxy_cache_blob_worker._all_blobs_downloaded_for_manifest(manifest.id, repo.id)
    assert result is True


def test_all_blobs_downloaded_for_manifest_incomplete(proxy_cache_blob_worker, initialized_db):
    """Test detection when some blobs for a manifest are still pending download"""
    from data.database import (
        ImageStorage,
        ImageStorageLocation,
        ImageStoragePlacement,
        Manifest,
        ManifestBlob,
        MediaType,
        Repository,
    )

    # Get a test repository
    repo = Repository.get(Repository.name == "simple")

    # Get or create media type for manifest
    media_type, _ = MediaType.get_or_create(
        name="application/vnd.docker.distribution.manifest.v2+json"
    )

    # Create a test manifest
    manifest = Manifest.create(
        digest="sha256:test_manifest_incomplete",
        manifest_bytes='{"test": "manifest"}',
        media_type=media_type,
        repository=repo,
    )

    # Create test blobs - one with placement, one without (placeholder)
    location = ImageStorageLocation.get()

    blob1 = ImageStorage.create(
        content_checksum="sha256:blob1_incomplete",
        image_size=1024,
        uncompressed_size=2048,
    )
    ImageStoragePlacement.create(storage=blob1, location=location.id)
    ManifestBlob.create(manifest=manifest, blob=blob1, repository=repo)

    # This blob is a placeholder - no ImageStoragePlacement
    blob2 = ImageStorage.create(
        content_checksum="sha256:blob2_incomplete",
        image_size=2048,
        uncompressed_size=4096,
    )
    ManifestBlob.create(manifest=manifest, blob=blob2, repository=repo)

    # One blob missing placement, should return False
    result = proxy_cache_blob_worker._all_blobs_downloaded_for_manifest(manifest.id, repo.id)
    assert result is False


def test_reset_security_status_when_blobs_complete(proxy_cache_blob_worker, initialized_db):
    """Test that security status is reset when all blobs for a manifest are downloaded"""
    from data.database import (
        ImageStorage,
        ImageStorageLocation,
        ImageStoragePlacement,
        IndexerVersion,
        IndexStatus,
        Manifest,
        ManifestBlob,
        ManifestSecurityStatus,
        MediaType,
        Repository,
    )

    # Get a test repository
    repo = Repository.get(Repository.name == "simple")

    # Get or create media type for manifest
    media_type, _ = MediaType.get_or_create(
        name="application/vnd.docker.distribution.manifest.v2+json"
    )

    # Create a test manifest
    manifest = Manifest.create(
        digest="sha256:test_manifest_reset",
        manifest_bytes='{"test": "manifest"}',
        media_type=media_type,
        repository=repo,
    )

    # Mark manifest as MANIFEST_UNSUPPORTED
    ManifestSecurityStatus.create(
        manifest=manifest,
        repository=repo,
        index_status=IndexStatus.MANIFEST_UNSUPPORTED,
        indexer_hash="none",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    # Create test blobs with placements
    location = ImageStorageLocation.get()

    blob1 = ImageStorage.create(
        content_checksum="sha256:blob1_reset",
        image_size=1024,
        uncompressed_size=2048,
    )
    ImageStoragePlacement.create(storage=blob1, location=location.id)
    ManifestBlob.create(manifest=manifest, blob=blob1, repository=repo)

    blob2 = ImageStorage.create(
        content_checksum="sha256:blob2_reset",
        image_size=2048,
        uncompressed_size=4096,
    )
    ImageStoragePlacement.create(storage=blob2, location=location.id)
    ManifestBlob.create(manifest=manifest, blob=blob2, repository=repo)

    # Verify security status exists before reset
    status = ManifestSecurityStatus.get(
        ManifestSecurityStatus.manifest == manifest,
        ManifestSecurityStatus.repository == repo,
    )
    assert status.index_status == IndexStatus.MANIFEST_UNSUPPORTED

    # Trigger the reset by calling with one of the blob digests
    proxy_cache_blob_worker._reset_security_status_if_complete("sha256:blob2_reset", repo.id)

    # Verify security status was deleted
    status_count = (
        ManifestSecurityStatus.select()
        .where(
            ManifestSecurityStatus.manifest == manifest,
            ManifestSecurityStatus.repository == repo,
        )
        .count()
    )
    assert status_count == 0


def test_reset_security_status_partial_download_no_reset(proxy_cache_blob_worker, initialized_db):
    """Test that security status is NOT reset when only some blobs are downloaded"""
    from data.database import (
        ImageStorage,
        ImageStorageLocation,
        ImageStoragePlacement,
        IndexerVersion,
        IndexStatus,
        Manifest,
        ManifestBlob,
        ManifestSecurityStatus,
        MediaType,
        Repository,
    )

    # Get a test repository
    repo = Repository.get(Repository.name == "simple")

    # Get or create media type for manifest
    media_type, _ = MediaType.get_or_create(
        name="application/vnd.docker.distribution.manifest.v2+json"
    )

    # Create a test manifest
    manifest = Manifest.create(
        digest="sha256:test_manifest_partial",
        manifest_bytes='{"test": "manifest"}',
        media_type=media_type,
        repository=repo,
    )

    # Mark manifest as MANIFEST_UNSUPPORTED
    ManifestSecurityStatus.create(
        manifest=manifest,
        repository=repo,
        index_status=IndexStatus.MANIFEST_UNSUPPORTED,
        indexer_hash="none",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    # Create test blobs - only one with placement
    location = ImageStorageLocation.get()

    blob1 = ImageStorage.create(
        content_checksum="sha256:blob1_partial",
        image_size=1024,
        uncompressed_size=2048,
    )
    ImageStoragePlacement.create(storage=blob1, location=location.id)
    ManifestBlob.create(manifest=manifest, blob=blob1, repository=repo)

    # This blob is a placeholder - no ImageStoragePlacement
    blob2 = ImageStorage.create(
        content_checksum="sha256:blob2_partial",
        image_size=2048,
        uncompressed_size=4096,
    )
    ManifestBlob.create(manifest=manifest, blob=blob2, repository=repo)

    # Trigger the reset attempt
    proxy_cache_blob_worker._reset_security_status_if_complete("sha256:blob1_partial", repo.id)

    # Verify security status still exists (not deleted)
    status = ManifestSecurityStatus.get(
        ManifestSecurityStatus.manifest == manifest,
        ManifestSecurityStatus.repository == repo,
    )
    assert status.index_status == IndexStatus.MANIFEST_UNSUPPORTED


def test_reset_security_status_only_affects_unsupported(proxy_cache_blob_worker, initialized_db):
    """Test that reset only deletes MANIFEST_UNSUPPORTED status, not other statuses"""
    from data.database import (
        ImageStorage,
        ImageStorageLocation,
        ImageStoragePlacement,
        IndexerVersion,
        IndexStatus,
        Manifest,
        ManifestBlob,
        ManifestSecurityStatus,
        MediaType,
        Repository,
    )

    # Get a test repository
    repo = Repository.get(Repository.name == "simple")

    # Get or create media type for manifest
    media_type, _ = MediaType.get_or_create(
        name="application/vnd.docker.distribution.manifest.v2+json"
    )

    # Create a test manifest
    manifest = Manifest.create(
        digest="sha256:test_manifest_failed",
        manifest_bytes='{"test": "manifest"}',
        media_type=media_type,
        repository=repo,
    )

    # Mark manifest as FAILED (not UNSUPPORTED)
    ManifestSecurityStatus.create(
        manifest=manifest,
        repository=repo,
        index_status=IndexStatus.FAILED,
        indexer_hash="test_hash",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    # Create test blobs with placements
    location = ImageStorageLocation.get()

    blob1 = ImageStorage.create(
        content_checksum="sha256:blob1_failed",
        image_size=1024,
        uncompressed_size=2048,
    )
    ImageStoragePlacement.create(storage=blob1, location=location.id)
    ManifestBlob.create(manifest=manifest, blob=blob1, repository=repo)

    # Trigger the reset attempt
    proxy_cache_blob_worker._reset_security_status_if_complete("sha256:blob1_failed", repo.id)

    # Verify security status still exists (should not be deleted because it's FAILED not UNSUPPORTED)
    status = ManifestSecurityStatus.get(
        ManifestSecurityStatus.manifest == manifest,
        ManifestSecurityStatus.repository == repo,
    )
    assert status.index_status == IndexStatus.FAILED


def test_should_download_blob_missing_from_storage(proxy_cache_blob_worker, initialized_db):
    """
    When a blob has a placement record in DB but the file is missing from
    storage, _should_download_blob should return True (PROJQUAY-10315).
    """
    from data.database import (
        ImageStorage,
        ImageStorageLocation,
        ImageStoragePlacement,
        Manifest,
        ManifestBlob,
        MediaType,
        Repository,
    )

    repo = Repository.get(Repository.name == "simple")
    location = ImageStorageLocation.get(name="local_us")

    content = b"worker test blob missing from storage"
    digest = str(sha256_digest(content))
    blob = store_blob_record_and_temp_link(
        repo.namespace_user.username,
        repo.name,
        digest,
        location,
        len(content),
        120,
    )
    layer_path = get_layer_path(blob)
    storage.put_content(["local_us"], layer_path, content)

    media_type, _ = MediaType.get_or_create(
        name="application/vnd.docker.distribution.manifest.v2+json"
    )
    manifest = Manifest.create(
        digest="sha256:worker_test_missing",
        manifest_bytes='{"test": "manifest"}',
        media_type=media_type,
        repository=repo,
    )
    ManifestBlob.create(manifest=manifest, blob=blob, repository=repo)

    assert ImageStoragePlacement.select().where(ImageStoragePlacement.storage == blob).exists()

    orgname = "testorg-worker-missing"
    user = get_user("devtable")
    org = create_organization(orgname, f"{orgname}@devtable.com", user)
    org.save()
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )
    with patch("data.registry_model.registry_proxy_model.Proxy", MagicMock()):
        registry_proxy_model = ProxyModel(orgname, "app-sre/ubi8-ubi", user)

    # File exists → should not download
    assert not proxy_cache_blob_worker._should_download_blob(digest, repo.id, registry_proxy_model)

    # Remove file from storage
    storage.remove(["local_us"], layer_path)
    assert not storage.exists(["local_us"], layer_path)

    # File missing → should download
    assert proxy_cache_blob_worker._should_download_blob(digest, repo.id, registry_proxy_model)


def test_should_download_blob_storage_error(proxy_cache_blob_worker, initialized_db):
    """
    When storage.exists() raises an exception, _should_download_blob should
    return True to trigger a re-download rather than serving stale data.
    """
    from data.database import (
        ImageStorage,
        ImageStorageLocation,
        ImageStoragePlacement,
        Manifest,
        ManifestBlob,
        MediaType,
        Repository,
    )

    repo = Repository.get(Repository.name == "simple")
    location = ImageStorageLocation.get(name="local_us")

    content = b"worker test blob storage error"
    digest = str(sha256_digest(content))
    blob = store_blob_record_and_temp_link(
        repo.namespace_user.username,
        repo.name,
        digest,
        location,
        len(content),
        120,
    )
    layer_path = get_layer_path(blob)
    storage.put_content(["local_us"], layer_path, content)

    media_type, _ = MediaType.get_or_create(
        name="application/vnd.docker.distribution.manifest.v2+json"
    )
    manifest = Manifest.create(
        digest="sha256:worker_test_error",
        manifest_bytes='{"test": "manifest"}',
        media_type=media_type,
        repository=repo,
    )
    ManifestBlob.create(manifest=manifest, blob=blob, repository=repo)

    orgname = "testorg-worker-error"
    user = get_user("devtable")
    org = create_organization(orgname, f"{orgname}@devtable.com", user)
    org.save()
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )
    with patch("data.registry_model.registry_proxy_model.Proxy", MagicMock()):
        registry_proxy_model = ProxyModel(orgname, "app-sre/ubi8-ubi", user)

    with patch(
        "workers.proxycacheblobworker.storage.exists",
        side_effect=IOError("storage unavailable"),
    ):
        assert proxy_cache_blob_worker._should_download_blob(
            digest, repo.id, registry_proxy_model
        )
