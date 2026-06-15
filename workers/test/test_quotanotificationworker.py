import pytest
from unittest.mock import patch, MagicMock

from data import model
from data.database import (
    NamespaceNotification,
    QuotaLimits,
    QuotaNamespaceSize,
    QuotaNotificationState,
    ExternalNotificationEvent,
    ExternalNotificationMethod,
    UserOrganizationQuota,
)
from data.model.namespacequota import (
    create_namespace_quota,
    create_namespace_quota_limit,
    get_namespace_quota_list,
)
from data.model.user import get_user
from data.model.quota_notification_state import record_notification

from test.fixtures import *
from workers.quotanotificationworker import QuotaNotificationWorker


class TestQuotaNotificationWorker:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.org = model.organization.get_organization("buynlarge")
        self.user = get_user("devtable")
        self.worker = QuotaNotificationWorker()

        QuotaNotificationState.delete().execute()
        NamespaceNotification.delete().execute()
        QuotaLimits.delete().execute()
        UserOrganizationQuota.delete().execute()

    def _set_namespace_size(self, namespace_user, size_bytes):
        QuotaNamespaceSize.delete().where(
            QuotaNamespaceSize.namespace_user == namespace_user,
        ).execute()
        QuotaNamespaceSize.create(
            namespace_user=namespace_user,
            size_bytes=size_bytes,
            backfill_start_ms=1,
            backfill_complete=True,
        )

    def _create_quota_with_limit(self, namespace_user, limit_bytes, threshold, quota_type):
        from data.model.namespacequota import update_namespace_quota_size

        quotas = get_namespace_quota_list(namespace_user.username)
        if quotas:
            quota = quotas[0]
            if quota.limit_bytes != limit_bytes:
                update_namespace_quota_size(quota, limit_bytes)
        else:
            quota = create_namespace_quota(namespace_user, limit_bytes)
        limit = create_namespace_quota_limit(quota, quota_type, threshold)
        return quota, limit

    def _create_namespace_notification(self, namespace_user, event_name="quota_warning"):
        event = ExternalNotificationEvent.get(ExternalNotificationEvent.name == event_name)
        method = ExternalNotificationMethod.select().first()
        return NamespaceNotification.create(
            namespace=namespace_user,
            event=event,
            method=method,
            config_json="{}",
            event_config_json="{}",
            title="test notification",
        )

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_namespace_over_threshold_fires(self, mock_trigger, initialized_db):
        """Namespace exceeding threshold fires a notification."""
        self._set_namespace_size(self.org, 850)
        self._create_quota_with_limit(self.org, 1000, 80, "Warning")
        self._create_namespace_notification(self.org)

        self.worker._check_quotas()

        mock_trigger.assert_called_once()
        args = mock_trigger.call_args
        assert args[0][0] == "buynlarge"
        result = args[0][1]
        assert result["severity_level"] == "Warning"
        assert result["threshold_percent"] == 80
        assert result["usage_bytes"] == 850

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_namespace_under_threshold_no_notification(self, mock_trigger, initialized_db):
        """Namespace under threshold does NOT fire a notification."""
        self._set_namespace_size(self.org, 500)
        self._create_quota_with_limit(self.org, 1000, 80, "Warning")
        self._create_namespace_notification(self.org)

        self.worker._check_quotas()

        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_dropped_below_threshold_clears_state(self, mock_trigger, initialized_db):
        """Usage dropping below a previously-notified threshold clears dedup state."""
        self._set_namespace_size(self.org, 500)
        self._create_quota_with_limit(self.org, 1000, 80, "Warning")
        self._create_namespace_notification(self.org)

        record_notification(self.org, 80)

        state = QuotaNotificationState.get(
            QuotaNotificationState.namespace == self.org,
            QuotaNotificationState.threshold_percent == 80,
        )
        assert state.cleared is False

        self.worker._check_quotas()

        state = QuotaNotificationState.get(
            QuotaNotificationState.namespace == self.org,
            QuotaNotificationState.threshold_percent == 80,
        )
        assert state.cleared is True
        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", False)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_feature_flag_off_skips(self, mock_trigger, initialized_db):
        """Worker skips entirely when FEATURE_QUOTA_NOTIFICATIONS is disabled."""
        self._set_namespace_size(self.org, 850)
        self._create_quota_with_limit(self.org, 1000, 80, "Warning")
        self._create_namespace_notification(self.org)

        self.worker._check_quotas()

        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_no_notification_config_skips(self, mock_trigger, initialized_db):
        """Namespace with quota but no NamespaceNotification config is not checked."""
        self._set_namespace_size(self.org, 850)
        self._create_quota_with_limit(self.org, 1000, 80, "Warning")

        self.worker._check_quotas()

        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_no_quota_skips(self, mock_trigger, initialized_db):
        """Namespace with notification config but no quota is skipped."""
        self._create_namespace_notification(self.org)

        self.worker._check_quotas()

        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_multiple_limits_checked(self, mock_trigger, initialized_db):
        """Worker checks all limits on a namespace and fires for each exceeded threshold."""
        self._set_namespace_size(self.org, 950)
        quota, _ = self._create_quota_with_limit(self.org, 1000, 80, "Warning")
        create_namespace_quota_limit(quota, "Reject", 90)
        self._create_namespace_notification(self.org)

        self.worker._check_quotas()

        assert mock_trigger.call_count == 2
        thresholds = {call.args[1]["threshold_percent"] for call in mock_trigger.call_args_list}
        assert thresholds == {80, 90}

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("workers.quotanotificationworker.maybe_trigger_quota_notification")
    def test_reject_type_fires_with_reject_severity(self, mock_trigger, initialized_db):
        """Reject-type threshold passes Reject severity."""
        self._set_namespace_size(self.org, 1050)
        self._create_quota_with_limit(self.org, 1000, 100, "Reject")
        self._create_namespace_notification(self.org)

        self.worker._check_quotas()

        mock_trigger.assert_called_once()
        result = mock_trigger.call_args[0][1]
        assert result["severity_level"] == "Reject"
