import pytest
from mock import Mock, patch

from data import model
from data.model.organization import delete_contact_email, get_contact_email, set_contact_email
from notifications.models_interface import Notification, Repository
from notifications.notificationevent import NotificationEvent, QuotaWarningEvent
from notifications.notificationmethod import (
    CannotValidateNotificationMethodException,
    EmailMethod,
)

from test.fixtures import *


class TestEmailNamespaceNotifications:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = model.user.get_user("devtable")
        self.org = model.organization.get_organization("buynlarge")
        self.event_handler = NotificationEvent.get_event("quota_warning")
        self.sample_data = self.event_handler.get_sample_data("buynlarge", None, {})
        self.mock_mail = Mock()

    def _make_namespace_notification(self, namespace_name, method_config=None):
        return Notification(
            uuid="fake-ns-uuid",
            event_name="quota_warning",
            method_name="email",
            event_config_dict={},
            method_config_dict=method_config or {},
            repository=Repository(namespace_name, None),
        )

    def _make_repo_notification(self, namespace_name, repo_name, method_config=None):
        return Notification(
            uuid="fake-repo-uuid",
            event_name="repo_push",
            method_name="email",
            event_config_dict={},
            method_config_dict=method_config or {"email": "test@example.com"},
            repository=Repository(namespace_name, repo_name),
        )

    def _perform_with_mock_mail(self, notification, event_handler=None, event_data=None):
        handler = event_handler or self.event_handler
        data = event_data or self.sample_data

        with patch("notifications.notificationmethod.Message") as msg_cls:
            method = EmailMethod()
            method.perform(notification, handler, {"event_data": data, "performer_data": {}})

        return msg_cls

    def test_org_with_contact_email(self, initialized_db):
        """Org namespace with contact_email set sends to that address."""
        set_contact_email(self.org, "ops-team@buynlarge.com")

        notification = self._make_namespace_notification("buynlarge")
        msg_cls = self._perform_with_mock_mail(notification)

        msg_cls.assert_called_once()
        call_args = msg_cls.call_args
        assert call_args[1]["recipients"] == ["ops-team@buynlarge.com"]

    def test_org_without_contact_email_falls_back_to_admins(self, initialized_db):
        """Org namespace without contact_email sends to all org admin emails."""
        delete_contact_email(self.org)
        assert get_contact_email(self.org) is None

        notification = self._make_namespace_notification("buynlarge")
        msg_cls = self._perform_with_mock_mail(notification)

        msg_cls.assert_called_once()
        call_args = msg_cls.call_args
        recipients = call_args[1]["recipients"]
        assert len(recipients) > 0

        admin_users = model.organization.get_admin_users(self.org)
        admin_emails = [u.email for u in admin_users if u.email]
        assert sorted(recipients) == sorted(admin_emails)

    def test_user_namespace_sends_to_user_email(self, initialized_db):
        """User namespace sends to the user's own email."""
        notification = self._make_namespace_notification("devtable")
        sample_data = self.event_handler.get_sample_data("devtable", None, {})

        msg_cls = self._perform_with_mock_mail(notification, event_data=sample_data)

        msg_cls.assert_called_once()
        call_args = msg_cls.call_args
        assert call_args[1]["recipients"] == ["jschorr@devtable.com"]

    def test_repo_notification_unchanged(self, initialized_db):
        """Repo notification still uses the configured email from method_config."""
        notification = self._make_repo_notification(
            "buynlarge", "orgrepo", {"email": "test@example.com"}
        )

        event_handler = NotificationEvent.get_event("repo_push")
        sample_data = event_handler.get_sample_data("buynlarge", "orgrepo", {})

        msg_cls = self._perform_with_mock_mail(
            notification, event_handler=event_handler, event_data=sample_data
        )

        msg_cls.assert_called_once()
        call_args = msg_cls.call_args
        assert call_args[1]["recipients"] == ["test@example.com"]

    def test_validate_namespace_context_skips_confirmation(self, initialized_db):
        """Namespace context (repo_name=None) skips RepositoryAuthorizedEmail check."""
        method = EmailMethod()
        method.validate("buynlarge", None, {"email": "anything@example.com"})

    def test_validate_repo_context_unchanged(self, initialized_db):
        """Repo context still requires RepositoryAuthorizedEmail confirmation."""
        method = EmailMethod()
        with pytest.raises(CannotValidateNotificationMethodException):
            method.validate("devtable", "simple", {"email": "unauthorized@example.com"})

    def test_nonexistent_namespace_no_recipients(self, initialized_db):
        """Namespace notification for a nonexistent namespace sends no email."""
        notification = self._make_namespace_notification("nonexistent_namespace")
        sample_data = self.event_handler.get_sample_data("nonexistent_namespace", None, {})

        with patch("notifications.notificationmethod.Message") as msg_cls:
            method = EmailMethod()
            method.perform(
                notification, self.event_handler, {"event_data": sample_data, "performer_data": {}}
            )

        msg_cls.assert_not_called()
