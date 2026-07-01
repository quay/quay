import pytest
from unittest.mock import patch, call

from data import model
from data.database import QuotaNamespaceSize
from data.model.namespacequota import (
    create_namespace_quota,
    create_namespace_quota_limit,
    get_namespace_quota_list,
    maybe_trigger_retroactive_notification,
    maybe_trigger_retroactive_notifications_for_quota,
)
from data.model.user import get_user

from test.fixtures import *


class TestMaybeTriggerRetroactiveNotification:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.org = model.organization.get_organization("buynlarge")
        self.user = get_user("devtable")

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

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_limit_created_above_threshold_fires(self, mock_trigger, initialized_db):
        """Creating a limit at 80% when usage is 85% fires a notification."""
        limit_bytes = 1000
        self._set_namespace_size(self.org, 850)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 80, "Warning")

        maybe_trigger_retroactive_notification("buynlarge", quota, 80, "Warning")

        mock_trigger.assert_called_once()
        args = mock_trigger.call_args
        assert args[0][0] == "buynlarge"
        result = args[0][1]
        assert result["severity_level"] == "Warning"
        assert result["threshold_percent"] == 80
        assert result["usage_bytes"] == 850
        assert result["quota_limit_bytes"] == 1000
        assert result["limit_bytes"] == 800

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_limit_created_under_threshold_no_notification(self, mock_trigger, initialized_db):
        """Creating a limit at 80% when usage is 50% does NOT fire."""
        limit_bytes = 1000
        self._set_namespace_size(self.org, 500)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 80, "Warning")

        maybe_trigger_retroactive_notification("buynlarge", quota, 80, "Warning")

        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_limit_updated_to_lower_threshold_fires(self, mock_trigger, initialized_db):
        """Updating a limit from 90% to 70% when usage is 75% fires."""
        limit_bytes = 1000
        self._set_namespace_size(self.org, 750)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 90, "Warning")

        maybe_trigger_retroactive_notification("buynlarge", quota, 70, "Warning")

        mock_trigger.assert_called_once()
        result = mock_trigger.call_args[0][1]
        assert result["threshold_percent"] == 70

    @patch("features.QUOTA_NOTIFICATIONS", False)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_feature_flag_off_no_notification(self, mock_trigger, initialized_db):
        """No notification when FEATURE_QUOTA_NOTIFICATIONS is disabled."""
        limit_bytes = 1000
        self._set_namespace_size(self.org, 850)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 80, "Warning")

        maybe_trigger_retroactive_notification("buynlarge", quota, 80, "Warning")

        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_reject_threshold_fires_with_reject_severity(self, mock_trigger, initialized_db):
        """Reject-type threshold passes Reject severity to trigger function."""
        limit_bytes = 1000
        self._set_namespace_size(self.org, 1050)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 100, "Reject")

        maybe_trigger_retroactive_notification("buynlarge", quota, 100, "Reject")

        mock_trigger.assert_called_once()
        result = mock_trigger.call_args[0][1]
        assert result["severity_level"] == "Reject"

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_at_exact_threshold_no_notification(self, mock_trigger, initialized_db):
        """Usage exactly at the threshold boundary does NOT fire (needs to exceed)."""
        limit_bytes = 1000
        self._set_namespace_size(self.org, 800)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 80, "Warning")

        maybe_trigger_retroactive_notification("buynlarge", quota, 80, "Warning")

        mock_trigger.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_quota_size_change_reevaluates_all_limits(self, mock_trigger, initialized_db):
        """Changing quota size triggers re-evaluation of all limits."""
        limit_bytes = 2000
        self._set_namespace_size(self.org, 1700)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 80, "Warning")
        create_namespace_quota_limit(quota, "Reject", 90)

        maybe_trigger_retroactive_notifications_for_quota("buynlarge", quota)

        assert mock_trigger.call_count == 2

    @patch("features.QUOTA_NOTIFICATIONS", False)
    @patch("data.model.namespacequota.maybe_trigger_quota_notification")
    def test_quota_size_change_feature_flag_off(self, mock_trigger, initialized_db):
        """Quota size change with feature flag off does nothing."""
        limit_bytes = 2000
        self._set_namespace_size(self.org, 1700)
        quota, _ = self._create_quota_with_limit(self.org, limit_bytes, 80, "Warning")

        maybe_trigger_retroactive_notifications_for_quota("buynlarge", quota)

        mock_trigger.assert_not_called()
