import time
from unittest.mock import MagicMock, patch

from data.database import (
    QuotaNamespaceSize,
    QuotaRepositorySize,
    QuotaTypes,
    Tag,
    User,
)
from data.model.namespacequota import (
    check_limits,
    create_namespace_quota,
    create_namespace_quota_limit,
    get_namespace_size,
)
from data.model.oci.tag import find_repository_with_garbage, get_tag, retarget_tag
from data.model.quota import get_namespace_size as get_namespace_size_row
from data.model.quota import get_repository_size as get_repository_size_row
from data.model.test.test_quota import (
    CONFIG_LAYER_JSON,
    _populate_blob,
    create_manifest_for_testing,
)
from workers.gc.gcworker import GarbageCollectionWorker
from workers.quotatotalworker import QuotaTotalWorker


def create_tag_for_manifest(repository, manifest, tag_name):
    """
    Create a tag pointing to a manifest.

    Args:
        repository: Repository object
        manifest: Manifest object to tag
        tag_name: Name of the tag

    Returns:
        Created tag object
    """
    return retarget_tag(tag_name, manifest.id, raise_on_error=True)


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

        # Resolve the *live* tag by name: after retarget_tag the repository can
        # hold an expired historical row alongside the live row with the same
        # name, and an unordered select could pick the historical one and expire
        # the wrong manifest. get_tag applies the alive-only filter.
        target = get_tag(repository.id, tag_name)
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
