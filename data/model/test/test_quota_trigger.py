import pytest
from unittest.mock import patch

from data import model
from data.model.namespacequota import maybe_trigger_quota_notification
from data.model.notification import create_namespace_notification
from data.model.user import get_user

from test.fixtures import *


class TestMaybeTriggerQuotaNotification:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.org = model.organization.get_organization("buynlarge")
        self.user = get_user("devtable")

    def _quota_result(self, severity, threshold=80, usage=800, limit=1000):
        return {
            "severity_level": severity,
            "threshold_percent": threshold,
            "usage_bytes": usage,
            "quota_limit_bytes": limit,
            "limit_bytes": int(limit * threshold / 100),
        }

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_warning_triggers_notification(self, mock_spawn, initialized_db):
        """Warning severity spawns a quota_warning namespace notification."""
        create_namespace_notification(
            self.org, "quota_warning", "quay_notification",
            {"target": {"kind": "user", "name": "public"}}, {},
        )

        quota = self._quota_result("Warning", threshold=80, usage=858993459, limit=1073741824)
        maybe_trigger_quota_notification("buynlarge", quota)

        mock_spawn.assert_called_once()
        call_args = mock_spawn.call_args
        assert call_args[0][0] == "buynlarge"
        assert call_args[0][1] == "quota_warning"
        extra = call_args[1]["extra_data"]
        assert extra["threshold_percent"] == 80
        assert extra["usage_bytes"] == 858993459
        assert extra["limit_bytes"] == 1073741824

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_reject_triggers_error_notification(self, mock_spawn, initialized_db):
        """Reject severity spawns a quota_error namespace notification."""
        quota = self._quota_result("Reject", threshold=100, usage=1200, limit=1000)
        maybe_trigger_quota_notification("buynlarge", quota)

        mock_spawn.assert_called_once()
        assert mock_spawn.call_args[0][1] == "quota_error"

    @patch("features.QUOTA_NOTIFICATIONS", False)
    @patch("notifications.spawn_namespace_notification")
    def test_feature_flag_off_no_notification(self, mock_spawn, initialized_db):
        """No notification when FEATURE_QUOTA_NOTIFICATIONS is disabled."""
        quota = self._quota_result("Warning")
        maybe_trigger_quota_notification("buynlarge", quota)

        mock_spawn.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_no_severity_no_notification(self, mock_spawn, initialized_db):
        """No notification when severity_level is None (under quota)."""
        quota = self._quota_result(None)
        maybe_trigger_quota_notification("buynlarge", quota)

        mock_spawn.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_dedup_prevents_duplicate_within_cooldown(self, mock_spawn, initialized_db):
        """Second call within cooldown does NOT spawn a duplicate notification."""
        quota = self._quota_result("Warning", threshold=80)

        maybe_trigger_quota_notification("buynlarge", quota)
        assert mock_spawn.call_count == 1

        maybe_trigger_quota_notification("buynlarge", quota)
        assert mock_spawn.call_count == 1

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_different_thresholds_independent(self, mock_spawn, initialized_db):
        """Different threshold percents are tracked independently for dedup."""
        quota_80 = self._quota_result("Warning", threshold=80)
        quota_90 = self._quota_result("Warning", threshold=90)

        maybe_trigger_quota_notification("buynlarge", quota_80)
        assert mock_spawn.call_count == 1

        maybe_trigger_quota_notification("buynlarge", quota_90)
        assert mock_spawn.call_count == 2

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_user_namespace_triggers_notification(self, mock_spawn, initialized_db):
        """Notification triggers for user namespaces, not just orgs."""
        quota = self._quota_result("Warning")
        maybe_trigger_quota_notification("devtable", quota)

        mock_spawn.assert_called_once()
        assert mock_spawn.call_args[0][0] == "devtable"

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_nonexistent_namespace_no_crash(self, mock_spawn, initialized_db):
        """Nonexistent namespace doesn't crash — silently returns."""
        quota = self._quota_result("Warning")
        maybe_trigger_quota_notification("nonexistent_ns_xyz", quota)

        mock_spawn.assert_not_called()

    @patch("features.QUOTA_NOTIFICATIONS", True)
    @patch("notifications.spawn_namespace_notification")
    def test_usage_percent_computed_correctly(self, mock_spawn, initialized_db):
        """usage_percent in event data is correctly computed from usage/limit."""
        quota = self._quota_result("Warning", threshold=80, usage=858993459, limit=1073741824)
        maybe_trigger_quota_notification("buynlarge", quota)

        extra = mock_spawn.call_args[1]["extra_data"]
        expected_percent = int(858993459 * 100 / 1073741824)
        assert extra["usage_percent"] == expected_percent
