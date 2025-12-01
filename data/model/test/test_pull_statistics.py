from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from peewee import IntegrityError

from data import model
from data.database import ManifestPullStatistics, TagPullStatistics
from data.model.oci import tag as oci_tag
from data.model.oci.tag import retarget_tag
from data.model.oci.test.test_oci_manifest import create_manifest_for_testing
from data.model.pull_statistics import (
    PullStatisticsException,
    bulk_upsert_manifest_statistics,
    bulk_upsert_tag_statistics,
    get_manifest_pull_statistics,
    get_tag_pull_statistics,
)
from data.model.repository import create_repository
from data.model.user import get_user
from test.fixtures import *


class TestPullStatistics:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")
        self.repo = create_repository("devtable", "newrepo", self.user, repo_kind="image")
        assert self.repo is not None, "Failed to create test repository"
        self.repo_id = self.repo.id

    def _normalize_datetime(self, dt):
        """
        Normalize datetime objects from different database backends for comparison.

        - SQLite: Returns string representations
        - MySQL: Returns timezone-naive datetime objects
        - PostgreSQL: Returns timezone-aware datetime objects
        """
        if isinstance(dt, str):
            # SQLite might return datetime as string
            return datetime.fromisoformat(dt.replace("Z", "+00:00"))
        elif dt.tzinfo is None:
            # MySQL returns timezone-naive datetime - assume UTC
            from datetime import timezone

            return dt.replace(tzinfo=timezone.utc)
        else:
            # PostgreSQL returns timezone-aware - use as-is
            return dt

    def test_bulk_upsert_tag_statistics_new_records(self, initialized_db):
        """Test inserting new tag pull statistics records."""
        tag_updates = [
            {
                "repository_id": self.repo_id,
                "tag_name": "latest",
                "manifest_digest": "sha256:abc123",
                "pull_count": 5,
                "last_pull_timestamp": datetime(2024, 1, 1, 12, 0, 0),
            },
            {
                "repository_id": self.repo_id,
                "tag_name": "v1.0",
                "manifest_digest": "sha256:def456",
                "pull_count": 3,
                "last_pull_timestamp": datetime(2024, 1, 2, 12, 0, 0),
            },
        ]

        rows_affected = bulk_upsert_tag_statistics(tag_updates)
        assert rows_affected == 2

        # Verify records were created
        latest_stats = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "latest"
        )
        assert latest_stats.tag_pull_count == 5
        assert latest_stats.current_manifest_digest == "sha256:abc123"
        assert latest_stats.last_tag_pull_date == datetime(2024, 1, 1, 12, 0, 0)

        v1_stats = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "v1.0"
        )
        assert v1_stats.tag_pull_count == 3
        assert v1_stats.current_manifest_digest == "sha256:def456"
        assert v1_stats.last_tag_pull_date == datetime(2024, 1, 2, 12, 0, 0)

    def test_bulk_upsert_tag_statistics_update_existing(self, initialized_db):
        """Test updating existing tag pull statistics records."""
        # Create initial record
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="latest",
            tag_pull_count=5,
            last_tag_pull_date=datetime(2024, 1, 1, 12, 0, 0),
            current_manifest_digest="sha256:old123",
        )

        # Update with new data
        tag_updates = [
            {
                "repository_id": self.repo_id,
                "tag_name": "latest",
                "manifest_digest": "sha256:new456",
                "pull_count": 3,  # Additional pulls
                "last_pull_timestamp": datetime(2024, 1, 3, 12, 0, 0),
            }
        ]

        rows_affected = bulk_upsert_tag_statistics(tag_updates)
        assert rows_affected == 1

        # Verify record was updated (count should be incremented atomically)
        updated_stats = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "latest"
        )
        assert updated_stats.tag_pull_count == 8  # 5 + 3 = 8 (atomic SQL addition, not max)
        assert updated_stats.current_manifest_digest == "sha256:new456"
        assert updated_stats.last_tag_pull_date == datetime(
            2024, 1, 3, 12, 0, 0
        )  # SQL CASE keeps latest

    def test_bulk_upsert_manifest_statistics_new_records(self, initialized_db):
        """Test inserting new manifest pull statistics records."""
        manifest_updates = [
            {
                "repository_id": self.repo_id,
                "manifest_digest": "sha256:abc123",
                "pull_count": 10,
                "last_pull_timestamp": datetime(2024, 1, 1, 12, 0, 0),
            },
            {
                "repository_id": self.repo_id,
                "manifest_digest": "sha256:def456",
                "pull_count": 7,
                "last_pull_timestamp": datetime(2024, 1, 2, 12, 0, 0),
            },
        ]

        rows_affected = bulk_upsert_manifest_statistics(manifest_updates)
        assert rows_affected == 2

        # Verify records were created
        abc_stats = ManifestPullStatistics.get(
            ManifestPullStatistics.repository == self.repo_id,
            ManifestPullStatistics.manifest_digest == "sha256:abc123",
        )
        assert abc_stats.manifest_pull_count == 10
        assert abc_stats.last_manifest_pull_date == datetime(2024, 1, 1, 12, 0, 0)

        def_stats = ManifestPullStatistics.get(
            ManifestPullStatistics.repository == self.repo_id,
            ManifestPullStatistics.manifest_digest == "sha256:def456",
        )
        assert def_stats.manifest_pull_count == 7
        assert def_stats.last_manifest_pull_date == datetime(2024, 1, 2, 12, 0, 0)

    def test_bulk_upsert_manifest_statistics_update_existing(self, initialized_db):
        """Test updating existing manifest pull statistics records."""
        # Create initial record
        ManifestPullStatistics.create(
            repository=self.repo,
            manifest_digest="sha256:abc123",
            manifest_pull_count=10,
            last_manifest_pull_date=datetime(2024, 1, 1, 12, 0, 0),
        )

        # Update with new data
        manifest_updates = [
            {
                "repository_id": self.repo_id,
                "manifest_digest": "sha256:abc123",
                "pull_count": 5,  # Additional pulls
                "last_pull_timestamp": datetime(2024, 1, 3, 12, 0, 0),
            }
        ]

        rows_affected = bulk_upsert_manifest_statistics(manifest_updates)
        assert rows_affected == 1

        # Verify record was updated (count should be incremented atomically)
        updated_stats = ManifestPullStatistics.get(
            ManifestPullStatistics.repository == self.repo_id,
            ManifestPullStatistics.manifest_digest == "sha256:abc123",
        )
        assert updated_stats.manifest_pull_count == 15  # 10 + 5 = 15 (atomic SQL addition, not max)
        assert updated_stats.last_manifest_pull_date == datetime(
            2024, 1, 3, 12, 0, 0
        )  # SQL CASE keeps latest

    def test_get_tag_pull_statistics_existing(self, initialized_db):
        """Test retrieving existing tag pull statistics."""
        # Create test data
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="v2.0",
            tag_pull_count=25,
            last_tag_pull_date=datetime(2024, 1, 15, 10, 30, 0),
            current_manifest_digest="sha256:test789",
        )

        stats = get_tag_pull_statistics(self.repo_id, "v2.0")

        assert stats is not None
        assert stats["repository_id"] == self.repo_id
        assert stats["tag_name"] == "v2.0"
        assert stats["pull_count"] == 25
        assert stats["last_pull_date"] == datetime(2024, 1, 15, 10, 30, 0)
        assert stats["current_manifest_digest"] == "sha256:test789"

    def test_get_tag_pull_statistics_missing(self, initialized_db):
        """Test retrieving non-existent tag pull statistics."""
        stats = get_tag_pull_statistics(self.repo_id, "nonexistent")
        assert stats is None

    def test_get_manifest_pull_statistics_existing(self, initialized_db):
        """Test retrieving existing manifest pull statistics."""
        # Create test data
        ManifestPullStatistics.create(
            repository=self.repo,
            manifest_digest="sha256:test999",
            manifest_pull_count=42,
            last_manifest_pull_date=datetime(2024, 1, 20, 14, 45, 0),
        )

        stats = get_manifest_pull_statistics(self.repo_id, "sha256:test999")

        assert stats is not None
        assert stats["repository_id"] == self.repo_id
        assert stats["manifest_digest"] == "sha256:test999"
        assert stats["pull_count"] == 42
        assert stats["last_pull_date"] == datetime(2024, 1, 20, 14, 45, 0)

    def test_get_manifest_pull_statistics_missing(self, initialized_db):
        """Test retrieving non-existent manifest pull statistics."""
        stats = get_manifest_pull_statistics(self.repo_id, "sha256:nonexistent")
        assert stats is None

    def test_bulk_upsert_tag_statistics_empty_list(self, initialized_db):
        """Test bulk upsert with empty list."""
        # Empty list should return 0
        rows_affected = bulk_upsert_tag_statistics([])
        assert rows_affected == 0

    def test_concurrent_updates_tag_statistics(self, initialized_db):
        """Test sequential updates to same tag statistics - atomic SQL ensures correct accumulation."""
        # Create initial record
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="concurrent",
            tag_pull_count=10,
            last_tag_pull_date=datetime(2024, 1, 1, 12, 0, 0),
            current_manifest_digest="sha256:initial",
        )

        # Simulate concurrent updates with different timestamps
        updates1 = [
            {
                "repository_id": self.repo_id,
                "tag_name": "concurrent",
                "manifest_digest": "sha256:update1",
                "pull_count": 5,
                "last_pull_timestamp": datetime(2024, 1, 2, 12, 0, 0),
            }
        ]

        updates2 = [
            {
                "repository_id": self.repo_id,
                "tag_name": "concurrent",
                "manifest_digest": "sha256:update2",
                "pull_count": 3,
                "last_pull_timestamp": datetime(2024, 1, 3, 12, 0, 0),  # Later timestamp
            }
        ]

        # Apply both updates
        bulk_upsert_tag_statistics(updates1)
        bulk_upsert_tag_statistics(updates2)

        # Verify final state - atomic SQL updates ensure correct accumulation
        final_stats = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "concurrent"
        )
        assert final_stats.tag_pull_count == 18  # 10 + 5 + 3 = 18 (atomic SQL addition)
        assert final_stats.current_manifest_digest == "sha256:update2"  # Latest update
        assert final_stats.last_tag_pull_date == datetime(
            2024, 1, 3, 12, 0, 0
        )  # SQL CASE keeps latest timestamp

    def test_unique_constraints_tag_statistics(self, initialized_db):
        """Test that unique constraints are enforced for tag statistics."""
        # Create initial tag statistics
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="unique_test",
            tag_pull_count=1,
            last_tag_pull_date=datetime.now(),
            current_manifest_digest="sha256:test",
        )

        # Try to create duplicate (should fail)
        with pytest.raises(IntegrityError):  # Unique constraint violation
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="unique_test",  # Same tag name for same repo
                tag_pull_count=2,
                last_tag_pull_date=datetime.now(),
                current_manifest_digest="sha256:test2",
            )

    def test_unique_constraints_manifest_statistics(self, initialized_db):
        """Test that unique constraints are enforced for manifest statistics."""
        # Create initial manifest statistics
        ManifestPullStatistics.create(
            repository=self.repo,
            manifest_digest="sha256:unique_test",
            manifest_pull_count=1,
            last_manifest_pull_date=datetime.now(),
        )

        # Try to create duplicate (should fail)
        with pytest.raises(IntegrityError):  # Unique constraint violation
            ManifestPullStatistics.create(
                repository=self.repo,
                manifest_digest="sha256:unique_test",  # Same digest for same repo
                manifest_pull_count=2,
                last_manifest_pull_date=datetime.now(),
            )

    def test_bulk_operations_performance(self, initialized_db):
        """Test bulk operations with larger datasets."""
        # Generate a larger set of updates
        tag_updates = []
        manifest_updates = []

        for i in range(100):
            tag_updates.append(
                {
                    "repository_id": self.repo_id,
                    "tag_name": f"tag_{i}",
                    "manifest_digest": f"sha256:digest_{i}",
                    "pull_count": i + 1,
                    "last_pull_timestamp": datetime(2024, 1, 1, 12, i % 60, 0),
                }
            )

            manifest_updates.append(
                {
                    "repository_id": self.repo_id,
                    "manifest_digest": f"sha256:manifest_{i}",
                    "pull_count": (i + 1) * 2,
                    "last_pull_timestamp": datetime(2024, 1, 1, 12, i % 60, 0),
                }
            )

        # Test bulk insert performance
        tag_rows = bulk_upsert_tag_statistics(tag_updates)
        manifest_rows = bulk_upsert_manifest_statistics(manifest_updates)

        assert tag_rows == 100
        assert manifest_rows == 100

        # Verify a few random records
        assert (
            TagPullStatistics.select().where(TagPullStatistics.repository == self.repo_id).count()
            == 100
        )
        assert (
            ManifestPullStatistics.select()
            .where(ManifestPullStatistics.repository == self.repo_id)
            .count()
            == 100
        )

        # Test sample record
        sample_tag = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "tag_50"
        )
        assert sample_tag.tag_pull_count == 51
        assert sample_tag.current_manifest_digest == "sha256:digest_50"

    def test_bulk_upsert_mixed_new_and_existing(self, initialized_db):
        """Test bulk upsert with both new records and existing record updates."""
        # Create some existing records first
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="existing1",
            tag_pull_count=10,
            last_tag_pull_date=datetime(2024, 1, 1, 12, 0, 0),
            current_manifest_digest="sha256:old1",
        )
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="existing2",
            tag_pull_count=20,
            last_tag_pull_date=datetime(2024, 1, 2, 12, 0, 0),
            current_manifest_digest="sha256:old2",
        )

        # Mix of updates to existing records and new record creation
        tag_updates = [
            # Update existing record
            {
                "repository_id": self.repo_id,
                "tag_name": "existing1",
                "manifest_digest": "sha256:new1",
                "pull_count": 5,
                "last_pull_timestamp": datetime(2024, 1, 5, 12, 0, 0),
            },
            # Create new record
            {
                "repository_id": self.repo_id,
                "tag_name": "brand_new",
                "manifest_digest": "sha256:new",
                "pull_count": 3,
                "last_pull_timestamp": datetime(2024, 1, 3, 12, 0, 0),
            },
            # Update another existing record
            {
                "repository_id": self.repo_id,
                "tag_name": "existing2",
                "manifest_digest": "sha256:new2",
                "pull_count": 7,
                "last_pull_timestamp": datetime(2024, 1, 4, 12, 0, 0),
            },
        ]

        rows_affected = bulk_upsert_tag_statistics(tag_updates)
        assert rows_affected == 3

        # Verify updated existing records - atomic SQL updates ensure correct values
        existing1 = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "existing1"
        )
        assert existing1.tag_pull_count == 15  # 10 + 5 = 15 (atomic SQL addition)
        assert existing1.current_manifest_digest == "sha256:new1"
        assert existing1.last_tag_pull_date == datetime(
            2024, 1, 5, 12, 0, 0
        )  # SQL CASE keeps latest (Jan 5 > Jan 1)

        existing2 = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "existing2"
        )
        assert existing2.tag_pull_count == 27  # 20 + 7 = 27 (atomic SQL addition)
        assert existing2.current_manifest_digest == "sha256:new2"
        assert existing2.last_tag_pull_date == datetime(
            2024, 1, 4, 12, 0, 0
        )  # SQL CASE keeps latest (Jan 4 > Jan 2)

        # Verify new record was created
        new_record = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "brand_new"
        )
        assert new_record.tag_pull_count == 3
        assert new_record.current_manifest_digest == "sha256:new"
        assert new_record.last_tag_pull_date == datetime(2024, 1, 3, 12, 0, 0)

    def test_bulk_upsert_string_timestamps(self, initialized_db):
        """Test bulk upsert with string timestamp formats (ISO format)."""
        tag_updates = [
            {
                "repository_id": self.repo_id,
                "tag_name": "string_timestamp",
                "manifest_digest": "sha256:string_test",
                "pull_count": 5,
                "last_pull_timestamp": "2024-01-15T14:30:00Z",  # ISO string with Z
            },
            {
                "repository_id": self.repo_id,
                "tag_name": "string_timestamp2",
                "manifest_digest": "sha256:string_test2",
                "pull_count": 3,
                "last_pull_timestamp": "2024-01-16T10:15:30.123Z",  # ISO string with milliseconds
            },
        ]

        rows_affected = bulk_upsert_tag_statistics(tag_updates)
        assert rows_affected == 2

        # Verify records were created with correct parsed timestamps
        record1 = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id,
            TagPullStatistics.tag_name == "string_timestamp",
        )
        assert record1.tag_pull_count == 5

        # Handle both datetime objects and string representations (SQLite vs PostgreSQL vs MySQL)
        last_pull_date = self._normalize_datetime(record1.last_tag_pull_date)
        expected_time1 = datetime.fromisoformat("2024-01-15T14:30:00+00:00")
        assert last_pull_date == expected_time1

        record2 = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id,
            TagPullStatistics.tag_name == "string_timestamp2",
        )
        # Test that milliseconds are handled (might be truncated depending on DB)
        assert record2.tag_pull_count == 3

        # Verify the timestamp was parsed and stored correctly (allowing for millisecond truncation)
        last_pull_date2 = self._normalize_datetime(record2.last_tag_pull_date)

        # Check that it's at least the correct date and time (milliseconds might be truncated)
        expected_time2_base = datetime.fromisoformat("2024-01-16T10:15:30+00:00")
        assert last_pull_date2 >= expected_time2_base

    def test_bulk_upsert_invalid_timestamp_format(self, initialized_db):
        """Test bulk upsert handles invalid timestamp formats gracefully."""
        tag_updates = [
            {
                "repository_id": self.repo_id,
                "tag_name": "invalid_timestamp",
                "manifest_digest": "sha256:invalid",
                "pull_count": 5,
                "last_pull_timestamp": "not-a-valid-timestamp",  # Invalid format
            }
        ]

        # Should raise PullStatisticsException due to invalid timestamp
        with pytest.raises(PullStatisticsException) as exc_info:
            bulk_upsert_tag_statistics(tag_updates)

        assert "Invalid tag update data" in str(exc_info.value)

    def test_bulk_upsert_maintains_last_pull_date_logic(self, initialized_db):
        """Test that bulk upsert properly handles last_pull_date using atomic SQL CASE to keep latest timestamp."""
        # Create existing record with later timestamp
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="timestamp_test",
            tag_pull_count=10,
            last_tag_pull_date=datetime(2024, 1, 10, 12, 0, 0),  # Later date
            current_manifest_digest="sha256:old",
        )

        # Try to update with earlier timestamp
        tag_updates = [
            {
                "repository_id": self.repo_id,
                "tag_name": "timestamp_test",
                "manifest_digest": "sha256:new",
                "pull_count": 5,
                "last_pull_timestamp": datetime(2024, 1, 5, 12, 0, 0),  # Earlier date
            }
        ]

        bulk_upsert_tag_statistics(tag_updates)

        # Verify the later timestamp is preserved using atomic SQL CASE (max for timestamp, addition for count)
        updated = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id,
            TagPullStatistics.tag_name == "timestamp_test",
        )
        assert updated.tag_pull_count == 15  # 10 + 5 = 15 (atomic SQL addition for count)
        assert updated.last_tag_pull_date == datetime(
            2024, 1, 10, 12, 0, 0
        )  # SQL CASE keeps later date atomically (max for timestamp)
        assert updated.current_manifest_digest == "sha256:new"  # But update manifest

    def test_delete_tag_clears_pull_statistics(self, initialized_db):
        """Test that deleting a tag clears its pull statistics."""
        with patch("data.model.oci.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = True

            # Create a manifest
            manifest, _ = create_manifest_for_testing(self.repo, "test1")

            # Create a tag
            _ = retarget_tag("test-tag", manifest)

            # Create pull statistics for the tag
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="test-tag",
                tag_pull_count=42,
                last_tag_pull_date=datetime(2024, 1, 1, 12, 0, 0),
                current_manifest_digest=manifest.digest,
            )

            # Verify statistics exist
            stats = TagPullStatistics.get(
                TagPullStatistics.repository == self.repo_id,
                TagPullStatistics.tag_name == "test-tag",
            )
            assert stats.tag_pull_count == 42

            # Delete the tag
            deleted_tag = oci_tag.delete_tag(self.repo.id, "test-tag")
            assert deleted_tag is not None

            # Verify pull statistics were deleted
            stats_query = TagPullStatistics.select().where(
                TagPullStatistics.repository == self.repo_id,
                TagPullStatistics.tag_name == "test-tag",
            )
            assert stats_query.count() == 0

    def test_delete_tag_with_feature_disabled(self, initialized_db):
        """Test that deleting a tag with IMAGE_PULL_STATS disabled preserves pull statistics."""
        with patch("data.model.oci.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = False

            # Create a manifest
            manifest, _ = create_manifest_for_testing(self.repo, "test2")

            # Create a tag
            _ = retarget_tag("test-tag-disabled", manifest)

            # Create pull statistics for the tag
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="test-tag-disabled",
                tag_pull_count=99,
                last_tag_pull_date=datetime(2024, 1, 15, 12, 0, 0),
                current_manifest_digest=manifest.digest,
            )

            # Verify statistics exist
            stats = TagPullStatistics.get(
                TagPullStatistics.repository == self.repo_id,
                TagPullStatistics.tag_name == "test-tag-disabled",
            )
            assert stats.tag_pull_count == 99

            # Delete the tag
            deleted_tag = oci_tag.delete_tag(self.repo.id, "test-tag-disabled")
            assert deleted_tag is not None

            # Verify pull statistics still exist (not deleted when feature is disabled)
            stats_query = TagPullStatistics.select().where(
                TagPullStatistics.repository == self.repo_id,
                TagPullStatistics.tag_name == "test-tag-disabled",
            )
            assert stats_query.count() == 1
            stats = stats_query.get()
            assert stats.tag_pull_count == 99

    def test_repush_tag_after_deletion_starts_fresh(self, initialized_db):
        """Test that re-pushing a tag after deletion starts with fresh pull statistics."""
        with patch("data.model.oci.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = True

            # Create first manifest
            manifest1, _ = create_manifest_for_testing(self.repo, "1")

            # Create tag
            _ = retarget_tag("redis", manifest1)

            # Simulate pulls by creating statistics
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="redis",
                tag_pull_count=100,
                last_tag_pull_date=datetime(2024, 1, 1, 12, 0, 0),
                current_manifest_digest=manifest1.digest,
            )

            # Delete the tag
            oci_tag.delete_tag(self.repo.id, "redis")

            # Verify statistics were cleared
            assert (
                TagPullStatistics.select()
                .where(
                    TagPullStatistics.repository == self.repo_id,
                    TagPullStatistics.tag_name == "redis",
                )
                .count()
                == 0
            )

            # Re-push the same tag name (simulating user scenario from bug report)
            manifest2, _ = create_manifest_for_testing(self.repo, "2")

            _ = retarget_tag("redis", manifest2)

            # Simulate new pulls
            tag_updates = [
                {
                    "repository_id": self.repo_id,
                    "tag_name": "redis",
                    "manifest_digest": manifest2.digest,
                    "pull_count": 5,
                    "last_pull_timestamp": datetime(2024, 2, 1, 12, 0, 0),
                }
            ]
            bulk_upsert_tag_statistics(tag_updates)

            # Verify statistics start fresh (not 105, but 5)
            stats = TagPullStatistics.get(
                TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "redis"
            )
            assert stats.tag_pull_count == 5  # Fresh start, not 100 + 5
            assert stats.last_tag_pull_date == datetime(2024, 2, 1, 12, 0, 0)
            assert stats.current_manifest_digest == manifest2.digest

    def test_remove_tag_from_timemachine_clears_pull_statistics(self, initialized_db):
        """Test that permanently deleting a tag clears its pull statistics."""
        with patch("data.model.oci.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = True

            # Create a manifest
            manifest, _ = create_manifest_for_testing(self.repo, "perm")

            # Create tag
            _ = retarget_tag("permanent-test", manifest)

            # Create pull statistics
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="permanent-test",
                tag_pull_count=75,
                last_tag_pull_date=datetime(2024, 3, 1, 10, 0, 0),
                current_manifest_digest=manifest.digest,
            )

            # Verify statistics exist
            assert (
                TagPullStatistics.select()
                .where(
                    TagPullStatistics.repository == self.repo_id,
                    TagPullStatistics.tag_name == "permanent-test",
                )
                .count()
                == 1
            )

            # Permanently delete the tag (bypass time machine)
            result = oci_tag.remove_tag_from_timemachine(
                self.repo.id,
                "permanent-test",
                manifest.id,
                include_submanifests=False,
                is_alive=True,
            )
            assert result is True

            # Verify pull statistics were cleared
            assert (
                TagPullStatistics.select()
                .where(
                    TagPullStatistics.repository == self.repo_id,
                    TagPullStatistics.tag_name == "permanent-test",
                )
                .count()
                == 0
            )

    def test_remove_tag_from_timemachine_with_feature_disabled_alive(self, initialized_db):
        """Test that permanently deleting an alive tag with IMAGE_PULL_STATS disabled preserves pull statistics."""
        with patch("data.model.oci.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = False

            # Create a manifest
            manifest, _ = create_manifest_for_testing(self.repo, "perm-disabled")

            # Create tag
            _ = retarget_tag("permanent-disabled-alive", manifest)

            # Create pull statistics
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="permanent-disabled-alive",
                tag_pull_count=85,
                last_tag_pull_date=datetime(2024, 3, 15, 10, 0, 0),
                current_manifest_digest=manifest.digest,
            )

            # Verify statistics exist
            assert (
                TagPullStatistics.select()
                .where(
                    TagPullStatistics.repository == self.repo_id,
                    TagPullStatistics.tag_name == "permanent-disabled-alive",
                )
                .count()
                == 1
            )

            # Permanently delete the tag (bypass time machine)
            result = oci_tag.remove_tag_from_timemachine(
                self.repo.id,
                "permanent-disabled-alive",
                manifest.id,
                include_submanifests=False,
                is_alive=True,
            )
            assert result is True

            # Verify pull statistics still exist (not deleted when feature is disabled)
            assert (
                TagPullStatistics.select()
                .where(
                    TagPullStatistics.repository == self.repo_id,
                    TagPullStatistics.tag_name == "permanent-disabled-alive",
                )
                .count()
                == 1
            )
            stats = TagPullStatistics.get(
                TagPullStatistics.repository == self.repo_id,
                TagPullStatistics.tag_name == "permanent-disabled-alive",
            )
            assert stats.tag_pull_count == 85

    def test_remove_tag_from_timemachine_with_feature_disabled_not_alive(self, initialized_db):
        """Test that permanently deleting a non-alive tag with IMAGE_PULL_STATS disabled preserves pull statistics."""
        with patch("data.model.oci.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = False

            # Create a manifest
            manifest, _ = create_manifest_for_testing(self.repo, "perm-not-alive")

            # Create tag
            tag = retarget_tag("permanent-disabled-not-alive", manifest)

            # Delete the tag first to make it not alive (but still in time machine)
            oci_tag.delete_tag(self.repo.id, "permanent-disabled-not-alive")

            # Create pull statistics for the deleted tag
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="permanent-disabled-not-alive",
                tag_pull_count=95,
                last_tag_pull_date=datetime(2024, 3, 20, 10, 0, 0),
                current_manifest_digest=manifest.digest,
            )

            # Verify statistics exist
            assert (
                TagPullStatistics.select()
                .where(
                    TagPullStatistics.repository == self.repo_id,
                    TagPullStatistics.tag_name == "permanent-disabled-not-alive",
                )
                .count()
                == 1
            )

            # Permanently delete the tag from time machine (is_alive=False)
            result = oci_tag.remove_tag_from_timemachine(
                self.repo.id,
                "permanent-disabled-not-alive",
                manifest.id,
                include_submanifests=False,
                is_alive=False,
            )
            assert result is True

            # Verify pull statistics still exist (not deleted when feature is disabled)
            assert (
                TagPullStatistics.select()
                .where(
                    TagPullStatistics.repository == self.repo_id,
                    TagPullStatistics.tag_name == "permanent-disabled-not-alive",
                )
                .count()
                == 1
            )
            stats = TagPullStatistics.get(
                TagPullStatistics.repository == self.repo_id,
                TagPullStatistics.tag_name == "permanent-disabled-not-alive",
            )
            assert stats.tag_pull_count == 95
