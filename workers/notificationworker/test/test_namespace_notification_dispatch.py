import json

import pytest
from httmock import HTTMock, urlmatch
from mock import Mock, patch

from data import model
from data.model.notification import (
    create_namespace_notification,
    increment_namespace_notification_failure_count,
)
from notifications.notificationevent import QuotaWarningEvent
from workers.notificationworker.models_pre_oci import pre_oci_model
from workers.notificationworker.notificationworker import NotificationWorker

from test.fixtures import *


class TestNamespaceNotificationDispatch:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = model.user.get_user("devtable")
        self.org = model.organization.get_organization("buynlarge")

    def _create_namespace_notification(self, namespace_user, method_name, method_config):
        return create_namespace_notification(
            namespace_user,
            "quota_warning",
            method_name,
            method_config,
            {},
        )

    def test_namespace_quay_notification_dispatch(self, initialized_db):
        """Namespace notification dispatches via quay_notification method end-to-end."""
        assert not pre_oci_model.user_has_local_notifications("public")

        notif = self._create_namespace_notification(
            self.org,
            "quay_notification",
            {"target": {"kind": "user", "name": "public"}},
        )

        event_data = QuotaWarningEvent().get_sample_data("buynlarge", None, {})

        worker = NotificationWorker(None)
        worker.process_queue_item(
            {
                "notification_uuid": notif.uuid,
                "event_data": event_data,
                "performer_data": {},
                "notification_type": "namespace",
            }
        )

        assert pre_oci_model.user_has_local_notifications("public")

    def test_namespace_webhook_dispatch(self, initialized_db):
        """Namespace notification dispatches via webhook method."""
        url_hit = [False]

        @urlmatch(netloc="example.com")
        def url_handler(_, __):
            url_hit[0] = True
            return ""

        notif = self._create_namespace_notification(
            self.org,
            "webhook",
            {"url": "http://example.com"},
        )

        event_data = QuotaWarningEvent().get_sample_data("buynlarge", None, {})

        with HTTMock(url_handler):
            worker = NotificationWorker(None)
            worker.process_queue_item(
                {
                    "notification_uuid": notif.uuid,
                    "event_data": event_data,
                    "performer_data": {},
                    "notification_type": "namespace",
                }
            )

        assert url_hit[0]

    def test_namespace_slack_dispatch(self, initialized_db):
        """Namespace notification dispatches via Slack method."""
        url_hit = [False]

        @urlmatch(netloc="hooks.slack.com")
        def url_handler(_, __):
            url_hit[0] = True
            return ""

        notif = self._create_namespace_notification(
            self.org,
            "slack",
            {"url": "http://hooks.slack.com/services/test"},
        )

        event_data = QuotaWarningEvent().get_sample_data("buynlarge", None, {})

        with HTTMock(url_handler):
            worker = NotificationWorker(None)
            worker.process_queue_item(
                {
                    "notification_uuid": notif.uuid,
                    "event_data": event_data,
                    "performer_data": {},
                    "notification_type": "namespace",
                }
            )

        assert url_hit[0]

    def test_repo_notification_still_works(self, initialized_db):
        """Existing repo notifications are unaffected by the namespace dispatch changes."""
        assert not pre_oci_model.user_has_local_notifications("public")

        notification_uuid = pre_oci_model.create_notification_for_testing("public")

        worker = NotificationWorker(None)
        worker.process_queue_item(
            {
                "notification_uuid": notification_uuid,
                "event_data": {},
            }
        )

        assert pre_oci_model.user_has_local_notifications("public")

    def test_repo_notification_with_explicit_type(self, initialized_db):
        """Repo notification with explicit notification_type='repo' works."""
        assert not pre_oci_model.user_has_local_notifications("public")

        notification_uuid = pre_oci_model.create_notification_for_testing("public")

        worker = NotificationWorker(None)
        worker.process_queue_item(
            {
                "notification_uuid": notification_uuid,
                "event_data": {},
                "notification_type": "repo",
            }
        )

        assert pre_oci_model.user_has_local_notifications("public")

    def test_disabled_namespace_notification_skipped(self, initialized_db):
        """Namespace notification with 3+ failures is skipped (not delivered)."""
        notif = self._create_namespace_notification(
            self.org,
            "quay_notification",
            {"target": {"kind": "user", "name": "public"}},
        )

        for _ in range(3):
            increment_namespace_notification_failure_count(notif.uuid)

        assert not pre_oci_model.user_has_local_notifications("public")

        worker = NotificationWorker(None)
        worker.process_queue_item(
            {
                "notification_uuid": notif.uuid,
                "event_data": QuotaWarningEvent().get_sample_data("buynlarge", None, {}),
                "performer_data": {},
                "notification_type": "namespace",
            }
        )

        assert not pre_oci_model.user_has_local_notifications("public")

    def test_nonexistent_namespace_notification_skipped(self, initialized_db):
        """A namespace notification with a bogus UUID is silently skipped."""
        worker = NotificationWorker(None)
        worker.process_queue_item(
            {
                "notification_uuid": "nonexistent-uuid-1234",
                "event_data": {},
                "performer_data": {},
                "notification_type": "namespace",
            }
        )

    def test_failure_count_incremented_on_error(self, initialized_db):
        """Namespace notification failure count is incremented when delivery fails."""
        notif = self._create_namespace_notification(
            self.org,
            "webhook",
            {"url": "http://example.com/fail"},
        )

        @urlmatch(netloc="example.com")
        def url_handler(_, __):
            return {"status_code": 500, "content": "error"}

        event_data = QuotaWarningEvent().get_sample_data("buynlarge", None, {})

        with HTTMock(url_handler):
            worker = NotificationWorker(None)
            with pytest.raises(Exception):
                worker.process_queue_item(
                    {
                        "notification_uuid": notif.uuid,
                        "event_data": event_data,
                        "performer_data": {},
                        "notification_type": "namespace",
                    }
                )

        from data.database import NamespaceNotification as NamespaceNotificationDB

        updated = NamespaceNotificationDB.get(NamespaceNotificationDB.uuid == notif.uuid)
        assert updated.number_of_failures == 1

    def test_failure_count_reset_on_success(self, initialized_db):
        """Namespace notification failure count is reset to 0 after successful delivery."""
        notif = self._create_namespace_notification(
            self.org,
            "quay_notification",
            {"target": {"kind": "user", "name": "public"}},
        )

        increment_namespace_notification_failure_count(notif.uuid)

        from data.database import NamespaceNotification as NamespaceNotificationDB

        updated = NamespaceNotificationDB.get(NamespaceNotificationDB.uuid == notif.uuid)
        assert updated.number_of_failures == 1

        event_data = QuotaWarningEvent().get_sample_data("buynlarge", None, {})

        worker = NotificationWorker(None)
        worker.process_queue_item(
            {
                "notification_uuid": notif.uuid,
                "event_data": event_data,
                "performer_data": {},
                "notification_type": "namespace",
            }
        )

        updated = NamespaceNotificationDB.get(NamespaceNotificationDB.uuid == notif.uuid)
        assert updated.number_of_failures == 0
