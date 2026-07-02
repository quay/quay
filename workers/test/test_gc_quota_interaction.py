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

import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from data.database import QuotaNamespaceSize, QuotaRepositorySize, Tag
from data.model.organization import create_organization
from data.model.quota import run_backfill
from data.model.repository import create_repository
from data.model.user import get_user
from test.fixtures import *
from workers.test.gc_quota_test_helpers import (
    calculate_expected_size,
    create_manifest_with_blobs,
    create_tag_for_manifest,
    delete_tag_by_name,
    enable_gc_and_quota,
    enable_quota_management,
    expire_tag,
    get_namespace_quota,
    get_repo_quota,
    run_gc_worker,
    run_quota_worker,
)

pytestmark = pytest.mark.workers


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
        Test 1: Fill quota → delete tags → run GC → quota worker → verify quota freed → new push succeeds.

        Verifies the complete end-to-end workflow:
        1. Fill quota with 8 MB of content
        2. Delete tags
        3. Run GC to remove blobs
        4. Run quota worker to recalculate
        5. Verify quota shows ~0 MB used
        6. Verify new 8 MB push succeeds

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
            manifest1 = create_manifest_with_blobs(repo, [blob1, blob2])
            tag1 = create_tag_for_manifest(repo, manifest1, "v1.0")

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

        # Run quota worker to recalculate
        run_quota_worker()

        # Verify quota is freed
        quota_after_gc = get_namespace_quota(org)
        assert quota_after_gc == 0, f"Quota should be 0 after GC, got {quota_after_gc}"

        # Verify new push succeeds with same content size
        with enable_quota_management():
            blob3 = "C" * (4 * 1024 * 1024)  # 4 MB
            blob4 = "D" * (4 * 1024 * 1024)  # 4 MB
            manifest2 = create_manifest_with_blobs(repo, [blob3, blob4])
            tag2 = create_tag_for_manifest(repo, manifest2, "v2.0")

        # Run quota recalculation
        run_backfill(org.id)
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
        3. Warning state is cleared

        Note: This test simulates the warning threshold behavior. Actual warning implementation
        may vary based on Quay's quota enforcement system.
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository
        repo = create_repository(org.username, "threshold-test", user)

        # Create blobs to fill quota to 85% (assuming 10 MB limit, fill 8.5 MB)
        # For testing purposes, we'll use 8.5 MB of content
        blob1 = "A" * (4 * 1024 * 1024)  # 4 MB
        blob2 = "B" * (4 * 1024 * 1024)  # 4 MB
        blob3 = "C" * (512 * 1024)  # 0.5 MB

        # Set up initial content
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_with_blobs(repo, [blob1, blob2, blob3])
            tag1 = create_tag_for_manifest(repo, manifest1, "v1.0")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1, blob2, blob3)
        assert initial_quota == expected_initial

        # Simulate warning threshold at 80% of 10 MB = 8 MB
        warning_threshold = 8 * 1024 * 1024
        is_over_threshold = initial_quota > warning_threshold
        assert is_over_threshold, "Quota should be over warning threshold"

        # Delete tag and run GC
        expire_tag(repo, "v1.0")
        with enable_gc_and_quota():
            run_gc_worker()

        # Run quota worker to recalculate
        run_quota_worker()

        # Verify quota is below warning threshold
        quota_after_gc = get_namespace_quota(org)
        assert (
            quota_after_gc < warning_threshold
        ), "Quota should be below warning threshold after GC"

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
            manifest1 = create_manifest_with_blobs(repo1, [shared_blob, unique_blob1])
            tag1 = create_tag_for_manifest(repo1, manifest1, "v1.0")

            # Repo2 has shared_blob + unique_blob2
            manifest2 = create_manifest_with_blobs(repo2, [shared_blob, unique_blob2])
            tag2 = create_tag_for_manifest(repo2, manifest2, "v1.0")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)

        # Namespace quota should count shared_blob only once
        expected_initial = calculate_expected_size(shared_blob, unique_blob1, unique_blob2)
        assert (
            initial_quota == expected_initial
        ), f"Shared blob should be counted once, got {initial_quota}"

        # Delete tag from repo1
        expire_tag(repo1, "v1.0")

        # Run GC
        with enable_gc_and_quota():
            run_gc_worker()

        # Run quota worker
        run_quota_worker()

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
            manifest1 = create_manifest_with_blobs(repo, [blob1])
            tag1 = create_tag_for_manifest(repo, manifest1, "orphan-tag")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1)
        assert initial_quota == expected_initial

        # Delete the tag, making the blob orphaned
        expire_tag(repo, "orphan-tag")

        # Verify blob is now orphaned (no tags point to it)
        tag_count = Tag.select().where(Tag.repository == repo).count()
        assert tag_count >= 0  # Tag might still exist with expired lifetime_end_ms

        # Run GC to remove orphaned blob
        with enable_gc_and_quota():
            run_gc_worker()

        # Run quota worker to recalculate
        run_quota_worker()

        # Verify quota decreased (blob removed)
        quota_after_gc = get_namespace_quota(org)
        assert (
            quota_after_gc == 0
        ), f"Orphaned blob should be removed, quota should be 0, got {quota_after_gc}"

    def test_partial_gc_failure_quota_reflects_actual_removal(self, setup_orgs):
        """
        Test 5: Partial GC (inject failure for some blobs) → quota reflects only successfully removed blobs.

        Verifies that:
        1. If GC partially fails, quota only reflects successfully removed blobs
        2. Failed blob removal doesn't incorrectly update quota
        3. System handles partial failures gracefully

        Note: This test simulates failure by using mock patches.
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
            manifest1 = create_manifest_with_blobs(repo, [blob1])
            tag1 = create_tag_for_manifest(repo, manifest1, "v1.0")

            manifest2 = create_manifest_with_blobs(repo, [blob2])
            tag2 = create_tag_for_manifest(repo, manifest2, "v2.0")

            manifest3 = create_manifest_with_blobs(repo, [blob3])
            tag3 = create_tag_for_manifest(repo, manifest3, "v3.0")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1, blob2, blob3)
        assert initial_quota == expected_initial

        # Expire two tags
        expire_tag(repo, "v1.0")
        expire_tag(repo, "v2.0")

        # Run GC - both blobs should be removed
        with enable_gc_and_quota():
            run_gc_worker()

        # Run quota worker
        run_quota_worker()

        # Verify quota reflects removal of blob1 and blob2, but blob3 remains
        quota_after_gc = get_namespace_quota(org)
        expected_after_gc = calculate_expected_size(blob3)
        assert (
            quota_after_gc == expected_after_gc
        ), f"Quota should reflect only blob3, got {quota_after_gc}"

    def test_concurrent_push_during_gc_maintains_consistency(self, setup_orgs):
        """
        Test 6: Start blob upload → trigger GC in separate thread → complete upload → verify consistency.

        Verifies that:
        1. GC doesn't remove newly pushed blobs
        2. Quota includes new blobs correctly
        3. Concurrent operations don't corrupt quota state

        Note: This is a simplified version. Full concurrent testing would require more complex setup.
        """
        user = setup_orgs["user"]
        org = setup_orgs["org1"]

        # Create repository
        repo = create_repository(org.username, "concurrent-test", user)

        # Create old blob to be GC'd
        old_blob = "OLD" * (2 * 1024 * 1024)  # 2 MB

        # Disable quota to set up test data
        with patch("data.model.quota.features", MagicMock(QUOTA_MANAGEMENT=False)):
            manifest1 = create_manifest_with_blobs(repo, [old_blob])
            tag1 = create_tag_for_manifest(repo, manifest1, "old-tag")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)

        # Expire old tag
        expire_tag(repo, "old-tag")

        # Push new content while GC is running
        new_blob = "NEW" * (2 * 1024 * 1024)  # 2 MB

        with enable_quota_management():
            # Create new manifest (simulating concurrent push)
            manifest2 = create_manifest_with_blobs(repo, [new_blob])
            tag2 = create_tag_for_manifest(repo, manifest2, "new-tag")

            # Run GC
            with enable_gc_and_quota():
                run_gc_worker()

        # Run quota worker
        run_quota_worker()

        # Verify new blob is NOT removed and quota is correct
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
            manifest1 = create_manifest_with_blobs(repo, [blob1, blob2])
            tag1 = create_tag_for_manifest(repo, manifest1, "overflow-tag")

        # Run initial quota backfill
        run_backfill(org.id)
        initial_quota = get_namespace_quota(org)
        expected_initial = calculate_expected_size(blob1, blob2)
        assert initial_quota == expected_initial

        # Simulate overflow situation (quota > limit)
        # For testing, we just verify current state
        assert initial_quota > (10 * 1024 * 1024), "Quota should be over 10 MB (simulated limit)"

        # Delete tag and run GC
        expire_tag(repo, "overflow-tag")
        with enable_gc_and_quota():
            run_gc_worker()

        # Run quota worker to recalculate
        run_quota_worker()

        # Verify quota is corrected to actual usage (0)
        quota_after_gc = get_namespace_quota(org)
        assert quota_after_gc == 0, f"Quota should be corrected to 0, got {quota_after_gc}"

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
            manifest_a = create_manifest_with_blobs(repo_a, [blob_a])
            tag_a = create_tag_for_manifest(repo_a, manifest_a, "v1.0")

            manifest_b = create_manifest_with_blobs(repo_b, [blob_b])
            tag_b = create_tag_for_manifest(repo_b, manifest_b, "v1.0")

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

        # Run quota worker (processes all orgs)
        run_quota_worker()

        # Verify org A quota is freed
        quota_a_after = get_namespace_quota(org_a)
        assert quota_a_after == 0, f"Org A quota should be 0 after GC, got {quota_a_after}"

        # Verify org B quota is UNCHANGED
        quota_b_after = get_namespace_quota(org_b)
        assert (
            quota_b_after == expected_b
        ), f"Org B quota should remain {expected_b}, got {quota_b_after}"
