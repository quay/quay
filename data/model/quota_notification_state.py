import logging
from datetime import datetime, timedelta

from peewee import IntegrityError

from data.database import QuotaNotificationState
from data.model import config, db_transaction

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 86400


def _get_cooldown_seconds():
    if config.app_config is None:
        return DEFAULT_COOLDOWN_SECONDS
    return config.app_config.get("QUOTA_NOTIFICATION_COOLDOWN_SECONDS", DEFAULT_COOLDOWN_SECONDS)


def claim_notification(namespace_user, threshold_percent):
    """
    Atomically claims the right to send a notification for this namespace + threshold.

    Returns True if the caller won the claim and should proceed to enqueue.
    Returns False if another caller already claimed it or cooldown hasn't expired.

    On success the state row is created/updated with cleared=False and last_notified_at=now,
    so concurrent callers that race on the same slot will lose.
    """
    now = datetime.utcnow()
    cooldown = timedelta(seconds=_get_cooldown_seconds())
    cutoff = now - cooldown

    with db_transaction():
        state = QuotaNotificationState.get_or_none(
            QuotaNotificationState.namespace == namespace_user,
            QuotaNotificationState.threshold_percent == threshold_percent,
        )

        if state is None:
            try:
                QuotaNotificationState.create(
                    namespace=namespace_user,
                    threshold_percent=threshold_percent,
                    last_notified_at=now,
                    cleared=False,
                )
                return True
            except IntegrityError:
                return False

        if (
            not state.cleared
            and state.last_notified_at is not None
            and state.last_notified_at > cutoff
        ):
            return False

        updated = (
            QuotaNotificationState.update(last_notified_at=now, cleared=False)
            .where(
                QuotaNotificationState.id == state.id,
                QuotaNotificationState.last_notified_at == state.last_notified_at,
                QuotaNotificationState.cleared == state.cleared,
            )
            .execute()
        )
        return updated > 0


def release_claim(namespace_user, threshold_percent):
    """
    Reverts a successful claim when no notifications were actually enqueued.
    Deletes the state row so the threshold starts fresh when a channel is later created.
    """
    QuotaNotificationState.delete().where(
        QuotaNotificationState.namespace == namespace_user,
        QuotaNotificationState.threshold_percent == threshold_percent,
    ).execute()


def should_notify(namespace_user, threshold_percent):
    """
    Read-only check: returns True if a notification is eligible for this namespace + threshold.
    Used by the background worker and tests. The push path should use claim_notification() instead.
    """
    state = QuotaNotificationState.get_or_none(
        QuotaNotificationState.namespace == namespace_user,
        QuotaNotificationState.threshold_percent == threshold_percent,
    )

    if state is None:
        return True

    if state.cleared:
        return True

    if state.last_notified_at is None:
        return True

    cooldown = timedelta(seconds=_get_cooldown_seconds())
    return datetime.utcnow() >= state.last_notified_at + cooldown


def record_notification(namespace_user, threshold_percent):
    """
    Creates or updates the state row: sets cleared=False, last_notified_at=now.
    Used by the background worker and tests. The push path should use claim_notification() instead.
    """
    now = datetime.utcnow()

    with db_transaction():
        state = QuotaNotificationState.get_or_none(
            QuotaNotificationState.namespace == namespace_user,
            QuotaNotificationState.threshold_percent == threshold_percent,
        )

        if state is None:
            QuotaNotificationState.create(
                namespace=namespace_user,
                threshold_percent=threshold_percent,
                last_notified_at=now,
                cleared=False,
            )
        else:
            state.last_notified_at = now
            state.cleared = False
            state.save()


def clear_notification(namespace_user, threshold_percent):
    """
    Sets cleared=True for the matching row. No-op if no row exists.
    """
    QuotaNotificationState.update(cleared=True).where(
        QuotaNotificationState.namespace == namespace_user,
        QuotaNotificationState.threshold_percent == threshold_percent,
    ).execute()


def clear_all_for_namespace(namespace_user):
    """
    Deletes all QuotaNotificationState rows for the given namespace.
    """
    QuotaNotificationState.delete().where(
        QuotaNotificationState.namespace == namespace_user,
    ).execute()
