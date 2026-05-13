import json
import time
from unittest.mock import MagicMock, patch

from app import storage
from data.database import (
    ImageStorageLocation,
    QuotaNamespaceSize,
    QuotaRepositorySize,
    Tag,
)
from data.model.blob import store_blob_record_and_temp_link
from data.model.namespacequota import get_namespace_size
from data.model.oci.manifest import get_or_create_manifest
from data.model.oci.tag import create_or_update_tag
from data.model.organization import create_organization
from data.model.quota import get_namespace_size as get_namespace_size_row
from data.model.quota import get_repository_size as get_repository_size_row
from data.model.quota import run_backfill
from data.model.repository import create_repository, get_repository_size
from data.model.storage import get_layer_path
from data.model.user import get_namespace_user_by_user_id, get_user
from digest.digest_tools import sha256_digest
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from util.bytes import Bytes
from workers.gc.gcworker import GarbageCollectionWorker
from workers.quotatotalworker import QuotaTotalWorker

CONFIG_LAYER_JSON = json.dumps(
    {
        "config": {},
        "rootfs": {"type": "layers", "diff_ids": []},
        "history": [],
    }
)


def create_manifest_with_blobs(repository, blobs):
    """
    Create a test manifest with specified blobs.

    Args:
        repository: Repository object to create manifest in
        blobs: List of blob content strings

    Returns:
        Created manifest object
    """
    remote_digest = sha256_digest(b"something")
    builder = DockerSchema2ManifestBuilder()
    namespace = get_namespace_user_by_user_id(repository.namespace_user)
    _, config_digest = _populate_blob(CONFIG_LAYER_JSON, namespace.username, repository.name)
    builder.set_config_digest(config_digest, len(CONFIG_LAYER_JSON.encode("utf-8")))
    builder.add_layer(remote_digest, 1234, urls=["http://hello/world"])
    for blob in blobs:
        _, blob_digest = _populate_blob(blob, namespace.username, repository.name)
        builder.add_layer(blob_digest, len(blob))

    manifest = builder.build()
    created = get_or_create_manifest(repository.id, manifest, storage)
    assert created
    return created.manifest


def create_tag_for_manifest(repository, manifest, tag_name, expiration_ms=None):
    """
    Create a tag pointing to a manifest.

    Args:
        repository: Repository object
        manifest: Manifest object to tag
        tag_name: Name of the tag
        expiration_ms: Optional expiration time in milliseconds

    Returns:
        Created tag object
    """
    tag = create_or_update_tag(
        repository.id,
        tag_name,
        manifest_digest=manifest.digest,
        lifetime_end_ms=expiration_ms,
    )
    return tag


def delete_tag_by_name(repository, tag_name):
    """
    Delete a tag by name.

    Args:
        repository: Repository object
        tag_name: Name of tag to delete

    Returns:
        True if tag was deleted, False otherwise
    """
    try:
        count = Tag.delete().where(Tag.repository == repository, Tag.name == tag_name).execute()
        return count > 0
    except Tag.DoesNotExist:
        return False


def run_gc_worker(skip_lock=True):
    """
    Execute the garbage collection worker.

    Args:
        skip_lock: If True, skip locking for testing

    Returns:
        GarbageCollectionWorker instance
    """
    worker = GarbageCollectionWorker()
    worker._garbage_collection_repos(skip_lock_for_testing=skip_lock)
    return worker


def run_quota_worker():
    """
    Execute the quota total worker to recalculate quotas.

    Returns:
        QuotaTotalWorker instance
    """
    worker = QuotaTotalWorker()
    worker.backfill()
    return worker


def get_namespace_quota(org_or_user):
    """
    Get the current quota size for a namespace.

    Args:
        org_or_user: Organization or User object

    Returns:
        Quota size in bytes, or 0 if not found
    """
    quota_row = get_namespace_size_row(org_or_user.id)
    return quota_row.size_bytes if quota_row else 0


def get_repo_quota(repository):
    """
    Get the current quota size for a repository.

    Args:
        repository: Repository object

    Returns:
        Quota size in bytes, or 0 if not found
    """
    quota_row = get_repository_size_row(repository.id)
    return quota_row.size_bytes if quota_row else 0


def set_namespace_quota_limit(org_or_user, limit_bytes):
    """
    Set quota limit for a namespace (organization or user).

    This is a placeholder - actual implementation would set the quota limit
    in the appropriate table.

    Args:
        org_or_user: Organization or User object
        limit_bytes: Quota limit in bytes
    """
    # TODO: Implement actual quota limit setting if needed for tests
    pass


def expire_tag(repository, tag_name):
    """
    Expire a tag by setting its lifetime_end_ms to the past.

    Args:
        repository: Repository object
        tag_name: Name of tag to expire

    Returns:
        True if tag was expired, False otherwise
    """
    try:
        past_time = int((time.time() - 3600) * 1000)  # 1 hour ago
        count = (
            Tag.update(lifetime_end_ms=past_time)
            .where(Tag.repository == repository, Tag.name == tag_name)
            .execute()
        )
        return count > 0
    except Tag.DoesNotExist:
        return False


def calculate_expected_size(*blobs):
    """
    Calculate expected size of blobs including config layer.

    Args:
        *blobs: Variable number of blob content strings

    Returns:
        Total size in bytes
    """
    size = len(CONFIG_LAYER_JSON)
    for blob in blobs:
        size += len(blob)
    return size


def _populate_blob(content, namespace_name, repository_name):
    """
    Store a blob in storage.

    Args:
        content: Blob content (string or bytes)
        namespace_name: Namespace name
        repository_name: Repository name

    Returns:
        Tuple of (blob object, digest)
    """
    content = Bytes.for_string_or_unicode(content).as_encoded_str()
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = store_blob_record_and_temp_link(
        namespace_name, repository_name, digest, location, len(content), 120
    )
    storage.put_content(["local_us"], get_layer_path(blob), content)
    return blob, digest


def enable_quota_management():
    """
    Context manager to enable quota management for testing.

    Usage:
        with enable_quota_management():
            # quota management is enabled here
    """
    return patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=True))


def enable_gc_and_quota():
    """
    Context manager to enable both GC and quota management for testing.

    Usage:
        with enable_gc_and_quota():
            # both features are enabled here
    """
    return patch(
        "data.model.gc.features",
        MagicMock(QUOTA_MANAGEMENT=True, GARBAGE_COLLECTION=True),
    )
