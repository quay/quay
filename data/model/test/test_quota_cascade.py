import pytest

from data.database import (
    NamespaceNotification,
    QuotaNotificationState,
)
from data.model.namespacequota import (
    create_namespace_quota,
    create_namespace_quota_limit,
    delete_namespace_quota,
    delete_namespace_quota_limit,
    get_namespace_quota_limit_list,
    get_namespace_quota_list,
)
from data.model.notification import create_namespace_notification
from data.model.organization import create_organization
from data.model.quota_notification_state import record_notification, should_notify
from data.model.user import get_user
from test.fixtures import *


class TestDeleteQuotaLimitCascade:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")
        self.org = create_organization("cascade-org", "cascade@test.com", self.user)
        self.quota = create_namespace_quota(self.org, 1000000000)
        self.limit = create_namespace_quota_limit(self.quota, "Warning", 80)

    def test_deleting_limit_removes_matching_dedup_state(self, initialized_db):
        record_notification(self.org, 80)
        assert should_notify(self.org, 80) is False

        delete_namespace_quota_limit(self.limit)

        assert should_notify(self.org, 80) is True
        count = QuotaNotificationState.select().where(
            QuotaNotificationState.namespace == self.org,
            QuotaNotificationState.threshold_percent == 80,
        ).count()
        assert count == 0

    def test_deleting_limit_preserves_other_thresholds(self, initialized_db):
        limit_90 = create_namespace_quota_limit(self.quota, "Reject", 90)
        record_notification(self.org, 80)
        record_notification(self.org, 90)

        delete_namespace_quota_limit(self.limit)

        assert should_notify(self.org, 80) is True
        assert should_notify(self.org, 90) is False

    def test_deleting_limit_without_dedup_state_succeeds(self, initialized_db):
        delete_namespace_quota_limit(self.limit)

        limits = get_namespace_quota_limit_list(self.quota)
        assert len(limits) == 0

    def test_recreated_threshold_starts_fresh(self, initialized_db):
        record_notification(self.org, 80)
        assert should_notify(self.org, 80) is False

        delete_namespace_quota_limit(self.limit)
        new_limit = create_namespace_quota_limit(self.quota, "Warning", 80)

        assert should_notify(self.org, 80) is True


class TestDeleteQuotaCascade:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")
        self.org = create_organization("cascade-quota-org", "cascadeq@test.com", self.user)
        self.quota = create_namespace_quota(self.org, 1000000000)
        create_namespace_quota_limit(self.quota, "Warning", 70)
        create_namespace_quota_limit(self.quota, "Warning", 80)
        create_namespace_quota_limit(self.quota, "Reject", 90)

    def test_deleting_quota_removes_all_dedup_state(self, initialized_db):
        record_notification(self.org, 70)
        record_notification(self.org, 80)
        record_notification(self.org, 90)

        delete_namespace_quota(self.quota)

        assert should_notify(self.org, 70) is True
        assert should_notify(self.org, 80) is True
        assert should_notify(self.org, 90) is True
        count = QuotaNotificationState.select().where(
            QuotaNotificationState.namespace == self.org,
        ).count()
        assert count == 0

    def test_deleting_quota_removes_namespace_notifications(self, initialized_db):
        create_namespace_notification(
            self.org, "quota_warning", "webhook", '{"url":"http://example.com"}', "{}"
        )
        create_namespace_notification(
            self.org, "quota_error", "email", '{"email":"a@b.com"}', "{}"
        )

        before = NamespaceNotification.select().where(
            NamespaceNotification.namespace == self.org,
        ).count()
        assert before == 2

        delete_namespace_quota(self.quota)

        after = NamespaceNotification.select().where(
            NamespaceNotification.namespace == self.org,
        ).count()
        assert after == 0

    def test_deleting_quota_preserves_other_namespace_state(self, initialized_db):
        other_user = get_user("public")
        other_org = create_organization("other-cascade-org", "other@test.com", other_user)
        other_quota = create_namespace_quota(other_org, 500000000)
        create_namespace_quota_limit(other_quota, "Warning", 80)
        record_notification(other_org, 80)
        create_namespace_notification(
            other_org, "quota_warning", "webhook", '{"url":"http://other.com"}', "{}"
        )

        record_notification(self.org, 80)

        delete_namespace_quota(self.quota)

        assert should_notify(other_org, 80) is False
        other_notif_count = NamespaceNotification.select().where(
            NamespaceNotification.namespace == other_org,
        ).count()
        assert other_notif_count == 1

    def test_deleting_quota_also_removes_limits(self, initialized_db):
        delete_namespace_quota(self.quota)

        quotas = get_namespace_quota_list(self.org.username)
        assert len(quotas) == 0

    def test_recreated_quota_starts_with_fresh_state(self, initialized_db):
        record_notification(self.org, 80)

        delete_namespace_quota(self.quota)

        new_quota = create_namespace_quota(self.org, 2000000000)
        create_namespace_quota_limit(new_quota, "Warning", 80)

        assert should_notify(self.org, 80) is True
        notif_count = NamespaceNotification.select().where(
            NamespaceNotification.namespace == self.org,
        ).count()
        assert notif_count == 0
