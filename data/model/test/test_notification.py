import json

import pytest

from data.database import Notification, NotificationKind, User
from data.model.notification import (
    create_notification,
    notification_exists_with_metadata,
)
from data.model.user import get_user
from test.fixtures import *


class TestNotification:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")
        self.test_kind = "quota_warning"

    def test_notification_exists_with_metadata_no_notifications(self, initialized_db):
        """Test that notification_exists_with_metadata returns False when no notifications exist."""
        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert not exists

    def test_notification_exists_with_metadata_no_matching_kind(self, initialized_db):
        """Test that notification_exists_with_metadata returns False when notification kind doesn't match."""
        # Create a notification with different kind
        create_notification("repo_push", self.user, {"repository": "test-repo"})

        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert not exists

    def test_notification_exists_with_metadata_no_matching_metadata(self, initialized_db):
        """Test that notification_exists_with_metadata returns False when metadata doesn't match."""
        # Create a notification with different metadata
        create_notification(
            self.test_kind, self.user, {"repository": "other-repo", "quota_percent": 80}
        )

        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert not exists

    def test_notification_exists_with_metadata_partial_match(self, initialized_db):
        """Test that notification_exists_with_metadata returns False when only part of metadata matches."""
        # Create a notification with partial metadata match
        create_notification(
            self.test_kind, self.user, {"repository": "test-repo", "quota_percent": 90}
        )

        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert not exists

    def test_notification_exists_with_metadata_exact_match(self, initialized_db):
        """Test that notification_exists_with_metadata returns True when exact match exists."""
        # Create a notification with exact metadata match
        create_notification(
            self.test_kind, self.user, {"repository": "test-repo", "quota_percent": 80}
        )

        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert exists

    def test_notification_exists_with_metadata_extra_metadata(self, initialized_db):
        """Test that notification_exists_with_metadata returns True when notification has extra metadata."""
        # Create a notification with more metadata than what we're checking for
        create_notification(
            self.test_kind,
            self.user,
            {"repository": "test-repo", "quota_percent": 80, "extra_field": "extra_value"},
        )

        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert exists

    def test_notification_exists_with_metadata_multiple_notifications(self, initialized_db):
        """Test that notification_exists_with_metadata works correctly with multiple notifications."""
        # Create multiple notifications
        create_notification(self.test_kind, self.user, {"repository": "repo1", "quota_percent": 70})
        create_notification(self.test_kind, self.user, {"repository": "repo2", "quota_percent": 80})
        create_notification(
            self.test_kind, self.user, {"repository": "test-repo", "quota_percent": 80}
        )

        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert exists

    def test_notification_exists_with_metadata_invalid_json(self, initialized_db):
        """Test that notification_exists_with_metadata handles invalid JSON gracefully."""
        # Create a notification directly with invalid JSON
        kind_ref = NotificationKind.get(name=self.test_kind)
        Notification.create(kind=kind_ref, target=self.user, metadata_json="invalid json")

        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo", quota_percent=80
        )
        assert not exists

    def test_notification_exists_with_metadata_empty_metadata(self, initialized_db):
        """Test that notification_exists_with_metadata works with empty metadata."""
        # Create a notification with empty metadata
        create_notification(self.test_kind, self.user, {})

        # Should not match when looking for specific metadata
        exists = notification_exists_with_metadata(
            self.user, self.test_kind, repository="test-repo"
        )
        assert not exists

        # Should match when looking for empty metadata
        exists = notification_exists_with_metadata(self.user, self.test_kind)
        assert exists
