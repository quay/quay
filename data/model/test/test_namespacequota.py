from unittest.mock import MagicMock, patch

import pytest

from data.database import Notification
from data.model.namespacequota import notify_organization_admins
from data.model.notification import (
    create_notification,
    notification_exists_with_metadata,
)
from data.model.organization import create_organization
from data.model.user import get_user
from notifications.models_interface import Repository
from test.fixtures import *


class TestNamespaceQuota:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")
        self.org_name = "test-org"
        self.repo_name = "test-repo"
        self.org = create_organization(self.org_name, f"{self.org_name}@devtable.com", self.user)
        self.repository_ref = Repository(namespace_name=self.org_name, name=self.repo_name)
        self.notification_kind = "quota_warning"
        self.metadata = {"quota_percent": 80}

    def test_notify_organization_admins_user_namespace_no_existing_notification(
        self, initialized_db
    ):
        """Test notification creation for user namespace when no notification exists."""
        user_repo_ref = Repository(namespace_name=self.user.username, name=self.repo_name)

        # Verify no notifications exist before
        assert not notification_exists_with_metadata(
            self.user, self.notification_kind, namespace=self.user.username, quota_percent=80
        )

        notify_organization_admins(user_repo_ref, self.notification_kind, self.metadata)

        # Verify notification was created
        assert notification_exists_with_metadata(
            self.user, self.notification_kind, namespace=self.user.username, quota_percent=80
        )

    def test_notify_organization_admins_user_namespace_existing_notification(self, initialized_db):
        """Test no duplicate notification creation for user namespace when notification exists."""
        user_repo_ref = Repository(namespace_name=self.user.username, name=self.repo_name)

        # Create existing notification
        create_notification(
            self.notification_kind, self.user, {"namespace": self.user.username, **self.metadata}
        )

        # Count notifications before
        notifications_before = Notification.select().where(Notification.target == self.user).count()

        notify_organization_admins(user_repo_ref, self.notification_kind, self.metadata)

        # Count notifications after - should be the same
        notifications_after = Notification.select().where(Notification.target == self.user).count()

        assert notifications_before == notifications_after

    @patch("data.model.organization.get_admin_users")
    def test_notify_organization_admins_org_namespace_no_existing_notifications(
        self, mock_get_admin_users, initialized_db
    ):
        """Test notification creation for organization admins when no notifications exist."""
        # Mock admin users
        admin1 = get_user("devtable")
        admin2 = get_user("public")  # Assuming this user exists in fixtures
        mock_get_admin_users.return_value = [admin1, admin2]

        # Verify no notifications exist before
        for admin in [admin1, admin2]:
            assert not notification_exists_with_metadata(
                admin, self.notification_kind, namespace=self.org_name, quota_percent=80
            )

        notify_organization_admins(self.repository_ref, self.notification_kind, self.metadata)

        # Verify notifications were created for all admins
        for admin in [admin1, admin2]:
            assert notification_exists_with_metadata(
                admin, self.notification_kind, namespace=self.org_name, quota_percent=80
            )

    @patch("data.model.organization.get_admin_users")
    def test_notify_organization_admins_org_namespace_partial_existing_notifications(
        self, mock_get_admin_users, initialized_db
    ):
        """Test notification creation when some admins already have notifications."""
        # Mock admin users
        admin1 = get_user("devtable")
        admin2 = get_user("public")
        mock_get_admin_users.return_value = [admin1, admin2]

        # Create notification for only one admin
        create_notification(
            self.notification_kind, admin1, {"namespace": self.org_name, **self.metadata}
        )

        # Count notifications before
        admin1_notifications_before = (
            Notification.select().where(Notification.target == admin1).count()
        )
        admin2_notifications_before = (
            Notification.select().where(Notification.target == admin2).count()
        )

        notify_organization_admins(self.repository_ref, self.notification_kind, self.metadata)

        # Count notifications after
        admin1_notifications_after = (
            Notification.select().where(Notification.target == admin1).count()
        )
        admin2_notifications_after = (
            Notification.select().where(Notification.target == admin2).count()
        )

        # Admin1 should have same number (no new notification)
        assert admin1_notifications_before == admin1_notifications_after

        # Admin2 should have one more notification
        assert admin2_notifications_after == admin2_notifications_before + 1

        # Verify admin2 now has the notification
        assert notification_exists_with_metadata(
            admin2, self.notification_kind, namespace=self.org_name, quota_percent=80
        )

    @patch("data.model.organization.get_admin_users")
    def test_notify_organization_admins_org_namespace_all_existing_notifications(
        self, mock_get_admin_users, initialized_db
    ):
        """Test no duplicate notifications when all admins already have notifications."""
        # Mock admin users
        admin1 = get_user("devtable")
        admin2 = get_user("public")
        mock_get_admin_users.return_value = [admin1, admin2]

        # Create notifications for all admins
        for admin in [admin1, admin2]:
            create_notification(
                self.notification_kind, admin, {"namespace": self.org_name, **self.metadata}
            )

        # Count total notifications before
        total_notifications_before = Notification.select().count()

        notify_organization_admins(self.repository_ref, self.notification_kind, self.metadata)

        # Count total notifications after - should be the same
        total_notifications_after = Notification.select().count()

        assert total_notifications_before == total_notifications_after

    def test_notify_organization_admins_metadata_is_updated_with_namespace(self, initialized_db):
        """Test that metadata is properly updated with namespace information."""
        user_repo_ref = Repository(namespace_name=self.user.username, name=self.repo_name)
        original_metadata = {"quota_percent": 80, "other_field": "value"}

        notify_organization_admins(user_repo_ref, self.notification_kind, original_metadata)

        # Verify the notification was created with namespace added to metadata
        assert notification_exists_with_metadata(
            self.user,
            self.notification_kind,
            namespace=self.user.username,
            quota_percent=80,
            other_field="value",
        )

    def test_notify_organization_admins_invalid_namespace(self, initialized_db):
        """Test that function raises InvalidUsernameException for non-existent namespace."""
        from data.model import InvalidUsernameException

        invalid_repo_ref = Repository(namespace_name="nonexistent-namespace", name=self.repo_name)

        with pytest.raises(InvalidUsernameException) as exc_info:
            notify_organization_admins(invalid_repo_ref, self.notification_kind, self.metadata)

        assert "Namespace 'nonexistent-namespace' does not exist" in str(exc_info.value)

    @patch("data.model.organization.get_admin_users")
    def test_notify_organization_admins_empty_admin_list(
        self, mock_get_admin_users, initialized_db
    ):
        """Test behavior when organization has no admin users."""
        # Mock empty admin list
        mock_get_admin_users.return_value = []

        # Count notifications before
        notifications_before = Notification.select().count()

        notify_organization_admins(self.repository_ref, self.notification_kind, self.metadata)

        # Count notifications after - should be the same (no new notifications)
        notifications_after = Notification.select().count()

        assert notifications_before == notifications_after

    def test_notify_organization_admins_different_metadata_creates_new_notification(
        self, initialized_db
    ):
        """Test that notifications with different metadata are treated as different."""
        user_repo_ref = Repository(namespace_name=self.user.username, name=self.repo_name)

        # Create notification with different metadata
        create_notification(
            self.notification_kind,
            self.user,
            {"namespace": self.user.username, "quota_percent": 90},
        )

        # Count notifications before
        notifications_before = Notification.select().where(Notification.target == self.user).count()

        # Send notification with different metadata
        notify_organization_admins(user_repo_ref, self.notification_kind, {"quota_percent": 80})

        # Count notifications after - should be one more
        notifications_after = Notification.select().where(Notification.target == self.user).count()

        assert notifications_after == notifications_before + 1
