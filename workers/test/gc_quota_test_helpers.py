import json
import time
from unittest.mock import MagicMock, patch

from app import storage
from data.database import (
    ImageStorageLocation,
    QuotaNamespaceSize,
    QuotaRepositorySize,
    QuotaTypes,
    Tag,
    User,
)
from data.model.blob import store_blob_record_and_temp_link
from data.model.namespacequota import (
    check_limits,
    create_namespace_quota,
    create_namespace_quota_limit,
    get_namespace_size,
)
from data.model.oci.manifest import get_or_create_manifest
from data.model.oci.tag import find_repository_with_garbage, get_tag, retarget_tag
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
    tag = retarget_tag(tag_name, manifest.id, raise_on_error=True)
    if expiration_ms is not None:
        Tag.update(lifetime_end_ms=expiration_ms).where(Tag.id == tag.id).execute()
        tag = get_tag(repository.id, tag_name)
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
    Execute the garbage collection worker deterministically.

    The GC worker normally (1) selects a *random* namespace GC policy via
    ``get_random_gc_policy`` and (2) collects at most one repository per
    invocation. That is unusable for deterministic tests. Tests make expired
    tags immediately collectable by dropping the owning namespace's
    ``removed_tag_expiration_s`` to 0 (see ``expire_tag``), so here we force the
    worker onto the 0-second policy and loop until no repository has
    collectable garbage left under that policy.

    Args:
        skip_lock: If True, skip locking for testing

    Returns:
        GarbageCollectionWorker instance
    """
    worker = GarbageCollectionWorker()
    with patch("workers.gc.gcworker.get_random_gc_policy", return_value=0):
        # Each call collects at most one repository; drain them all. The bound
        # is a safety net against an unexpected non-terminating condition.
        for _ in range(1000):
            if find_repository_with_garbage(0) is None:
                break
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


def set_namespace_quota_limit(org_or_user, limit_bytes, warning_percent=80, reject_percent=100):
    """
    Persist a real quota limit for a namespace (organization or user).

    Creates a UserOrganizationQuota row with the given limit and, unless
    disabled, the warning/reject QuotaLimits thresholds, so that the actual
    quota enforcement state can be asserted via get_namespace_quota_severity.

    Args:
        org_or_user: Organization or User object
        limit_bytes: Quota limit in bytes
        warning_percent: Percent of the limit at which a warning fires
            (pass None to skip creating the warning threshold)
        reject_percent: Percent of the limit at which pushes are rejected
            (pass None to skip creating the reject threshold)

    Returns:
        The created UserOrganizationQuota row
    """
    quota = create_namespace_quota(org_or_user, limit_bytes)
    if warning_percent is not None:
        create_namespace_quota_limit(quota, QuotaTypes.WARNING, warning_percent)
    if reject_percent is not None:
        create_namespace_quota_limit(quota, QuotaTypes.REJECT, reject_percent)
    return quota


def get_namespace_quota_severity(org_or_user):
    """
    Return the current quota enforcement severity for a namespace based on its
    real persisted usage and configured limits.

    Returns:
        QuotaTypes.REJECT, QuotaTypes.WARNING, or None depending on how the
        current namespace size compares to the configured quota thresholds.
    """
    namespace_size = get_namespace_size(org_or_user.username)
    return check_limits(org_or_user.username, namespace_size)["severity_level"]


def expire_tag(repository, tag_name):
    """
    Expire a tag and make its manifest immediately eligible for GC.

    Expires the named tag *and* every other tag that still references the same
    manifest, then drops the owning namespace's removed_tag_expiration_s to 0.

    Expiring all tags on the manifest is required because get_or_create_manifest
    creates a temporary hidden "$temp-*" tag (with a short future expiration) to
    protect a freshly-pushed manifest. In real usage that temp tag expires soon
    after the push and a later GC pass collects the now-unreferenced manifest;
    here we simulate that elapsed time so the manifest becomes fully
    unreferenced and its blobs are collectable in a single GC run. Only tags for
    this specific manifest are touched, so other manifests in the repository are
    unaffected.

    GC only collects tags expired *beyond* the namespace's expiration window
    (default 14 days); setting the window to 0 means a tag expired even one
    second ago is past the window and collectable on the next GC run (see
    find_repository_with_garbage / run_gc_worker).

    Args:
        repository: Repository object
        tag_name: Name of tag to expire

    Returns:
        True if the tag was found and expired, False otherwise
    """
    try:
        past_time = int((time.time() - 3600) * 1000)  # 1 hour ago

        target = Tag.select().where(Tag.repository == repository, Tag.name == tag_name).first()
        if target is None:
            return False

        # Expire the named tag along with any temporary/hidden tag protecting
        # the same manifest.
        Tag.update(lifetime_end_ms=past_time).where(
            Tag.repository == repository, Tag.manifest == target.manifest_id
        ).execute()

        # Collapse the namespace's expiration window so the just-expired tags
        # are past it and can be collected immediately.
        User.update(removed_tag_expiration_s=0).where(
            User.id == repository.namespace_user_id
        ).execute()
        return True
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
