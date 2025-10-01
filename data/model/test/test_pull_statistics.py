from datetime import datetime, timedelta

import pytest

from data import model
from data.database import ManifestPullStatistics, TagPullStatistics
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
        self.repo = create_repository("devtable", "testpullstats", self.user, repo_kind="image")
        self.repo_id = self.repo.id

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

        # Verify record was updated (count should be incremented)
        updated_stats = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "latest"
        )
        assert updated_stats.tag_pull_count == 8  # 5 + 3
        assert updated_stats.current_manifest_digest == "sha256:new456"
        assert updated_stats.last_tag_pull_date == datetime(2024, 1, 3, 12, 0, 0)

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

        # Verify record was updated (count should be incremented)
        updated_stats = ManifestPullStatistics.get(
            ManifestPullStatistics.repository == self.repo_id,
            ManifestPullStatistics.manifest_digest == "sha256:abc123",
        )
        assert updated_stats.manifest_pull_count == 15  # 10 + 5
        assert updated_stats.last_manifest_pull_date == datetime(2024, 1, 3, 12, 0, 0)

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

    @pytest.mark.parametrize(
        "updates",
        [
            [],  # Empty list
            [
                {
                    "repository_id": 999999,
                    "manifest_digest": "sha256:abc",
                    "pull_count": 1,
                    "last_pull_timestamp": datetime.now(),
                }
            ],  # Invalid repo
        ],
    )
    def test_concurrent_updates_tag_statistics(self, initialized_db):
        """Test concurrent updates to same tag statistics."""
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

        # Verify final state
        final_stats = TagPullStatistics.get(
            TagPullStatistics.repository == self.repo_id, TagPullStatistics.tag_name == "concurrent"
        )
        assert final_stats.tag_pull_count == 18  # 10 + 5 + 3
        assert final_stats.current_manifest_digest == "sha256:update2"  # Latest update
        assert final_stats.last_tag_pull_date == datetime(2024, 1, 3, 12, 0, 0)  # Latest timestamp

    def test_foreign_key_constraints(self, initialized_db):
        """Test that foreign key constraints are enforced."""
        # Test tag statistics with non-existent repository
        with pytest.raises(Exception):  # Foreign key constraint violation
            TagPullStatistics.create(
                repository_id=999999,  # Non-existent repository
                tag_name="test",
                tag_pull_count=1,
                last_tag_pull_date=datetime.now(),
                current_manifest_digest="sha256:test",
            )

        # Test manifest statistics with non-existent repository
        with pytest.raises(Exception):  # Foreign key constraint violation
            ManifestPullStatistics.create(
                repository_id=999999,  # Non-existent repository
                manifest_digest="sha256:test",
                manifest_pull_count=1,
                last_manifest_pull_date=datetime.now(),
            )

    def test_unique_constraints(self, initialized_db):
        """Test that unique constraints are enforced."""
        # Create initial tag statistics
        TagPullStatistics.create(
            repository=self.repo,
            tag_name="unique_test",
            tag_pull_count=1,
            last_tag_pull_date=datetime.now(),
            current_manifest_digest="sha256:test",
        )

        # Try to create duplicate (should fail)
        with pytest.raises(Exception):  # Unique constraint violation
            TagPullStatistics.create(
                repository=self.repo,
                tag_name="unique_test",  # Same tag name for same repo
                tag_pull_count=2,
                last_tag_pull_date=datetime.now(),
                current_manifest_digest="sha256:test2",
            )

        # Create initial manifest statistics
        ManifestPullStatistics.create(
            repository=self.repo,
            manifest_digest="sha256:unique_test",
            manifest_pull_count=1,
            last_manifest_pull_date=datetime.now(),
        )

        # Try to create duplicate (should fail)
        with pytest.raises(Exception):  # Unique constraint violation
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
