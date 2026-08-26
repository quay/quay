from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from data.database import QuotaNotificationState
from data.model.quota_notification_state import (
    claim_notification,
    clear_all_for_namespace,
    clear_notification,
    record_notification,
    release_claim,
    should_notify,
)
from data.model.user import get_user
from test.fixtures import *


class TestQuotaNotificationState:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")

    def test_fresh_state_should_notify(self, initialized_db):
        """should_notify returns True for a namespace+threshold with no prior state."""
        assert should_notify(self.user, 80) is True

    def test_after_recording_should_not_notify(self, initialized_db):
        """should_notify returns False immediately after record_notification."""
        record_notification(self.user, 80)
        assert should_notify(self.user, 80) is False

    def test_within_cooldown_should_not_notify(self, initialized_db):
        """should_notify returns False when last_notified_at is within the cooldown window."""
        record_notification(self.user, 80)

        # Set last_notified_at to 1 hour ago (well within 24h default cooldown)
        QuotaNotificationState.update(
            last_notified_at=datetime.utcnow() - timedelta(hours=1)
        ).where(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        ).execute()

        assert should_notify(self.user, 80) is False

    def test_cooldown_expired_should_notify(self, initialized_db):
        """should_notify returns True when last_notified_at is older than the cooldown."""
        record_notification(self.user, 80)

        # Set last_notified_at to 25 hours ago (past 24h default cooldown)
        QuotaNotificationState.update(
            last_notified_at=datetime.utcnow() - timedelta(seconds=86401)
        ).where(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        ).execute()

        assert should_notify(self.user, 80) is True

    def test_cleared_and_cooldown_expired_should_notify(self, initialized_db):
        """After clear_notification + cooldown expired, should_notify returns True (re-exceeded)."""
        record_notification(self.user, 80)
        clear_notification(self.user, 80)

        # Set last_notified_at to 25 hours ago (past cooldown)
        QuotaNotificationState.update(
            last_notified_at=datetime.utcnow() - timedelta(seconds=86401)
        ).where(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        ).execute()

        assert should_notify(self.user, 80) is True

    def test_cleared_within_cooldown_should_notify(self, initialized_db):
        """After clear_notification, should_notify returns True even within cooldown."""
        record_notification(self.user, 80)
        clear_notification(self.user, 80)

        # cleared=True means usage dropped below threshold; re-crossing should re-notify immediately
        assert should_notify(self.user, 80) is True

    def test_drop_below_and_rise_again_cycle(self, initialized_db):
        """Full cycle: record -> clear -> re-notify immediately -> record again."""
        # Step 1: Record notification (usage exceeded threshold)
        record_notification(self.user, 80)
        assert should_notify(self.user, 80) is False

        # Step 2: Clear notification (usage dropped below threshold)
        clear_notification(self.user, 80)

        # Step 3: Usage rises again — cleared flag means immediate re-notification
        assert should_notify(self.user, 80) is True

        # Step 4: Record the new notification
        record_notification(self.user, 80)
        assert should_notify(self.user, 80) is False

    def test_multiple_thresholds_independent(self, initialized_db):
        """Two different threshold_percents for the same namespace are tracked independently."""
        # Record notification for 80% threshold
        record_notification(self.user, 80)

        # 90% threshold should still be eligible
        assert should_notify(self.user, 90) is True
        assert should_notify(self.user, 80) is False

        # Record 90% threshold
        record_notification(self.user, 90)
        assert should_notify(self.user, 90) is False
        assert should_notify(self.user, 80) is False

        # Expire cooldown only for 80%
        QuotaNotificationState.update(
            last_notified_at=datetime.utcnow() - timedelta(seconds=86401)
        ).where(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        ).execute()

        # 80% should be eligible again, 90% should not
        assert should_notify(self.user, 80) is True
        assert should_notify(self.user, 90) is False

    def test_clear_all_for_namespace(self, initialized_db):
        """clear_all_for_namespace deletes all rows; should_notify returns True for all thresholds."""
        # Record notifications for multiple thresholds
        record_notification(self.user, 70)
        record_notification(self.user, 80)
        record_notification(self.user, 90)

        # Verify all are in cooldown
        assert should_notify(self.user, 70) is False
        assert should_notify(self.user, 80) is False
        assert should_notify(self.user, 90) is False

        # Clear all state for the namespace
        clear_all_for_namespace(self.user)

        # All thresholds should be eligible again
        assert should_notify(self.user, 70) is True
        assert should_notify(self.user, 80) is True
        assert should_notify(self.user, 90) is True

    def test_record_notification_upsert_no_duplicates(self, initialized_db):
        """Calling record_notification twice for same namespace+threshold doesn't create duplicates."""
        record_notification(self.user, 80)

        # Expire the cooldown so the second record actually updates
        QuotaNotificationState.update(
            last_notified_at=datetime.utcnow() - timedelta(seconds=86401)
        ).where(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        ).execute()

        record_notification(self.user, 80)

        # Verify only one row exists for this namespace+threshold
        count = (
            QuotaNotificationState.select()
            .where(
                QuotaNotificationState.namespace == self.user,
                QuotaNotificationState.threshold_percent == 80,
            )
            .count()
        )
        assert count == 1

    def test_clear_notification_noop_when_no_row(self, initialized_db):
        """clear_notification is a no-op when no state row exists."""
        clear_notification(self.user, 80)
        count = (
            QuotaNotificationState.select()
            .where(
                QuotaNotificationState.namespace == self.user,
                QuotaNotificationState.threshold_percent == 80,
            )
            .count()
        )
        assert count == 0

    def test_custom_cooldown_config(self, initialized_db):
        """should_notify respects a custom QUOTA_NOTIFICATION_COOLDOWN_SECONDS value."""
        record_notification(self.user, 80)

        # Set last_notified_at to 2 hours ago
        QuotaNotificationState.update(
            last_notified_at=datetime.utcnow() - timedelta(hours=2)
        ).where(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        ).execute()

        # With default 24h cooldown, should NOT notify
        assert should_notify(self.user, 80) is False

        # With 1h cooldown, should notify (2h > 1h)
        with patch("data.model.quota_notification_state.config") as mock_config:
            mock_config.app_config = {"QUOTA_NOTIFICATION_COOLDOWN_SECONDS": 3600}
            assert should_notify(self.user, 80) is True


class TestClaimNotification:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")

    def test_basic_claim_succeeds(self, initialized_db):
        """First claim for a namespace+threshold returns True."""
        assert claim_notification(self.user, 80) is True

    def test_second_claim_within_cooldown_rejected(self, initialized_db):
        """Second claim within cooldown returns False."""
        assert claim_notification(self.user, 80) is True
        assert claim_notification(self.user, 80) is False

    def test_claim_after_cleared_succeeds(self, initialized_db):
        """Claim succeeds after the state has been cleared (usage dropped and rose again)."""
        assert claim_notification(self.user, 80) is True
        clear_notification(self.user, 80)
        assert claim_notification(self.user, 80) is True

    def test_claim_after_cooldown_expired_succeeds(self, initialized_db):
        """Claim succeeds when the previous cooldown has expired."""
        assert claim_notification(self.user, 80) is True

        QuotaNotificationState.update(
            last_notified_at=datetime.utcnow() - timedelta(seconds=86401)
        ).where(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        ).execute()

        assert claim_notification(self.user, 80) is True

    def test_claim_creates_state_row(self, initialized_db):
        """Successful claim creates a QuotaNotificationState row."""
        claim_notification(self.user, 80)

        state = QuotaNotificationState.get_or_none(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        )
        assert state is not None
        assert state.cleared is False
        assert state.last_notified_at is not None


class TestReleaseClaim:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        self.user = get_user("devtable")

    def test_release_claim_deletes_state(self, initialized_db):
        """release_claim removes the state row so the threshold starts fresh."""
        claim_notification(self.user, 80)

        state = QuotaNotificationState.get_or_none(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        )
        assert state is not None

        release_claim(self.user, 80)

        state = QuotaNotificationState.get_or_none(
            QuotaNotificationState.namespace == self.user,
            QuotaNotificationState.threshold_percent == 80,
        )
        assert state is None

    def test_release_claim_allows_reclaim(self, initialized_db):
        """After release_claim, the same namespace+threshold can be claimed again."""
        assert claim_notification(self.user, 80) is True
        release_claim(self.user, 80)
        assert claim_notification(self.user, 80) is True

    def test_release_claim_noop_when_no_state(self, initialized_db):
        """release_claim is a no-op when no state row exists."""
        release_claim(self.user, 80)
