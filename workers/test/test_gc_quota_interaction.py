"""
Integration tests for GC + Quota Recalculation Worker Interaction.

These tests verify the critical workflow:
    fill quota → delete content → run GC → recalculate quota → verify quota is freed

Tests ensure that:
- Quota is recalculated correctly after GC runs
- Users can push new images after deleting old content and running GC
- Quota warning thresholds are cleared after GC frees space
- Shared blob deduplication works correctly in quota calculations after GC
- Orphaned blobs are removed by GC and quota is updated accordingly
- Concurrent operations (e.g., push during GC) maintain quota consistency
- Cross-org quota isolation is preserved during GC operations
"""

from unittest.mock import MagicMock, patch

import pytest

from data.database import (
    ExternalNotificationEvent,
    ExternalNotificationMethod,
    ImageStorage,
    ManifestBlob,
    NamespaceNotification,
    QuotaNotificationState,
    QuotaTypes,
)
from data.model import gc as gc_model
from data.model import storage as storage_model
from data.model.oci.tag import get_tag
from data.model.organization import create_organization
from data.model.quota import run_backfill
from data.model.repository import create_repository
from data.model.test.test_quota import create_manifest_for_testing
from data.model.user import get_user
from test.fixtures import *
from workers.quotatotalworker import QuotaTotalWorker
from workers.test.gc_quota_test_helpers import (
    calculate_expected_size,
    create_tag_for_manifest,
    delete_upload_links,
    enable_gc_and_quota,
    enable_quota_management,
    expire_tag,
    get_namespace_quota,
    get_namespace_quota_severity,
    get_repo_quota,
    run_gc_worker,
    run_quota_worker,
    set_namespace_quota_limit,
)


@pytest.fixture
def setup_orgs(initialized_db):
    """
    Create test organizations and users.

    Returns:
        Dict with 'user', 'org1', and 'org2' objects
    """
    user = get_user("devtable")
    org1 = create_organization("gcquotatest1", "gcquotatest1@devtable.com", user)
    org2 = create_organization("gcquotatest2", "gcquotatest2@devtable.com", user)
    return {"user": user, "org1": org1, "org2": org2}


class TestGCQuotaInteraction:
    """Integration tests for GC + Quota recalculation worker coordination."""

    def test_quota_freed_after_delete_gc_and_recalculation(self, setup_orgs):
        """
        Test 1: Push 8 MB → delete tags → run GC → quota worker → verify quota freed → new push counted.

        Verifies the complete end-to-end workflow:
        1. Push 8 MB of content
        2. Delete tags
        3. Run GC to remove blobs
        4. Run quota worker to recalculate
        5. Verify quota is 0 after GC
        6. Verify a new 8 MB push is counted in quota

        This is the primary integration test validating the core GC + quota interaction.
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository
        repo = create_repository(org.username, "test-repo", user)

        # Create large blobs (8 MB total)
        blob1 = "A" * (4 * 1024 * 1024)  # 4 MB
        blob2 = "B" * (4 * 1024 * 1024)  # 4 MB

        # Disable quota initially to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_for_testing(repo, [blob1, blob2])
            tag1 = create_tag_for_manifest(manifest1, "v1.0")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1, blob2)
        assert (
            initial_quota == expected_initial
        ), f"Initial quota should be ~8 MB, got {initial_quota}"

        # Delete the tag to make blobs eligible for GC
        expire_tag(repo, "v1.0")

        # Run GC with quota management enabled
        with enable_gc_and_quota():
            run_gc_worker()

        run_quota_worker(org.id)

        # Verify quota is freed
        quota_after_gc = get_namespace_quota(org)
        assert quota_after_gc == 0, f"Quota should be 0 after GC, got {quota_after_gc}"

        # Verify a new 8 MB push is counted in quota
        with enable_quota_management():
            blob3 = "C" * (4 * 1024 * 1024)  # 4 MB
            blob4 = "D" * (4 * 1024 * 1024)  # 4 MB
            manifest2 = create_manifest_for_testing(repo, [blob3, blob4])
            tag2 = create_tag_for_manifest(manifest2, "v2.0")

        # Verify quota shows the new content (incremental update during push)
        final_quota = get_namespace_quota(org)
        expected_final = calculate_expected_size(blob3, blob4)
        assert (
            final_quota == expected_final
        ), f"New push should register in quota, got {final_quota}"

    def test_quota_warning_threshold_cleared_after_gc(self, setup_orgs):
        """
        Test 2: Set quota warning threshold (80%) → fill to 85% → delete tags → run GC → verify warning cleared.

        Verifies that:
        1. Quota warning threshold logic works
        2. After GC and quota recalculation, usage drops below threshold
        3. The persisted 80% QuotaNotificationState is cleared by the quota worker

        Configures a real UserOrganizationQuota with warning/reject thresholds and
        asserts both the enforcement severity (via check_limits) and the
        notification state written by QuotaTotalWorker._check_quotas.
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository
        repo = create_repository(org.username, "threshold-test", user)

        # 8.5 MB is 85% of the 10 MB limit set below.
        blob1 = "A" * (4 * 1024 * 1024)  # 4 MB
        blob2 = "B" * (4 * 1024 * 1024)  # 4 MB
        blob3 = "C" * (512 * 1024)  # 0.5 MB

        # Set up initial content
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_for_testing(repo, [blob1, blob2, blob3])
            tag1 = create_tag_for_manifest(manifest1, "v1.0")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1, blob2, blob3)
        assert initial_quota == expected_initial

        # Configure a real 10 MB namespace quota with an 80% (8 MB) warning
        # threshold, then assert the warning state is actually triggered by the
        # persisted usage rather than comparing against a local constant.
        quota_limit_bytes = 10 * 1024 * 1024
        set_namespace_quota_limit(org, quota_limit_bytes, warning_percent=80, reject_percent=100)
        assert (
            get_namespace_quota_severity(org) == QuotaTypes.WARNING
        ), "Usage above 80% of the limit should trigger the warning threshold before GC"

        # _check_quotas only notifies namespaces with a quota_warning
        # notification; firing it persists the 80% QuotaNotificationState.
        NamespaceNotification.create(
            namespace=org,
            event=ExternalNotificationEvent.get(name="quota_warning"),
            method=ExternalNotificationMethod.get(name="webhook"),
            config_json="{}",
            event_config_json="{}",
            title="quota warning",
        )
        with patch("features.QUOTA_NOTIFICATIONS", True):
            QuotaTotalWorker()._check_quotas()
        state = QuotaNotificationState.get(
            QuotaNotificationState.namespace == org,
            QuotaNotificationState.threshold_percent == 80,
        )
        assert state.cleared is False, "Warning notification state should be set before GC"

        # Delete tag and run GC
        expire_tag(repo, "v1.0")
        with enable_gc_and_quota():
            run_gc_worker()

        run_quota_worker(org.id)
        with patch("features.QUOTA_NOTIFICATIONS", True):
            QuotaTotalWorker()._check_quotas()

        # Verify usage dropped below the limit and the warning state is cleared
        # based on the real quota limits (severity is no longer Warning/Reject).
        quota_after_gc = get_namespace_quota(org)
        assert (
            quota_after_gc < quota_limit_bytes
        ), "Usage should drop below the quota limit after GC"
        assert (
            get_namespace_quota_severity(org) is None
        ), "Warning state should be cleared after GC frees space"
        state = QuotaNotificationState.get_by_id(state.id)
        assert state.cleared is True, "Persisted warning notification state should be cleared"

    def test_shared_blob_deduplication_after_gc(self, setup_orgs):
        """
        Test 3: Multiple repos same org → shared blob GC → quota deduplicated.

        Verifies that:
        1. Shared blobs are counted only once in namespace quota
        2. When one repo deletes a tag using shared blob, blob is not removed if other repo uses it
        3. Quota reflects correct deduplication after GC
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create two repositories in same org
        repo1 = create_repository(org.username, "shared-repo1", user)
        repo2 = create_repository(org.username, "shared-repo2", user)

        # Create shared blob
        shared_blob = "SHARED" * (1024 * 1024)  # 6 MB shared blob
        unique_blob1 = "UNIQUE1" * (1024 * 1024)  # 7 MB unique to repo1
        unique_blob2 = "UNIQUE2" * (1024 * 1024)  # 7 MB unique to repo2

        # Disable quota to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            # Repo1 has shared_blob + unique_blob1
            manifest1 = create_manifest_for_testing(repo1, [shared_blob, unique_blob1])
            tag1 = create_tag_for_manifest(manifest1, "v1.0")

            # Repo2 has shared_blob + unique_blob2
            manifest2 = create_manifest_for_testing(repo2, [shared_blob, unique_blob2])
            tag2 = create_tag_for_manifest(manifest2, "v1.0")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)

        # Namespace quota should count shared_blob only once
        expected_initial = calculate_expected_size(shared_blob, unique_blob1, unique_blob2)
        assert (
            initial_quota == expected_initial
        ), f"Shared blob should be counted once, got {initial_quota}"

        # Storage ids are deduplicated by digest, so the shared ones are the
        # intersection of the two manifests' blobs.
        repo1_ids = {
            mb.blob_id for mb in ManifestBlob.select().where(ManifestBlob.manifest == manifest1.id)
        }
        repo2_ids = {
            mb.blob_id for mb in ManifestBlob.select().where(ManifestBlob.manifest == manifest2.id)
        }
        shared_ids = repo1_ids & repo2_ids
        unique1_ids = repo1_ids - repo2_ids
        assert shared_ids and unique1_ids

        # Delete tag from repo1
        expire_tag(repo1, "v1.0")
        delete_upload_links(repo1)
        delete_upload_links(repo2)

        # Run GC
        with enable_gc_and_quota():
            run_gc_worker()

        assert ImageStorage.select().where(ImageStorage.id << list(shared_ids)).count() == len(
            shared_ids
        ), "Shared blob storage should survive GC while repo2 references it"
        assert (
            ImageStorage.select().where(ImageStorage.id << list(unique1_ids)).count() == 0
        ), "Repo1's unique blob storage should be removed by GC"

        run_quota_worker(org.id)

        # Verify quota after GC
        quota_after_gc = get_namespace_quota(org)

        # shared_blob should still exist (used by repo2), only unique_blob1 should be removed
        expected_after_gc = calculate_expected_size(shared_blob, unique_blob2)
        assert (
            quota_after_gc == expected_after_gc
        ), f"Shared blob should remain, got {quota_after_gc}"

        # Verify repo quotas
        repo1_quota = get_repo_quota(repo1)
        repo2_quota = get_repo_quota(repo2)
        assert repo1_quota == 0, f"Repo1 should have 0 quota after GC, got {repo1_quota}"
        expected_repo2 = calculate_expected_size(shared_blob, unique_blob2)
        assert repo2_quota == expected_repo2, f"Repo2 quota incorrect, got {repo2_quota}"

    def test_orphaned_blob_removal_and_quota_update(self, setup_orgs):
        """
        Test 4: Delete all tags pointing to a blob → verify blob becomes orphaned → run GC → verify quota decreased.

        Verifies that:
        1. Blobs become orphaned when no tags reference them
        2. GC removes orphaned blobs
        3. Quota is updated to reflect removed blobs
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository
        repo = create_repository(org.username, "orphan-test", user)

        # Create blob that will become orphaned
        blob1 = "ORPHAN" * (2 * 1024 * 1024)  # 12 MB

        # Disable quota to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_for_testing(repo, [blob1])
            tag1 = create_tag_for_manifest(manifest1, "orphan-tag")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1)
        assert initial_quota == expected_initial

        # GC deletes the ManifestBlob rows, so capture the storage ids first.
        storage_ids = [
            mb.blob_id for mb in ManifestBlob.select().where(ManifestBlob.manifest == manifest1.id)
        ]
        assert storage_ids

        # Delete the tag, making the blob orphaned
        expire_tag(repo, "orphan-tag")
        delete_upload_links(repo)

        # Run GC to remove orphaned blob
        with enable_gc_and_quota():
            run_gc_worker()

        run_quota_worker(org.id)

        # Verify the tag is gone
        assert get_tag(repo.id, "orphan-tag") is None, "Tag should be removed after GC"

        # Verify the blob's ImageStorage row was deleted
        remaining_storage = ImageStorage.select().where(ImageStorage.id << storage_ids).count()
        assert remaining_storage == 0, "Orphaned blob's ImageStorage should be removed by GC"

        # Verify quota decreased (blob removed)
        quota_after_gc = get_namespace_quota(org)
        assert (
            quota_after_gc == 0
        ), f"Orphaned blob should be removed, quota should be 0, got {quota_after_gc}"

    def test_skipped_manifest_remains_counted(self, setup_orgs):
        """
        Test 5: Partial GC (manifest not collected) → quota reflects only successfully removed blobs.

        Verifies that:
        1. If GC skips a manifest (returns False), quota only reflects successfully removed blobs
        2. Skipped manifest's blobs remain counted in quota
        3. System handles partial collection correctly

        Note: This test simulates a skipped manifest by patching _garbage_collect_manifest
        to return False, which indicates the manifest is still referenced or already gone.
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository with multiple manifests
        repo = create_repository(org.username, "partial-gc-test", user)

        blob1 = "A" * (2 * 1024 * 1024)  # 2 MB
        blob2 = "B" * (2 * 1024 * 1024)  # 2 MB
        blob3 = "C" * (2 * 1024 * 1024)  # 2 MB

        # Disable quota to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_for_testing(repo, [blob1])
            tag1 = create_tag_for_manifest(manifest1, "v1.0")

            manifest2 = create_manifest_for_testing(repo, [blob2])
            tag2 = create_tag_for_manifest(manifest2, "v2.0")

            manifest3 = create_manifest_for_testing(repo, [blob3])
            tag3 = create_tag_for_manifest(manifest3, "v3.0")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1, blob2, blob3)
        assert initial_quota == expected_initial

        # Expire two tags
        expire_tag(repo, "v1.0")
        expire_tag(repo, "v2.0")

        # Make GC skip manifest1 (blob1) while allowing
        # manifest2 (blob2) to be collected normally. Quay counts a blob toward
        # quota via its ManifestBlob rows, and GC deletes those rows during the
        # manifest-purge step (before the later storage-removal step). So to
        # keep the skipped blob counted, the skip must be injected at the
        # manifest-purge step, not at storage removal.
        real_gc_manifest = gc_model._garbage_collect_manifest

        def _fail_manifest1(manifest_id, context):
            if manifest_id == manifest1.id:
                # Simulate a failed/skipped collection of this manifest.
                return False
            return real_gc_manifest(manifest_id, context)

        with patch.object(gc_model, "_garbage_collect_manifest", side_effect=_fail_manifest1):
            with enable_gc_and_quota():
                run_gc_worker()

        run_quota_worker(org.id)

        # blob2 was removed successfully, but blob1's collection was skipped so its
        # ManifestBlob rows survive and it remains counted alongside the never-
        # expired blob3.
        quota_after_gc = get_namespace_quota(org)
        expected_after_gc = calculate_expected_size(blob1, blob3)
        assert (
            quota_after_gc == expected_after_gc
        ), f"Skipped blob1 should remain counted with blob3, got {quota_after_gc}"

    def test_concurrent_push_during_gc_maintains_consistency(self, setup_orgs):
        """
        Test 6: Run GC → push a new manifest from inside GC's storage-removal step → verify consistency.

        Verifies that:
        1. GC doesn't remove the tag or manifest pushed while it runs
        2. Quota includes new blobs correctly
        3. Concurrent operations don't corrupt quota state

        The concurrent push is injected mid-GC via a synchronization hook (deterministic,
        since the test DB fixture is single-connection and cannot be shared across threads).
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository
        repo = create_repository(org.username, "concurrent-test", user)

        # Create old blob to be GC'd
        old_blob = "OLD" * (2 * 1024 * 1024)  # 2 MB

        # Disable quota to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_for_testing(repo, [old_blob])
            tag1 = create_tag_for_manifest(manifest1, "old-tag")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)

        # Expire old tag
        expire_tag(repo, "old-tag")

        # New content that lands "concurrently" while GC is in progress.
        new_blob = "NEW" * (2 * 1024 * 1024)  # 2 MB

        # Coordinate the concurrent push via a synchronization hook: the first
        # time GC reaches its storage-removal step (i.e. after it has already
        # computed the set of blobs to remove for the expired tag), the push is
        # injected. GC is therefore in progress when the new blob is written.
        # A synchronization hook is used instead of real threads because the
        # test DB fixture is single-connection and cannot be shared across
        # threads; this keeps the interleaving deterministic while still
        # exercising the race: GC must not remove a blob pushed after it
        # computed its removal set.
        real_gc_storage = storage_model.garbage_collect_storage
        push_state = {}

        def _push_during_gc(storage_id_whitelist, namespace=None, repo_name=None):
            if "manifest" not in push_state:
                with enable_quota_management():
                    push_state["manifest"] = create_manifest_for_testing(repo, [new_blob])
                    push_state["tag"] = create_tag_for_manifest(push_state["manifest"], "new-tag")
            return real_gc_storage(storage_id_whitelist, namespace=namespace, repo_name=repo_name)

        with patch.object(storage_model, "garbage_collect_storage", side_effect=_push_during_gc):
            with enable_gc_and_quota():
                run_gc_worker()

        # The push must have actually been injected during GC.
        assert "manifest" in push_state, "Concurrent push hook did not fire during GC"

        run_quota_worker(org.id)

        # Verify the pushed content survived: tag must still resolve
        new_tag = get_tag(repo.id, "new-tag")
        assert new_tag is not None, "Concurrently pushed tag should survive GC"
        assert (
            new_tag.manifest_id == push_state["manifest"].id
        ), "Tag should point to pushed manifest"

        # Verify quota reflects the new blob
        quota_after = get_namespace_quota(org)
        expected_after = calculate_expected_size(new_blob)
        assert quota_after == expected_after, f"New blob should be preserved, got {quota_after}"

    def test_quota_overflow_corrected_by_gc(self, setup_orgs):
        """
        Test 7: Fill quota to 105% (overflow) → delete tags → run GC → verify quota corrected.

        Verifies that:
        1. Quota can be corrected even when in overflow state
        2. GC + quota recalculation brings quota back to normal
        3. Overflow scenarios are handled correctly
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository
        repo = create_repository(org.username, "overflow-test", user)

        # Create blobs that exceed typical limits
        blob1 = "A" * (6 * 1024 * 1024)  # 6 MB
        blob2 = "B" * (6 * 1024 * 1024)  # 6 MB

        # Disable quota to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_for_testing(repo, [blob1, blob2])
            tag1 = create_tag_for_manifest(manifest1, "overflow-tag")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1, blob2)
        assert initial_quota == expected_initial

        # Configure a real 10 MB namespace quota. With ~12 MB of content the
        # namespace is in overflow, so the reject threshold (100%) must fire.
        quota_limit_bytes = 10 * 1024 * 1024
        set_namespace_quota_limit(org, quota_limit_bytes, warning_percent=80, reject_percent=100)
        assert initial_quota > quota_limit_bytes, "Usage should exceed the quota limit (overflow)"
        assert (
            get_namespace_quota_severity(org) == QuotaTypes.REJECT
        ), "Overflow usage should trigger the reject threshold before GC"

        # Delete tag and run GC
        expire_tag(repo, "overflow-tag")
        with enable_gc_and_quota():
            run_gc_worker()

        run_quota_worker(org.id)

        # Verify quota is corrected to actual usage (0) and enforcement cleared.
        quota_after_gc = get_namespace_quota(org)
        assert quota_after_gc == 0, f"Quota should be corrected to 0, got {quota_after_gc}"
        assert (
            get_namespace_quota_severity(org) is None
        ), "Reject/overflow state should be cleared after GC frees space"

    def test_cross_org_quota_isolation_during_gc(self, setup_orgs):
        """
        Test 8: Create two orgs → fill quota in org A → run GC in org A → verify org B unchanged.

        Verifies that:
        1. GC operations in one org don't affect other orgs
        2. Quota isolation is maintained across organizations
        3. Cross-org quota state remains independent
        """
        user = setup_orgs["user"]
        org_a = setup_orgs["org1"]
        org_b = setup_orgs["org2"]

        # Create repositories in both orgs
        repo_a = create_repository(org_a.username, "repo-a", user)
        repo_b = create_repository(org_b.username, "repo-b", user)

        blob_a = "A" * (4 * 1024 * 1024)  # 4 MB
        blob_b = "B" * (4 * 1024 * 1024)  # 4 MB

        # Disable quota to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest_a = create_manifest_for_testing(repo_a, [blob_a])
            tag_a = create_tag_for_manifest(manifest_a, "v1.0")

            manifest_b = create_manifest_for_testing(repo_b, [blob_b])
            tag_b = create_tag_for_manifest(manifest_b, "v1.0")

        # Run initial quota backfill for both orgs
        run_backfill(org_a.id)
        run_backfill(org_b.id)

        quota_a_initial = get_namespace_quota(org_a)
        quota_b_initial = get_namespace_quota(org_b)

        expected_a = calculate_expected_size(blob_a)
        expected_b = calculate_expected_size(blob_b)

        assert (
            quota_a_initial == expected_a
        ), f"Org A quota should be {expected_a}, got {quota_a_initial}"
        assert (
            quota_b_initial == expected_b
        ), f"Org B quota should be {expected_b}, got {quota_b_initial}"

        # Delete tag in org A and run GC
        expire_tag(repo_a, "v1.0")
        with enable_gc_and_quota():
            run_gc_worker()

        # Check org B before any recalculation, so GC's own effect is observed.
        quota_b_after_gc = get_namespace_quota(org_b)
        assert (
            quota_b_after_gc == expected_b
        ), f"GC in org A should not change org B quota, got {quota_b_after_gc}"

        run_quota_worker(org_a.id)

        # Verify org A quota is freed
        quota_a_after = get_namespace_quota(org_a)
        assert quota_a_after == 0, f"Org A quota should be 0 after GC, got {quota_a_after}"

        # Verify org B quota is UNCHANGED
        quota_b_after = get_namespace_quota(org_b)
        assert (
            quota_b_after == expected_b
        ), f"Org B quota should remain {expected_b}, got {quota_b_after}"
